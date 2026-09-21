from datetime import datetime, timezone

from sqlalchemy import and_, or_, select

from app.celery_app import celery_app
from app.config import settings
from app.database import SessionLocal
from app.enums import EmailDeliveryStatus
from app.models import EmailDelivery
from app.services.email_delivery import deliver_email


@celery_app.task(name="jobtracker.send_email_delivery")
def send_email_delivery_task(delivery_id: int) -> str:
    return deliver_email(delivery_id)


@celery_app.task(name="jobtracker.dispatch_email_deliveries")
def dispatch_email_deliveries_task(batch_size: int = 100) -> int:
    if not 1 <= batch_size <= 100:
        raise ValueError("Batch size must be between 1 and 100")

    if not settings.email_delivery_enabled:
        return 0

    now = datetime.now(timezone.utc)

    pending_due = and_(
        EmailDelivery.status == EmailDeliveryStatus.pending,
        EmailDelivery.next_attempt_at <= now,
    )

    processing_expired = and_(
        EmailDelivery.status == EmailDeliveryStatus.processing,
        or_(
            EmailDelivery.lease_until <= now,
            EmailDelivery.lease_until.is_(None),
        ),
    )

    query = (
        select(EmailDelivery.id)
        .where(or_(pending_due, processing_expired))
        .order_by(
            EmailDelivery.next_attempt_at,
            EmailDelivery.id,
        )
        .limit(batch_size)
    )

    with SessionLocal() as db:
        delivery_ids = list(db.scalars(query))

    for delivery_id in delivery_ids:
        send_email_delivery_task.apply_async(
            args=[delivery_id],
            retry=False,
        )

    return len(delivery_ids)