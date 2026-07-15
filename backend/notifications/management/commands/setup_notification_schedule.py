"""Create/refresh the reminder-dispatch schedule (every 5 minutes).

Idempotent — safe to re-run on every deploy, same pattern as
setup_scraper_schedule.
"""

from django.core.management.base import BaseCommand
from django_celery_beat.models import IntervalSchedule, PeriodicTask


class Command(BaseCommand):
    help = "Set up the Celery Beat schedule that dispatches due reminders"

    def handle(self, *args, **options):
        schedule, _ = IntervalSchedule.objects.get_or_create(
            every=5, period=IntervalSchedule.MINUTES
        )
        task, created = PeriodicTask.objects.update_or_create(
            name="dispatch-due-reminders",
            defaults={
                "interval": schedule,
                "task": "notifications.tasks.dispatch_due_reminders_task",
            },
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Reminder dispatch {'created' if created else 'updated'}: every 5 minutes"
            )
        )
