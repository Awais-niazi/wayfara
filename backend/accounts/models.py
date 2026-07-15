from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    """Manager for email-based authentication (no username). Identity is the
    email; credentials live in Supabase."""

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
    """Auth mirror + entitlement. Domain profile lives on students.Student.

    Identity now belongs to Supabase: credentials, sessions, OTP, and token
    issuance are all theirs. This row is a local shadow keyed by `supabase_id`
    (the Supabase user UUID), created just-in-time the first time a valid
    Supabase token is seen. `tier`/`role` and the person's name are ours —
    account-level facts Supabase doesn't know about. (A separate username was
    collected briefly in July 2026, then dropped: students are greeted by
    first name instead.)
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
    # The Supabase auth user UUID. Null only for the brief window before first
    # login provisions it (and for fixtures/tests using force_authenticate).
    supabase_id = models.UUIDField(unique=True, null=True, blank=True)
    tier = models.CharField(max_length=10, choices=Tier.choices, default=Tier.FREE)
    # Advisors are provisioned by a superuser (management command / admin) —
    # there is no advisor self-signup. Staff/admin access stays on
    # is_staff/is_superuser as usual.
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
