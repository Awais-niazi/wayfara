from rest_framework.permissions import BasePermission


class IsAdvisor(BasePermission):
    """Gate for the /api/advisor/ surface. Advisors are provisioned by a
    superuser in admin (User.role = advisor); there is no self-signup path."""

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.role == user.Role.ADVISOR
        )
