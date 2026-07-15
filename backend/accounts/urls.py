from django.urls import path

from .views import DeviceRegisterView, LogoutView, MeView

urlpatterns = [
    path("me/", MeView.as_view(), name="me"),
    path("devices/", DeviceRegisterView.as_view(), name="device_register"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
]
