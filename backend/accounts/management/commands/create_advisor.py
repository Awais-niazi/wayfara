"""Provision an advisor: invite them in Supabase + create the local advisor row.

Usage:  python manage.py create_advisor advisor@example.com

Supabase emails the invitee a set-password link, so the advisor's credential
is only ever known to them. Promoting an *existing* account to advisor is done
from the Django admin (User → "Provision as advisor") instead.
"""

from django.core.management.base import BaseCommand, CommandError

from accounts.supabase import SupabaseAdminError, provision_advisor


class Command(BaseCommand):
    help = "Invite a new advisor via Supabase and create their local advisor account."

    def add_arguments(self, parser):
        parser.add_argument("email", help="Advisor's email address")

    def handle(self, *args, **options):
        email = options["email"].strip().lower()
        try:
            user, created = provision_advisor(email)
        except SupabaseAdminError as exc:
            raise CommandError(str(exc))

        verb = "Invited" if created else "Updated"
        self.stdout.write(
            self.style.SUCCESS(
                f"{verb} advisor {user.email} (Supabase id {user.supabase_id}). "
                "They'll set their password from the Supabase invite email."
            )
        )
