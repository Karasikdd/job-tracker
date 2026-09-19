from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.enums import EmailDeliveryStatus
from app.models import EmailDelivery, Notification, NotificationSettings
from app.services.reminders import process_due_reminders


def create_account(client):
    credentials = {
        "email": f"{uuid4().hex}@example.com",
        "password": "Example-password-123",
    }

    response = client.post("/auth/register", json=credentials)
    assert response.status_code == 201, response.text

    response = client.post("/auth/login", json=credentials)
    assert response.status_code == 200, response.text

    token = response.json()["access_token"]

    return {"Authorization": f"Bearer {token}"}


def create_application(client, headers):
    response = client.post(
        "/applications",
        headers=headers,
        json={
            "company": "Example GmbH",
            "position": "Backend Intern",
            "status": "saved",
        },
    )

    assert response.status_code == 201, response.text

    return response.json()


def reminder_payload(**overrides):
    payload = {
        "title": "Contact recruiter",
        "message": "Ask about the next stage.",
        "kind": "follow_up",
        "remind_at": (
            datetime.now(timezone.utc) + timedelta(days=1)
        ).isoformat(),
        "send_email": False,
    }
    payload.update(overrides)

    return payload


def create_reminder(client, headers, application_id, **overrides):
    response = client.post(
        f"/applications/{application_id}/reminders",
        headers=headers,
        json=reminder_payload(**overrides),
    )

    assert response.status_code == 201, response.text

    return response.json()


def process_created_reminders(db_session, reminders):
    processing_time = max(
        datetime.fromisoformat(
            reminder["remind_at"].replace("Z", "+00:00")
        )
        for reminder in reminders
    ) + timedelta(seconds=1)

    processed = process_due_reminders(
        db_session,
        processing_time,
    )
    db_session.commit()

    return processed


