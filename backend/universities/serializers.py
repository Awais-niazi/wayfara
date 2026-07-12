from rest_framework import serializers

from wayfara.serializers import StrictModelSerializer

from .models import Program, University


class _ProfileMixin(StrictModelSerializer):
    """Curated KB fields, flattened from the related UniversityProfile.

    Editorial text (overview) stays hidden until a human signs it off
    (needs_review=False), so unreviewed content never reaches students.
    """

    world_ranking = serializers.SerializerMethodField()
    ranking_system = serializers.SerializerMethodField()
    ranking_year = serializers.SerializerMethodField()
    featured = serializers.SerializerMethodField()
    data_verified = serializers.SerializerMethodField()
    overview = serializers.SerializerMethodField()

    def _profile(self, obj):
        return getattr(obj, "profile", None)

    def get_world_ranking(self, obj):
        p = self._profile(obj)
        return p.world_ranking if p else None

    def get_ranking_system(self, obj):
        p = self._profile(obj)
        return p.ranking_system if p and p.world_ranking else ""

    def get_ranking_year(self, obj):
        p = self._profile(obj)
        return p.ranking_year if p else None

    def get_featured(self, obj):
        p = self._profile(obj)
        return bool(p and p.featured)

    def get_data_verified(self, obj):
        p = self._profile(obj)
        return bool(p and p.operational_verified)

    def get_overview(self, obj):
        p = self._profile(obj)
        return p.overview if (p and not p.needs_review) else ""


class UniversityListSerializer(_ProfileMixin):
    class Meta:
        model = University
        fields = [
            "id", "name", "institution_type", "city", "logo_url", "website",
            "world_ranking", "ranking_system", "ranking_year",
            "featured", "data_verified", "overview",
        ]


class CatalogProgramSerializer(StrictModelSerializer):
    campus = serializers.CharField(source="campus.name", read_only=True, default=None)

    class Meta:
        model = Program
        fields = [
            "id", "name", "degree_level", "field_of_study", "language",
            "duration_years", "tuition_fee_eur", "scholarship_available",
            "intake", "application_deadline", "min_ielts_score", "campus",
        ]


class UniversityDetailSerializer(_ProfileMixin):
    programs = serializers.SerializerMethodField()

    class Meta:
        model = University
        fields = [
            "id", "name", "institution_type", "city", "logo_url", "website",
            "description", "world_ranking", "ranking_system", "ranking_year",
            "featured", "data_verified", "overview", "programs",
        ]

    def get_programs(self, obj):
        active = [p for p in obj.programs.all() if p.is_active]
        return CatalogProgramSerializer(active, many=True).data
