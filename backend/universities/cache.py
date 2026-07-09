"""Version-based cache invalidation for the university catalog.

The catalog is read-heavy and identical for every student, but it *does*
change — nightly via the scraper and occasionally via admin. Rather than a
blind TTL (which serves stale data for a window), we key cached payloads on a
monotonic version that any write to a catalog model bumps. A stale key can
never be read: the moment data changes, the version — and therefore the key —
changes with it.
"""

from django.core.cache import cache

_VERSION_KEY = "catalog:version"


def get_catalog_version():
    version = cache.get(_VERSION_KEY)
    if version is None:
        version = 1
        cache.set(_VERSION_KEY, version, None)  # no expiry
    return version


def bump_catalog_version():
    """Invalidate every cached catalog payload. `incr` is atomic in Redis."""
    try:
        cache.incr(_VERSION_KEY)
    except ValueError:
        # Key absent (e.g. after a cache flush) — seed it past 1.
        cache.set(_VERSION_KEY, 2, None)


def catalog_key(name):
    return f"catalog:{get_catalog_version()}:{name}"
