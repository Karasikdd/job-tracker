import pytest
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.enums import ReminderStatus
from app.models import EmailDelivery, Notification
from app.schemas import ReminderCreate
from app.services.reminders import (
    cancel_reminder,
    create_reminder,
    process_due_reminders,
)


def create_account(client, email):
    credentials = {
        "email": email,
        "password": "Example-password-123",
    }

    response = client.post("/auth/register", json=credentials)
    assert response.status_code == 201, response.text

    response = client.post("/auth/login", json=credentials)
    assert response.status_code == 200, response.text

    return {
        "Authorization": f"Bearer {response.json()['access_token']}",
    }


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("GET", "/notifications", None),
        ("GET", "/notifications/unread-count", None),
        ("PATCH", "/notifications/1/read", None),
        ("GET", "/users/me/notification-settings", None),
        (
            "PATCH",
            "/users/me/notification-settings",
            {"email_enabled": True},
        ),
    ],
)
def test_notification_endpoints_require_authentication(
    client,
    method,
    path,
    payload,
):
    kwargs = {}

    if payload is not None:
        kwargs["json"] = payload

    response = client.request(method, path, **kwargs)

    assert response.status_code == 401, response.text


def test_new_account_has_no_notifications(client):
    headers = create_account(client, "empty@example.com")

    response = client.get("/notifications", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json() == []

    response = client.get(
        "/notifications/unread-count",
        headers=headers,
    )
    assert response.status_code == 200, response.text
    assert response.json() == {"count": 0}


@pytest.mark.parametrize(
    "params",
    [
        {"limit": 0},
        {"limit": 101},
        {"offset": -1},
        {"unread": "invalid"},
    ],
)
def test_invalid_notification_filters_are_rejected(client, params):
    headers = create_account(client, "filters@example.com")

    response = client.get(
        "/notifications",
        params=params,
        headers=headers,
    )

    assert response.status_code == 422, response.text


def get_email_setting(client, headers):
    response = client.get(
        "/users/me/notification-settings",
        headers=headers,
    )

    assert response.status_code == 200, response.text
    value = response.json()["email_enabled"]
    assert isinstance(value, bool)

    return value


def set_email_setting(client, headers, enabled):
    response = client.patch(
        "/users/me/notification-settings",
        json={"email_enabled": enabled},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["email_enabled"] is enabled


def test_email_settings_are_saved_and_isolated(client):
    owner = create_account(client, "settings-owner@example.com")
    other = create_account(client, "settings-other@example.com")

    # Устанавливаем известное начальное состояние обоим пользователям.
    set_email_setting(client, owner, False)
    set_email_setting(client, other, False)

    # Включение email у владельца не меняет настройки другого аккаунта.
    set_email_setting(client, owner, True)

    assert get_email_setting(client, owner) is True
    assert get_email_setting(client, other) is False

    # Затем меняем настройки второго аккаунта независимо.
    set_email_setting(client, other, True)
    set_email_setting(client, owner, False)

    assert get_email_setting(client, owner) is False
    assert get_email_setting(client, other) is True


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"email_enabled": None},
        {"email_enabled": True, "unexpected_field": True},
    ],
)
def test_invalid_settings_do_not_change_saved_value(client, payload):
    headers = create_account(client, "invalid-settings@example.com")
    set_email_setting(client, headers, False)

    response = client.patch(
        "/users/me/notification-settings",
        json=payload,
        headers=headers,
    )

    assert response.status_code == 422, response.text
    assert get_email_setting(client, headers) is False
TEST_NOW = datetime(2030, 1, 15, 12, 0, tzinfo=timezone.utc)


def make_reminder(
    client,
    db_session,
    headers,
    *,
    send_email=False,
    minutes=5,
):
    response = client.get("/users/me", headers=headers)
    assert response.status_code == 200, response.text
    user_id = response.json()["id"]

    response = client.post(
        "/applications",
        headers=headers,
        json={
            "company": "Reminder Test GmbH",
            "position": "Backend Developer",
            "status": "saved",
        },
    )
    assert response.status_code == 201, response.text
    application_id = response.json()["id"]

    return create_reminder(
        db=db_session,
        user_id=user_id,
        application_id=application_id,
        payload=ReminderCreate(
            title="Prepare for interview",
            message="Review the job description.",
            remind_at=TEST_NOW + timedelta(minutes=minutes),
            send_email=send_email,
        ),
        now=TEST_NOW,
    )


def notifications_for(db_session, reminder):
    return list(
        db_session.scalars(
            select(Notification).where(
                Notification.reminder_id == reminder.id,
            )
        )
    )


def deliveries_for(db_session, notification):
    return list(
        db_session.scalars(
            select(EmailDelivery).where(
                EmailDelivery.notification_id == notification.id,
            )
        )
    )


def notification_ids(client, headers, **params):
    response = client.get(
        "/notifications",
        headers=headers,
        params=params,
    )
    assert response.status_code == 200, response.text

    return [item["id"] for item in response.json()]


def unread_count(client, headers):
    response = client.get(
        "/notifications/unread-count",
        headers=headers,
    )
    assert response.status_code == 200, response.text

    return response.json()["count"]


