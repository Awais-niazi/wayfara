from django.db import transaction
from django.utils import timezone
from rest_framework import generics, serializers, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

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
    """The Get Started form: authenticated profile submission.

    The user has already signed up with Supabase (its token authenticates this
    request); onboarding claims a username, stores the Student profile, and
    kicks off university matching + timeline generation in the background.
    """

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "onboarding"

    def post(self, request):
        serializer = OnboardingSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            student = serializer.save()
            transaction.on_commit(lambda: match_programs_task.delay(student.pk))
            transaction.on_commit(lambda: generate_timeline_task.delay(student.pk))
        return Response(
            {
                "detail": "We're matching universities to your profile.",
                "username": student.user.username,
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
        qs = Task.objects.owned_by(self.request.user)
        phase = self.request.query_params.get("phase")
        if phase is not None:
            # Task.phase is a PositiveSmallIntegerField — a non-numeric value
            # would otherwise hit the DB driver and 500. Reject it at the door.
            if not phase.isdigit():
                raise serializers.ValidationError({"phase": ["Must be a non-negative integer."]})
            qs = qs.filter(phase=int(phase))
        return qs


class TaskStatusView(APIView):
    """Mark a task complete / skipped / back to pending."""

    def post(self, request, pk):
        task = Task.objects.owned_by(request.user).filter(pk=pk).first()
        if task is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = TaskStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task.status = serializer.validated_data["status"]
        task.completed_at = timezone.now() if task.status == Task.Status.COMPLETED else None
        task.save(update_fields=["status", "completed_at", "updated_at"])
        return Response(TaskSerializer(task).data)
