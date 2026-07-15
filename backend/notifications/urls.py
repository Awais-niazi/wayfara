from django.urls import path

from .views import NotificationListView, NotificationMarkReadView

urlpatterns = [
    path("notifications/", NotificationListView.as_view(), name="notifications"),
    path(
        "notifications/read/",
        NotificationMarkReadView.as_view(),
        name="notifications_read",
    ),
]
