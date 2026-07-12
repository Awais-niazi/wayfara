"""Project-level views not owned by any single domain app."""

import logging

from django.core.cache import cache
from django.db import connection
from django.db.utils import Error as DatabaseError
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


class HealthCheckView(APIView):
    """Liveness/readiness probe for load balancers and uptime monitors.

    Deliberately outside auth, throttling, and API versioning: infrastructure
    (Railway, an uptime monitor, a future load balancer) hits this exact path
    forever, unauthenticated, so its contract must stay stable independent of
    API evolution. Checks the two synchronous dependencies every request
    needs — database and cache — not Celery/Redis-as-broker, since a slow
    background queue isn't the same thing as "can't serve requests."
    """

    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_classes = []

    def get(self, request):
        checks = {"database": self._check_database(), "cache": self._check_cache()}
        healthy = all(v == "ok" for v in checks.values())
        return Response(
            {"status": "ok" if healthy else "unhealthy", "checks": checks},
            status=200 if healthy else 503,
        )

    def _check_database(self):
        try:
            connection.ensure_connection()
            return "ok"
        except DatabaseError:
            logger.exception("Health check: database unreachable")
            return "error"

    def _check_cache(self):
        try:
            cache.set("healthz:probe", "1", 5)
            return "ok" if cache.get("healthz:probe") == "1" else "error"
        except Exception:  # noqa: BLE001 — cache backend errors vary by backend
            logger.exception("Health check: cache unreachable")
            return "error"
