from rest_framework import serializers

from wayfara.serializers import StrictSerializer

from .models import DeviceToken


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
