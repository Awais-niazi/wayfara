"""Notification platform core.

Single spine for every notification in the product: sources (reminder
dispatcher, advisor messages, admin broadcasts, scraper updates, future
doc/visa events) all call notify(); delivery is an inbox row + a mirrored
Expo push. Adding a source is one call — never new plumbing.
"""

import logging
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from accounts.push import send_push_to_user
from students.models import Reminder, Student

from .models import Broadcast, Notification

logger = logging.getLogger("notifications")

# A reminder further past due than this is swallowed (marked sent, logged,
# never pushed) — after a worker outage, students must not get a week of
# stale pings at once.
STALE_AFTER = timedelta(hours=24)


def notify(user, *, category, title, body="", data=None, push=True):
    """THE entry point: record in the inbox, mirror as a push.

    Returns the Notification row. Push failures never propagate — the row is
    the durable record and send_push_to_user is already best-effort.
    """
    notification = Notification.objects.create(
        user=user, category=category, title=title, body=body, data=data or {}
    )
    if push:
        send_push_to_user(
            user,
            title=title,
            body=body,
            data={"notification_id": notification.pk, **(data or {})},
        )
        notification.push_sent_at = timezone.now()
        notification.save(update_fields=["push_sent_at"])
    return notification


def dispatch_due_reminders():
    """Send every due, unsent reminder. Runs from Celery Beat every 5 min.

    Claim-then-send: rows are stamped `sent` in one atomic UPDATE before any
    push goes out, so overlapping runs (or multiple workers) can't double-send.
    Returns (dispatched, swallowed_stale).
    """
    now = timezone.now()
    due_ids = list(
        Reminder.objects.filter(sent=False, remind_at__lte=now).values_list("id", flat=True)
    )
    if not due_ids:
        return 0, 0
    # The claim: only rows still unsent flip; whatever we flipped is ours.
    claimed = Reminder.objects.filter(id__in=due_ids, sent=False).update(
        sent=True, sent_at=now
    )
    if not claimed:
        return 0, 0

    dispatched = swallowed = 0
    for reminder in Reminder.objects.filter(id__in=due_ids, sent_at=now).select_related(
        "student__user", "task"
    ):
        if now - reminder.remind_at > STALE_AFTER:
            swallowed += 1
            logger.warning(
                "Swallowed stale reminder %s (due %s): dispatcher was down?",
                reminder.pk,
                reminder.remind_at,
            )
            continue
        data = {"type": "task"}
        if reminder.task_id:
            data.update(task_id=reminder.task_id, phase=reminder.task.phase)
        notify(
            reminder.student.user,
            category=Notification.Category.REMINDER,
            title=reminder.title,
            body=reminder.body,
            data=data,
        )
        dispatched += 1
    return dispatched, swallowed


def _broadcast_recipients(broadcast):
    """Resolve the audience to a queryset of Students (one row per student)."""
    students = Student.objects.filter(onboarding_completed=True).select_related("user")
    if broadcast.audience == Broadcast.Audience.BY_INTAKE_YEAR:
        return students.filter(intake_year=broadcast.intake_year)
    if broadcast.audience == Broadcast.Audience.BY_UNIVERSITY:
        return students.filter(
            matches__program__university=broadcast.university
        ).distinct()
    return students


def send_broadcast(broadcast_id):
    """Fan an admin-composed Broadcast out to its audience. Celery task body.

    Guard: only a draft can be sent — the admin action flips it to SENDING
    atomically, so a double-click (or duplicate task) fans out once.
    """
    with transaction.atomic():
        broadcast = Broadcast.objects.select_for_update().get(pk=broadcast_id)
        if broadcast.status == Broadcast.Status.SENT:
            return 0
        broadcast.status = Broadcast.Status.SENDING
        broadcast.save(update_fields=["status"])

    count = 0
    for student in _broadcast_recipients(broadcast):
        notify(
            student.user,
            category=broadcast.category,
            title=broadcast.title,
            body=broadcast.body,
            data={"type": "broadcast", "broadcast_id": broadcast.pk},
        )
        count += 1

    broadcast.status = Broadcast.Status.SENT
    broadcast.sent_at = timezone.now()
    broadcast.recipient_count = count
    broadcast.save(update_fields=["status", "sent_at", "recipient_count"])
    return count


def notify_students_of_data_change(change_id):
    """Scraper hook: a critical, admin-approved catalogue change notifies the
    students it affects (those matched to the university in question).
    Celery task body; called on_commit from DataChange.apply().

    DataChange.target is generic — a Program or a University; anything else
    (e.g. a PolicyFigure) has no per-student audience yet and is skipped.
    """
    from scraping.models import DataChange
    from universities.models import Program, University

    change = DataChange.objects.filter(pk=change_id).first()
    if change is None:
        return 0
    target = change.target
    if isinstance(target, Program):
        university, subject = target.university, target.name
    elif isinstance(target, University):
        university, subject = target, target.name
    else:
        return 0

    field = change.field_name.replace("_", " ")
    students = (
        Student.objects.filter(
            onboarding_completed=True, matches__program__university=university
        )
        .distinct()
        .select_related("user")
    )
    count = 0
    for student in students:
        notify(
            student.user,
            category=Notification.Category.UPDATE,
            title=f"{university.name} updated",
            body=f"{subject}: {field} changed to {change.new_display or 'a new value'}. "
            "Check how this affects your plan.",
            data={"type": "university", "university_id": university.pk},
        )
        count += 1
    return count
