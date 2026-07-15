from django.urls import path

from .views import (
    ApplicationDetailView,
    ApplicationListCreateView,
    ApplicationStatusView,
    MatchListView,
)

urlpatterns = [
    path("matches/", MatchListView.as_view(), name="matches"),
    path("applications/", ApplicationListCreateView.as_view(), name="applications"),
    path("applications/<int:pk>/", ApplicationDetailView.as_view(), name="application_detail"),
    path(
        "applications/<int:pk>/status/",
        ApplicationStatusView.as_view(),
        name="application_status",
    ),
]
