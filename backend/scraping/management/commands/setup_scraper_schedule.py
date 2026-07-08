"""Create/refresh the 2 AM (Helsinki) nightly scraper schedule. Idempotent."""

from django.core.management.base import BaseCommand
from django_celery_beat.models import CrontabSchedule, PeriodicTask


class Command(BaseCommand):
    help = "Set up the nightly scraper Celery Beat schedule"

    def handle(self, *args, **options):
        schedule, _ = CrontabSchedule.objects.get_or_create(
            minute="0", hour="2", day_of_week="*", day_of_month="*", month_of_year="*",
            timezone="Europe/Helsinki",
        )
        task, created = PeriodicTask.objects.update_or_create(
            name="nightly-scrape",
            defaults={"crontab": schedule, "task": "scraping.tasks.run_all_scrapers_task"},
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Nightly scrape {'created' if created else 'updated'}: 02:00 Europe/Helsinki"
            )
        )
