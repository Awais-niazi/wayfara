"""Supabase-issued JWT authentication for DRF.

Supabase is the identity authority: the mobile app authenticates directly
against it and forwards the resulting access token as a Bearer credential.
Django's job is only to *verify* that token and resolve it to a local `User`
row (its domain shadow), provisioned just-in-time on first sight.

Verification supports both Supabase signing schemes:
- Asymmetric (ES256/RS256, the default on newer projects): the public key is
  fetched from the project's JWKS endpoint and cached; no shared secret needed.
- Legacy HS256: verified against SUPABASE_JWT_SECRET.
The token's own header picks the path, so a key rotation on the Supabase side
needs no code change here.
"""

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import authentication, exceptions

User = get_user_model()

# Supabase stamps every user access token with this audience.
SUPABASE_AUDIENCE = "authenticated"

ASYMMETRIC_ALGORITHMS = ["ES256", "RS256", "EdDSA"]

# Module-level so the fetched JWKS is cached across requests.
_jwks_client = None


def _get_jwks_client():
    global _jwks_client
    if _jwks_client is None:
        base = settings.SUPABASE_URL.rstrip("/")
        _jwks_client = jwt.PyJWKClient(
            f"{base}/auth/v1/.well-known/jwks.json",
            cache_keys=True,
            lifespan=3600,
        )
    return _jwks_client


class SupabaseJWTAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        header = authentication.get_authorization_header(request).split()
        if not header or header[0].lower() != b"bearer":
            return None  # no credentials → unauthenticated, let permissions 401
        if len(header) != 2:
            raise exceptions.AuthenticationFailed("Malformed Authorization header.")

        token = header[1].decode("utf-8", "ignore")
        claims = self._decode(token)

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
    def _decode(token):
        """Verify the token with whichever scheme its header declares."""
        try:
            alg = jwt.get_unverified_header(token).get("alg", "")
        except jwt.InvalidTokenError:
            raise exceptions.AuthenticationFailed("Invalid token.")

        if alg == "HS256":
            key = getattr(settings, "SUPABASE_JWT_SECRET", "")
            algorithms = ["HS256"]
            if not key:
                # A token was presented but we can't verify anything — treat as
                # a server misconfiguration rather than silently authenticating.
                raise exceptions.AuthenticationFailed("Auth is not configured.")
        elif alg in ASYMMETRIC_ALGORITHMS:
            if not getattr(settings, "SUPABASE_URL", ""):
                raise exceptions.AuthenticationFailed("Auth is not configured.")
            try:
                key = _get_jwks_client().get_signing_key_from_jwt(token).key
            except jwt.PyJWKClientError:
                raise exceptions.AuthenticationFailed("Unable to verify token.")
            algorithms = ASYMMETRIC_ALGORITHMS
        else:
            raise exceptions.AuthenticationFailed("Invalid token.")

        try:
            return jwt.decode(
                token, key, algorithms=algorithms, audience=SUPABASE_AUDIENCE
            )
        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed("Token has expired.")
        except jwt.InvalidTokenError:
            raise exceptions.AuthenticationFailed("Invalid token.")

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
