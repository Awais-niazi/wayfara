import secrets

from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone


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
    """Auth + entitlement only. Domain profile lives on students.Student.

    `tier` sits here (not on Student) because it is account-level: the payment
    webhook flips it, and it is never writable through the API.
    """

    class Tier(models.TextChoices):
        FREE = "free", "Free"
        FULL = "full", "Full Access"
        PREMIUM = "premium", "Premium"

    class Role(models.TextChoices):
        STUDENT = "student", "Student"
        ADVISOR = "advisor", "Advisor"

    username = None
    email = models.EmailField("email address", unique=True)
    tier = models.CharField(max_length=10, choices=Tier.choices, default=Tier.FREE)
    # Advisors are provisioned by a superuser in admin — there is no advisor
    # signup. Staff/admin access stays on is_staff/is_superuser as usual.
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.STUDENT)
    email_verified = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    @property
    def has_advisor_access(self):
        """Human-advisor messaging is a Premium entitlement."""
        return self.tier == self.Tier.PREMIUM

    def __str__(self):
        return self.email


class DeviceToken(models.Model):
    """An Expo push token for one of a user's devices.

    Registered by the app after the user grants notification permission;
    pruned when Expo reports the token is no longer valid.
    """

    class Platform(models.TextChoices):
        IOS = "ios", "iOS"
        ANDROID = "android", "Android"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="device_tokens"
    )
    token = models.CharField(max_length=255, unique=True)
    platform = models.CharField(max_length=10, choices=Platform.choices, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user} · {self.platform or 'device'}"


class EmailOTP(models.Model):
    """One-time 6-digit code for passwordless onboarding/login.

    Issuing a new code invalidates all previous unused codes for the user.
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="otps")
    code = models.CharField(max_length=6)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["user", "used", "expires_at"])]

    @classmethod
    def issue(cls, user):
        cls.objects.filter(user=user, used=False).update(used=True)
        return cls.objects.create(
            user=user,
            code=f"{secrets.randbelow(1_000_000):06d}",
            expires_at=timezone.now() + timezone.timedelta(minutes=settings.OTP_LIFETIME_MINUTES),
        )

    def is_valid_now(self):
        return (
            not self.used
            and self.attempts < settings.OTP_MAX_ATTEMPTS
            and self.expires_at > timezone.now()
        )
