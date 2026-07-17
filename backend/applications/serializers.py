from rest_framework import serializers

from wayfara.serializers import StrictModelSerializer, StrictSerializer

from .models import Application, Match


class MatchSerializer(StrictModelSerializer):
    program_name = serializers.CharField(source="program.name", read_only=True)
    degree_level = serializers.CharField(source="program.degree_level", read_only=True)
    university = serializers.CharField(source="program.university.name", read_only=True)
    university_id = serializers.IntegerField(source="program.university_id", read_only=True)
    city = serializers.CharField(source="program.university.city", read_only=True)
    campus = serializers.CharField(source="program.campus.name", read_only=True, default=None)
    tuition_fee_eur = serializers.DecimalField(
        source="program.tuition_fee_eur", max_digits=8, decimal_places=2, read_only=True
    )
    duration_years = serializers.DecimalField(
        source="program.duration_years", max_digits=3, decimal_places=1, read_only=True
    )
    application_deadline = serializers.DateField(
        source="program.application_deadline", read_only=True
    )
    # Knowledge-base fields (present only for curated universities).
    world_ranking = serializers.SerializerMethodField()
    featured = serializers.SerializerMethodField()
    data_verified = serializers.SerializerMethodField()

    class Meta:
        model = Match
        fields = [
            "id",
            "program",
            "program_name",
            "degree_level",
            "university",
            "university_id",
            "city",
            "campus",
            "tuition_fee_eur",
            "duration_years",
            "application_deadline",
            "world_ranking",
            "featured",
            "data_verified",
            "fit",
            "score",
            "created_at",
        ]

    def _profile(self, obj):
        return getattr(obj.program.university, "profile", None)

    def get_world_ranking(self, obj):
        profile = self._profile(obj)
        return profile.world_ranking if profile else None

    def get_featured(self, obj):
        profile = self._profile(obj)
        return bool(profile and profile.featured)

    def get_data_verified(self, obj):
        profile = self._profile(obj)
        return bool(profile and profile.operational_verified)


class ApplicationCreateSerializer(StrictModelSerializer):
    """POST /applications/ — start an application for one programme."""

    class Meta:
        model = Application
        fields = ["program"]

    def validate_program(self, program):
        if not program.is_active or not program.university.is_active:
            raise serializers.ValidationError("This programme is no longer open.")
        student = getattr(self.context["request"].user, "student", None)
        if student and Application.objects.filter(student=student, program=program).exists():
            raise serializers.ValidationError(
                "You already have an application for this programme."
            )
        return program

    def create(self, validated_data):
        student = self.context["request"].user.student
        program = validated_data["program"]
        # Carry the matching engine's realistic-chances read onto the application.
        match = Match.objects.filter(student=student, program=program).first()
        return Application.objects.create(
            student=student, program=program, fit=match.fit if match else ""
        )


class ApplicationListSerializer(StrictModelSerializer):
    program_name = serializers.CharField(source="program.name", read_only=True)
    university = serializers.CharField(source="program.university.name", read_only=True)
    university_id = serializers.IntegerField(source="program.university_id", read_only=True)
    city = serializers.CharField(source="program.university.city", read_only=True)
    degree_level = serializers.CharField(source="program.degree_level", read_only=True)
    application_deadline = serializers.DateField(
        source="program.application_deadline", read_only=True
    )
    tuition_fee_eur = serializers.DecimalField(
        source="program.tuition_fee_eur", max_digits=8, decimal_places=2, read_only=True
    )
    docs_ready = serializers.SerializerMethodField()
    docs_total = serializers.SerializerMethodField()

    class Meta:
        model = Application
        fields = [
            "id", "status", "fit", "priority",
            "program", "program_name", "university", "university_id", "city",
            "degree_level", "application_deadline", "tuition_fee_eur",
            "docs_ready", "docs_total", "submitted_at", "created_at",
        ]
        read_only_fields = fields

    def _checklist(self, obj):
        from .services import get_checklist

        cache = self.context.setdefault("_checklists", {})
        if obj.pk not in cache:
            cache[obj.pk] = get_checklist(
                obj, student_documents=self.context.get("student_documents")
            )
        return cache[obj.pk]

    def get_docs_ready(self, obj):
        return sum(1 for row in self._checklist(obj) if row["required"] and row["fulfilled"])

    def get_docs_total(self, obj):
        return sum(1 for row in self._checklist(obj) if row["required"])


class ApplicationDetailSerializer(ApplicationListSerializer):
    checklist = serializers.SerializerMethodField()
    # Deep link to the programme's own Studyinfo page (or a pre-filled search
    # for uncurated rows) — the workspace's "open the gate" button target.
    studyinfo_url = serializers.CharField(source="program.studyinfo_url", read_only=True)
    # Secondary escape hatch: the university's official site, for programmes
    # whose application round Studyinfo hasn't published yet.
    university_website = serializers.CharField(source="program.university.website", read_only=True)

    class Meta(ApplicationListSerializer.Meta):
        fields = ApplicationListSerializer.Meta.fields + [
            "checklist", "motivation_letter", "studyinfo_reference", "notes",
            "decision_at", "studyinfo_url", "university_website",
        ]
        read_only_fields = fields

    def get_checklist(self, obj):
        return self._checklist(obj)


class ApplicationUpdateSerializer(StrictModelSerializer):
    """PATCH — the fields the student edits in the workspace."""

    class Meta:
        model = Application
        fields = ["motivation_letter", "notes", "priority", "studyinfo_reference"]


class ApplicationStatusSerializer(StrictSerializer):
    status = serializers.ChoiceField(choices=Application.Status.choices)
