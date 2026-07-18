"""Operational state — the app's own pulse, queryable and admin-visible.

Heartbeat rows are dead-man's switches for everything periodic: each critical
job stamps its row on success. /healthz/deep and the canary watchdog read the
staleness; an external uptime monitor (armed at deploy) turns a stale pulse
into a page. See docs/PLAYBOOK.md § Monitoring.
"""

from django.db import models
from django.utils import timezone


class Heartbeat(models.Model):
    """Last known pulse of one periodic job (see ops.services.EXPECTED_EVERY)."""

    name = models.CharField(max_length=60, unique=True)
    last_ok = models.DateTimeField(null=True, blank=True)
    last_error = models.DateTimeField(null=True, blank=True)
    last_error_message = models.TextField(blank=True)
    # Free-form counters from the last successful run ({"dispatched": 3, ...})
    last_result = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} (ok {self.last_ok:%d %b %H:%M})" if self.last_ok else self.name

    @classmethod
    def beat(cls, name, result=None):
        obj, _ = cls.objects.update_or_create(
            name=name,
            defaults={"last_ok": timezone.now(), "last_result": result or {}},
        )
        return obj

    @classmethod
    def fail(cls, name, message):
        obj, _ = cls.objects.update_or_create(
            name=name,
            defaults={"last_error": timezone.now(), "last_error_message": str(message)[:2000]},
        )
        return obj


class PushTicket(models.Model):
    """One Expo push ticket awaiting its delivery receipt.

    Expo accepts a push synchronously (ticket) but can fail it minutes later
    (receipt) — without checking receipts, delivery failures are invisible.
    ops.tasks.check_push_receipts_task fetches receipts, prunes dead device
    tokens, and surfaces persistent errors.
    """

    ticket_id = models.CharField(max_length=64, unique=True)
    token = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    checked = models.BooleanField(default=False)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.ticket_id} ({'checked' if self.checked else 'pending'})"
