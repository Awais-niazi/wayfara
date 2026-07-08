from django.urls import path

from .views import (
    ActivateView,
    AssignedStudentDetailView,
    AssignedStudentsView,
    DocumentDownloadView,
)

urlpatterns = [
    path("advisor/activate/", ActivateView.as_view(), name="advisor_activate"),
    path("advisor/students/", AssignedStudentsView.as_view(), name="advisor_students"),
    path(
        "advisor/students/<int:pk>/",
        AssignedStudentDetailView.as_view(),
        name="advisor_student_detail",
    ),
    path(
        "advisor/documents/<int:pk>/download/",
        DocumentDownloadView.as_view(),
        name="advisor_document_download",
    ),
]
