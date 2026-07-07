from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ["email", "password", "first_name", "last_name"]

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
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
            "tier",
            "onboarding_completed",
        ]
        read_only_fields = ["id", "email", "tier", "current_phase"]
