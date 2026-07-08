"""Reconcile engine + run orchestration.

All business logic lives here; Celery tasks (tasks.py) are thin invokers.
"""

import logging

from django.apps import apps
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from .models import DataChange, ScrapeRun, ScrapeSource
from .risk import risk_for
from .scrapers import SCRAPER_REGISTRY

logger = logging.getLogger(__name__)


def _is_same(field, old_value, new_value):
    """Coerce the scraped value to the field's type before comparing, so
    Decimal('15000.00') vs '15000' or a date vs its ISO string aren't false diffs.
    """
    try:
        coerced = field.to_python(new_value)
    except Exception:
        coerced = new_value
    if old_value is None or coerced is None:
        return old_value == coerced
    return old_value == coerced or str(old_value).strip() == str(coerced).strip()


def _diff_record(run, record):
    """Compare one ScrapedRecord to its DB row; create DataChanges. Returns count."""
    Model = apps.get_model(record.model)
    obj = Model.objects.filter(**record.natural_key).first()
    if obj is None:
        # New rows are out of scope for auto-handling: a brand-new program's
        # critical fields shouldn't be invented unattended. Log for a human.
        logger.info("Scrape: unmatched %s %s (new record, skipped)", record.model, record.natural_key)
        return 0

    ct = ContentType.objects.get_for_model(Model)
    changes = 0
    for field_name, new_value in record.fields.items():
        old_value = getattr(obj, field_name)
        if _is_same(obj._meta.get_field(field_name), old_value, new_value):
            continue
        risk = risk_for(record.model, field_name)
        change = DataChange.objects.create(
            run=run,
            content_type=ct,
            object_id=obj.pk,
            field_name=field_name,
            old_display="" if old_value is None else str(old_value),
            new_display="" if new_value is None else str(new_value),
            new_value=new_value,
            risk=risk,
        )
        if risk == DataChange.Risk.LOW:
            change.apply(automatic=True)  # tiered policy: low-risk auto-applies
        changes += 1
    return changes


def run_source(source_id):
    """Execute one source's scraper, reconcile, and audit. Isolated: an error
    here fails only this source's run, never the whole nightly sweep.
    """
    source = ScrapeSource.objects.get(pk=source_id)
    run = ScrapeRun.objects.create(source=source)
    try:
        scraper_cls = SCRAPER_REGISTRY.get(source.scraper_key)
        if scraper_cls is None:
            raise KeyError(f"No scraper registered for key '{source.scraper_key}'")

        records = scraper_cls(source).scrape()
        total_changes = 0
        with transaction.atomic():
            for record in records:
                total_changes += _diff_record(run, record)
        run.records_scraped = len(records)
        run.changes_detected = total_changes
        run.finish(ScrapeRun.Status.SUCCESS)
    except Exception as exc:  # noqa: BLE001 — isolate per-source failure
        logger.exception("Scrape failed for source %s", source.name)
        run.finish(ScrapeRun.Status.FAILED, error=str(exc))
    finally:
        source.last_run_at = timezone.now()
        source.save(update_fields=["last_run_at"])

    _alert_on_pending_critical(run)
    return run.pk


def run_all_sources():
    """Fan out over active sources. Returns the run ids."""
    return [run_source(sid) for sid in ScrapeSource.objects.filter(is_active=True).values_list("pk", flat=True)]


def _alert_on_pending_critical(run):
    pending = run.changes.filter(
        risk=DataChange.Risk.CRITICAL, status=DataChange.Status.PENDING_REVIEW
    )
    count = pending.count()
    if not count:
        return
    lines = [f"- {c.field_name}: {c.old_display!r} -> {c.new_display!r} ({c.target})" for c in pending[:50]]
    send_mail(
        subject=f"[Wayfara] {count} critical data change(s) need review — {run.source.name}",
        message=(
            f"The nightly scraper for {run.source.name} found {count} critical "
            "change(s) awaiting your approval before they go live:\n\n"
            + "\n".join(lines)
            + "\n\nReview them in the admin under Scraping › Data changes."
        ),
        from_email=None,
        recipient_list=[settings.SCRAPER_ALERT_EMAIL],
        fail_silently=True,
    )
