from django.contrib import admin

from .models import Campus, Program, University, UniversityProfile


class CampusInline(admin.TabularInline):
    model = Campus
    extra = 0


class ProfileInline(admin.StackedInline):
    model = UniversityProfile
    extra = 0


@admin.register(University)
class UniversityAdmin(admin.ModelAdmin):
    list_display = ["name", "institution_type", "city", "is_active"]
    list_filter = ["institution_type", "is_active"]
    search_fields = ["name", "city"]
    inlines = [ProfileInline, CampusInline]


@admin.register(UniversityProfile)
class UniversityProfileAdmin(admin.ModelAdmin):
    list_display = [
        "university", "featured", "sort_order", "world_ranking",
        "ranking_system", "operational_verified", "needs_review",
    ]
    list_filter = ["featured", "operational_verified", "needs_review", "ranking_system"]
    list_editable = ["featured", "sort_order"]
    search_fields = ["university__name"]


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = [
        "name", "university", "degree_level", "field_of_study",
        "tuition_fee_eur", "intake", "application_deadline", "is_active",
    ]
    list_filter = ["degree_level", "intake", "field_of_study", "is_active"]
    search_fields = ["name", "university__name"]
