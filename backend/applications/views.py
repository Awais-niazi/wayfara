from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from students.models import Student

from .models import Application, Match
from .serializers import (
    ApplicationCreateSerializer,
    ApplicationDetailSerializer,
    ApplicationListSerializer,
    ApplicationStatusSerializer,
    ApplicationUpdateSerializer,
    MatchSerializer,
)
from .services import transition_application


class MatchListView(generics.ListAPIView):
    """The student's university recommendations, best fit first."""

    serializer_class = MatchSerializer

    def get_queryset(self):
        return (
            Match.objects.owned_by(self.request.user)
            .select_related("program__university__profile", "program__campus")
            .order_by("-score")
        )


class ApplicationListCreateView(generics.ListCreateAPIView):
    """The student's applications: list (priority order) and start a new one."""

    def get_serializer_class(self):
        return (
            ApplicationCreateSerializer
            if self.request.method == "POST"
            else ApplicationListSerializer
        )

    def get_queryset(self):
        return (
            Application.objects.owned_by(self.request.user)
            .select_related("program__university")
            .prefetch_related("program__required_documents")
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.request.method == "GET":
            student = getattr(self.request.user, "student", None)
            context["student_documents"] = (
                list(student.documents.all()) if student else []
            )
        return context

    def create(self, request, *args, **kwargs):
        # get_or_create the Student the same way the profile endpoint does —
        # an un-onboarded user shouldn't 500 here.
        Student.objects.get_or_create(user=request.user)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Duplicates are rejected in validate_program; the DB unique
        # constraint remains the race-condition backstop.
        application = serializer.save()
        return Response(
            ApplicationDetailSerializer(application, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )


class ApplicationDetailView(generics.RetrieveUpdateAPIView):
    """The workspace: checklist + SOP + status, PATCH for the editable fields."""

    def get_serializer_class(self):
        return (
            ApplicationUpdateSerializer
            if self.request.method in ("PATCH", "PUT")
            else ApplicationDetailSerializer
        )

    def get_queryset(self):
        return (
            Application.objects.owned_by(self.request.user)
            .select_related("program__university")
            .prefetch_related("program__required_documents")
        )

    def update(self, request, *args, **kwargs):
        super().update(request, *args, **kwargs)
        # Always answer with the full workspace payload, whatever was patched.
        return Response(
            ApplicationDetailSerializer(
                self.get_object(), context=self.get_serializer_context()
            ).data
        )


class ApplicationStatusView(APIView):
    """Advance an application along its ladder; milestones notify."""

    def post(self, request, pk):
        application = (
            Application.objects.owned_by(request.user)
            .select_related("program__university")
            .filter(pk=pk)
            .first()
        )
        if application is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = ApplicationStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            transition_application(application, serializer.validated_data["status"])
        except ValueError as exc:
            return Response({"status": [str(exc)]}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ApplicationDetailSerializer(application).data)
