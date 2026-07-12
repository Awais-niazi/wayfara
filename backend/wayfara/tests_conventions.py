"""Guardrails for firm architectural rules — enforced by CI, not just by
docstrings and good intentions. If one of these fails, either the change
violates the rule on purpose (update the rule here too) or by accident
(fix the change).
"""

import importlib

from django.test import SimpleTestCase
from rest_framework import serializers

from wayfara.serializers import StrictModelSerializer, StrictSerializer
from wayfara.urls import urlpatterns

# Our own apps only — third-party serializers (SimpleJWT's token serializers,
# wired directly in wayfara/urls.py) aren't ours to modify and carry no
# mass-assignment risk: fixed, tiny payloads with no model write surface.
LOCAL_APPS = ["accounts", "advisor", "students", "applications", "universities", "scraping"]

ALLOWED_TOP_LEVEL_PREFIXES = ("admin/", "healthz", "api/v1/")


class URLVersioningTests(SimpleTestCase):
    def test_every_top_level_route_is_versioned_admin_or_health(self):
        for pattern in urlpatterns:
            route = str(pattern.pattern)
            self.assertTrue(
                route.startswith(ALLOWED_TOP_LEVEL_PREFIXES),
                f"{route!r} is not under an approved prefix {ALLOWED_TOP_LEVEL_PREFIXES} — "
                "new endpoints must live under the current API version (api/v1/), "
                "not a bare 'api/' or another unversioned path.",
            )


class StrictSerializerConventionTests(SimpleTestCase):
    def test_all_local_serializers_use_the_strict_base(self):
        offenders = []
        for app_label in LOCAL_APPS:
            try:
                module = importlib.import_module(f"{app_label}.serializers")
            except ModuleNotFoundError:
                continue  # app has no serializers module yet
            for name in dir(module):
                obj = getattr(module, name)
                if (
                    isinstance(obj, type)
                    and issubclass(obj, serializers.BaseSerializer)
                    and obj.__module__ == module.__name__  # defined here, not just imported
                    and not issubclass(obj, (StrictSerializer, StrictModelSerializer))
                ):
                    offenders.append(f"{app_label}.serializers.{name}")
        self.assertEqual(
            offenders,
            [],
            "These serializers must inherit StrictSerializer/StrictModelSerializer "
            f"(wayfara/serializers.py) instead of DRF's plain base classes: {offenders}",
        )
