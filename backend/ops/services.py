"""Observability core: deep health, dead-man staleness, business canaries.

Three layers of "nothing breaks silently":
  1. Exceptions   → Sentry (settings.py init; Django + Celery integrations).
  2. Liveness     → Heartbeat rows stamped by periodic jobs; staleness turns
                    /healthz/deep unhealthy (external monitor pages) and the
                    canary watchdog raises a Sentry event (partial outages).
  3. Correctness  → run_canaries(): product-level checks encoding real
                    incidents (July 2026 testing week) where nothing threw
                    but the product was broken.

Every alert names its playbook entry: docs/PLAYBOOK.md.
"""

import logging
from datetime import timedelta

import requests
from django.conf import settings
from django.db import connection
from django.utils import timezone

from .models import Heartbeat, PushTicket

logger = logging.getLogger("ops")

EXPO_RECEIPTS_URL = "https://exp.host/--/api/v2/push/getReceipts"

# Dead-man thresholds: a heartbeat older than this means the job is down.
# Generous multiples of each schedule so restarts/deploys don't false-page.
EXPECTED_EVERY = {
    "celery-beat": timedelta(minutes=15),        # pulse task runs every 5 min
    "reminder-dispatcher": timedelta(minutes=20),  # runs every 5 min
    "push-receipts": timedelta(hours=1),          # runs every 15 min
    "canaries": timedelta(hours=3),               # runs hourly
    "scraper-monthly": timedelta(days=35),        # 1st of month, 2 AM Helsinki
}


def _capture(message, level="error", fingerprint=None):
    """Sentry event + log line; degrades to log-only when Sentry is off."""
    logger.error("[ops] %s", message)
    if getattr(settings, "SENTRY_DSN", ""):
        import sentry_sdk

        with sentry_sdk.push_scope() as scope:
            if fingerprint:
                scope.fingerprint = [fingerprint]
            sentry_sdk.capture_message(message, level=level)


# ─── Deep health ─────────────────────────────────────────────────────────────

def _check_db():
    with connection.cursor() as cur:
        cur.execute("SELECT 1")
    return "ok"


def _check_broker():
    """Redis broker reachability (skip in eager mode — no broker in the loop)."""
    if settings.CELERY_TASK_ALWAYS_EAGER:
        return "skipped (eager mode)"
    import redis

    redis.Redis.from_url(settings.CELERY_BROKER_URL, socket_timeout=3).ping()
    return "ok"


def _check_storage():
    """R2 reachability via a cheap existence probe (local disk in dev)."""
    from django.core.files.storage import default_storage

    default_storage.exists("ops/healthcheck-probe")  # result irrelevant; reachability isn't
    return "ok"


def _check_supabase():
    """JWKS endpoint reachability — if this is down, every login fails."""
    url = getattr(settings, "SUPABASE_URL", "")
    if not url:
        return "skipped (not configured)"
    resp = requests.get(f"{url}/auth/v1/.well-known/jwks.json", timeout=4)
    resp.raise_for_status()
    return "ok"


def _check_heartbeats():
    """Staleness per registered dead-man switch. In dev (eager mode) there is
    no beat process, so staleness is reported but never fails the check."""
    now = timezone.now()
    stale, detail = [], {}
    beats = {h.name: h for h in Heartbeat.objects.all()}
    for name, budget in EXPECTED_EVERY.items():
        hb = beats.get(name)
        if hb is None or hb.last_ok is None:
            detail[name] = "never"
            stale.append(name)
        elif now - hb.last_ok > budget:
            detail[name] = f"stale ({(now - hb.last_ok).total_seconds() // 60:.0f} min)"
            stale.append(name)
        else:
            detail[name] = "ok"
    if settings.CELERY_TASK_ALWAYS_EAGER:
        return {"status": "skipped (eager mode)", "beats": detail}
    return {"status": "ok" if not stale else f"stale: {', '.join(stale)}", "beats": detail}


def deep_health():
    """Full dependency + liveness picture. Returns (healthy: bool, report)."""
    checks = {
        "db": _check_db,
        "broker": _check_broker,
        "storage": _check_storage,
        "supabase": _check_supabase,
    }
    report, healthy = {}, True
    for name, check in checks.items():
        try:
            report[name] = check()
        except Exception as exc:
            report[name] = f"FAIL: {exc.__class__.__name__}: {exc}"
            healthy = False

    hb = _check_heartbeats()
    report["heartbeats"] = hb
    if hb["status"].startswith("stale"):
        healthy = False
    return healthy, report


# ─── Expo push receipts ──────────────────────────────────────────────────────

def record_push_tickets(tickets, tokens):
    """Store ok-tickets for later receipt checking (called from accounts.push)."""
    rows = []
    for i, ticket in enumerate(tickets):
        tid = ticket.get("id")
        if ticket.get("status") == "ok" and tid and i < len(tokens):
            rows.append(PushTicket(ticket_id=tid, token=tokens[i]))
    if rows:
        PushTicket.objects.bulk_create(rows, ignore_conflicts=True)


