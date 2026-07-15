"""Advisor messaging logic (service layer — views stay thin).

Advisor *provisioning* (creating the Supabase identity + local advisor row)
lives in accounts.supabase.provision_advisor; advisors set their own password
through Supabase's invite email, so no Django-side activation exists here.
"""

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import AdvisorMessage, AdvisorThread


# --- Messaging ---------------------------------------------------------------

def get_thread_for_student(student):
    """Return the student's thread, creating it against their currently
    assigned advisor. Returns None if no advisor is assigned yet (nothing to
    talk to). Keeps the advisor snapshot current on reassignment.
    """
    if student.assigned_advisor_id is None:
        return None
    thread, created = AdvisorThread.objects.get_or_create(
        student=student, defaults={"advisor": student.assigned_advisor}
    )
    if not created and thread.advisor_id != student.assigned_advisor_id:
        thread.advisor = student.assigned_advisor
        thread.save(update_fields=["advisor"])
    return thread


def post_message(thread, sender, body="", audio=None, audio_duration=None):
    message = AdvisorMessage.objects.create(
        thread=thread, sender=sender, body=body,
        audio=audio, audio_duration_seconds=audio_duration,
    )
    thread.last_message_at = message.created_at
    thread.save(update_fields=["last_message_at"])
    # Notify the *other* participant. Delegated to Celery so the send request
    # returns immediately; the task is a thin invoker of notify_new_message().
    from .tasks import notify_new_message_task

    transaction.on_commit(lambda: notify_new_message_task.delay(message.id))
    return message


def recipient_of(message):
    """The participant who should be notified: whoever didn't send it."""
    thread = message.thread
    student_user = thread.student.user
    advisor = thread.advisor
    if message.sender_id == student_user.id:
        return advisor
    return student_user


def notify_new_message(message_id):
    """Notify the other participant of a new message. Routed through the
    notification platform (notifications.services.notify) so the message
    lands in the in-app inbox AND as a push — a missed push isn't lost."""
    from notifications.models import Notification
    from notifications.services import notify

    message = (
        AdvisorMessage.objects.select_related(
            "thread__student__user", "thread__advisor", "sender"
        )
        .filter(id=message_id)
        .first()
    )
    if message is None:
        return
    recipient = recipient_of(message)
    if recipient is None:
        return
    sender_is_student = message.sender_id == message.thread.student.user_id
    title = "Your advisor" if sender_is_student else "New message from your advisor"
    preview = message.body[:120] if message.body else "Sent you a voice note"
    notify(
        recipient,
        category=Notification.Category.ADVISOR,
        title=title,
        body=preview,
        data={"type": "advisor_message", "thread_id": message.thread_id},
    )


def mark_read_by(thread, reader):
    """Mark messages the reader did NOT send as read. Returns rows updated."""
    return thread.messages.filter(read_at__isnull=True).filter(
        ~Q(sender=reader)
    ).update(read_at=timezone.now())


def unread_count_for(thread, reader):
    return thread.messages.filter(read_at__isnull=True).exclude(sender=reader).count()
