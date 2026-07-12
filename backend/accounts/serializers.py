from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from wayfara.serializers import StrictModelSerializer, StrictSerializer

from .models import DeviceToken

User = get_user_model()


class RegisterSerializer(StrictModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ["email", "password", "first_name", "last_name"]

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class SetPasswordSerializer(StrictSerializer):
    """Post-verification password creation (onboarding step 3)."""

    password = serializers.CharField(write_only=True, validators=[validate_password])


class RequestOTPSerializer(StrictSerializer):
    email = serializers.EmailField()


class VerifyOTPSerializer(StrictSerializer):
    email = serializers.EmailField()
    code = serializers.CharField(min_length=6, max_length=6)


class DeviceTokenSerializer(StrictSerializer):
    token = serializers.CharField(max_length=255)
    platform = serializers.ChoiceField(
        choices=DeviceToken.Platform.choices, required=False, allow_blank=True
    )


class DeviceTokenDeleteSerializer(StrictSerializer):
    token = serializers.CharField(max_length=255)


class LogoutSerializer(StrictSerializer):
    refresh = serializers.CharField()
    device_token = serializers.CharField(required=False, allow_blank=True)
