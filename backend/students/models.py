from django.conf import settings
from django.db import models


class Student(models.Model):
    """Domain profile for a user on the study-in-Finland journey.

    One-to-one with the auth User; created lazily on first profile access.
    Fields mirror the Phase 0 onboarding questions.
    """

    class StudyLevel(models.TextChoices):
        UNDERGRADUATE = "undergraduate", "Undergraduate (FSc/A-Levels)"
        MASTERS = "masters", "Masters (Bachelor's degree)"

    class LanguageTestStatus(models.TextChoices):
        NOT_TAKEN = "not_taken", "Not taken yet"
        BOOKED = "booked", "Test booked"
        TAKEN = "taken", "Score available"

    class Intake(models.TextChoices):
        SEPTEMBER = "september", "September"
        JANUARY = "january", "January"

    class Stage(models.TextChoices):
        EXPLORING = "exploring", "Just exploring"
        READY = "ready", "Ready to apply"
        APPLIED = "applied", "Already applied"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="student")

    nationality = models.CharField(max_length=100, default="Pakistan")
    phone = models.CharField(max_length=30, blank=True)
    home_city = models.CharField(max_length=100, blank=True)

    # Onboarding profile (Phase 0)
    study_level = models.CharField(max_length=20, choices=StudyLevel.choices, blank=True)
    field_of_study = models.CharField(max_length=100, blank=True)
    grades = models.CharField(
        max_length=100, blank=True, help_text="GPA, percentage, or A-Level grades as entered"
    )
    language_test_status = models.CharField(
        max_length=20, choices=LanguageTestStatus.choices, blank=True
    )
    language_test_score = models.CharField(max_length=20, blank=True)
    budget_eur_per_year = models.PositiveIntegerField(
        null=True, blank=True, help_text="Annual tuition budget in EUR; null = tuition-free only"
    )
    intake = models.CharField(max_length=20, choices=Intake.choices, blank=True)
    intake_year = models.PositiveSmallIntegerField(null=True, blank=True)
    stage = models.CharField(max_length=20, choices=Stage.choices, blank=True)

    # Journey state
    current_phase = models.PositiveSmallIntegerField(default=0)
    onboarding_completed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Student<{self.user.email}>"


class Document(models.Model):
    class DocType(models.TextChoices):
        PASSPORT = "passport", "Passport"
        PHOTO = "photo", "Passport photo (36×47mm)"
        TRANSCRIPT = "transcript", "Academic transcript"
        DEGREE_CERTIFICATE = "degree_certificate", "Degree / school certificate"
        LANGUAGE_CERTIFICATE = "language_certificate", "IELTS/TOEFL certificate"
        BANK_STATEMENT = "bank_statement", "Bank statement"
        SPONSOR_LETTER = "sponsor_letter", "Financial guarantee / sponsor letter"
        HEALTH_INSURANCE = "health_insurance", "Health insurance"
        ACCEPTANCE_LETTER = "acceptance_letter", "University acceptance letter"
        TUITION_RECEIPT = "tuition_receipt", "Tuition payment receipt"
        ACCOMMODATION_PROOF = "accommodation_proof", "Proof of accommodation"
        CV = "cv", "CV"
        MOTIVATION_LETTER = "motivation_letter", "Motivation letter"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        UPLOADED = "uploaded", "Uploaded"
        AI_REVIEWED = "ai_reviewed", "AI reviewed"
        ISSUES_FOUND = "issues_found", "Issues found"
        VERIFIED = "verified", "Verified"

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="documents")
    doc_type = models.CharField(max_length=30, choices=DocType.choices)
    file = models.FileField(upload_to="documents/%Y/%m/")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.UPLOADED)

    # Premium AI document review (PRD §6.3): structured findings + fixes
    ai_review = models.JSONField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    expires_at = models.DateField(
        null=True, blank=True, help_text="e.g. passport expiry — Migri needs 15+ months validity"
    )

    application = models.ForeignKey(
        "applications.Application", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="documents",
    )
    visa = models.ForeignKey(
        "applications.Visa", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="documents",
    )

    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]
        indexes = [models.Index(fields=["student", "doc_type"])]

    def __str__(self):
        return f"{self.get_doc_type_display()} — {self.student}"