@pytest.mark.parametrize(
    "method,path,payload",
    [
        ("GET", "/reminders", None),
        ("GET", "/applications/1/reminders", None),
        (
            "POST",
            "/applications/1/reminders",
            {
                "title": "Test",
                "remind_at": "2099-01-01T12:00:00Z",
            },
        ),
        ("PATCH", "/reminders/1", {"title": "Changed"}),
        ("POST", "/reminders/1/cancel", None),
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


def test_reminder_api_lifecycle(client):
    headers = create_account(client)
    application = create_application(client, headers)

    reminder = create_reminder(
        client,
        headers,
        application["id"],
    )

    assert reminder["application_id"] == application["id"]
    assert reminder["status"] == "scheduled"

    response = client.get(
        f"/applications/{application['id']}/reminders",
        headers=headers,
    )
    assert response.status_code == 200, response.text
    assert [item["id"] for item in response.json()] == [reminder["id"]]

    path = f"/reminders/{reminder['id']}"

    response = client.patch(
        path,
        headers=headers,
        json={
            "title": "Prepare for interview",
            "message": None,
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["title"] == "Prepare for interview"
    assert response.json()["message"] is None

    new_time = datetime.now(timezone.utc) + timedelta(days=2)

    response = client.patch(
        path,
        headers=headers,
        json={"remind_at": new_time.isoformat()},
    )
    assert response.status_code == 200, response.text

    returned_time = datetime.fromisoformat(
        response.json()["remind_at"].replace("Z", "+00:00")
    )
    assert returned_time == new_time

    response = client.post(f"{path}/cancel", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "cancelled"

    response = client.post(f"{path}/cancel", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "cancelled"

    response = client.patch(
        path,
        headers=headers,
        json={"title": "Cannot change this"},
    )
    assert response.status_code == 409, response.text


def test_foreign_reminders_are_hidden(client):
    owner = create_account(client)
    other = create_account(client)
    application = create_application(client, owner)
    reminder = create_reminder(client, owner, application["id"])

    application_path = (
        f"/applications/{application['id']}/reminders"
    )
    reminder_path = f"/reminders/{reminder['id']}"

    response = client.get(application_path, headers=other)
    assert response.status_code == 404, response.text

    response = client.post(
        application_path,
        headers=other,
        json=reminder_payload(),
    )
    assert response.status_code == 404, response.text

    response = client.patch(
        reminder_path,
        headers=other,
        json={"title": "Unauthorized change"},
    )
    assert response.status_code == 404, response.text

    response = client.post(
        f"{reminder_path}/cancel",
        headers=other,
    )
    assert response.status_code == 404, response.text

    response = client.get("/reminders", headers=other)
    assert response.status_code == 200, response.text
    assert response.json() == []


@pytest.mark.parametrize(
    "overrides",
    [
        {"title": "   "},
        {"title": None},
        {"message": "x" * 2001},
        {"remind_at": "2000-01-01T12:00:00Z"},
        {"remind_at": "2099-01-01T12:00:00"},
        {"kind": "unknown"},
        {"user_id": 123},
        {"status": "fired"},
    ],
)
def test_invalid_reminder_creation_is_rejected(client, overrides):
    headers = create_account(client)
    application = create_application(client, headers)

    response = client.post(
        f"/applications/{application['id']}/reminders",
        headers=headers,
        json=reminder_payload(**overrides),
    )

    assert response.status_code == 422, response.text


def test_reminder_filters_and_pagination(client):
    headers = create_account(client)
    application = create_application(client, headers)
    base_time = datetime.now(timezone.utc) + timedelta(days=1)

    first = create_reminder(
        client,
        headers,
        application["id"],
        remind_at=base_time.isoformat(),
    )
    second = create_reminder(
        client,
        headers,
        application["id"],
        remind_at=(base_time + timedelta(hours=1)).isoformat(),
    )
    third = create_reminder(
        client,
        headers,
        application["id"],
        remind_at=(base_time + timedelta(hours=2)).isoformat(),
    )

    response = client.post(
        f"/reminders/{third['id']}/cancel",
        headers=headers,
    )
    assert response.status_code == 200, response.text

    for offset, expected_id in (
        (0, first["id"]),
        (1, second["id"]),
    ):
        response = client.get(
            "/reminders",
            headers=headers,
            params={
                "status": "scheduled",
                "limit": 1,
                "offset": offset,
            },
        )
        assert response.status_code == 200, response.text
        assert [item["id"] for item in response.json()] == [expected_id]

    response = client.get(
        "/reminders",
        headers=headers,
        params={"status": "cancelled"},
    )
    assert response.status_code == 200, response.text
    assert [item["id"] for item in response.json()] == [third["id"]]


def test_settings_default_and_account_isolation(client, db_session):
    owner = create_account(client)
    other = create_account(client)

    response = client.get("/users/me", headers=owner)
    assert response.status_code == 200, response.text
    owner_id = response.json()["id"]

    assert db_session.get(NotificationSettings, owner_id) is None

    response = client.get(
        "/users/me/notification-settings",
        headers=owner,
    )
    assert response.status_code == 200, response.text
    assert response.json() == {"email_enabled": False}

    assert db_session.get(NotificationSettings, owner_id) is None

    response = client.patch(
        "/users/me/notification-settings",
        headers=owner,
        json={"email_enabled": True},
    )
    assert response.status_code == 200, response.text
    assert response.json() == {"email_enabled": True}

    response = client.get(
        "/users/me/notification-settings",
        headers=other,
    )
    assert response.status_code == 200, response.text
    assert response.json() == {"email_enabled": False}

    response = client.get(
        "/users/me/notification-settings",
        headers=owner,
    )
    assert response.status_code == 200, response.text
    assert response.json() == {"email_enabled": True}


def test_email_reminder_requires_enabled_settings(client):
    headers = create_account(client)
    application = create_application(client, headers)
    path = f"/applications/{application['id']}/reminders"

    response = client.post(
        path,
        headers=headers,
        json=reminder_payload(send_email=True),
    )
    assert response.status_code == 409, response.text

    response = client.patch(
        "/users/me/notification-settings",
        headers=headers,
        json={"email_enabled": True},
    )
    assert response.status_code == 200, response.text

    response = client.post(
        path,
        headers=headers,
        json=reminder_payload(send_email=True),
    )
    assert response.status_code == 201, response.text
    assert response.json()["send_email"] is True


def test_notification_visibility_count_and_read(client, db_session):
    owner = create_account(client)
    other = create_account(client)
    application = create_application(client, owner)

    reminders = [
        create_reminder(client, owner, application["id"])
        for _ in range(3)
    ]

    assert process_created_reminders(db_session, reminders) == 3

    response = client.get(
        "/notifications",
        headers=owner,
        params={"limit": 1},
    )
    assert response.status_code == 200, response.text
    assert len(response.json()) == 1

    notification_id = response.json()[0]["id"]

    response = client.get(
        "/notifications/unread-count",
        headers=owner,
    )
    assert response.status_code == 200, response.text
    assert response.json() == {"count": 3}

    response = client.get("/notifications", headers=other)
    assert response.status_code == 200, response.text
    assert response.json() == []

    response = client.get(
        "/notifications/unread-count",
        headers=other,
    )
    assert response.status_code == 200, response.text
    assert response.json() == {"count": 0}

    path = f"/notifications/{notification_id}/read"

    response = client.patch(path, headers=other)
    assert response.status_code == 404, response.text

    response = client.patch(path, headers=owner)
    assert response.status_code == 200, response.text
    first_read_at = response.json()["read_at"]
    assert first_read_at is not None

    response = client.patch(path, headers=owner)
    assert response.status_code == 200, response.text
    assert response.json()["read_at"] == first_read_at

    response = client.get(
        "/notifications/unread-count",
        headers=owner,
    )
    assert response.status_code == 200, response.text
    assert response.json() == {"count": 2}

    response = client.get(
        "/notifications",
        headers=owner,
        params={"unread": True},
    )
    assert response.status_code == 200, response.text
    assert len(response.json()) == 2
    assert all(item["read_at"] is None for item in response.json())

    response = client.get(
        "/notifications",
        headers=owner,
        params={"unread": False},
    )
    assert response.status_code == 200, response.text
    assert [item["id"] for item in response.json()] == [notification_id]

    response = client.post(
        f"/reminders/{reminders[0]['id']}/cancel",
        headers=owner,
    )
    assert response.status_code == 409, response.text


def test_disabling_email_cancels_pending_delivery(client, db_session):
    headers = create_account(client)
    application = create_application(client, headers)

    response = client.patch(
        "/users/me/notification-settings",
        headers=headers,
        json={"email_enabled": True},
    )
    assert response.status_code == 200, response.text

    reminder = create_reminder(
        client,
        headers,
        application["id"],
        send_email=True,
    )

    assert process_created_reminders(db_session, [reminder]) == 1

    notification = db_session.scalar(
        select(Notification).where(
            Notification.reminder_id == reminder["id"],
        )
    )
    assert notification is not None

    delivery = db_session.scalar(
        select(EmailDelivery).where(
            EmailDelivery.notification_id == notification.id,
        )
    )
    assert delivery is not None
    assert delivery.status == EmailDeliveryStatus.pending

    response = client.patch(
        "/users/me/notification-settings",
        headers=headers,
        json={"email_enabled": False},
    )
    assert response.status_code == 200, response.text

    db_session.refresh(delivery)
    assert delivery.status == EmailDeliveryStatus.cancelled

    response = client.patch(
        "/users/me/notification-settings",
        headers=headers,
        json={"email_enabled": True},
    )
    assert response.status_code == 200, response.text

    db_session.refresh(delivery)
    assert delivery.status == EmailDeliveryStatus.cancelled

    count = db_session.scalar(
        select(func.count())
        .select_from(EmailDelivery)
        .where(EmailDelivery.notification_id == notification.id)
    )
    assert count == 1


def test_enabling_email_does_not_send_old_notifications(
    client,
    db_session,
):
    headers = create_account(client)
    application = create_application(client, headers)

    reminder = create_reminder(
        client,
        headers,
        application["id"],
        send_email=False,
    )

    assert process_created_reminders(db_session, [reminder]) == 1

    notification = db_session.scalar(
        select(Notification).where(
            Notification.reminder_id == reminder["id"],
        )
    )
    assert notification is not None

    response = client.patch(
        "/users/me/notification-settings",
        headers=headers,
        json={"email_enabled": True},
    )
    assert response.status_code == 200, response.text

    delivery = db_session.scalar(
        select(EmailDelivery).where(
            EmailDelivery.notification_id == notification.id,
        )
    )
    assert delivery is None


@pytest.mark.parametrize(
    "path,params",
    [
        ("/reminders", {"limit": 101}),
        ("/reminders", {"offset": -1}),
        ("/reminders", {"status": "unknown"}),
        ("/notifications", {"limit": 101}),
        ("/notifications", {"offset": -1}),
    ],
)
def test_list_validation(client, path, params):
    headers = create_account(client)

    response = client.get(path, headers=headers, params=params)

    assert response.status_code == 422, response.text