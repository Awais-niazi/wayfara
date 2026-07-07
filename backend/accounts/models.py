from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    """Manager for email-based authentication (no username)."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """FinnGuide user: auth + onboarding profile + entitlement tier.

    Profile fields mirror the Phase 0 onboarding questions and stay blank
    until onboarding completes.
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

    class Tier(models.TextChoices):
        FREE = "free", "Free"
        FULL = "full", "Full Access"
        PREMIUM = "premium", "Premium"

    username = None
    email = models.EmailField("email address", unique=True)

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

    # Journey + entitlement
    current_phase = models.PositiveSmallIntegerField(default=0)
    tier = models.CharField(max_length=10, choices=Tier.choices, default=Tier.FREE)
    onboarding_completed = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email
