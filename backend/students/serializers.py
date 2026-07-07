from rest_framework import serializers

from .models import Student


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
