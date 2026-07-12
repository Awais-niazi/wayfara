from rest_framework import serializers

from wayfara.serializers import StrictModelSerializer

from .models import Match


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
