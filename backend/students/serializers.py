from django.contrib.auth import get_user_model
from rest_framework import serializers

from accounts.serializers import username_field
from wayfara.serializers import StrictModelSerializer, StrictSerializer

from .models import Student, Task
from .validators import validate_academic

User = get_user_model()


def _username_taken(value, exclude_user):
    return (
        User.objects.filter(username__iexact=value)
        .exclude(pk=exclude_user.pk)
        .exists()
    )

# The academic fields whose values are validated against each other
# (grade value vs scale, test score vs test type, budget range).
ACADEMIC_FIELDS = (
    "grade_scale",
    "grades",
    "language_test_status",
    "language_test",
    "language_test_score",
    "budget_eur_per_year",
)


class TaskSerializer(StrictModelSerializer):
    is_critical = serializers.BooleanField(source="template.is_critical", default=False, read_only=True)

    class Meta:
        model = Task
        fields = [
            "id", "phase", "title", "description", "due_date",
            "order", "status", "is_critical", "completed_at",
        ]


class TaskStatusSerializer(StrictSerializer):
    status = serializers.ChoiceField(choices=Task.Status.choices)


class OnboardingSerializer(StrictModelSerializer):
    """The Get Started form: username + profile for the authenticated user.

    Identity (email/credentials) already lives in Supabase — the request is
    authenticated by its token, so onboarding only claims a username and
    stores the academic profile.
    """

    username = username_field()

    class Meta:
        model = Student
        fields = [
            "username",
            "study_level",
            "field_of_study",
            "grade_scale",
            "grades",
            "language_test_status",
            "language_test",
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

    def validate_username(self, value):
        if _username_taken(value, self.context["request"].user):
            raise serializers.ValidationError("That username is taken.")
        return value

    def validate(self, attrs):
        # Everything is present on create, so validate the payload directly.
        validate_academic(attrs)
        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
        user.username = validated_data.pop("username")
        user.save(update_fields=["username"])
        student, _ = Student.objects.update_or_create(
            user=user, defaults={**validated_data, "onboarding_completed": True}
        )
        return student


class ProfileSerializer(StrictModelSerializer):
    """Flat profile view over Student + account fields from User.

    Name is editable (it belongs to the person); email and tier are not —
    email is the account key and tier is flipped only by the payment webhook.
    """

    email = serializers.EmailField(source="user.email", read_only=True)
    username = username_field(source="user.username", required=False)
    first_name = serializers.CharField(
        source="user.first_name", required=False, allow_blank=True, max_length=150
    )
    last_name = serializers.CharField(
        source="user.last_name", required=False, allow_blank=True, max_length=150
    )
    tier = serializers.CharField(source="user.tier", read_only=True)

    def validate_username(self, value):
        if _username_taken(value, self.instance.user):
            raise serializers.ValidationError("That username is taken.")
        return value

    def validate(self, attrs):
        # PATCH is partial: validate each academic field against its effective
        # value (the incoming one, or the stored one it isn't changing), so a
        # lone `grades` edit is still checked against the saved `grade_scale`.
        effective = {}
        for field in ACADEMIC_FIELDS:
            if field in attrs:
                effective[field] = attrs[field]
            elif self.instance is not None:
                effective[field] = getattr(self.instance, field)
        validate_academic(effective)
        return attrs

    def update(self, instance, validated_data):
        # Writable user.* fields arrive nested under "user" via their source.
        user_data = validated_data.pop("user", None)
        if user_data:
            for attr, value in user_data.items():
                setattr(instance.user, attr, value)
            instance.user.save(update_fields=list(user_data))
        return super().update(instance, validated_data)

    class Meta:
        model = Student
        fields = [
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "tier",
            "nationality",
            "phone",
            "home_city",
            "study_level",
            "field_of_study",
            "grade_scale",
            "grades",
            "language_test_status",
            "language_test",
            "language_test_score",
            "budget_eur_per_year",
            "intake",
            "intake_year",
            "stage",
            "current_phase",
            "onboarding_completed",
        ]
        read_only_fields = ["id", "current_phase"]
