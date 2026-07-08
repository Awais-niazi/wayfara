from django.urls import path

from .views import LogoutView, MeView, RegisterView, RequestOTPView, VerifyOTPView

urlpatterns = [
    path("me/", MeView.as_view(), name="me"),
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("auth/otp/request/", RequestOTPView.as_view(), name="otp_request"),
    path("auth/otp/verify/", VerifyOTPView.as_view(), name="otp_verify"),
]
