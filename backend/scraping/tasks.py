"""Thin Celery invokers — business logic lives in scraping/services.py."""

from celery import shared_task

from .services import run_all_sources, run_source

# Ingestion fetches detail per programme (hundreds of requests), so these
# override the global 60s task limit. 30-minute hard cap.
SCRAPE_TIME_LIMIT = 30 * 60


@shared_task(time_limit=SCRAPE_TIME_LIMIT, soft_time_limit=SCRAPE_TIME_LIMIT - 60)
def run_all_scrapers_task():
    from ops.models import Heartbeat

    try:
        run_ids = run_all_sources()
    except Exception as exc:
        Heartbeat.fail("scraper-monthly", exc)
        raise
    Heartbeat.beat("scraper-monthly", {"runs": len(run_ids)})
    return run_ids


@shared_task(time_limit=SCRAPE_TIME_LIMIT, soft_time_limit=SCRAPE_TIME_LIMIT - 60)
def run_scraper_task(source_id):
    return run_source(source_id)
