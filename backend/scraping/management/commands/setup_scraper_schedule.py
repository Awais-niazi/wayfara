"""Create/refresh the monthly scraper schedule (1st of the month, 02:00
Helsinki). Idempotent; removes the retired nightly entry if present."""

from django.core.management.base import BaseCommand
from django_celery_beat.models import CrontabSchedule, PeriodicTask

from scraping.models import ScrapeSource


class Command(BaseCommand):
    help = "Set up the monthly scraper Celery Beat schedule and register sources"

    def handle(self, *args, **options):
        ScrapeSource.objects.update_or_create(
            name="Opintopolku (Studyinfo)",
            defaults={
                "scraper_key": "opintopolku_programs",
                "url": "https://opintopolku.fi",
                "is_active": True,
            },
        )

        # Retired cadence — drop it so old deployments don't run both.
        PeriodicTask.objects.filter(name="nightly-scrape").delete()

        schedule, _ = CrontabSchedule.objects.get_or_create(
            minute="0", hour="2", day_of_week="*", day_of_month="1", month_of_year="*",
            timezone="Europe/Helsinki",
        )
        task, created = PeriodicTask.objects.update_or_create(
            name="monthly-scrape",
            defaults={"crontab": schedule, "task": "scraping.tasks.run_all_scrapers_task"},
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Monthly scrape {'created' if created else 'updated'}: "
                "02:00 Europe/Helsinki on the 1st"
            )
        )
