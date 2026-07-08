"""Thin Celery invokers — business logic lives in scraping/services.py."""

from celery import shared_task

from .services import run_all_sources, run_source


@shared_task
def run_all_scrapers_task():
    return run_all_sources()


@shared_task
def run_scraper_task(source_id):
    return run_source(source_id)
