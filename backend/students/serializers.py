from django.contrib.auth import get_user_model
from rest_framework import serializers

from wayfara.serializers import StrictModelSerializer, StrictSerializer

from .models import Document, Student, Task
from .validators import validate_academic

User = get_user_model()

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
    """The Get Started form: the student's name + profile, for the
    authenticated user.

    Identity (email/credentials) already lives in Supabase — the request is
    authenticated by its token, so onboarding records who the person is and
    stores the academic profile.
    """

    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)

    class Meta:
        model = Student
        fields = [
            "first_name",
            "last_name",
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

    def validate(self, attrs):
        # Everything is present on create, so validate the payload directly.
        validate_academic(attrs)
        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
        user.first_name = validated_data.pop("first_name").strip()
        user.last_name = validated_data.pop("last_name").strip()
        user.save(update_fields=["first_name", "last_name"])
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
    first_name = serializers.CharField(
        source="user.first_name", required=False, allow_blank=True, max_length=150
    )
    last_name = serializers.CharField(
        source="user.last_name", required=False, allow_blank=True, max_length=150
    )
    tier = serializers.CharField(source="user.tier", read_only=True)

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


# ─── Documents ────────────────────────────────────────────────────────────────

MAX_DOCUMENT_BYTES = 10 * 1024 * 1024  # 10 MB — a scan, not an archive
ALLOWED_DOC_EXTENSIONS = {"pdf", "jpg", "jpeg", "png"}
ALLOWED_DOC_CONTENT_TYPES = {"application/pdf", "image/jpeg", "image/png"}
# What the file's first bytes must actually be, per extension. Extension and
# declared content-type are both attacker-controlled; the magic bytes are the
# only claim about the format we verify ourselves — these files get opened by
# admins and advisors.
MAGIC_BY_EXTENSION = {
    "pdf": (b"%PDF-",),
    "jpg": (b"\xff\xd8\xff",),
    "jpeg": (b"\xff\xd8\xff",),
    "png": (b"\x89PNG\r\n\x1a\n",),
}


class DocumentUploadSerializer(StrictModelSerializer):
    class Meta:
        model = Document
        fields = ["doc_type", "file", "expires_at"]
        extra_kwargs = {"doc_type": {"required": True}}

    def validate_file(self, value):
        if value.size > MAX_DOCUMENT_BYTES:
            raise serializers.ValidationError("File is too large (max 10 MB).")
        extension = value.name.rsplit(".", 1)[-1].lower() if "." in value.name else ""
        if extension not in ALLOWED_DOC_EXTENSIONS:
            raise serializers.ValidationError("Upload a PDF, JPG or PNG.")
        content_type = getattr(value, "content_type", "") or ""
        if content_type and content_type not in ALLOWED_DOC_CONTENT_TYPES:
            raise serializers.ValidationError("Upload a PDF, JPG or PNG.")
        head = value.read(8)
        value.seek(0)
        if not any(head.startswith(sig) for sig in MAGIC_BY_EXTENSION[extension]):
            raise serializers.ValidationError(
                "The file's content doesn't match its type — upload the "
                "original PDF, JPG or PNG."
            )
        return value

    def create(self, validated_data):
        return Document.objects.create(
            student=self.context["request"].user.student, **validated_data
        )


class DocumentSerializer(StrictModelSerializer):
    filename = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = ["id", "doc_type", "status", "filename", "expires_at", "uploaded_at"]
        read_only_fields = fields

    def get_filename(self, obj):
        return obj.file.name.rsplit("/", 1)[-1] if obj.file else ""
