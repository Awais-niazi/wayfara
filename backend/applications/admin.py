from django.contrib import admin

from .models import Application, Visa


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ["student", "program", "status", "fit", "priority", "tuition_paid", "submitted_at"]
    list_filter = ["status", "fit", "tuition_paid"]
    search_fields = ["student__user__email", "program__name"]


@admin.register(Visa)
class VisaAdmin(admin.ModelAdmin):
    list_display = ["student", "status", "embassy_location", "embassy_appointment_at", "submitted_at", "decision_at"]
    list_filter = ["status", "embassy_location"]
    search_fields = ["student__user__email", "enter_finland_reference"]
