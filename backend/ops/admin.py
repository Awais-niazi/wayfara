from django.contrib import admin

from .models import Heartbeat, PushTicket


@admin.register(Heartbeat)
class HeartbeatAdmin(admin.ModelAdmin):
    list_display = ("name", "last_ok", "last_error", "last_error_message", "last_result")
    readonly_fields = ("name", "last_ok", "last_error", "last_error_message", "last_result")

    def has_add_permission(self, request):
        return False


@admin.register(PushTicket)
class PushTicketAdmin(admin.ModelAdmin):
    list_display = ("ticket_id", "token", "created_at", "checked")
    list_filter = ("checked",)
    readonly_fields = ("ticket_id", "token", "created_at", "checked")

    def has_add_permission(self, request):
        return False
