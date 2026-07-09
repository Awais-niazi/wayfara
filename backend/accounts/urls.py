from django.urls import path

from .views import (
    DeviceRegisterView,
    LogoutView,
    MeView,
    RegisterView,
    RequestOTPView,
    SetPasswordView,
    VerifyOTPView,
)

urlpatterns = [
    path("me/", MeView.as_view(), name="me"),
    path("devices/", DeviceRegisterView.as_view(), name="device_register"),
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("auth/otp/request/", RequestOTPView.as_view(), name="otp_request"),
    path("auth/otp/verify/", VerifyOTPView.as_view(), name="otp_verify"),
    path("auth/password/", SetPasswordView.as_view(), name="set_password"),
]
