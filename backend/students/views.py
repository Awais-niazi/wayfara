from django.db import transaction
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.services import issue_and_send_otp
from applications.tasks import match_programs_task

from .models import Student, Task
from .tasks import generate_timeline_task
from .serializers import (
    OnboardingSerializer,
    ProfileSerializer,
    TaskSerializer,
    TaskStatusSerializer,
)


class OnboardingView(APIView):
    """The Get Started form: anonymous profile submission.

    Creates the account (passwordless) + Student, kicks off university
    matching in the background, and emails an OTP so the user verifies
    while matching runs.
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = OnboardingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            student = serializer.save()
            transaction.on_commit(lambda: match_programs_task.delay(student.pk))
            transaction.on_commit(lambda: generate_timeline_task.delay(student.pk))
        issue_and_send_otp(student.user)
        return Response(
            {
                "detail": "We're matching universities to your profile. "
                "Check your email for your verification code.",
                "email": student.user.email,
            },
            status=status.HTTP_201_CREATED,
        )


class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer

    def get_object(self):
        student, _ = Student.objects.get_or_create(user=self.request.user)
        return student


class TaskListView(generics.ListAPIView):
    """The student's journey plan; filter with ?phase=N."""

    serializer_class = TaskSerializer

    def get_queryset(self):
        qs = Task.objects.filter(student__user=self.request.user)
        phase = self.request.query_params.get("phase")
        if phase is not None:
            qs = qs.filter(phase=phase)
        return qs


class TaskStatusView(APIView):
    """Mark a task complete / skipped / back to pending."""

    def post(self, request, pk):
        task = Task.objects.filter(student__user=request.user, pk=pk).first()
        if task is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = TaskStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task.status = serializer.validated_data["status"]
        task.completed_at = timezone.now() if task.status == Task.Status.COMPLETED else None
        task.save(update_fields=["status", "completed_at", "updated_at"])
        return Response(TaskSerializer(task).data)
