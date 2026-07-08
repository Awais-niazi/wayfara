"""Thin Celery invokers — business logic lives in applications/services.py."""

from celery import shared_task

from .services import match_programs_for_student


@shared_task
def match_programs_task(student_id):
    return match_programs_for_student(student_id)
