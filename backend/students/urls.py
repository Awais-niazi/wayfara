from django.urls import path

from .views import (
    DocumentDetailView,
    DocumentDownloadView,
    DocumentListCreateView,
    OnboardingView,
    ProfileView,
    TaskListView,
    TaskStatusView,
)

urlpatterns = [
    path("onboarding/", OnboardingView.as_view(), name="onboarding"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("tasks/", TaskListView.as_view(), name="tasks"),
    path("tasks/<int:pk>/status/", TaskStatusView.as_view(), name="task_status"),
    path("documents/", DocumentListCreateView.as_view(), name="documents"),
    path("documents/<int:pk>/", DocumentDetailView.as_view(), name="document_detail"),
    path(
        "documents/<int:pk>/download/",
        DocumentDownloadView.as_view(),
        name="document_download",
    ),
]
