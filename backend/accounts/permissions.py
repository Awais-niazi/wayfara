from rest_framework.permissions import BasePermission

SAFE_METHODS = ("GET", "HEAD", "OPTIONS")


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


class HasAdvisorAccess(BasePermission):
    """Student side of advisor messaging. Reading a thread is open to any
    authenticated student; *sending* requires the Premium entitlement, so a
    lapsed subscription leaves the conversation readable but read-only."""

    message = "Messaging an advisor is a Premium feature."

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return user.has_advisor_access
