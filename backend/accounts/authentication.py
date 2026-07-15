"""Supabase-issued JWT authentication for DRF.

Supabase is the identity authority: the mobile app authenticates directly
against it and forwards the resulting access token as a Bearer credential.
Django's job is only to *verify* that token and resolve it to a local `User`
row (its domain shadow), provisioned just-in-time on first sight.

Verification is HS256 against the project's JWT secret — the shared-secret
scheme Supabase issues by default. Newer projects can move to asymmetric
(ES256 via JWKS); swap the `decode` call for a JWKS-backed key fetch if so.
"""

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import authentication, exceptions

User = get_user_model()

# Supabase stamps every user access token with this audience.
SUPABASE_AUDIENCE = "authenticated"


class SupabaseJWTAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        header = authentication.get_authorization_header(request).split()
        if not header or header[0].lower() != b"bearer":
            return None  # no credentials → unauthenticated, let permissions 401
        if len(header) != 2:
            raise exceptions.AuthenticationFailed("Malformed Authorization header.")

        secret = getattr(settings, "SUPABASE_JWT_SECRET", "")
        if not secret:
            # A token was presented but we can't verify anything — treat as a
            # server misconfiguration rather than silently authenticating.
            raise exceptions.AuthenticationFailed("Auth is not configured.")

        token = header[1].decode("utf-8", "ignore")
        try:
            claims = jwt.decode(
                token,
                secret,
                algorithms=["HS256"],
                audience=SUPABASE_AUDIENCE,
            )
        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed("Token has expired.")
        except jwt.InvalidTokenError:
            raise exceptions.AuthenticationFailed("Invalid token.")

        sub = claims.get("sub")
        email = (claims.get("email") or "").lower()
        if not sub:
            raise exceptions.AuthenticationFailed("Token is missing a subject.")

        user = self._get_or_provision(sub, email)
        if not user.is_active:
            raise exceptions.AuthenticationFailed("User account is disabled.")
        return (user, token)

    def authenticate_header(self, request):
        return "Bearer"

    @staticmethod
    def _get_or_provision(supabase_id, email):
        """Load the local shadow by Supabase UUID; create/link it on first sight.

        A row may already exist keyed by email (e.g. an advisor provisioned
        before their first login) — link it rather than colliding on the
        unique email.
        """
        user = User.objects.filter(supabase_id=supabase_id).first()
        if user is not None:
            if email and user.email != email:
                user.email = email
                user.save(update_fields=["email"])
            return user

        user, _ = User.objects.get_or_create(
            email=email,
            defaults={"supabase_id": supabase_id, "email_verified": True},
        )
        if user.supabase_id is None:
            user.supabase_id = supabase_id
            user.email_verified = True
            user.save(update_fields=["supabase_id", "email_verified"])
        return user
