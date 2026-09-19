from datetime import datetime, timezone

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.models import Notification
from app.schemas import NotificationRead, UnreadCountRead
from app.security import CurrentUser, Db
from app.services.notifications import mark_notification_read


router = APIRouter(
    prefix="/notifications",
    tags=["notifications"],
)


@router.get(
    "",
    response_model=list[NotificationRead],
)
def list_notifications(
    db: Db,
    user: CurrentUser,
    unread: bool | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    query = select(Notification).where(
        Notification.user_id == user.id,
    )

    if unread is True:
        query = query.where(Notification.read_at.is_(None))
    elif unread is False:
        query = query.where(Notification.read_at.is_not(None))

    query = (
        query
        .order_by(
            Notification.created_at.desc(),
            Notification.id.desc(),
        )
        .offset(offset)
        .limit(limit)
    )

    return list(db.scalars(query))


@router.get(
    "/unread-count",
    response_model=UnreadCountRead,
)
def get_unread_count(
    db: Db,
    user: CurrentUser,
):
    query = (
        select(func.count())
        .select_from(Notification)
        .where(
            Notification.user_id == user.id,
            Notification.read_at.is_(None),
        )
    )

    count = db.scalar(query)

    return UnreadCountRead(
        count=count if count is not None else 0,
    )


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationRead,
)
def read_notification(
    notification_id: int,
    db: Db,
    user: CurrentUser,
):
    try:
        notification = mark_notification_read(
            db=db,
            user_id=user.id,
            notification_id=notification_id,
            now=datetime.now(timezone.utc),
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(notification)
    return notification