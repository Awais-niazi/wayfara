"""Celery application.

Discipline: Celery tasks are thin invokers only — all business logic lives in
regular service functions (see applications/services.py, students/services.py).
Tasks exist solely to schedule those functions onto the queue.
"""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "wayfara.settings")

app = Celery("wayfara")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
