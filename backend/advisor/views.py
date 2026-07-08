from django.http import FileResponse, Http404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from accounts.permissions import HasAdvisorAccess, IsAdvisor
from students.models import Document, Student

from .serializers import (
    ActivateSerializer,
    AdvisorMessageSerializer,
    AdvisorStudentDetailSerializer,
    AdvisorStudentListSerializer,
    SendMessageSerializer,
)
from .services import (
    activate_advisor,
    get_thread_for_student,
    mark_read_by,
    post_message,
)


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


def _serialize_thread(thread, request):
    msgs = thread.messages.select_related("sender")
    return {
        "advisor": {
            "name": (
                f"{thread.advisor.first_name} {thread.advisor.last_name}".strip()
                or thread.advisor.email
            )
            if thread.advisor
            else None
        },
        "messages": AdvisorMessageSerializer(
            msgs, many=True, context={"request": request}
        ).data,
    }


class MyAdvisorMessagesView(APIView):
    """Student's side of the advisor conversation.

    Reading is open to any authenticated student; sending is Premium-gated
    by HasAdvisorAccess, so a lapsed subscriber keeps read access but can no
    longer post.
    """

    permission_classes = [HasAdvisorAccess]

    def _student(self, request):
        return Student.objects.filter(user=request.user).select_related("assigned_advisor").first()

    def get(self, request):
        student = self._student(request)
        if student is None:
            return Response({"advisor": None, "messages": []})
        thread = get_thread_for_student(student)
        if thread is None:
            return Response(
                {"advisor": None, "messages": [],
                 "detail": "An advisor will be assigned to you shortly."}
            )
        mark_read_by(thread, request.user)
        return Response(_serialize_thread(thread, request))

    def post(self, request):
        student = self._student(request)
        if student is None:
            return Response(
                {"detail": "Complete onboarding first."}, status=status.HTTP_400_BAD_REQUEST
            )
        thread = get_thread_for_student(student)
        if thread is None:
            return Response(
                {"detail": "No advisor is assigned to you yet."},
                status=status.HTTP_409_CONFLICT,
            )
        serializer = SendMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = post_message(thread, request.user, serializer.validated_data["body"])
        return Response(
            AdvisorMessageSerializer(message, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class StudentMessagesView(APIView):
    """Advisor's side: the thread with one assigned student."""

    permission_classes = [IsAdvisor]

    def _student(self, request, pk):
        return (
            Student.objects.filter(pk=pk, assigned_advisor=request.user)
            .select_related("assigned_advisor")
            .first()
        )

    def get(self, request, pk):
        student = self._student(request, pk)
        if student is None:
            raise Http404
        thread = get_thread_for_student(student)
        mark_read_by(thread, request.user)
        return Response(_serialize_thread(thread, request))

    def post(self, request, pk):
        student = self._student(request, pk)
        if student is None:
            raise Http404
        thread = get_thread_for_student(student)
        serializer = SendMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = post_message(thread, request.user, serializer.validated_data["body"])
        return Response(
            AdvisorMessageSerializer(message, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )
