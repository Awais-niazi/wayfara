from django.db import models


class Match(models.Model):
    """A program recommendation produced by the background matching task.

    Distinct from Application: a Match is what Wayfara suggests; an
    Application is what the student decides to pursue.
    """

    class Fit(models.TextChoices):
        SAFETY = "safety", "Safety"
        GOOD_FIT = "good_fit", "Good fit"
        REACH = "reach", "Reach"

    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="matches")
    program = models.ForeignKey("universities.Program", on_delete=models.CASCADE, related_name="matches")
    fit = models.CharField(max_length=10, choices=Fit.choices)
    score = models.DecimalField(max_digits=5, decimal_places=2, help_text="0–100 composite fit score")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "matches"
        ordering = ["-score"]
        constraints = [
            models.UniqueConstraint(fields=["student", "program"], name="unique_match_per_program"),
        ]

    def __str__(self):
        return f"{self.student} ~ {self.program} [{self.fit} {self.score}]"


class Application(models.Model):
    """A student's application to one specific program."""

    class Status(models.TextChoices):
        SHORTLISTED = "shortlisted", "Shortlisted"
        IN_PROGRESS = "in_progress", "Preparing application"
        SUBMITTED = "submitted", "Submitted"
        OFFER_RECEIVED = "offer_received", "Offer received"
        WAITLISTED = "waitlisted", "Waitlisted"
        REJECTED = "rejected", "Rejected"
        PLACE_CONFIRMED = "place_confirmed", "Study place confirmed"
        WITHDRAWN = "withdrawn", "Withdrawn"

    class Fit(models.TextChoices):
        SAFETY = "safety", "Safety"
        GOOD_FIT = "good_fit", "Good fit"
        REACH = "reach", "Reach"

    student = models.ForeignKey(
        "students.Student", on_delete=models.CASCADE, related_name="applications"
    )
    program = models.ForeignKey(
        "universities.Program", on_delete=models.PROTECT, related_name="applications"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SHORTLISTED)
    fit = models.CharField(
        max_length=10, choices=Fit.choices, blank=True,
        help_text="Realistic-chances indicator shown during shortlisting",
    )
    priority = models.PositiveSmallIntegerField(
        default=0, help_text="Student's own ranking among their applications"
    )

    studyinfo_reference = models.CharField(max_length=100, blank=True)
    motivation_letter = models.TextField(blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    decision_at = models.DateTimeField(null=True, blank=True)

    # Offer + tuition (Phase 3)
    offer_confirm_deadline = models.DateField(
        null=True, blank=True, help_text="Missing this cancels the offer"
    )
    tuition_amount_due_eur = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    tuition_payment_reference = models.CharField(
        max_length=100, blank=True,
        help_text="Bank transfer reference — most common costly mistake is getting this wrong",
    )
    tuition_paid = models.BooleanField(default=False)
    tuition_paid_at = models.DateField(null=True, blank=True)

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["priority", "-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["student", "program"], name="unique_application_per_program"),
        ]

    def __str__(self):
        return f"{self.student} → {self.program} [{self.get_status_display()}]"


class Visa(models.Model):
    """A student residence-permit application with Migri (Phase 4).

    FK rather than one-to-one so a rejected student can reapply with history kept.
    """

    class Status(models.TextChoices):
        NOT_STARTED = "not_started", "Not started"
        PREPARING = "preparing", "Preparing documents"
        SUBMITTED = "submitted", "Submitted on Enter Finland"
        BIOMETRICS_SCHEDULED = "biometrics_scheduled", "Embassy/biometrics appointment booked"
        ADDITIONAL_DOCS = "additional_docs", "Additional documents requested"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    class EmbassyLocation(models.TextChoices):
        ISLAMABAD = "islamabad", "Islamabad (VFS Global)"
        KARACHI = "karachi", "Karachi"

    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="visas")
    application = models.ForeignKey(
        Application, on_delete=models.SET_NULL, null=True, blank=True, related_name="visas",
        help_text="The confirmed study place this permit is based on",
    )
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.NOT_STARTED)

    enter_finland_reference = models.CharField(max_length=100, blank=True)
    funds_required_eur = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True,
        help_text="Migri financial requirement snapshot at application time (changes periodically)",
    )

    embassy_location = models.CharField(max_length=20, choices=EmbassyLocation.choices, blank=True)
    embassy_appointment_at = models.DateTimeField(null=True, blank=True)

    submitted_at = models.DateTimeField(null=True, blank=True)
    decision_at = models.DateTimeField(null=True, blank=True)
    permit_start = models.DateField(null=True, blank=True)
    permit_end = models.DateField(null=True, blank=True)

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Visa {self.get_status_display()} — {self.student}"
