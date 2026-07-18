"""Deep health endpoint — the external monitor's window into the system.

/healthz stays the cheap liveness ping (process up, DB reachable).
/healthz/deep exercises every dependency + the dead-man heartbeats and goes
503 when anything is wrong, so a dumb uptime pinger (armed at deploy) becomes
a full-system alarm. Unauthenticated by design: it reports status words only,
never configuration or data.
"""

from django.http import JsonResponse
from django.views import View

from .services import deep_health


class DeepHealthView(View):
    def get(self, request):
        healthy, report = deep_health()
        return JsonResponse(
            {"status": "ok" if healthy else "degraded", "checks": report},
            status=200 if healthy else 503,
        )
