"""Thin Celery invokers — business logic lives in notifications/services.py."""

from celery import shared_task

from .services import (
    dispatch_due_reminders,
    notify_students_of_data_change,
    send_broadcast,
)


@shared_task
def dispatch_due_reminders_task():
    """Beat: every 5 minutes. Sends due journey reminders as notifications."""
    from ops.models import Heartbeat

    try:
        dispatched, stale = dispatch_due_reminders()
    except Exception as exc:
        Heartbeat.fail("reminder-dispatcher", exc)
        raise
    result = {"dispatched": dispatched, "stale_swallowed": stale}
    Heartbeat.beat("reminder-dispatcher", result)
    return result


@shared_task
def send_broadcast_task(broadcast_id):
    return send_broadcast(broadcast_id)


@shared_task
def notify_students_of_data_change_task(change_id):
    return notify_students_of_data_change(change_id)
