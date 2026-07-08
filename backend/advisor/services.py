"""Advisor onboarding logic (service layer — views stay thin).

Activation reuses Django's password-reset token machinery: the token is
derived from the user's current password hash + timestamp, so it is
single-use (setting a password invalidates it) and expires after
PASSWORD_RESET_TIMEOUT (72h). A freshly provisioned advisor has an unusable
password, so the same token doubles as a first-time set-password link.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db.models import Q
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from wayfara import settings as wf_settings

from .models import AdvisorMessage, AdvisorThread

User = get_user_model()


def send_advisor_activation(user):
    """Email a one-time link that lets the advisor set their own password."""
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    link = f"{wf_settings.ADVISOR_CONSOLE_URL}/activate/{uidb64}/{token}"
    send_mail(
        subject="Set up your Wayfara advisor account",
        message=(
            "You've been added as an advisor on Wayfara.\n\n"
            f"Set your password to activate your account:\n{link}\n\n"
            "This link is single-use and expires in 72 hours. If it lapses, "
            "ask the administrator to resend it.\n\n"
            "— Wayfara"
        ),
        from_email=None,  # DEFAULT_FROM_EMAIL
        recipient_list=[user.email],
        fail_silently=False,
    )


def activate_advisor(uidb64, token, password):
    """Validate the link + password and set it. Returns (user, error).

    error is None on success, otherwise a short reason string.
    """
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (ValueError, TypeError, User.DoesNotExist):
        return None, "Invalid activation link."

    # Only advisors activate this way; students use OTP login.
    if user.role != User.Role.ADVISOR:
        return None, "Invalid activation link."

    if not default_token_generator.check_token(user, token):
        return None, "This link is invalid or has expired."

    try:
        validate_password(password, user)
    except ValidationError as exc:
        return None, " ".join(exc.messages)

    user.set_password(password)
    user.email_verified = True
    user.save(update_fields=["password", "email_verified"])
    return user, None


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


def post_message(thread, sender, body):
    message = AdvisorMessage.objects.create(thread=thread, sender=sender, body=body)
    thread.last_message_at = message.created_at
    thread.save(update_fields=["last_message_at"])
    return message


def mark_read_by(thread, reader):
    """Mark messages the reader did NOT send as read. Returns rows updated."""
    return thread.messages.filter(read_at__isnull=True).filter(
        ~Q(sender=reader)
    ).update(read_at=timezone.now())


def unread_count_for(thread, reader):
    return thread.messages.filter(read_at__isnull=True).exclude(sender=reader).count()
