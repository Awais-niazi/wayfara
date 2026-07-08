from django.urls import path

from .views import RegisterView, RequestOTPView, VerifyOTPView

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/otp/request/", RequestOTPView.as_view(), name="otp_request"),
    path("auth/otp/verify/", VerifyOTPView.as_view(), name="otp_verify"),
]
