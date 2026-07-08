from django.db import transaction
from django_q.tasks import async_task
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.services import issue_and_send_otp

from .models import Student
from .serializers import OnboardingSerializer, ProfileSerializer


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
            transaction.on_commit(
                lambda: async_task(
                    "applications.services.match_programs_for_student", student.pk
                )
            )
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
