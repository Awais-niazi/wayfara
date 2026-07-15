from rest_framework import serializers

from wayfara.serializers import StrictSerializer

from .models import DeviceToken, username_validator


def username_field(**kwargs):
    """A username input bound to the model's format rule. Reused by the
    onboarding and profile serializers so both enforce the same handle shape;
    the DB unique constraint (surfaced by DRF as a field error) enforces
    uniqueness."""
    return serializers.CharField(
        min_length=3, max_length=20, validators=[username_validator], **kwargs
    )


class DeviceTokenSerializer(StrictSerializer):
    token = serializers.CharField(max_length=255)
    platform = serializers.ChoiceField(
        choices=DeviceToken.Platform.choices, required=False, allow_blank=True
    )


class DeviceTokenDeleteSerializer(StrictSerializer):
    token = serializers.CharField(max_length=255)


class LogoutSerializer(StrictSerializer):
    """Supabase revokes the session client-side (`signOut()`); the only
    server-side cleanup left is dropping this device's push token."""

    device_token = serializers.CharField(required=False, allow_blank=True)
