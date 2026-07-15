from django.conf import settings
from django.db import models


class Notification(models.Model):
    """One item in a user's notification inbox.

    Every notification in the product — reminder, advisor message, news,
    scraper-detected update, future doc/visa events — is a row here, created
    exclusively through services.notify(). Push delivery mirrors the row; the
    row itself is the durable record (a missed push isn't a lost message).
    """

    class Category(models.TextChoices):
        REMINDER = "reminder", "Journey reminder"
        ADVISOR = "advisor", "Advisor message"
        NEWS = "news", "News / announcement"
        UPDATE = "update", "University / policy update"
        SYSTEM = "system", "System"
        # Reserved for later phases (doc verification, application/visa events)
        DOCUMENT = "document", "Document"
        APPLICATION = "application", "Application"
        VISA = "visa", "Visa"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    category = models.CharField(max_length=20, choices=Category.choices)
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    # Deep-link payload the app routes on, e.g. {"type": "task", "task_id": 7}.
    data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    push_sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["user", "read_at"]),
        ]

    def __str__(self):
        return f"{self.get_category_display()} → {self.user}: {self.title}"


class Broadcast(models.Model):
    """An admin-composed announcement fanned out to a targeted audience.

    Written in Django admin, sent via the "Send now" action → Celery task →
    one Notification per recipient. Targeting is deliberately coarse for now
    (everyone / intake year / matched university); finer segments can be
    added as audiences without touching the fan-out.
    """

    class Audience(models.TextChoices):
        ALL = "all", "All onboarded students"
        BY_INTAKE_YEAR = "by_intake_year", "Students targeting an intake year"
        BY_UNIVERSITY = "by_university", "Students matched to a university"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENDING = "sending", "Sending"
        SENT = "sent", "Sent"

    title = models.CharField(max_length=200)
    body = models.TextField()
    category = models.CharField(
        max_length=20,
        choices=Notification.Category.choices,
        default=Notification.Category.NEWS,
    )
    audience = models.CharField(
        max_length=20, choices=Audience.choices, default=Audience.ALL
    )
    intake_year = models.PositiveSmallIntegerField(
        null=True, blank=True, help_text="Required when audience = intake year"
    )
    university = models.ForeignKey(
        "universities.University",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Required when audience = matched university",
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    recipient_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} [{self.get_status_display()}]"
