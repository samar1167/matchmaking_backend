from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserProfile, PrivatePerson, CompatibilityScore

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
