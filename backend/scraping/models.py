from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone


class ScrapeSource(models.Model):
    """A configured data source and which scraper class handles it."""

    name = models.CharField(max_length=200, unique=True)
    scraper_key = models.CharField(
        max_length=100, help_text="Key registered in scraping.scrapers.SCRAPER_REGISTRY"
    )
    url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    last_run_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name


class ScrapeRun(models.Model):
    """Audit record for one execution of one source's scraper."""

    class Status(models.TextChoices):
        RUNNING = "running", "Running"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"

    source = models.ForeignKey(ScrapeSource, on_delete=models.CASCADE, related_name="runs")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.RUNNING)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    records_scraped = models.PositiveIntegerField(default=0)
    changes_detected = models.PositiveIntegerField(default=0)
    error = models.TextField(blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.source.name} @ {self.started_at:%Y-%m-%d %H:%M} [{self.status}]"

    def finish(self, status, error=""):
        self.status = status
        self.error = error
        self.finished_at = timezone.now()
        self.save(
            update_fields=[
                "status", "error", "finished_at", "records_scraped", "changes_detected"
            ]
        )


class DataChange(models.Model):
    """One field-level difference the scraper detected between the live DB and
    a freshly scraped value. Low-risk changes are applied immediately; critical
    ones wait in PENDING_REVIEW until an admin approves.
    """

    class Risk(models.TextChoices):
        LOW = "low", "Low"
        CRITICAL = "critical", "Critical"

    class Status(models.TextChoices):
        PENDING_REVIEW = "pending_review", "Pending review"
        APPLIED = "applied", "Applied"
        REJECTED = "rejected", "Rejected"

    run = models.ForeignKey(ScrapeRun, on_delete=models.CASCADE, related_name="changes")

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    target = GenericForeignKey("content_type", "object_id")

    field_name = models.CharField(max_length=100)
    old_display = models.TextField(blank=True)
    new_display = models.TextField(blank=True)
    new_value = models.JSONField(help_text="Raw scraped value, coerced to the field type on apply")

    risk = models.CharField(max_length=10, choices=Risk.choices)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING_REVIEW)
    applied_automatically = models.BooleanField(default=False)
    applied_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "risk"])]

    def __str__(self):
        return f"{self.target}.{self.field_name}: {self.old_display!r} -> {self.new_display!r}"

    def apply(self, automatic=False):
        """Coerce the scraped value to the field's type and write it to the target."""
        if self.target is None:
            return
        field = self.target._meta.get_field(self.field_name)
        setattr(self.target, self.field_name, field.to_python(self.new_value))
        self.target.save(update_fields=[self.field_name])
        self.status = self.Status.APPLIED
        self.applied_automatically = automatic
        self.applied_at = timezone.now()
        self.save(update_fields=["status", "applied_automatically", "applied_at"])

    def reject(self):
        self.status = self.Status.REJECTED
        self.save(update_fields=["status"])