def test_reminder_fires_only_when_due(client, db_session):
    headers = create_account(client, "due@example.com")
    reminder = make_reminder(client, db_session, headers)

    processed = process_due_reminders(
        db_session,
        reminder.remind_at - timedelta(seconds=1),
    )

    assert processed == 0
    assert notifications_for(db_session, reminder) == []

    db_session.refresh(reminder)
    assert reminder.status == ReminderStatus.scheduled
    assert reminder.fired_at is None

    due_at = reminder.remind_at
    processed = process_due_reminders(db_session, due_at)

    assert processed == 1

    db_session.refresh(reminder)
    assert reminder.status == ReminderStatus.fired
    assert reminder.fired_at == due_at

    notifications = notifications_for(db_session, reminder)
    assert len(notifications) == 1

    notification = notifications[0]
    assert notification.user_id == reminder.user_id
    assert notification.application_id == reminder.application_id
    assert notification.title == reminder.title
    assert reminder.message in notification.body
    assert notification.read_at is None
    assert deliveries_for(db_session, notification) == []


def test_reprocessing_does_not_duplicate_notification_or_email(
    client,
    db_session,
):
    headers = create_account(client, "repeat@example.com")
    set_email_setting(client, headers, True)

    reminder = make_reminder(
        client,
        db_session,
        headers,
        send_email=True,
    )
    due_at = reminder.remind_at

    assert process_due_reminders(db_session, due_at) == 1

    db_session.commit()

    assert process_due_reminders(
        db_session,
        due_at + timedelta(minutes=1),
    ) == 0

    notifications = notifications_for(db_session, reminder)
    assert len(notifications) == 1
    assert len(deliveries_for(db_session, notifications[0])) == 1


def test_cancelled_reminder_does_not_fire(client, db_session):
    headers = create_account(client, "cancelled@example.com")
    reminder = make_reminder(client, db_session, headers)

    cancel_reminder(
        db=db_session,
        user_id=reminder.user_id,
        reminder_id=reminder.id,
    )

    assert process_due_reminders(
        db_session,
        reminder.remind_at + timedelta(minutes=1),
    ) == 0

    db_session.refresh(reminder)
    assert reminder.status == ReminderStatus.cancelled
    assert reminder.fired_at is None
    assert notifications_for(db_session, reminder) == []


def test_disabling_email_preserves_in_app_notification(
    client,
    db_session,
):
    headers = create_account(client, "disabled-email@example.com")
    set_email_setting(client, headers, True)

    reminder = make_reminder(
        client,
        db_session,
        headers,
        send_email=True,
    )

    set_email_setting(client, headers, False)

    assert process_due_reminders(
        db_session,
        reminder.remind_at,
    ) == 1

    notifications = notifications_for(db_session, reminder)
    assert len(notifications) == 1
    assert deliveries_for(db_session, notifications[0]) == []


def test_other_user_cannot_list_or_read_notification(
    client,
    db_session,
):
    owner = create_account(client, "notification-owner@example.com")
    other = create_account(client, "notification-other@example.com")

    owner_reminder = make_reminder(client, db_session, owner)
    other_reminder = make_reminder(client, db_session, other)

    assert process_due_reminders(
        db_session,
        TEST_NOW + timedelta(minutes=10),
    ) == 2
    db_session.commit()

    owner_notification = notifications_for(
        db_session,
        owner_reminder,
    )[0]
    other_notification = notifications_for(
        db_session,
        other_reminder,
    )[0]

    assert notification_ids(client, owner) == [owner_notification.id]
    assert notification_ids(client, other) == [other_notification.id]
    assert unread_count(client, owner) == 1
    assert unread_count(client, other) == 1

    response = client.patch(
        f"/notifications/{owner_notification.id}/read",
        headers=other,
    )
    assert response.status_code == 404, response.text

    db_session.refresh(owner_notification)
    assert owner_notification.read_at is None
    assert unread_count(client, owner) == 1


def test_marking_read_twice_preserves_timestamp_and_count(
    client,
    db_session,
):
    headers = create_account(client, "read-twice@example.com")

    first_reminder = make_reminder(client, db_session, headers)
    make_reminder(client, db_session, headers)

    assert process_due_reminders(
        db_session,
        TEST_NOW + timedelta(minutes=10),
    ) == 2

    notification = notifications_for(
        db_session,
        first_reminder,
    )[0]
    path = f"/notifications/{notification.id}/read"

    assert unread_count(client, headers) == 2

    response = client.patch(path, headers=headers)
    assert response.status_code == 200, response.text

    first_read_at = response.json()["read_at"]
    assert first_read_at is not None
    assert unread_count(client, headers) == 1

    response = client.patch(path, headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["read_at"] == first_read_at
    assert unread_count(client, headers) == 1

    assert notification.id not in notification_ids(
        client,
        headers,
        unread="true",
    )
    assert notification_ids(
        client,
        headers,
        unread="false",
    ) == [notification.id]
    assert len(notification_ids(client, headers)) == 2