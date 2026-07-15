from django.urls import path

from .views import (
    AssignedStudentDetailView,
    AssignedStudentsView,
    DocumentDownloadView,
    MessageAudioView,
    MyAdvisorMessagesView,
    StudentMessagesView,
)

urlpatterns = [
    path("advisor/students/", AssignedStudentsView.as_view(), name="advisor_students"),
    path(
        "advisor/students/<int:pk>/",
        AssignedStudentDetailView.as_view(),
        name="advisor_student_detail",
    ),
    path(
        "advisor/students/<int:pk>/messages/",
        StudentMessagesView.as_view(),
        name="advisor_student_messages",
    ),
    path(
        "advisor/documents/<int:pk>/download/",
        DocumentDownloadView.as_view(),
        name="advisor_document_download",
    ),
    path(
        "advisor/messages/<int:pk>/audio/",
        MessageAudioView.as_view(),
        name="advisor_message_audio",
    ),
    # Student side of the same conversation.
    path("my-advisor/messages/", MyAdvisorMessagesView.as_view(), name="my_advisor_messages"),
]
