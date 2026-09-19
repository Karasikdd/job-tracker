from celery import Celery

from app.config import settings


celery_app = Celery(
    "job_tracker",
    broker=settings.broker_url,
    include=["app.tasks.reminders"],
)

celery_app.conf.update(
    timezone="UTC",
    enable_utc=True,
    task_serializer="json",
    accept_content=["json"],
    task_ignore_result=True,
    broker_connection_retry_on_startup=True,
    beat_schedule={
        "process-due-reminders": {
            "task": "jobtracker.process_due_reminders",
            "schedule": 30.0,
        },
    },
)