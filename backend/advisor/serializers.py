from rest_framework import serializers

from students.models import Document, Student


class ActivateSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    password = serializers.CharField(write_only=True, min_length=8)


class AdvisorStudentListSerializer(serializers.ModelSerializer):
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


class AdvisorDocumentSerializer(serializers.ModelSerializer):
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
