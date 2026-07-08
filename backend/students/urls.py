from django.urls import path

from .views import OnboardingView, ProfileView

urlpatterns = [
    path("onboarding/", OnboardingView.as_view(), name="onboarding"),
    path("profile/", ProfileView.as_view(), name="profile"),
]
