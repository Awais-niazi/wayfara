"""Create/refresh the observability schedules (idempotent, run on deploy).

  beat-pulse          every 5 min   proves beat + a worker are alive
  check-push-receipts every 15 min  Expo delivery receipts → prune/alert
  run-canaries        every 60 min  business-correctness checks → Sentry

Same pattern as setup_notification_schedule / setup_scraper_schedule.
"""

from django.core.management.base import BaseCommand
from django_celery_beat.models import IntervalSchedule, PeriodicTask

JOBS = [
    ("ops-beat-pulse", "ops.tasks.beat_pulse_task", 5),
    ("ops-check-push-receipts", "ops.tasks.check_push_receipts_task", 15),
    ("ops-run-canaries", "ops.tasks.run_canaries_task", 60),
]


class Command(BaseCommand):
    help = "Set up the Celery Beat schedules for observability (pulse/receipts/canaries)"

    def handle(self, *args, **options):
        for name, task, minutes in JOBS:
            schedule, _ = IntervalSchedule.objects.get_or_create(
                every=minutes, period=IntervalSchedule.MINUTES
            )
            _, created = PeriodicTask.objects.update_or_create(
                name=name, defaults={"interval": schedule, "task": task}
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"{name} {'created' if created else 'updated'}: every {minutes} min"
                )
            )
