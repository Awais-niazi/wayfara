from django.contrib import admin

from .models import Conversation, Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ["role", "content", "feedback", "created_at"]


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ["__str__", "student", "phase_context", "updated_at"]
    list_filter = ["phase_context"]
    inlines = [MessageInline]
