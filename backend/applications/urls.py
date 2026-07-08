from django.urls import path

from .views import MatchListView

urlpatterns = [
    path("matches/", MatchListView.as_view(), name="matches"),
]
