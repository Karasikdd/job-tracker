from datetime import datetime, timezone

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.enums import ReminderStatus
from app.models import Reminder
from app.schemas import ReminderCreate, ReminderPatch, ReminderRead
from app.security import CurrentUser, Db
from app.services import reminders as reminder_service


router = APIRouter(tags=["reminders"])


@router.post(
    "/applications/{application_id}/reminders",
    response_model=ReminderRead,
    status_code=201,
)
def create_application_reminder(
    application_id: int,
    payload: ReminderCreate,
    db: Db,
    user: CurrentUser,
):
    try:
        reminder = reminder_service.create_reminder(
            db=db,
            user_id=user.id,
            application_id=application_id,
            payload=payload,
            now=datetime.now(timezone.utc),
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(reminder)
    return reminder


@router.get(
    "/applications/{application_id}/reminders",
    response_model=list[ReminderRead],
)
def list_application_reminders(
    application_id: int,
    db: Db,
    user: CurrentUser,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    reminder_service.get_owned_application(
        db=db,
        user_id=user.id,
        application_id=application_id,
    )

    query = (
        select(Reminder)
        .where(
            Reminder.user_id == user.id,
            Reminder.application_id == application_id,
        )
        .order_by(Reminder.remind_at, Reminder.id)
        .offset(offset)
        .limit(limit)
    )

    return list(db.scalars(query))


@router.get(
    "/reminders",
    response_model=list[ReminderRead],
)
def list_reminders(
    db: Db,
    user: CurrentUser,
    status: ReminderStatus | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    query = select(Reminder).where(
        Reminder.user_id == user.id,
    )

    if status is not None:
        query = query.where(Reminder.status == status)

    query = (
        query
        .order_by(Reminder.remind_at, Reminder.id)
        .offset(offset)
        .limit(limit)
    )

    return list(db.scalars(query))


@router.patch(
    "/reminders/{reminder_id}",
    response_model=ReminderRead,
)
def update_reminder(
    reminder_id: int,
    payload: ReminderPatch,
    db: Db,
    user: CurrentUser,
):
    try:
        reminder = reminder_service.update_reminder(
            db=db,
            user_id=user.id,
            reminder_id=reminder_id,
            payload=payload,
            now=datetime.now(timezone.utc),
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(reminder)
    return reminder


@router.post(
    "/reminders/{reminder_id}/cancel",
    response_model=ReminderRead,
)
def cancel_reminder(
    reminder_id: int,
    db: Db,
    user: CurrentUser,
):
    try:
        reminder = reminder_service.cancel_reminder(
            db=db,
            user_id=user.id,
            reminder_id=reminder_id,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(reminder)
    return reminder