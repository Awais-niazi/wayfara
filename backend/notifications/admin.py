from django.contrib import admin, messages
from django.db import transaction

from .models import Broadcast, Notification
from .tasks import send_broadcast_task


@admin.register(Broadcast)
class BroadcastAdmin(admin.ModelAdmin):
    list_display = ["title", "category", "audience", "status", "recipient_count", "sent_at"]
    list_filter = ["status", "category", "audience"]
    readonly_fields = ["status", "sent_at", "recipient_count"]
    actions = ["send_now"]

    @admin.action(description="Send now to the selected audience")
    def send_now(self, request, queryset):
        """Fan the broadcast out via Celery. Drafts only — a sent broadcast
        can't be re-fired from the UI (compose a new one instead)."""
        queued = 0
        for broadcast in queryset:
            if broadcast.status != Broadcast.Status.DRAFT:
                self.message_user(
                    request, f"'{broadcast.title}' was already sent — skipped.",
                    messages.WARNING,
                )
                continue
            transaction.on_commit(
                lambda pk=broadcast.pk: send_broadcast_task.delay(pk)
            )
            queued += 1
        if queued:
            self.message_user(request, f"{queued} broadcast(s) queued for sending.", messages.SUCCESS)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Read-only surface for support/debugging — notifications are created by
    the platform (services.notify), never composed here."""

    list_display = ["user", "category", "title", "created_at", "read_at", "push_sent_at"]
    list_filter = ["category"]
    search_fields = ["user__email", "title"]
    readonly_fields = [f.name for f in Notification._meta.fields]

    def has_add_permission(self, request):
        return False
