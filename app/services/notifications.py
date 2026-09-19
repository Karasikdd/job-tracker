from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Notification


def get_owned_notification(
    db: Session,
    user_id: int,
    notification_id: int,
    *,
    lock: bool = False,
) -> Notification:
    query = select(Notification).where(
        Notification.id == notification_id,
        Notification.user_id == user_id,
    )

    if lock:
        query = query.with_for_update().execution_options(
            populate_existing=True,
        )

    notification = db.scalar(query)

    if notification is None:
        raise HTTPException(
            status_code=404,
            detail="Notification not found",
        )

    return notification


def mark_notification_read(
    db: Session,
    user_id: int,
    notification_id: int,
    now: datetime,
) -> Notification:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("A timezone-aware datetime is required")

    notification = get_owned_notification(
        db,
        user_id,
        notification_id,
        lock=True,
    )

    if notification.read_at is not None:
        return notification

    notification.read_at = now.astimezone(timezone.utc)

    db.flush()
    db.refresh(notification)

    return notification