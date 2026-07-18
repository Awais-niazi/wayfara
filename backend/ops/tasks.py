"""Thin Celery invokers — logic lives in ops/services.py."""

from celery import shared_task

from .models import Heartbeat
from .services import check_push_receipts, run_canaries


@shared_task
def beat_pulse_task():
    """Beat: every 5 minutes. Existing = beat scheduler AND a worker are alive."""
    Heartbeat.beat("celery-beat")
    return "pulse"


@shared_task
def check_push_receipts_task():
    """Beat: every 15 minutes. Expo delivery receipts → prune/alert."""
    try:
        counters = check_push_receipts()
    except Exception as exc:
        Heartbeat.fail("push-receipts", exc)
        raise
    Heartbeat.beat("push-receipts", counters)
    return counters


@shared_task
def run_canaries_task():
    """Beat: hourly. Business-correctness checks; findings go to Sentry."""
    try:
        findings = run_canaries()
    except Exception as exc:
        Heartbeat.fail("canaries", exc)
        raise
    Heartbeat.beat("canaries", {"findings": len(findings)})
    return findings
