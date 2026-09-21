from datetime import datetime, timezone

from app.celery_app import celery_app
from app.database import SessionLocal
from app.services.reminders import process_due_reminders


@celery_app.task(name="jobtracker.process_due_reminders")
def process_due_reminders_task() -> int:
    now = datetime.now(timezone.utc)

    with SessionLocal.begin() as db:
        processed_count = process_due_reminders(
            db,
            now,
            batch_size=100,
        )

    return processed_count