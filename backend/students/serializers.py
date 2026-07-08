from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Student, Task

User = get_user_model()


class TaskSerializer(serializers.ModelSerializer):
    is_critical = serializers.BooleanField(source="template.is_critical", default=False, read_only=True)

    class Meta:
        model = Task
        fields = [
            "id", "phase", "title", "description", "due_date",
            "order", "status", "is_critical", "completed_at",
        ]


class TaskStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Task.Status.choices)


class OnboardingSerializer(serializers.ModelSerializer):
    """The Get Started form: email + profile in one anonymous submission."""

    email = serializers.EmailField()

    class Meta:
        model = Student
        fields = [
            "email",
            "study_level",
            "field_of_study",
            "grades",
            "language_test_status",
            "language_test_score",
            "budget_eur_per_year",
            "intake",
            "intake_year",
            "stage",
        ]
        extra_kwargs = {
            "study_level": {"required": True},
            "field_of_study": {"required": True},
        }

    def create(self, validated_data):
        email = validated_data.pop("email")
        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            user = User.objects.create_user(email=email)  # password=None -> unusable; OTP is the login
        student, _ = Student.objects.update_or_create(
            user=user, defaults={**validated_data, "onboarding_completed": True}
        )
        return student


class ProfileSerializer(serializers.ModelSerializer):
    """Flat profile view over Student + read-only account fields from User."""

    email = serializers.EmailField(source="user.email", read_only=True)
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)
    tier = serializers.CharField(source="user.tier", read_only=True)

    class Meta:
        model = Student
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "tier",
            "nationality",
            "phone",
            "home_city",
            "study_level",
            "field_of_study",
            "grades",
            "language_test_status",
            "language_test_score",
            "budget_eur_per_year",
            "intake",
            "intake_year",
            "stage",
            "current_phase",
            "onboarding_completed",
        ]
        read_only_fields = ["id", "current_phase"]
