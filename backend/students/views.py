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
    request); onboarding records the student's name, stores the Student
    profile, and kicks off university matching + timeline generation in the
    background.
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
                "first_name": student.user.first_name,
            },
            status=status.HTTP_201_CREATED,
        )


# Profile fields the matching engine actually reads — an edit to any of these
# makes the current match list describe a profile that no longer exists.
MATCH_RELEVANT_FIELDS = (
    "study_level",
    "field_of_study",
    "budget_eur_per_year",
    "language_test_status",
    "language_test",
    "language_test_score",
    "grade_scale",
    "grades",
    "intake",
)

# Fields the timeline engine reads: intake anchors every due date, and
# language_test_status gates the conditional "book your test" task. Regen
# preserves completed/skipped tasks — only pending ones are rebuilt.
TIMELINE_RELEVANT_FIELDS = ("language_test_status", "intake", "intake_year")


class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer

    def get_object(self):
        student, _ = Student.objects.get_or_create(user=self.request.user)
        return student

    def perform_update(self, serializer):
        # Re-run matching / timeline generation when (and only when) a field
        # the respective engine reads changed — the Profile screen promises
        # "changing these updates your matches", and a student who just added
        # a test score must stop being told to book the test. A name edit
        # churns neither.
        student = serializer.instance
        watched = set(MATCH_RELEVANT_FIELDS) | set(TIMELINE_RELEVANT_FIELDS)
        before = {f: getattr(student, f) for f in watched}
        serializer.save()
        if any(getattr(student, f) != before[f] for f in MATCH_RELEVANT_FIELDS):
            transaction.on_commit(lambda: match_programs_task.delay(student.pk))
        if any(getattr(student, f) != before[f] for f in TIMELINE_RELEVANT_FIELDS):
            transaction.on_commit(lambda: generate_timeline_task.delay(student.pk))


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
