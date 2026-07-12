from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.validators import RegexValidator
from rest_framework import serializers

from wayfara.serializers import StrictModelSerializer, StrictSerializer

from .models import DeviceToken

User = get_user_model()

# Product decision (Awais, July 2026): passwords are 8–20 characters.
# Note: NIST 800-63B recommends allowing 64+; if that ever bites (password
# managers, passphrases), raising this cap is backwards-compatible — existing
# shorter passwords keep working, and login never length-checks.
PASSWORD_MAX_LENGTH = 20

# RFC 5321: the longest deliverable address. Bounds attacker-controlled input
# before it reaches validation or the DB.
EMAIL_MAX_LENGTH = 254

_password_field = dict(
    write_only=True, max_length=PASSWORD_MAX_LENGTH, validators=[validate_password]
)

digits_only = RegexValidator(r"^\d{6}$", "Enter the 6-digit code from your email.")


class RegisterSerializer(StrictModelSerializer):
    password = serializers.CharField(**_password_field)

    class Meta:
        model = User
        fields = ["email", "password", "first_name", "last_name"]

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class SetPasswordSerializer(StrictSerializer):
    """Post-verification password creation (onboarding step 3)."""

    password = serializers.CharField(**_password_field)


class RequestOTPSerializer(StrictSerializer):
    email = serializers.EmailField(max_length=EMAIL_MAX_LENGTH)


class VerifyOTPSerializer(StrictSerializer):
    email = serializers.EmailField(max_length=EMAIL_MAX_LENGTH)
    code = serializers.CharField(min_length=6, max_length=6, validators=[digits_only])


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
