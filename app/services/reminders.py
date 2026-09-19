from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enums import ReminderStatus
from app.models import Application, NotificationSettings, Reminder
from app.schemas import ReminderCreate, ReminderPatch


def normalize_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("A timezone-aware datetime is required")

    return value.astimezone(timezone.utc)


def validate_future_time(
    remind_at: datetime,
    now: datetime,
) -> datetime:
    normalized_time = normalize_utc(remind_at)
    normalized_now = normalize_utc(now)

    if normalized_time <= normalized_now:
        raise HTTPException(
            status_code=422,
            detail="Reminder time must be in the future",
        )

    return normalized_time


def get_owned_application(
    db: Session,
    user_id: int,
    application_id: int,
) -> Application:
    query = select(Application).where(
        Application.id == application_id,
        Application.user_id == user_id,
    )

    application = db.scalar(query)

    if application is None:
        raise HTTPException(
            status_code=404,
            detail="Application not found",
        )

    return application


def get_owned_reminder(
    db: Session,
    user_id: int,
    reminder_id: int,
    *,
    lock: bool = False,
) -> Reminder:
    query = select(Reminder).where(
        Reminder.id == reminder_id,
        Reminder.user_id == user_id,
    )

    if lock:
        query = query.with_for_update().execution_options(
            populate_existing=True,
        )

    reminder = db.scalar(query)

    if reminder is None:
        raise HTTPException(
            status_code=404,
            detail="Reminder not found",
        )

    return reminder


def ensure_email_enabled(
    db: Session,
    user_id: int,
) -> None:
    email_enabled = db.scalar(
        select(NotificationSettings.email_enabled).where(
            NotificationSettings.user_id == user_id,
        )
    )

    if not email_enabled:
        raise HTTPException(
            status_code=409,
            detail="Enable email notifications in your settings first",
        )


def create_reminder(
    db: Session,
    user_id: int,
    application_id: int,
    payload: ReminderCreate,
    now: datetime,
) -> Reminder:
    application = get_owned_application(
        db,
        user_id,
        application_id,
    )

    remind_at = validate_future_time(payload.remind_at, now)

    if payload.send_email:
        ensure_email_enabled(db, user_id)

    reminder = Reminder(
        user_id=user_id,
        application_id=application.id,
        kind=payload.kind,
        title=payload.title,
        message=payload.message,
        remind_at=remind_at,
        status=ReminderStatus.scheduled,
        send_email=payload.send_email,
    )

    db.add(reminder)
    db.flush()
    db.refresh(reminder)

    return reminder


def update_reminder(
    db: Session,
    user_id: int,
    reminder_id: int,
    payload: ReminderPatch,
    now: datetime,
) -> Reminder:
    reminder = get_owned_reminder(
        db,
        user_id,
        reminder_id,
        lock=True,
    )

    if reminder.status != ReminderStatus.scheduled:
        raise HTTPException(
            status_code=409,
            detail="Only scheduled reminders can be edited",
        )

    changes = payload.model_dump(exclude_unset=True)

    if not changes:
        return reminder

    if "remind_at" in changes:
        changes["remind_at"] = validate_future_time(
            changes["remind_at"],
            now,
        )

    if changes.get("send_email") is True:
        ensure_email_enabled(db, user_id)

    for field, value in changes.items():
        setattr(reminder, field, value)

    db.flush()
    db.refresh(reminder)

    return reminder


def cancel_reminder(
    db: Session,
    user_id: int,
    reminder_id: int,
) -> Reminder:
    reminder = get_owned_reminder(
        db,
        user_id,
        reminder_id,
        lock=True,
    )

    if reminder.status == ReminderStatus.cancelled:
        return reminder

    if reminder.status == ReminderStatus.fired:
        raise HTTPException(
            status_code=409,
            detail="A fired reminder cannot be cancelled",
        )

    reminder.status = ReminderStatus.cancelled

    db.flush()
    db.refresh(reminder)

    return reminder