from django.conf import settings
from django.db import models


class University(models.Model):
    class InstitutionType(models.TextChoices):
        UNIVERSITY = "university", "University"
        AMK = "amk", "University of Applied Sciences (AMK)"

    name = models.CharField(max_length=200, unique=True)
    institution_type = models.CharField(max_length=20, choices=InstitutionType.choices)
    city = models.CharField(max_length=100, help_text="Main campus city")
    website = models.URLField(blank=True)
    description = models.TextField(blank=True, help_text="Plain-English description, no bureaucratic language")
    logo_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "universities"
        ordering = ["name"]

    def __str__(self):
        return self.name


class UniversityProfile(models.Model):
    """Curated knowledge base for the handful of high-traffic universities.

    Holds ONLY what the scraper can't produce — ranking/selectivity and a human
    "verified" stamp on the scraped operational facts. It never re-enters
    tuition/deadline/campus (the scraper owns those). City guides / cost of
    living deliberately live in the paid AI layer, not here.
    """

    class RankingSystem(models.TextChoices):
        QS = "qs", "QS World University Rankings"
        THE = "the", "Times Higher Education"
        ARWU = "arwu", "Academic Ranking of World Universities (Shanghai)"

    university = models.OneToOneField(University, on_delete=models.CASCADE, related_name="profile")

    featured = models.BooleanField(default=False, help_text="Surface among popular universities")
    sort_order = models.PositiveSmallIntegerField(default=0)
    overview = models.TextField(blank=True, help_text="Short plain-English editorial overview")

    # Rating / selectivity — curated, with provenance since rankings move yearly.
    world_ranking = models.PositiveIntegerField(null=True, blank=True)
    ranking_system = models.CharField(max_length=10, choices=RankingSystem.choices, blank=True)
    ranking_year = models.PositiveSmallIntegerField(null=True, blank=True)
    ranking_source_url = models.URLField(blank=True)

    # Human confirmation that the scraper's tuition/deadline/campus are correct
    # for this (high-traffic) university.
    operational_verified = models.BooleanField(default=False)
    verified_at = models.DateField(null=True, blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    # Editorial content stays gated until a human signs off.
    needs_review = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "university__name"]

    def __str__(self):
        return f"Profile<{self.university.name}>"


class Campus(models.Model):
    university = models.ForeignKey(University, on_delete=models.CASCADE, related_name="campuses")
    name = models.CharField(max_length=200)
    city = models.CharField(max_length=100)
    address = models.CharField(max_length=300, blank=True)

    class Meta:
        verbose_name_plural = "campuses"
        constraints = [
            models.UniqueConstraint(fields=["university", "name"], name="unique_campus_per_university"),
        ]

    def __str__(self):
        return f"{self.university.name} — {self.name}"


class Program(models.Model):
    class DegreeLevel(models.TextChoices):
        BACHELORS = "bachelors", "Bachelor's"
        MASTERS = "masters", "Master's"

    class Intake(models.TextChoices):
        SEPTEMBER = "september", "September"
        JANUARY = "january", "January"

    university = models.ForeignKey(University, on_delete=models.CASCADE, related_name="programs")
    campus = models.ForeignKey(
        Campus, on_delete=models.SET_NULL, null=True, blank=True, related_name="programs"
    )
    name = models.CharField(max_length=200)
    degree_level = models.CharField(max_length=20, choices=DegreeLevel.choices)
    field_of_study = models.CharField(max_length=100, db_index=True)
    language = models.CharField(max_length=50, default="English")
    description = models.TextField(blank=True)
    duration_years = models.DecimalField(max_digits=3, decimal_places=1, default=2)

    tuition_fee_eur = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True,
        help_text="Annual tuition for non-EU students; 0 = tuition-free, null = unknown",
    )
    scholarship_available = models.BooleanField(default=False)
    scholarship_notes = models.TextField(blank=True)

    intake = models.CharField(max_length=20, choices=Intake.choices)
    application_opens = models.DateField(null=True, blank=True)
    application_deadline = models.DateField(null=True, blank=True, db_index=True)
    start_date = models.DateField(null=True, blank=True)

    min_ielts_score = models.DecimalField(max_digits=2, decimal_places=1, null=True, blank=True)
    entry_requirements = models.TextField(blank=True, help_text="Plain-English entry requirements")
    acceptance_rate = models.DecimalField(
        max_digits=4, decimal_places=1, null=True, blank=True, help_text="Percentage, e.g. 12.5"
    )

    is_active = models.BooleanField(default=True)

    # Provenance for live-ingested rows (e.g. Opintopolku koulutus oid). Lets
    # the scraper upsert deterministically instead of guessing by name.
    external_source = models.CharField(max_length=40, blank=True)
    external_id = models.CharField(max_length=100, blank=True, null=True, unique=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["university__name", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["university", "name", "degree_level", "intake"],
                name="unique_program_per_university",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_degree_level_display()}) — {self.university.name}"


# Lazy (callable) choices so this module never imports students.models at
# load time — keeps the model-import graph one-directional.
def _doc_type_choices():
    from students.models import Document

    return Document.DocType.choices


class RequiredDocument(models.Model):
    """One document a specific program demands from applicants.

    Curated in admin (inline on Program) for the programs the KB team has
    verified. Semantics are REPLACEMENT, not merge: a program with any rows
    defines its complete checklist; programs without rows fall back to the
    standard Finnish master's baseline (applications/services.py). The
    doc_type choices live on students.Document so the checklist and the
    student's uploads always speak the same vocabulary.
    """

    program = models.ForeignKey(
        Program, on_delete=models.CASCADE, related_name="required_documents"
    )
    doc_type = models.CharField(max_length=30, choices=_doc_type_choices)
    required = models.BooleanField(
        default=True, help_text="Unticked = optional but recommended"
    )
    notes = models.CharField(
        max_length=200, blank=True,
        help_text='Program-specific detail, e.g. "IELTS Academic only, min 6.5"',
    )

    class Meta:
        ordering = ["program", "-required", "doc_type"]
        constraints = [
            models.UniqueConstraint(
                fields=["program", "doc_type"], name="unique_required_doc_per_program"
            ),
        ]

    def __str__(self):
        return f"{self.program}: {self.doc_type}{'' if self.required else ' (optional)'}"