def check_push_receipts():
    """Fetch delivery receipts for tickets old enough to have one.

    DeviceNotRegistered → prune the token (uninstalled app). Other errors →
    Sentry (these mean pushes are silently not arriving). Old tickets are
    swept so the table can't grow unbounded.
    Returns dict of counters (stored on the heartbeat for the playbook).
    """
    from accounts.models import DeviceToken

    cutoff = timezone.now() - timedelta(minutes=20)
    batch = list(PushTicket.objects.filter(checked=False, created_at__lte=cutoff)[:300])
    counters = {"checked": 0, "delivered": 0, "pruned": 0, "errors": 0}
    if batch:
        resp = requests.post(
            EXPO_RECEIPTS_URL, json={"ids": [t.ticket_id for t in batch]}, timeout=10
        )
        resp.raise_for_status()
        receipts = resp.json().get("data", {})
        by_id = {t.ticket_id: t for t in batch}
        for tid, receipt in receipts.items():
            ticket = by_id.get(tid)
            if ticket is None:
                continue
            counters["checked"] += 1
            if receipt.get("status") == "ok":
                counters["delivered"] += 1
                continue
            error = (receipt.get("details") or {}).get("error", "")
            if error == "DeviceNotRegistered":
                DeviceToken.objects.filter(token=ticket.token).delete()
                counters["pruned"] += 1
            else:
                counters["errors"] += 1
                _capture(
                    f"Expo push receipt error '{error or receipt.get('message')}' — pushes are "
                    "failing after send. PLAYBOOK: 'Push notifications not arriving'.",
                    fingerprint="push-receipt-error",
                )
        PushTicket.objects.filter(pk__in=[t.pk for t in batch]).update(checked=True)
    # Sweep: anything older than 3 days is history (receipts expire anyway).
    PushTicket.objects.filter(created_at__lt=timezone.now() - timedelta(days=3)).delete()
    return counters


# ─── Business canaries ───────────────────────────────────────────────────────

def run_canaries():
    """Product-correctness checks. Each finding = one Sentry event pointing at
    its playbook entry. Returns the list of findings (empty = all quiet).
    """
    from applications.models import Match
    from notifications.models import Notification
    from students.models import Document, Student

    findings = []
    now = timezone.now()

    # 1. Matching went silent: student finished onboarding ≥30 min ago WITH a
    #    positive budget, yet has zero matches. (Blank budget = tuition-free
    #    only, which legitimately yields zero — that case is by design.)
    starved = Student.objects.filter(
        onboarding_completed=True,
        budget_eur_per_year__gt=0,
        created_at__lte=now - timedelta(minutes=30),
        matches__isnull=True,
    ).count()
    if starved:
        findings.append(
            f"{starved} onboarded student(s) with a budget have ZERO matches — matching may "
            "not be running. PLAYBOOK: 'Student sees no matches'."
        )

    # 2. Notifications created but never pushed (notify() crashed mid-way or
    #    push infra down). Only counts rows young enough to be actionable.
    unpushed = Notification.objects.filter(
        push_sent_at__isnull=True,
        created_at__gte=now - timedelta(hours=24),
        created_at__lte=now - timedelta(minutes=15),
        user__device_tokens__isnull=False,
    ).distinct().count()
    if unpushed:
        findings.append(
            f"{unpushed} notification(s) for users WITH devices were never pushed. "
            "PLAYBOOK: 'Push notifications not arriving'."
        )

    # 3. Documents whose blob is missing from storage (upload said 201 but the
    #    object isn't there / was deleted out-of-band).
    from django.core.files.storage import default_storage

    missing = 0
    for doc in Document.objects.exclude(file="").order_by("-uploaded_at")[:25]:
        try:
            if not default_storage.exists(doc.file.name):
                missing += 1
        except Exception:  # storage down → surfaced by deep_health, not here
            break
    if missing:
        findings.append(
            f"{missing} recent document(s) have NO blob in storage — uploads are silently "
            "losing files. PLAYBOOK: 'Document upload / download failures'."
        )

    # 4. Matches pointing at dead catalog rows (bad merge / deactivation leak).
    orphaned = Match.objects.filter(program__is_active=False).count()
    if orphaned:
        findings.append(
            f"{orphaned} match(es) point at INACTIVE programmes — students can apply to dead "
            "rows. PLAYBOOK: 'Catalog duplicates / bad programme data'."
        )

    # 5. Watchdog for partial outages: worker alive (we're running) but a
    #    sibling job's pulse is stale. Beat-fully-dead is caught externally
    #    via /healthz/deep. Skipped in dev (no beat in eager mode).
    if not settings.CELERY_TASK_ALWAYS_EAGER:
        hb = _check_heartbeats()
        if hb["status"].startswith("stale"):
            findings.append(
                f"Heartbeats {hb['status']} — a periodic job stopped running. "
                "PLAYBOOK: 'Background jobs went quiet'."
            )

    for finding in findings:
        _capture(finding, fingerprint=finding.split("PLAYBOOK")[0][:60])
    return findings
