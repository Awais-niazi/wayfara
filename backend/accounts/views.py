from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import DeviceToken
from .serializers import (
    DeviceTokenDeleteSerializer,
    DeviceTokenSerializer,
    LogoutSerializer,
)


class MeView(APIView):
    """Session bootstrap: one call on app launch decides the route.

    No valid Supabase token -> 401 -> Get Started. Otherwise the app routes on
    `role` (student home vs advisor console) and `onboarding_complete`, and
    greets the user by `username`.
    """

    def get(self, request):
        user = request.user
        return Response(
            {
                "email": user.email,
                "username": user.username,
                "role": user.role,
                "tier": user.tier,
                "email_verified": user.email_verified,
                # Student profile is created by onboarding, so its existence
                # is the onboarded signal. Advisors have no Student profile.
                "onboarding_complete": hasattr(user, "student"),
            }
        )


class LogoutView(APIView):
    """Session revocation is Supabase's job (client `signOut()`); here we just
    drop this device's push token so a signed-out phone stops receiving pushes."""

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        device = serializer.validated_data.get("device_token")
        if device:
            DeviceToken.objects.filter(user=request.user, token=device).delete()
        return Response(status=status.HTTP_205_RESET_CONTENT)


class DeviceRegisterView(APIView):
    """Register (POST) or remove (DELETE) this device's Expo push token.

    A token is globally unique and always re-homed to the current user, so a
    shared phone doesn't leak notifications to a previous account.
    """

    def post(self, request):
        serializer = DeviceTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        DeviceToken.objects.update_or_create(
            token=serializer.validated_data["token"],
            defaults={
                "user": request.user,
                "platform": serializer.validated_data.get("platform", ""),
            },
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    def delete(self, request):
        serializer = DeviceTokenDeleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        DeviceToken.objects.filter(
            user=request.user, token=serializer.validated_data["token"]
        ).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
