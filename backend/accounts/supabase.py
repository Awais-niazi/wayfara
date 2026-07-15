"""Server-side Supabase Admin API calls.

Only privileged operations the app can't do for itself live here — chiefly
advisor provisioning, which mints a Supabase identity from the service-role
key and sends the invite email. Student signup happens entirely client-side
against the anon key, so it never touches this module.
"""

import requests
from django.conf import settings


class SupabaseAdminError(RuntimeError):
    """Raised when the Supabase Admin API call fails or isn't configured."""


def _admin_headers():
    key = getattr(settings, "SUPABASE_SERVICE_ROLE_KEY", "")
    url = getattr(settings, "SUPABASE_URL", "")
    if not key or not url:
        raise SupabaseAdminError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set to provision "
            "advisors."
        )
    return url.rstrip("/"), {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def invite_user(email):
    """Create + invite a Supabase auth user by email. Returns the user UUID.

    Uses the invite endpoint so Supabase emails a set-password link and the
    advisor's password is only ever known to them — the admin never holds it.
    """
    base, headers = _admin_headers()
    resp = requests.post(
        f"{base}/auth/v1/invite",
        json={"email": email},
        headers=headers,
        timeout=15,
    )
    if resp.status_code >= 400:
        raise SupabaseAdminError(
            f"Supabase invite failed ({resp.status_code}): {resp.text}"
        )
    data = resp.json()
    user_id = data.get("id") or data.get("user", {}).get("id")
    if not user_id:
        raise SupabaseAdminError(f"Supabase invite returned no user id: {data}")
    return user_id


def provision_advisor(email):
    """Invite an advisor in Supabase and create/link the local advisor row.

    Returns (user, created). An already-linked account (has a supabase_id) is
    just promoted to advisor — no second invite. Raises SupabaseAdminError if
    a brand-new account can't be invited.
    """
    from django.contrib.auth import get_user_model

    User = get_user_model()
    email = email.strip().lower()
    user = User.objects.filter(email__iexact=email).first()

    if user is not None and user.supabase_id is not None:
        # Existing Supabase identity — a role change is all that's needed.
        if user.role != User.Role.ADVISOR:
            user.role = User.Role.ADVISOR
            user.save(update_fields=["role"])
        return user, False

    supabase_id = invite_user(email)
    created = user is None
    if user is None:
        user = User(email=email)
        # The password lives in Supabase; the Django row must never authenticate.
        user.set_unusable_password()
    user.role = User.Role.ADVISOR
    user.supabase_id = supabase_id
    user.email_verified = True
    user.save()
    return user, created
