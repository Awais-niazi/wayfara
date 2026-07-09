from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import DeviceToken

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ["email", "password", "first_name", "last_name"]

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class SetPasswordSerializer(serializers.Serializer):
    """Post-verification password creation (onboarding step 3)."""

    password = serializers.CharField(write_only=True, validators=[validate_password])


class RequestOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()


class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(min_length=6, max_length=6)


class DeviceTokenSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=255)
    platform = serializers.ChoiceField(
        choices=DeviceToken.Platform.choices, required=False, allow_blank=True
    )
