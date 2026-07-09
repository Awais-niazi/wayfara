from django.urls import path

from .views import UniversityDetailView, UniversityListView

urlpatterns = [
    path("universities/", UniversityListView.as_view(), name="university_list"),
    path("universities/<int:pk>/", UniversityDetailView.as_view(), name="university_detail"),
]
