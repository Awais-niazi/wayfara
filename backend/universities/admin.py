from django.contrib import admin

from .models import Campus, Program, University


class CampusInline(admin.TabularInline):
    model = Campus
    extra = 0


@admin.register(University)
class UniversityAdmin(admin.ModelAdmin):
    list_display = ["name", "institution_type", "city", "is_active"]
    list_filter = ["institution_type", "is_active"]
    search_fields = ["name", "city"]
    inlines = [CampusInline]


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = [
        "name", "university", "degree_level", "field_of_study",
        "tuition_fee_eur", "intake", "application_deadline", "is_active",
    ]
    list_filter = ["degree_level", "intake", "field_of_study", "is_active"]
    search_fields = ["name", "university__name"]
