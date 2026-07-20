from django.contrib import admin

from .models import Application, Match, PolicyFigure, Visa


@admin.register(PolicyFigure)
class PolicyFigureAdmin(admin.ModelAdmin):
    list_display = ["code", "label", "value", "unit", "needs_verification", "updated_at"]
    list_filter = ["needs_verification"]
    search_fields = ["code", "label"]


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ["student", "program", "fit", "score", "created_at"]
    # Student.__str__ → user.email; Program.__str__ → university.name. Join
    # both second levels or the change list queries twice per row.
    list_select_related = ["student__user", "program__university"]
    list_filter = ["fit"]
    search_fields = ["student__user__email", "program__name"]


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ["student", "program", "status", "fit", "priority", "tuition_paid", "submitted_at"]
    list_select_related = ["student__user", "program__university"]
    list_filter = ["status", "fit", "tuition_paid"]
    search_fields = ["student__user__email", "program__name"]


@admin.register(Visa)
class VisaAdmin(admin.ModelAdmin):
    list_display = ["student", "status", "embassy_location", "embassy_appointment_at", "submitted_at", "decision_at"]
    list_select_related = ["student__user"]
    list_filter = ["status", "embassy_location"]
    search_fields = ["student__user__email", "enter_finland_reference"]
