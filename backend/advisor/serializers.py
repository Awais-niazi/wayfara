from rest_framework import serializers

from students.models import Document, Student
from wayfara.serializers import StrictModelSerializer, StrictSerializer

from .models import AdvisorMessage


class AdvisorMessageSerializer(StrictModelSerializer):
    mine = serializers.SerializerMethodField()
    audio_url = serializers.SerializerMethodField()

    class Meta:
        model = AdvisorMessage
        fields = [
            "id", "body", "audio_url", "audio_duration_seconds",
            "created_at", "read_at", "mine",
        ]

    def get_mine(self, obj):
        request = self.context.get("request")
        return bool(request and obj.sender_id == request.user.id)

    def get_audio_url(self, obj):
        if not obj.audio:
            return None
        from django.urls import reverse

        request = self.context.get("request")
        url = reverse("advisor_message_audio", args=[obj.pk])
        return request.build_absolute_uri(url) if request else url


MAX_AUDIO_BYTES = 10 * 1024 * 1024  # 10 MB — a voice note, not a podcast


class SendMessageSerializer(StrictSerializer):
    body = serializers.CharField(
        max_length=5000, required=False, allow_blank=True, trim_whitespace=True
    )
    audio = serializers.FileField(required=False)
    audio_duration_seconds = serializers.IntegerField(
        required=False, min_value=0, max_value=600
    )

    def validate_audio(self, value):
        if value.size > MAX_AUDIO_BYTES:
            raise serializers.ValidationError("Voice note is too large (max 10 MB).")
        return value

    def validate(self, data):
        if not data.get("body") and not data.get("audio"):
            raise serializers.ValidationError("Send a message or a voice note.")
        return data


class AdvisorStudentListSerializer(StrictModelSerializer):
    """Compact row for the advisor's caseload list."""

    email = serializers.EmailField(source="user.email", read_only=True)
    name = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = [
            "id", "email", "name", "study_level", "field_of_study",
            "intake", "intake_year", "current_phase", "stage",
        ]

    def get_name(self, obj):
        full = f"{obj.user.first_name} {obj.user.last_name}".strip()
        return full or None


class AdvisorDocumentSerializer(StrictModelSerializer):
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            "id", "doc_type", "status", "expires_at", "uploaded_at", "download_url",
        ]

    def get_download_url(self, obj):
        request = self.context.get("request")
        from django.urls import reverse

        url = reverse("advisor_document_download", args=[obj.pk])
        return request.build_absolute_uri(url) if request else url


class AdvisorStudentDetailSerializer(AdvisorStudentListSerializer):
    """Full profile the advisor sees for one assigned student."""

    documents = serializers.SerializerMethodField()

    class Meta(AdvisorStudentListSerializer.Meta):
        fields = AdvisorStudentListSerializer.Meta.fields + [
            "phone", "home_city", "grades", "language_test_status",
            "language_test_score", "budget_eur_per_year", "documents",
        ]

    def get_documents(self, obj):
        return AdvisorDocumentSerializer(
            obj.documents.all(), many=True, context=self.context
        ).data
