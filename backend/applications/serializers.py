from rest_framework import serializers

from .models import Match


class MatchSerializer(serializers.ModelSerializer):
    program_name = serializers.CharField(source="program.name", read_only=True)
    degree_level = serializers.CharField(source="program.degree_level", read_only=True)
    university = serializers.CharField(source="program.university.name", read_only=True)
    city = serializers.CharField(source="program.university.city", read_only=True)
    tuition_fee_eur = serializers.DecimalField(
        source="program.tuition_fee_eur", max_digits=8, decimal_places=2, read_only=True
    )
    application_deadline = serializers.DateField(
        source="program.application_deadline", read_only=True
    )

    class Meta:
        model = Match
        fields = [
            "id",
            "program",
            "program_name",
            "degree_level",
            "university",
            "city",
            "tuition_fee_eur",
            "application_deadline",
            "fit",
            "score",
            "created_at",
        ]
