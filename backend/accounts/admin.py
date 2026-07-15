from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin

from .models import DeviceToken, User
from .supabase import SupabaseAdminError, provision_advisor


@admin.register(User)
class WayfaraUserAdmin(UserAdmin):
    ordering = ["email"]
    list_display = ["email", "first_name", "last_name", "role", "tier", "is_active", "date_joined"]
    list_filter = ["role", "tier", "is_active"]
    search_fields = ["email", "first_name", "last_name"]
    readonly_fields = ["supabase_id"]
    actions = ["provision_as_advisor"]

    @admin.action(description="Provision as advisor (Supabase invite)")
    def provision_as_advisor(self, request, queryset):
        """Make the selected users advisors. New accounts get a Supabase invite
        so they set their own password; already-linked accounts are just
        promoted. The admin never holds an advisor's password."""
        done = 0
        for user in queryset:
            try:
                provision_advisor(user.email)
                done += 1
            except SupabaseAdminError as exc:
                self.message_user(request, f"{user.email}: {exc}", messages.ERROR)
        if done:
            self.message_user(
                request, f"{done} advisor(s) provisioned.", messages.SUCCESS
            )

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Identity", {"fields": ("supabase_id",)}),
        ("Personal info", {"fields": ("first_name", "last_name")}),
        ("Entitlement", {"fields": ("tier", "role")}),
        (
            "Permissions",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "password1", "password2")}),
    )


@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
    list_display = ["user", "platform", "created_at", "last_used_at"]
    list_filter = ["platform"]
    search_fields = ["user__email"]
