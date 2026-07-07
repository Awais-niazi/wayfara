from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class FinnGuideUserAdmin(UserAdmin):
    ordering = ["email"]
    list_display = ["email", "tier", "current_phase", "stage", "onboarding_completed"]
    list_filter = ["tier", "study_level", "intake", "stage"]
    search_fields = ["email", "first_name", "last_name"]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name")}),
        (
            "Onboarding profile",
            {
                "fields": (
                    "study_level",
                    "field_of_study",
                    "grades",
                    "language_test_status",
                    "language_test_score",
                    "budget_eur_per_year",
                    "intake",
                    "intake_year",
                    "stage",
                    "onboarding_completed",
                )
            },
        ),
        ("Journey & entitlement", {"fields": ("current_phase", "tier")}),
        (
            "Permissions",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "password1", "password2")}),
    )
