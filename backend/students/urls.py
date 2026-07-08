from django.urls import path

from .views import OnboardingView, ProfileView, TaskListView, TaskStatusView

urlpatterns = [
    path("onboarding/", OnboardingView.as_view(), name="onboarding"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("tasks/", TaskListView.as_view(), name="tasks"),
    path("tasks/<int:pk>/status/", TaskStatusView.as_view(), name="task_status"),
]
