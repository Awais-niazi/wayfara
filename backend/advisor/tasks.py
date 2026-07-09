"""Celery tasks for the advisor app — thin invokers only.

Business logic lives in services; tasks just schedule/invoke it.
"""

from celery import shared_task


@shared_task
def notify_new_message_task(message_id):
    from .services import notify_new_message

    notify_new_message(message_id)
