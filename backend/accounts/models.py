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
    """Auth + entitlement only. Domain profile lives on students.Student.

    `tier` sits here (not on Student) because it is account-level: the payment
    webhook flips it, and it is never writable through the API.
    """

    class Tier(models.TextChoices):
        FREE = "free", "Free"
        FULL = "full", "Full Access"
        PREMIUM = "premium", "Premium"

    username = None
    email = models.EmailField("email address", unique=True)
    tier = models.CharField(max_length=10, choices=Tier.choices, default=Tier.FREE)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email
