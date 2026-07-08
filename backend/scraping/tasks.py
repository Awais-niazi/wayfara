"""Thin Celery invokers — business logic lives in scraping/services.py."""

from celery import shared_task

from .services import run_all_sources, run_source

# Ingestion fetches detail per programme (hundreds of requests), so these
# override the global 60s task limit. 30-minute hard cap.
SCRAPE_TIME_LIMIT = 30 * 60


@shared_task(time_limit=SCRAPE_TIME_LIMIT, soft_time_limit=SCRAPE_TIME_LIMIT - 60)
def run_all_scrapers_task():
    return run_all_sources()


@shared_task(time_limit=SCRAPE_TIME_LIMIT, soft_time_limit=SCRAPE_TIME_LIMIT - 60)
def run_scraper_task(source_id):
    return run_source(source_id)
