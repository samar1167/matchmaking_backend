from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import (
    UserProfile, UserMatchPreference, PrivatePerson, CompatibilityScore, CompatibilityParameter,
    PaymentRecord, UserPlan, AuthActionToken,
)

User = get_user_model()

MAX_PROFILE_PICTURE_BYTES = 4 * 1024 * 1024
ALLOWED_PROFILE_PICTURE_TYPES = {'image/jpeg', 'image/png', 'image/webp'}
MIN_PROFILE_PICTURE_DIMENSION = 300
MAX_PROFILE_PICTURE_DIMENSION = 3000
MIN_PROFILE_PICTURE_ASPECT_RATIO = 0.67
MAX_PROFILE_PICTURE_ASPECT_RATIO = 1.5

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    email = serializers.EmailField()

    class Meta:
        model = User
        fields = ('id', 'email', 'password')

    def validate_email(self, value):
        email = value.strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("A user with that email already exists.")
        return email

    def create(self, validated_data):
        email = validated_data['email']
        return User.objects.create_user(
            username=email,
            email=email,
            password=validated_data['password'],
            is_active=False,
        )

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name')


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = 'email'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'] = serializers.EmailField()
        self.fields['password'] = serializers.CharField(write_only=True)
        self.fields.pop('username', None)

    def validate(self, attrs):
        email = attrs.get('email', '').strip().lower()
        password = attrs.get('password')
        request = self.context.get('request')

        self.user = authenticate(request=request, username=email, password=password)
        if not self.user:
            user = User.objects.filter(email__iexact=email).first()
            if user and not user.is_active:
                raise AuthenticationFailed('Email verification is required before login.')
            raise AuthenticationFailed('No active account found with the given credentials.')

        refresh = self.get_token(self.user)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }


class VerifyEmailSerializer(serializers.Serializer):
    token = serializers.CharField()

    def validate(self, attrs):
        token = attrs['token'].strip()
        record = AuthActionToken.objects.filter(
            token=token,
            purpose=AuthActionToken.PURPOSE_EMAIL_VERIFICATION,
        ).select_related('user').first()
        if not record or not record.is_usable:
            raise serializers.ValidationError({'token': 'Invalid or expired verification token.'})
        attrs['record'] = record
        return attrs


class EmailAddressSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        return value.strip().lower()


class ResetPasswordSerializer(serializers.Serializer):
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        token = attrs['token'].strip()
        record = AuthActionToken.objects.filter(
            token=token,
            purpose=AuthActionToken.PURPOSE_PASSWORD_RESET,
        ).select_related('user').first()
        if not record or not record.is_usable:
            raise serializers.ValidationError({'token': 'Invalid or expired reset token.'})

        try:
            validate_password(attrs['new_password'], record.user)
        except Exception as exc:
            raise serializers.ValidationError({'new_password': list(exc)}) from exc

        attrs['record'] = record
        return attrs

class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    first_name = serializers.CharField(max_length=150, write_only=True, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, write_only=True, required=False, allow_blank=True)

    class Meta:
        model = UserProfile
        fields = (
            'id',
            'user',
            'first_name',
            'last_name',
            'date_of_birth',
            'time_of_birth',
            'place_of_birth',
            'latitude',
            'longitude',
            'timezone',
            'profile_picture',
            'public_match',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'user', 'created_at', 'updated_at')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['first_name'] = instance.user.first_name
        data['last_name'] = instance.user.last_name
        return data

    def validate_first_name(self, value):
        value = value.strip()
        return value

    def validate_last_name(self, value):
        value = value.strip()
        return value

    def validate_profile_picture(self, value):
        if not value:
            return value

        if value.size > MAX_PROFILE_PICTURE_BYTES:
            raise serializers.ValidationError('Profile picture must be 4 MB or smaller.')

        content_type = getattr(value, 'content_type', None)
        if content_type not in ALLOWED_PROFILE_PICTURE_TYPES:
            raise serializers.ValidationError('Profile picture must be a JPEG, PNG, or WebP image.')

        width = getattr(value, 'image', None).width if getattr(value, 'image', None) else None
        height = getattr(value, 'image', None).height if getattr(value, 'image', None) else None
        if not width or not height:
            raise serializers.ValidationError('Uploaded file is not a valid image.')

        if width < MIN_PROFILE_PICTURE_DIMENSION or height < MIN_PROFILE_PICTURE_DIMENSION:
            raise serializers.ValidationError('Profile picture must be at least 300x300 pixels.')

        if width > MAX_PROFILE_PICTURE_DIMENSION or height > MAX_PROFILE_PICTURE_DIMENSION:
            raise serializers.ValidationError('Profile picture must be at most 3000x3000 pixels.')

        aspect_ratio = width / height
        if not (MIN_PROFILE_PICTURE_ASPECT_RATIO <= aspect_ratio <= MAX_PROFILE_PICTURE_ASPECT_RATIO):
            raise serializers.ValidationError('Profile picture must be roughly square or portrait-oriented.')

        return value

    def create(self, validated_data):
        user_data = {
            'first_name': validated_data.pop('first_name', None),
            'last_name': validated_data.pop('last_name', None),
        }
        profile = UserProfile.objects.create(**validated_data)
        self._update_user(profile.user, user_data)
        return profile

    def update(self, instance, validated_data):
        user_data = {}
        if 'first_name' in validated_data:
            user_data['first_name'] = validated_data.pop('first_name')
        if 'last_name' in validated_data:
            user_data['last_name'] = validated_data.pop('last_name')
        self._update_user(instance.user, user_data)
        return super().update(instance, validated_data)

    def _update_user(self, user, user_data):
        changed_fields = []
        for field in ('first_name', 'last_name'):
            if user_data.get(field) is not None:
                setattr(user, field, user_data[field])
                changed_fields.append(field)

        if changed_fields:
            user.save(update_fields=changed_fields)


class UserMatchPreferenceSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    public_match_criteria = serializers.DictField(read_only=True)
    compatibility_weights = serializers.DictField(read_only=True)

    class Meta:
        model = UserMatchPreference
        fields = (
            'id',
            'user',
            'preferred_gender',
            'preferred_age_min',
            'preferred_age_max',
            'preferred_relationship_intent',
            'preferred_marital_status',
            'modern_methods',
            'karmic_glue',
            'ancient_methods',
            'deal_maker',
            'sizzle',
            'public_match_criteria',
            'compatibility_weights',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'user', 'public_match_criteria', 'compatibility_weights', 'created_at', 'updated_at')

    def validate(self, attrs):
        instance = self.instance
        min_age = attrs.get('preferred_age_min', getattr(instance, 'preferred_age_min', None))
        max_age = attrs.get('preferred_age_max', getattr(instance, 'preferred_age_max', None))

        if min_age is not None and max_age is not None and min_age > max_age:
            raise serializers.ValidationError({
                'preferred_age_min': 'Preferred minimum age cannot be greater than preferred maximum age.'
            })

        return attrs


class PrivatePersonSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrivatePerson
        fields = ('id', 'name', 'nickname', 'notes', 'date_of_birth', 'time_of_birth', 'place_of_birth', 'latitude', 'longitude', 'timezone', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')

class CompatibilityScoreSerializer(serializers.ModelSerializer):
    matched_user_email          = serializers.EmailField(source='matched_user.user.email', read_only=True)
    matched_private_person_name = serializers.CharField(source='matched_private_person.name', read_only=True)
    is_private_match            = serializers.BooleanField(read_only=True)
    class Meta:
        model = CompatibilityScore
        fields = ('id', 'user', 'matched_user', 'matched_user_email', 'matched_private_person', 'matched_private_person_name', 'is_private_match', 'overall_score', 'sun_compatibility', 'moon_compatibility', 'venus_compatibility', 'mars_compatibility', 'description', 'created_at', 'updated_at')
        read_only_fields = ('id', 'api_response', 'created_at', 'updated_at')

class CompatibilityRequestSerializer(serializers.Serializer):
    matched_user_id           = serializers.IntegerField(required=False)
    matched_private_person_id = serializers.IntegerField(required=False)
    force_refresh             = serializers.BooleanField(default=False, required=False)
    def validate(self, data):
        has_user    = bool(data.get('matched_user_id'))
        has_private = bool(data.get('matched_private_person_id'))
        if has_user == has_private:
            raise serializers.ValidationError("Provide exactly one of 'matched_user_id' or 'matched_private_person_id'.")
        return data

class CompatibilityParameterSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompatibilityParameter
        fields = ('key', 'label', 'is_free', 'order')


class UserPlanSerializer(serializers.ModelSerializer):
    total_credits  = serializers.IntegerField(read_only=True)
    is_paid_session = serializers.BooleanField(read_only=True)

    class Meta:
        model = UserPlan
        fields = ('free_credits', 'paid_credits', 'total_credits', 'is_paid_session', 'updated_at')


class PaymentRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentRecord
        fields = ('id', 'amount_usd', 'credits_purchased', 'status', 'payment_reference', 'created_at', 'completed_at')
        read_only_fields = ('id', 'amount_usd', 'credits_purchased', 'status', 'created_at', 'completed_at')


class PurchaseCreditsSerializer(serializers.Serializer):
    """Request body for purchasing paid credits."""
    payment_reference = serializers.CharField(max_length=255,
        help_text="Transaction ID from your payment gateway (Stripe, Razorpay, etc.)")

class ParameterResultSerializer(serializers.Serializer):
    """Single parameter in a compatibility result."""
    key    = serializers.CharField()
    label  = serializers.CharField()
    score  = serializers.FloatField(allow_null=True)
    locked = serializers.BooleanField()


class CompatibilityScoreSerializer(serializers.ModelSerializer):
    matched_user_email           = serializers.EmailField(source='matched_user.user.email', read_only=True)
    matched_private_person_name  = serializers.CharField(source='matched_private_person.name', read_only=True)
    is_private_match             = serializers.BooleanField(read_only=True)
    parameters                   = serializers.SerializerMethodField()
    upgrade_required             = serializers.SerializerMethodField()
    credits_remaining            = serializers.SerializerMethodField()

    class Meta:
        model = CompatibilityScore
        fields = (
            'id', 'user',
            'matched_user', 'matched_user_email',
            'matched_private_person', 'matched_private_person_name',
            'is_private_match',
            'is_paid',
            'overall_score',
            'parameters',          # replaces flat sun/moon/venus/mars fields
            'description',
            'upgrade_required',
            'credits_remaining',
            'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'api_response', 'created_at', 'updated_at')

    def get_parameters(self, obj):
        is_paid = obj.is_paid
        params  = CompatibilityParameter.objects.filter(is_active=True)
        result  = []
        for param in params:
            score = obj.api_response.get(param.key) if obj.api_response else None
            locked = not (param.is_free or is_paid)
            result.append({
                'key':    param.key,
                'label':  param.label,
                'score':  None if locked else score,
                'locked': locked,
            })
        return result

    def get_upgrade_required(self, obj):
        return not obj.is_paid

    def get_credits_remaining(self, obj):
        request = self.context.get('request')
        if request and hasattr(request.user, 'plan'):
            return request.user.plan.total_credits
        return 0
