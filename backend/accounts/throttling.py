from rest_framework.throttling import SimpleRateThrottle


class OTPEmailRateThrottle(SimpleRateThrottle):
    """Rate-limit OTP requests per *target inbox*, not per client IP.

    IP throttles don't stop an attacker rotating IPs to flood one person's
    mailbox with codes (annoyance + email-sender reputation damage). Keying
    on the requested email closes that hole. Requests without an email fall
    through un-throttled — serializer validation rejects them anyway.
    """

    scope = "otp_email"

    def get_cache_key(self, request, view):
        # request.data can be a list/str for malformed JSON bodies — .get()
        # on those raised, turning garbage input into an unauthenticated 500.
        if not isinstance(request.data, dict):
            return None  # no key -> not throttled here; validation rejects it
        email = request.data.get("email")
        if not isinstance(email, str) or not email:
            return None  # no key -> not throttled here; validation handles it
        return self.cache_format % {
            "scope": self.scope,
            "ident": email.strip().lower(),
        }