class TaskTemplate(models.Model):
    """Admin-editable blueprint for journey tasks (the PRD's CMS mitigation).

    The timeline engine instantiates these into per-student Tasks, computing
    due dates from the anchor + offset.
    """

    class Anchor(models.TextChoices):
        APPLICATION_DEADLINE = "application_deadline", "Application deadline"
        OFFER_DEADLINE = "offer_deadline", "Offer confirmation deadline"
        VISA_SUBMISSION = "visa_submission", "Visa submission"
        INTAKE_START = "intake_start", "Intake start date"
        ARRIVAL = "arrival", "Arrival in Finland"

    phase = models.PositiveSmallIntegerField(help_text="Journey phase 0–6")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    why_it_matters = models.TextField(
        blank=True, help_text="Shown to the student — every step explains WHY (PRD trust principle)"
    )
    order = models.PositiveSmallIntegerField(default=0)
    offset_anchor = models.CharField(max_length=30, choices=Anchor.choices, blank=True)
    offset_days = models.IntegerField(
        default=0, help_text="Days relative to the anchor; negative = before"
    )
    is_critical = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["phase", "order"]

    def __str__(self):
        return f"[Phase {self.phase}] {self.title}"


class Task(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In progress"
        COMPLETED = "completed", "Completed"
        SKIPPED = "skipped", "Skipped"

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="tasks")
    template = models.ForeignKey(
        TaskTemplate, on_delete=models.SET_NULL, null=True, blank=True, related_name="tasks"
    )
    phase = models.PositiveSmallIntegerField()
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    due_date = models.DateField(null=True, blank=True)
    order = models.PositiveSmallIntegerField(default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    completed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["phase", "order", "due_date"]
        indexes = [
            models.Index(fields=["student", "phase"]),
            models.Index(fields=["student", "due_date"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.student})"


class Reminder(models.Model):
    class Channel(models.TextChoices):
        PUSH = "push", "Push notification"
        EMAIL = "email", "Email"

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="reminders")
    task = models.ForeignKey(Task, on_delete=models.CASCADE, null=True, blank=True, related_name="reminders")
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    channel = models.CharField(max_length=10, choices=Channel.choices, default=Channel.PUSH)
    remind_at = models.DateTimeField()
    sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["remind_at"]
        indexes = [models.Index(fields=["sent", "remind_at"])]

    def __str__(self):
        return f"{self.title} @ {self.remind_at:%Y-%m-%d %H:%M}"


class Accommodation(models.Model):
    class Kind(models.TextChoices):
        STUDENT_HOUSING = "student_housing", "Student housing (HOAS/TYS/PSOAS…)"
        PRIVATE_RENTAL = "private_rental", "Private rental"
        TEMPORARY = "temporary", "Temporary (hostel/Airbnb/friend)"

    class Status(models.TextChoices):
        RESEARCHING = "researching", "Researching"
        APPLIED = "applied", "Applied"
        WAITLISTED = "waitlisted", "Waitlisted"
        OFFERED = "offered", "Offer received"
        CONFIRMED = "confirmed", "Confirmed"
        REJECTED = "rejected", "Rejected"

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="accommodations")
    kind = models.CharField(max_length=20, choices=Kind.choices)
    provider = models.CharField(max_length=100, blank=True, help_text="e.g. HOAS, TYS, PSOAS, private landlord")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RESEARCHING)
    city = models.CharField(max_length=100, blank=True)
    address = models.CharField(max_length=300, blank=True)
    monthly_rent_eur = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    deposit_eur = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    contract_start = models.DateField(null=True, blank=True)
    contract_end = models.DateField(null=True, blank=True)
    applied_at = models.DateField(null=True, blank=True)
    confirmed_at = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_kind_display()} — {self.student}"


class Flight(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="flights")
    airline = models.CharField(max_length=100)
    flight_number = models.CharField(max_length=20)
    booking_reference = models.CharField(max_length=50, blank=True)
    depart_airport = models.CharField(max_length=100, help_text="e.g. ISB — Islamabad")
    arrive_airport = models.CharField(max_length=100, help_text="e.g. HEL — Helsinki-Vantaa")
    depart_at = models.DateTimeField()
    arrive_at = models.DateTimeField()
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["depart_at"]

    def __str__(self):
        return f"{self.flight_number} {self.depart_airport} → {self.arrive_airport}"
