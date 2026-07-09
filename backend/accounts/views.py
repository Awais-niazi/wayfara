from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .models import DeviceToken
from .serializers import (
    DeviceTokenSerializer,
    RegisterSerializer,
    RequestOTPSerializer,
    SetPasswordSerializer,
    VerifyOTPSerializer,
)
from .services import issue_and_send_otp, verify_otp
from .throttling import OTPEmailRateThrottle

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "register"


class RequestOTPView(APIView):
    """Send a login/verification code. Always 200 — no account enumeration."""

    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle, OTPEmailRateThrottle]
    throttle_scope = "otp_request"

    def post(self, request):
        serializer = RequestOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(email__iexact=serializer.validated_data["email"]).first()
        if user is not None:
            issue_and_send_otp(user)
        return Response({"detail": "If that account exists, a code has been sent."})


class VerifyOTPView(APIView):
    """Exchange email + code for JWT tokens; marks the email verified."""

    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "otp_verify"

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(email__iexact=serializer.validated_data["email"]).first()
        if user is None or not verify_otp(user, serializer.validated_data["code"]):
            return Response(
                {"detail": "Invalid or expired code."}, status=status.HTTP_400_BAD_REQUEST
            )
        if not user.email_verified:
            user.email_verified = True
            user.save(update_fields=["email_verified"])
        refresh = RefreshToken.for_user(user)
        return Response({"access": str(refresh.access_token), "refresh": str(refresh)})


class SetPasswordView(APIView):
    """Set the account password (authenticated).

    Onboarding step 3: after the OTP verifies the email, the user creates a
    password before entering the dashboard. Also serves as a plain password
    change for already-established accounts.
    """

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "set_password"

    def post(self, request):
        serializer = SetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["password"])
        request.user.save(update_fields=["password"])
        return Response({"detail": "Password set."})


class MeView(APIView):
    """Session bootstrap: one call on app launch decides the route.

    No JWT -> 401 -> Get Started. Otherwise the app routes on `role`
    (student home vs advisor console) and `onboarding_complete`.
    """

    def get(self, request):
        user = request.user
        return Response(
            {
                "email": user.email,
                "role": user.role,
                "tier": user.tier,
                "email_verified": user.email_verified,
                # Onboarding step 3 (create password) is pending while False.
                "has_password": user.has_usable_password(),
                # Student profile is created by onboarding, so its existence
                # is the onboarded signal. Advisors have no Student profile.
                "onboarding_complete": hasattr(user, "student"),
            }
        )


class LogoutView(APIView):
    """Blacklist the refresh token so logout actually revokes the session."""

    def post(self, request):
        token = request.data.get("refresh")
        if not token:
            return Response(
                {"detail": "refresh token required."}, status=status.HTTP_400_BAD_REQUEST
            )
        try:
            RefreshToken(token).blacklist()
        except TokenError:
            pass  # already expired/blacklisted — logout is idempotent
        # Drop this device's push token on logout so a signed-out phone stops
        # receiving notifications.
        device = request.data.get("device_token")
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
        token = request.data.get("token")
        if token:
            DeviceToken.objects.filter(user=request.user, token=token).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
