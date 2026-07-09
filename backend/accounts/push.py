"""Expo push delivery (service layer).

Sends to Expo's push API for the Wayfara app's iOS/Android devices. A push
failure must never break the action that triggered it, so everything here is
best-effort: it logs and prunes dead tokens rather than raising.
"""

import logging

import requests
from django.conf import settings

logger = logging.getLogger("accounts.push")

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


def send_push_to_user(user, title, body, data=None):
    """Deliver one notification to every registered device of `user`.

    No-ops silently when the user has no devices (the common case in tests
    and for web-only users), so callers never need to guard.
    """
    tokens = list(user.device_tokens.values_list("token", flat=True))
    if not tokens or not getattr(settings, "PUSH_ENABLED", True):
        return

    messages = [
        {"to": t, "title": title, "body": body, "sound": "default", "data": data or {}}
        for t in tokens
    ]
    try:
        resp = requests.post(EXPO_PUSH_URL, json=messages, timeout=10)
        resp.raise_for_status()
        _prune_dead_tokens(resp.json(), tokens)
    except requests.RequestException as exc:
        logger.warning("Expo push failed for %s: %s", user, exc)


def _prune_dead_tokens(response_json, tokens):
    """Delete tokens Expo reports as no longer registered."""
    from .models import DeviceToken

    tickets = response_json.get("data", []) if isinstance(response_json, dict) else []
    dead = [
        tokens[i]
        for i, ticket in enumerate(tickets)
        if i < len(tokens)
        and ticket.get("status") == "error"
        and ticket.get("details", {}).get("error") == "DeviceNotRegistered"
    ]
    if dead:
        DeviceToken.objects.filter(token__in=dead).delete()
