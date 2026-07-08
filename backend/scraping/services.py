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


def _coerce(Model, field_name, value):
    try:
        return Model._meta.get_field(field_name).to_python(value)
    except Exception:
        return value


def _process_record(run, record):
    """Reconcile one ScrapedRecord. Returns ('created'|'updated'|'unchanged', n_changes).

    - No existing row + allow_create -> create it (additive; a new programme
      appearing is not a risk to a student's existing decisions).
    - Existing row -> diff each field under the tiered policy: low-risk
      auto-applies, critical is staged for review.
    """
    Model = apps.get_model(record.model)
    obj = Model.objects.filter(**record.natural_key).first()

    if obj is None:
        if not record.allow_create:
            logger.info("Scrape: unmatched %s %s (skipped)", record.model, record.natural_key)
            return "unchanged", 0
        create_kwargs = dict(record.natural_key)
        create_kwargs.update(record.related)
        create_kwargs.update({f: _coerce(Model, f, v) for f, v in record.fields.items()})
        Model.objects.create(**create_kwargs)
        return "created", 0

    # Reconcile related FKs (campus, university) directly — these are
    # descriptive links, not gated scalar values.
    fk_updates = [
        name for name, rel in record.related.items()
        if getattr(obj, f"{name}_id") != rel.pk
    ]
    if fk_updates:
        for name in fk_updates:
            setattr(obj, name, record.related[name])
        obj.save(update_fields=fk_updates)

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
        # Tiered policy: low-risk auto-applies. First-time population of a
        # previously-empty field is not a risky change either — we only gate
        # CHANGING a value a student may already be relying on.
        is_population = old_value in (None, "")
        if risk == DataChange.Risk.LOW or is_population:
            change.apply(automatic=True)
        changes += 1
    return ("updated" if changes else "unchanged"), changes


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

        # Process incrementally: each record commits in its own short
        # transaction so a long ingest keeps its progress even if a later
        # fetch fails, and DB locks stay brief.
        scraped = total_changes = created = 0
        for record in scraper_cls(source).scrape():
            with transaction.atomic():
                outcome, n = _process_record(run, record)
            scraped += 1
            total_changes += n
            created += outcome == "created"
        run.records_scraped = scraped
        run.records_created = created
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
