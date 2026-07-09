"""Bump the catalog cache version whenever catalog data changes.

Covers scraper writes and admin edits alike — both go through the ORM, so
post_save/post_delete is the single choke point.
"""

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .cache import bump_catalog_version
from .models import Campus, Program, University, UniversityProfile

_CATALOG_MODELS = (University, UniversityProfile, Campus, Program)


@receiver(post_save)
@receiver(post_delete)
def _invalidate_catalog(sender, **kwargs):
    if sender in _CATALOG_MODELS:
        bump_catalog_version()
