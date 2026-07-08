from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import RegisterSerializer, RequestOTPSerializer, VerifyOTPSerializer
from .services import issue_and_send_otp, verify_otp

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class RequestOTPView(APIView):
    """Send a login/verification code. Always 200 — no account enumeration."""

    permission_classes = [permissions.AllowAny]

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
