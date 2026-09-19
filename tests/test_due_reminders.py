from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.enums import (
    EmailDeliveryStatus,
    ReminderKind,
    ReminderStatus,
)
from app.models import (
    Application,
    EmailDelivery,
    Notification,
    NotificationSettings,
    Reminder,
    User,
)
from app.services.reminders import process_due_reminders


@pytest.mark.parametrize(
    "email_enabled, send_email, expected_deliveries",
    [
        (None, True, 0),
        (False, True, 0),
        (True, False, 0),
        (True, True, 1),
    ],
)
def test_due_reminder_creates_notification_once(
    db_session,
    email_enabled,
    send_email,
    expected_deliveries,
):
    now = datetime(2030, 1, 15, 12, 0, tzinfo=timezone.utc)

    user = User(
        email=f"{uuid4().hex}@example.com",
        password_hash="unused-in-service-test",
    )
    db_session.add(user)
    db_session.flush()

    application = Application(
        user_id=user.id,
        company="Test Company",
        position="Backend Intern",
    )
    db_session.add(application)
    db_session.flush()

    if email_enabled is not None:
        db_session.add(
            NotificationSettings(
                user_id=user.id,
                email_enabled=email_enabled,
            )
        )

    reminder = Reminder(
        user_id=user.id,
        application_id=application.id,
        kind=ReminderKind.follow_up,
        title="Contact recruiter",
        message="Ask about the next stage.",
        remind_at=now - timedelta(minutes=5),
        status=ReminderStatus.scheduled,
        send_email=send_email,
    )
    db_session.add(reminder)
    db_session.flush()

    assert process_due_reminders(db_session, now) == 1
    assert reminder.status == ReminderStatus.fired
    assert reminder.fired_at == now
    assert reminder.remind_at == now - timedelta(minutes=5)

    notifications = list(
        db_session.scalars(
            select(Notification).where(
                Notification.reminder_id == reminder.id,
            )
        )
    )

    assert len(notifications) == 1

    notification = notifications[0]

    assert notification.user_id == user.id
    assert notification.application_id == application.id
    assert notification.title == "Contact recruiter"
    assert "Ask about the next stage." in notification.body
    assert reminder.remind_at.isoformat() in notification.body
    assert notification.created_at == now
    assert notification.read_at is None

    deliveries = list(
        db_session.scalars(
            select(EmailDelivery).where(
                EmailDelivery.notification_id == notification.id,
            )
        )
    )

    assert len(deliveries) == expected_deliveries

    if deliveries:
        assert deliveries[0].status == EmailDeliveryStatus.pending
        assert deliveries[0].attempts == 0
        assert deliveries[0].next_attempt_at == now

    assert process_due_reminders(db_session, now) == 0

    notification_ids = list(
        db_session.scalars(
            select(Notification.id).where(
                Notification.reminder_id == reminder.id,
            )
        )
    )

    assert notification_ids == [notification.id]


@pytest.mark.parametrize(
    "reminder_status, time_offset",
    [
        (ReminderStatus.scheduled, timedelta(hours=1)),
        (ReminderStatus.cancelled, timedelta(minutes=-5)),
    ],
)
def test_future_and_cancelled_reminders_are_not_processed(
    db_session,
    reminder_status,
    time_offset,
):
    now = datetime(2030, 1, 15, 12, 0, tzinfo=timezone.utc)

    user = User(
        email=f"{uuid4().hex}@example.com",
        password_hash="unused-in-service-test",
    )
    db_session.add(user)
    db_session.flush()

    application = Application(
        user_id=user.id,
        company="Test Company",
        position="Backend Intern",
    )
    db_session.add(application)
    db_session.flush()

    reminder = Reminder(
        user_id=user.id,
        application_id=application.id,
        kind=ReminderKind.custom,
        title="Test reminder",
        remind_at=now + time_offset,
        status=reminder_status,
        send_email=False,
    )
    db_session.add(reminder)
    db_session.flush()

    assert process_due_reminders(db_session, now) == 0
    assert reminder.status == reminder_status
    assert reminder.fired_at is None

    notification = db_session.scalar(
        select(Notification).where(
            Notification.reminder_id == reminder.id,
        )
    )

    assert notification is None