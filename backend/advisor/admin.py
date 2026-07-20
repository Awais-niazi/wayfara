from django.contrib import admin

from .models import AdvisorMessage, AdvisorThread


class MessageInline(admin.TabularInline):
    model = AdvisorMessage
    extra = 0
    readonly_fields = ["sender", "body", "created_at", "read_at"]
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(AdvisorThread)
class AdvisorThreadAdmin(admin.ModelAdmin):
    list_display = ["student", "advisor", "last_message_at", "created_at"]
    # Student.__str__ reads user.email — join it or the list queries per row.
    list_select_related = ["student__user", "advisor"]
    search_fields = ["student__user__email", "advisor__email"]
    readonly_fields = ["student", "advisor", "created_at", "last_message_at"]
    inlines = [MessageInline]
