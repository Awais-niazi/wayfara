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
