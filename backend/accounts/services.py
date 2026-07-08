"""OTP issue/verify + onboarding email."""

from django.conf import settings
from django.core.mail import send_mail

from .models import EmailOTP


def issue_and_send_otp(user):
    otp = EmailOTP.issue(user)
    send_mail(
        subject="Your Wayfara code",
        message=(
            f"Your Wayfara verification code is: {otp.code}\n\n"
            f"It expires in {settings.OTP_LIFETIME_MINUTES} minutes.\n\n"
            "We're matching universities to your profile right now — enter the "
            "code in the app to see your results.\n\n"
            "— Wayfara"
        ),
        from_email=None,  # DEFAULT_FROM_EMAIL
        recipient_list=[user.email],
        fail_silently=False,
    )
    return otp


def verify_otp(user, code):
    """Return True and consume the code if valid; count failed attempts."""
    otp = user.otps.filter(used=False).order_by("-created_at").first()
    if otp is None or not otp.is_valid_now():
        return False
    if otp.code != code:
        otp.attempts += 1
        otp.save(update_fields=["attempts"])
        return False
    otp.used = True
    otp.save(update_fields=["used"])
    return True
