from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserProfile, PrivatePerson, CompatibilityScore, CompatibilityParameter, PaymentRecord, UserPlan

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password')
    def create(self, validated_data):
        return User.objects.create_user(**validated_data)

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email')

class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    class Meta:
        model = UserProfile
        fields = ('id', 'user', 'date_of_birth', 'time_of_birth', 'place_of_birth', 'latitude', 'longitude', 'timezone', 'created_at', 'updated_at')
        read_only_fields = ('id', 'user', 'created_at', 'updated_at')

class PrivatePersonSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrivatePerson
        fields = ('id', 'name', 'nickname', 'notes', 'date_of_birth', 'time_of_birth', 'place_of_birth', 'latitude', 'longitude', 'timezone', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')

class CompatibilityScoreSerializer(serializers.ModelSerializer):
    matched_user_username       = serializers.CharField(source='matched_user.user.username', read_only=True)
    matched_private_person_name = serializers.CharField(source='matched_private_person.name', read_only=True)
    is_private_match            = serializers.BooleanField(read_only=True)
    class Meta:
        model = CompatibilityScore
        fields = ('id', 'user', 'matched_user', 'matched_user_username', 'matched_private_person', 'matched_private_person_name', 'is_private_match', 'overall_score', 'sun_compatibility', 'moon_compatibility', 'venus_compatibility', 'mars_compatibility', 'description', 'created_at', 'updated_at')
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
    matched_user_username        = serializers.CharField(source='matched_user.user.username', read_only=True)
    matched_private_person_name  = serializers.CharField(source='matched_private_person.name', read_only=True)
    is_private_match             = serializers.BooleanField(read_only=True)
    parameters                   = serializers.SerializerMethodField()
    upgrade_required             = serializers.SerializerMethodField()
    credits_remaining            = serializers.SerializerMethodField()

    class Meta:
        model = CompatibilityScore
        fields = (
            'id', 'user',
            'matched_user', 'matched_user_username',
            'matched_private_person', 'matched_private_person_name',
            'is_private_match',
            'overall_score',
            'parameters',          # replaces flat sun/moon/venus/mars fields
            'description',
            'upgrade_required',
            'credits_remaining',
            'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'api_response', 'created_at', 'updated_at')

    def get_parameters(self, obj):
        request = self.context.get('request')
        is_paid = self.context.get('is_paid_session', False)
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
        return not self.context.get('is_paid_session', False)

    def get_credits_remaining(self, obj):
        request = self.context.get('request')
        if request and hasattr(request.user, 'plan'):
            return request.user.plan.total_credits
        return 0