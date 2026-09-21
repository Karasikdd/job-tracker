import smtplib
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.enums import EmailDeliveryStatus, ReminderStatus
from app.models import (
    Application,
    EmailDelivery,
    Notification,
    NotificationSettings,
    Reminder,
    User,
)
from app.services import email_delivery
from app.tasks import email as email_tasks


@pytest.fixture
def fixed_now():
    return datetime(2030, 1, 15, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def enabled_email(monkeypatch):
    configuration = SimpleNamespace(email_delivery_enabled=True)

    monkeypatch.setattr(email_delivery, "settings", configuration)
    monkeypatch.setattr(email_tasks, "settings", configuration)

    return configuration


@pytest.fixture
def delivery_data(db_session, fixed_now):
    user = User(
        email=f"{uuid4().hex}@example.com",
        password_hash="unused-in-service-test",
    )
    db_session.add(user)
    db_session.flush()

    application = Application(
        user_id=user.id,
        company="Email Test Company",
        position="Backend Intern",
    )
    db_session.add(application)
    db_session.flush()

    preferences = NotificationSettings(
        user_id=user.id,
        email_enabled=True,
    )

    reminder = Reminder(
        user_id=user.id,
        application_id=application.id,
        title="Email delivery test",
        message="Test message",
        remind_at=fixed_now - timedelta(minutes=1),
        status=ReminderStatus.fired,
        send_email=True,
        fired_at=fixed_now,
    )
    db_session.add_all([preferences, reminder])
    db_session.flush()

    notification = Notification(
        user_id=user.id,
        application_id=application.id,
        reminder_id=reminder.id,
        title=reminder.title,
        body="Email delivery test body",
        created_at=fixed_now,
    )
    db_session.add(notification)
    db_session.flush()

    delivery = EmailDelivery(
        notification_id=notification.id,
        status=EmailDeliveryStatus.pending,
        attempts=0,
        next_attempt_at=fixed_now,
    )
    db_session.add(delivery)
    db_session.flush()

    return SimpleNamespace(
        user=user,
        application=application,
        preferences=preferences,
        reminder=reminder,
        notification=notification,
        delivery=delivery,
    )


@pytest.fixture
def local_transactions(db_session, monkeypatch, fixed_now):
    @contextmanager
    def transaction():
        with db_session.begin_nested():
            yield db_session

    monkeypatch.setattr(
        email_delivery,
        "SessionLocal",
        SimpleNamespace(begin=transaction),
    )
    monkeypatch.setattr(
        email_delivery,
        "utc_now",
        lambda: fixed_now,
    )


def test_successful_claim_blocks_second_claim(
    db_session,
    delivery_data,
    enabled_email,
    fixed_now,
):
    delivery = delivery_data.delivery

    first = email_delivery.claim_email_delivery(
        db_session,
        delivery.id,
        fixed_now,
    )
    second = email_delivery.claim_email_delivery(
        db_session,
        delivery.id,
        fixed_now,
    )

    assert first is not None
    assert second is None
    assert first.recipient == delivery_data.user.email
    assert first.application_id == delivery_data.application.id
    assert delivery.status == EmailDeliveryStatus.processing
    assert delivery.attempts == 1
    assert delivery.lease_token == first.lease_token
    assert delivery.lease_until == fixed_now + timedelta(minutes=2)


@pytest.mark.parametrize(
    "status",
    [
        EmailDeliveryStatus.sent,
        EmailDeliveryStatus.failed,
        EmailDeliveryStatus.cancelled,
    ],
)
def test_terminal_delivery_is_not_claimed(
    db_session,
    delivery_data,
    enabled_email,
    fixed_now,
    status,
):
    delivery = delivery_data.delivery
    delivery.status = status
    db_session.flush()

    claim = email_delivery.claim_email_delivery(
        db_session,
        delivery.id,
        fixed_now,
    )

    assert claim is None
    assert delivery.attempts == 0
    assert delivery.status == status


def test_future_retry_is_not_claimed(
    db_session,
    delivery_data,
    enabled_email,
    fixed_now,
):
    delivery = delivery_data.delivery
    delivery.next_attempt_at = fixed_now + timedelta(minutes=5)
    db_session.flush()

    claim = email_delivery.claim_email_delivery(
        db_session,
        delivery.id,
        fixed_now,
    )

    assert claim is None
    assert delivery.attempts == 0
    assert delivery.status == EmailDeliveryStatus.pending


def test_global_switch_does_not_consume_attempt(
    db_session,
    delivery_data,
    enabled_email,
    fixed_now,
):
    enabled_email.email_delivery_enabled = False
    delivery = delivery_data.delivery

    claim = email_delivery.claim_email_delivery(
        db_session,
        delivery.id,
        fixed_now,
    )

    assert claim is None
    assert delivery.attempts == 0
    assert delivery.status == EmailDeliveryStatus.pending


def test_disabled_user_email_cancels_delivery(
    db_session,
    delivery_data,
    enabled_email,
    fixed_now,
):
    delivery_data.preferences.email_enabled = False
    db_session.flush()

    delivery = delivery_data.delivery

    claim = email_delivery.claim_email_delivery(
        db_session,
        delivery.id,
        fixed_now,
    )

    assert claim is None
    assert delivery.status == EmailDeliveryStatus.cancelled
    assert delivery.attempts == 0
    assert delivery.lease_token is None


def test_expired_lease_rejects_old_result(
    db_session,
    delivery_data,
    enabled_email,
    fixed_now,
):
    delivery = delivery_data.delivery

    old_claim = email_delivery.claim_email_delivery(
        db_session,
        delivery.id,
        fixed_now,
    )
    assert old_claim is not None

    later = fixed_now + timedelta(minutes=3)

    new_claim = email_delivery.claim_email_delivery(
        db_session,
        delivery.id,
        later,
    )
    assert new_claim is not None
    assert new_claim.lease_token != old_claim.lease_token
    assert delivery.attempts == 2

    applied = email_delivery.finish_email_delivery(
        db_session,
        old_claim,
        later,
    )

    assert applied is False
    assert delivery.status == EmailDeliveryStatus.processing
    assert delivery.lease_token == new_claim.lease_token

    applied = email_delivery.finish_email_delivery(
        db_session,
        new_claim,
        later,
    )

    assert applied is True
    assert delivery.status == EmailDeliveryStatus.sent
    assert delivery.sent_at == later
    assert delivery.lease_token is None


def test_retry_delays_and_attempt_limit(
    db_session,
    delivery_data,
    enabled_email,
    fixed_now,
):
    delivery = delivery_data.delivery
    current_time = fixed_now

    delays = (
        timedelta(seconds=30),
        timedelta(minutes=2),
        timedelta(minutes=5),
        timedelta(minutes=15),
    )

    for attempt in range(1, 6):
        claim = email_delivery.claim_email_delivery(
            db_session,
            delivery.id,
            current_time,
        )

        assert claim is not None
        assert delivery.attempts == attempt

        applied = email_delivery.finish_email_delivery(
            db_session,
            claim,
            current_time,
            error_code="smtp_timeout",
            retryable=True,
        )

        assert applied is True
        assert delivery.lease_token is None
        assert delivery.lease_until is None

        if attempt < 5:
            assert delivery.status == EmailDeliveryStatus.pending
            assert delivery.next_attempt_at == (
                current_time + delays[attempt - 1]
            )

            early_claim = email_delivery.claim_email_delivery(
                db_session,
                delivery.id,
                delivery.next_attempt_at - timedelta(seconds=1),
            )

            assert early_claim is None
            assert delivery.attempts == attempt

            current_time = delivery.next_attempt_at
        else:
            assert delivery.status == EmailDeliveryStatus.failed

    assert email_delivery.claim_email_delivery(
        db_session,
        delivery.id,
        current_time + timedelta(days=1),
    ) is None

    assert delivery.attempts == 5


def test_expired_final_attempt_is_not_restarted(
    db_session,
    delivery_data,
    enabled_email,
    fixed_now,
):
    delivery = delivery_data.delivery
    delivery.status = EmailDeliveryStatus.processing
    delivery.attempts = 5
    delivery.lease_token = str(uuid4())
    delivery.lease_until = fixed_now - timedelta(seconds=1)
    db_session.flush()

    claim = email_delivery.claim_email_delivery(
        db_session,
        delivery.id,
        fixed_now,
    )

    assert claim is None
    assert delivery.status == EmailDeliveryStatus.failed
    assert delivery.attempts == 5
    assert delivery.last_error_code == "attempt_limit_reached"
    assert delivery.lease_token is None


def test_successful_send_is_not_repeated(
    db_session,
    delivery_data,
    enabled_email,
    local_transactions,
    monkeypatch,
    fixed_now,
):
    sent_messages = []

    def fake_send(**kwargs):
        sent_messages.append(kwargs)

    monkeypatch.setattr(
        email_delivery,
        "send_notification_email",
        fake_send,
    )

    delivery = delivery_data.delivery

    assert email_delivery.deliver_email(delivery.id) == "sent"
    assert email_delivery.deliver_email(delivery.id) == "skipped"

    db_session.refresh(delivery)

    assert len(sent_messages) == 1
    assert sent_messages[0]["recipient"] == delivery_data.user.email
    assert delivery.status == EmailDeliveryStatus.sent
    assert delivery.sent_at == fixed_now
    assert delivery.attempts == 1


@pytest.mark.parametrize(
    "smtp_code,expected_status,expected_next_delay",
    [
        (451, EmailDeliveryStatus.pending, timedelta(seconds=30)),
        (550, EmailDeliveryStatus.failed, None),
    ],
)
def test_smtp_failure_is_recorded_safely(
    db_session,
    delivery_data,
    enabled_email,
    local_transactions,
    monkeypatch,
    fixed_now,
    smtp_code,
    expected_status,
    expected_next_delay,
):
    def fake_send(**kwargs):
        raise smtplib.SMTPDataError(
            smtp_code,
            b"Private server details must not be stored",
        )

    monkeypatch.setattr(
        email_delivery,
        "send_notification_email",
        fake_send,
    )

    delivery = delivery_data.delivery

    result = email_delivery.deliver_email(delivery.id)

    db_session.refresh(delivery)

    assert result == "send_failed"
    assert delivery.status == expected_status
    assert delivery.attempts == 1
    assert delivery.last_error_code == f"smtp_response_{smtp_code}"
    assert delivery.sent_at is None
    assert delivery.lease_token is None

    if expected_next_delay is not None:
        assert delivery.next_attempt_at == (
            fixed_now + expected_next_delay
        )


def test_deleted_application_does_not_send(
    db_session,
    delivery_data,
    enabled_email,
    local_transactions,
    monkeypatch,
):
    delivery_id = delivery_data.delivery.id

    db_session.delete(delivery_data.application)
    db_session.flush()

    def forbidden_send(**kwargs):
        raise AssertionError("Deleted delivery must not be sent")

    monkeypatch.setattr(
        email_delivery,
        "send_notification_email",
        forbidden_send,
    )

    assert email_delivery.deliver_email(delivery_id) == "skipped"


def test_dispatch_failure_keeps_pending_delivery(
    db_session,
    delivery_data,
    enabled_email,
    monkeypatch,
    fixed_now,
):
    delivery = delivery_data.delivery
    delivery.next_attempt_at = (
        datetime.now(timezone.utc) - timedelta(minutes=1)
    )
    db_session.flush()

    @contextmanager
    def session_scope():
        yield db_session

    monkeypatch.setattr(
        email_tasks,
        "SessionLocal",
        session_scope,
    )

    attempted_publications = []

    def fail_publish(*, args, retry):
        attempted_publications.append(args[0])
        raise ConnectionError("Redis unavailable")

    monkeypatch.setattr(
        email_tasks.send_email_delivery_task,
        "apply_async",
        fail_publish,
    )

    with pytest.raises(ConnectionError, match="Redis unavailable"):
        email_tasks.dispatch_email_deliveries_task.run()

    db_session.refresh(delivery)

    assert delivery.id in attempted_publications
    assert delivery.status == EmailDeliveryStatus.pending
    assert delivery.attempts == 0

    existing_id = db_session.scalar(
        select(EmailDelivery.id).where(
            EmailDelivery.id == delivery.id,
        )
    )

    assert existing_id == delivery.id