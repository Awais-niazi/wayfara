"""Thin Celery invokers — business logic lives in students/services.py."""

from celery import shared_task

from .services import generate_timeline


@shared_task
def generate_timeline_task(student_id):
    return generate_timeline(student_id)
