from django.contrib import admin

from .models import Accommodation, Document, Flight, Reminder, Student, Task, TaskTemplate


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ["user", "study_level", "intake", "intake_year", "stage", "current_phase", "onboarding_completed"]
    list_filter = ["study_level", "intake", "stage", "onboarding_completed"]
    search_fields = ["user__email"]


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ["doc_type", "student", "status", "expires_at", "uploaded_at"]
    list_filter = ["doc_type", "status"]
    search_fields = ["student__user__email"]


@admin.register(TaskTemplate)
class TaskTemplateAdmin(admin.ModelAdmin):
    list_display = ["phase", "order", "title", "offset_anchor", "offset_days", "is_critical", "is_active"]
    list_filter = ["phase", "is_critical", "is_active"]
    list_editable = ["order"]
    search_fields = ["title"]


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ["title", "student", "phase", "due_date", "status"]
    list_filter = ["phase", "status"]
    search_fields = ["title", "student__user__email"]


@admin.register(Reminder)
class ReminderAdmin(admin.ModelAdmin):
    list_display = ["title", "student", "remind_at", "channel", "sent"]
    list_filter = ["channel", "sent"]


@admin.register(Accommodation)
class AccommodationAdmin(admin.ModelAdmin):
    list_display = ["student", "kind", "provider", "status", "city", "monthly_rent_eur"]
    list_filter = ["kind", "status"]


@admin.register(Flight)
class FlightAdmin(admin.ModelAdmin):
    list_display = ["student", "flight_number", "depart_airport", "arrive_airport", "depart_at"]
