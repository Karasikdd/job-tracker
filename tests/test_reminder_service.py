from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import func, select

from app.enums import ReminderStatus
from app.models import (
    Application,
    EmailDelivery,
    Notification,
    NotificationSettings,
    Reminder,
    User,
)
from app.schemas import ReminderCreate, ReminderPatch
from app.services.notifications import mark_notification_read
from app.services.reminders import (
    cancel_reminder,
    create_reminder,
    process_due_reminders,
    update_reminder,
)


@pytest.fixture
def fixed_now():
    return datetime(2030, 1, 15, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def owner_application(db_session):
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

    return user, application


@pytest.fixture
def other_user(db_session):
    user = User(
        email=f"{uuid4().hex}@example.com",
        password_hash="unused-in-service-test",
    )
    db_session.add(user)
    db_session.flush()

    return user


@pytest.fixture
def reminder_factory(db_session, owner_application, fixed_now):
    user, application = owner_application

    def create(
        *,
        remind_at=None,
        status=ReminderStatus.scheduled,
        send_email=False,
    ):
        reminder = Reminder(
            user_id=user.id,
            application_id=application.id,
            title="Test reminder",
            message="Test message",
            remind_at=(
                remind_at
                if remind_at is not None
                else fixed_now + timedelta(hours=1)
            ),
            status=status,
            send_email=send_email,
        )
        db_session.add(reminder)
        db_session.flush()

        return reminder

    return create


def test_create_reminder_for_owned_application(
    db_session,
    owner_application,
    fixed_now,
):
    user, application = owner_application

    payload = ReminderCreate(
        title="  Contact recruiter  ",
        remind_at=fixed_now + timedelta(hours=1),
    )

    reminder = create_reminder(
        db_session,
        user.id,
        application.id,
        payload,
        fixed_now,
    )

    assert reminder.id is not None
    assert reminder.user_id == user.id
    assert reminder.application_id == application.id
    assert reminder.title == "Contact recruiter"
    assert reminder.status == ReminderStatus.scheduled
    assert reminder.send_email is False


def test_create_reminder_for_foreign_application_is_rejected(
    db_session,
    owner_application,
    other_user,
    fixed_now,
):
    _, application = owner_application

    payload = ReminderCreate(
        title="Contact recruiter",
        remind_at=fixed_now + timedelta(hours=1),
    )

    with pytest.raises(HTTPException) as error:
        create_reminder(
            db_session,
            other_user.id,
            application.id,
            payload,
            fixed_now,
        )

    assert error.value.status_code == 404

    count = db_session.scalar(
        select(func.count())
        .select_from(Reminder)
        .where(Reminder.application_id == application.id)
    )

    assert count == 0


@pytest.mark.parametrize("offset_minutes", [-1, 0])
def test_create_requires_future_time(
    db_session,
    owner_application,
    fixed_now,
    offset_minutes,
):
    user, application = owner_application

    payload = ReminderCreate(
        title="Contact recruiter",
        remind_at=fixed_now + timedelta(minutes=offset_minutes),
    )

    with pytest.raises(HTTPException) as error:
        create_reminder(
            db_session,
            user.id,
            application.id,
            payload,
            fixed_now,
        )

    assert error.value.status_code == 422


def test_equivalent_timezones_produce_same_utc_time(
    db_session,
    owner_application,
    fixed_now,
):
    user, application = owner_application
    utc_time = fixed_now + timedelta(hours=1)
    local_time = utc_time.astimezone(
        timezone(timedelta(hours=2))
    )

    reminders = [
        create_reminder(
            db_session,
            user.id,
            application.id,
            ReminderCreate(
                title="Timezone test",
                remind_at=value,
            ),
            fixed_now,
        )
        for value in (utc_time, local_time)
    ]

    assert reminders[0].remind_at == reminders[1].remind_at
    assert reminders[0].remind_at == utc_time


def test_create_rejects_timezone_naive_time():
    with pytest.raises(ValidationError):
        ReminderCreate(
            title="Contact recruiter",
            remind_at="2030-01-15T15:00:00",
        )


def test_create_rejects_user_id_in_payload(fixed_now):
    with pytest.raises(ValidationError):
        ReminderCreate.model_validate(
            {
                "title": "Contact recruiter",
                "remind_at": fixed_now + timedelta(hours=1),
                "user_id": 123,
            }
        )


def test_email_requires_enabled_settings(
    db_session,
    owner_application,
    fixed_now,
):
    user, application = owner_application

    payload = ReminderCreate(
        title="Email reminder",
        remind_at=fixed_now + timedelta(hours=1),
        send_email=True,
    )

    with pytest.raises(HTTPException) as error:
        create_reminder(
            db_session,
            user.id,
            application.id,
            payload,
            fixed_now,
        )

    assert error.value.status_code == 409


@pytest.mark.parametrize(
    "status",
    [ReminderStatus.fired, ReminderStatus.cancelled],
)
def test_update_requires_scheduled_status(
    db_session,
    owner_application,
    reminder_factory,
    fixed_now,
    status,
):
    user, _ = owner_application
    reminder = reminder_factory(status=status)

    with pytest.raises(HTTPException) as error:
        update_reminder(
            db_session,
            user.id,
            reminder.id,
            ReminderPatch(title="Changed title"),
            fixed_now,
        )

    assert error.value.status_code == 409
    assert reminder.title == "Test reminder"


def test_update_can_clear_message(
    db_session,
    owner_application,
    reminder_factory,
    fixed_now,
):
    user, _ = owner_application
    reminder = reminder_factory()
    original_time = reminder.remind_at

    updated = update_reminder(
        db_session,
        user.id,
        reminder.id,
        ReminderPatch(message=None),
        fixed_now,
    )

    assert updated.message is None
    assert updated.title == "Test reminder"
    assert updated.remind_at == original_time


def test_empty_patch_preserves_values(
    db_session,
    owner_application,
    reminder_factory,
    fixed_now,
):
    user, _ = owner_application
    reminder = reminder_factory()

    original_values = (
        reminder.title,
        reminder.message,
        reminder.remind_at,
        reminder.updated_at,
    )

    updated = update_reminder(
        db_session,
        user.id,
        reminder.id,
        ReminderPatch(),
        fixed_now,
    )

    assert (
        updated.title,
        updated.message,
        updated.remind_at,
        updated.updated_at,
    ) == original_values


def test_cancel_is_idempotent(
    db_session,
    owner_application,
    reminder_factory,
):
    user, _ = owner_application
    reminder = reminder_factory()

    cancel_reminder(db_session, user.id, reminder.id)
    first_updated_at = reminder.updated_at

    cancel_reminder(db_session, user.id, reminder.id)

    assert reminder.status == ReminderStatus.cancelled
    assert reminder.updated_at == first_updated_at


def test_fired_reminder_cannot_be_cancelled(
    db_session,
    owner_application,
    reminder_factory,
):
    user, _ = owner_application
    reminder = reminder_factory(status=ReminderStatus.fired)

    with pytest.raises(HTTPException) as error:
        cancel_reminder(db_session, user.id, reminder.id)

    assert error.value.status_code == 409


def test_foreign_reminder_cannot_be_modified(
    db_session,
    other_user,
    reminder_factory,
    fixed_now,
):
    reminder = reminder_factory()

    with pytest.raises(HTTPException) as update_error:
        update_reminder(
            db_session,
            other_user.id,
            reminder.id,
            ReminderPatch(title="Unauthorized change"),
            fixed_now,
        )

    assert update_error.value.status_code == 404

    with pytest.raises(HTTPException) as cancel_error:
        cancel_reminder(
            db_session,
            other_user.id,
            reminder.id,
        )

    assert cancel_error.value.status_code == 404
    assert reminder.status == ReminderStatus.scheduled
    assert reminder.title == "Test reminder"


def test_processing_respects_batch_size(
    db_session,
    reminder_factory,
    fixed_now,
):
    first = reminder_factory(
        remind_at=fixed_now - timedelta(minutes=2)
    )
    second = reminder_factory(
        remind_at=fixed_now - timedelta(minutes=1)
    )

    assert process_due_reminders(
        db_session,
        fixed_now,
        batch_size=1,
    ) == 1

    assert first.status == ReminderStatus.fired
    assert second.status == ReminderStatus.scheduled

    assert process_due_reminders(
        db_session,
        fixed_now,
        batch_size=1,
    ) == 1

    assert second.status == ReminderStatus.fired


def test_processing_rolls_back_all_changes_on_error(
    db_session,
    owner_application,
    reminder_factory,
    fixed_now,
):
    user, _ = owner_application

    db_session.add(
        NotificationSettings(
            user_id=user.id,
            email_enabled=True,
        )
    )

    reminder = reminder_factory(
        remind_at=fixed_now,
        send_email=True,
    )
    reminder_id = reminder.id

    with pytest.raises(RuntimeError, match="Simulated failure"):
        with db_session.begin_nested():
            assert process_due_reminders(
                db_session,
                fixed_now,
            ) == 1

            notification = db_session.scalar(
                select(Notification).where(
                    Notification.reminder_id == reminder_id,
                )
            )

            assert notification is not None

            delivery = db_session.scalar(
                select(EmailDelivery).where(
                    EmailDelivery.notification_id == notification.id,
                )
            )

            assert delivery is not None

            raise RuntimeError("Simulated failure")

    db_session.expire_all()

    restored = db_session.get(Reminder, reminder_id)

    assert restored.status == ReminderStatus.scheduled
    assert restored.fired_at is None

    notification = db_session.scalar(
        select(Notification).where(
            Notification.reminder_id == reminder_id,
        )
    )

    assert notification is None

    delivery_count = db_session.scalar(
        select(func.count()).select_from(EmailDelivery)
    )

    assert delivery_count == 0


def test_application_deletion_cascades(
    db_session,
    owner_application,
    reminder_factory,
    fixed_now,
):
    user, application = owner_application

    db_session.add(
        NotificationSettings(
            user_id=user.id,
            email_enabled=True,
        )
    )

    reminder = reminder_factory(
        remind_at=fixed_now,
        send_email=True,
    )

    process_due_reminders(db_session, fixed_now)

    notification = db_session.scalar(
        select(Notification).where(
            Notification.reminder_id == reminder.id,
        )
    )
    assert notification is not None

    delivery_id = db_session.scalar(
        select(EmailDelivery.id).where(
            EmailDelivery.notification_id == notification.id,
        )
    )
    assert delivery_id is not None

    reminder_id = reminder.id
    notification_id = notification.id

    db_session.delete(application)
    db_session.flush()
    db_session.expire_all()

    for model, record_id in (
        (Reminder, reminder_id),
        (Notification, notification_id),
        (EmailDelivery, delivery_id),
    ):
        existing_id = db_session.scalar(
            select(model.id).where(model.id == record_id)
        )
        assert existing_id is None


def test_notification_read_is_owned_and_idempotent(
    db_session,
    owner_application,
    other_user,
    reminder_factory,
    fixed_now,
):
    user, _ = owner_application
    reminder = reminder_factory(remind_at=fixed_now)

    process_due_reminders(db_session, fixed_now)

    notification = db_session.scalar(
        select(Notification).where(
            Notification.reminder_id == reminder.id,
        )
    )
    assert notification is not None

    with pytest.raises(HTTPException) as error:
        mark_notification_read(
            db_session,
            other_user.id,
            notification.id,
            fixed_now,
        )

    assert error.value.status_code == 404
    assert notification.read_at is None

    mark_notification_read(
        db_session,
        user.id,
        notification.id,
        fixed_now,
    )

    mark_notification_read(
        db_session,
        user.id,
        notification.id,
        fixed_now + timedelta(minutes=10),
    )

    assert notification.read_at == fixed_now