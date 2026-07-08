from django.http import FileResponse, Http404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from accounts.permissions import IsAdvisor
from students.models import Document, Student

from .serializers import (
    ActivateSerializer,
    AdvisorStudentDetailSerializer,
    AdvisorStudentListSerializer,
)
from .services import activate_advisor


class ActivateView(APIView):
    """Set an advisor's password from the one-time invite link. Public: the
    token IS the credential. Throttled to blunt token brute-forcing."""

    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "advisor_activate"

    def post(self, request):
        serializer = ActivateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user, error = activate_advisor(
            serializer.validated_data["uid"],
            serializer.validated_data["token"],
            serializer.validated_data["password"],
        )
        if error:
            return Response({"detail": error}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"detail": "Account activated. You can now log in."})


class AssignedStudentsView(generics.ListAPIView):
    """The advisor's caseload — only students assigned to them."""

    permission_classes = [IsAdvisor]
    serializer_class = AdvisorStudentListSerializer

    def get_queryset(self):
        return (
            Student.objects.filter(assigned_advisor=self.request.user)
            .select_related("user")
            .order_by("user__email")
        )


class AssignedStudentDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAdvisor]
    serializer_class = AdvisorStudentDetailSerializer

    def get_queryset(self):
        return Student.objects.filter(assigned_advisor=self.request.user).select_related("user")


class DocumentDownloadView(APIView):
    """Authorize-then-serve for a student's uploaded document.

    Access requires being that student's assigned advisor (or, if we later
    route student self-downloads here, the owner). Streaming through Django
    keeps documents off any public URL; when storage moves to S3/R2 this
    becomes a short-lived signed-URL redirect, same authorization gate.
    """

    permission_classes = [IsAdvisor]

    def get(self, request, pk):
        document = (
            Document.objects.filter(pk=pk, student__assigned_advisor=request.user)
            .select_related("student")
            .first()
        )
        if document is None or not document.file:
            raise Http404
        return FileResponse(document.file.open("rb"), as_attachment=True)
