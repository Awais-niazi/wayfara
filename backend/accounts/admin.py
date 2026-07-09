from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin

from advisor.services import send_advisor_activation

from .models import DeviceToken, User


@admin.register(User)
class WayfaraUserAdmin(UserAdmin):
    ordering = ["email"]
    list_display = ["email", "role", "tier", "is_active", "date_joined"]
    list_filter = ["role", "tier", "is_active"]
    search_fields = ["email", "first_name", "last_name"]
    actions = ["provision_as_advisor"]

    @admin.action(description="Provision as advisor + send activation link")
    def provision_as_advisor(self, request, queryset):
        """Make the selected users advisors and email each an invite link.

        Any existing password is wiped (set unusable) so only the advisor's
        own self-set password will ever work — the admin never holds it.
        """
        for user in queryset:
            user.role = User.Role.ADVISOR
            user.set_unusable_password()
            user.save(update_fields=["role", "password"])
            send_advisor_activation(user)
        self.message_user(
            request,
            f"{queryset.count()} advisor(s) provisioned; activation links sent.",
            messages.SUCCESS,
        )

    fieldsets = (
        (None, {"fields": ("email", "password")}),
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
