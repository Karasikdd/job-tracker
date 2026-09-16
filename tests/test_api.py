from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.config import settings


def account(client, email):
    credentials = {"email": email, "password": "Example-password-123"}
    response = client.post("/auth/register", json=credentials)
    assert response.status_code == 201, response.text
    assert "password_hash" not in response.json()
    response = client.post("/auth/login", json=credentials)
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def application(client, headers, **overrides):
    data = {"company": "Example GmbH", "position": "Backend", "status": "saved"}
    data.update(overrides)
    response = client.post("/applications", json=data, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def test_creation_update_history_and_deletion(client):
    headers = account(client, "owner@example.com")
    item = application(client, headers)
    path = f"/applications/{item['id']}"
    assert client.get(path, headers=headers).json()["company"] == "Example GmbH"
    response = client.patch(path, json={"status": "applied"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["company"] == "Example GmbH"
    assert response.json()["status"] == "applied"
    client.patch(path, json={"status": "applied"}, headers=headers)
    history = client.get(path + "/history", headers=headers).json()
    assert len(history) == 1
    assert history[0]["old_status"] == "saved"
    assert history[0]["new_status"] == "applied"
    assert client.delete(path, headers=headers).status_code == 204
    assert client.get(path, headers=headers).status_code == 404


@pytest.mark.parametrize("method", ["GET", "PATCH", "DELETE"])
def test_other_user_cannot_access_application(client, method):
    owner = account(client, "owner@example.com")
    other = account(client, "other@example.com")
    item = application(client, owner)
    kwargs = {"headers": other}
    if method == "PATCH":
        kwargs["json"] = {"status": "offer"}
    response = client.request(method, f"/applications/{item['id']}", **kwargs)
    assert response.status_code == 404
    assert client.get(f"/applications/{item['id']}", headers=owner).status_code == 200
    assert client.get("/applications", headers=other).json() == []
    assert client.get("/stats", headers=other).json()["total"] == 0
    assert client.get(
        f"/applications/{item['id']}/history", headers=other
    ).status_code == 404


@pytest.mark.parametrize("patch", [{"company": None}, {"status": "banana"}])
def test_invalid_patch_is_rejected(client, patch):
    headers = account(client, "owner@example.com")
    item = application(client, headers)
    response = client.patch(
        f"/applications/{item['id']}", json=patch, headers=headers
    )
    assert response.status_code == 422


def test_filters_pagination_and_stats(client):
    headers = account(client, "owner@example.com")
    application(client, headers, company="Alpha", status="applied")
    application(client, headers, company="Beta", status="saved")
    application(client, headers, company="Alpha Labs", status="applied")
    filtered = client.get(
        "/applications", params={"status": "applied", "search": "alpha"},
        headers=headers,
    ).json()
    assert len(filtered) == 2
    assert all(row["status"] == "applied" for row in filtered)
    first = client.get(
        "/applications", params={"limit": 1, "offset": 0}, headers=headers
    ).json()
    second = client.get(
        "/applications", params={"limit": 1, "offset": 1}, headers=headers
    ).json()
    assert first[0]["id"] != second[0]["id"]
    stats = client.get("/stats", headers=headers).json()
    assert stats["total"] == 3
    assert stats["by_status"]["applied"] == 2


def test_authentication_failures(client):
    headers = account(client, "owner@example.com")
    user_id = client.get("/users/me", headers=headers).json()["id"]
    assert client.get("/applications").status_code == 401
    assert client.get(
        "/applications", headers={"Authorization": "Bearer broken-token"}
    ).status_code == 401
    assert client.post(
        "/auth/login",
        json={"email": "owner@example.com", "password": "Incorrect-password-123"},
    ).status_code == 401
    expired = jwt.encode(
        {
            "sub": str(user_id),
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        },
        settings.secret_key,
        algorithm="HS256",
    )
    assert client.get(
        "/applications", headers={"Authorization": f"Bearer {expired}"}
    ).status_code == 401


def test_validation_and_nullable_fields(client):
    headers = account(client, "owner@example.com")
    bad = {"company": "   ", "position": "Backend"}
    assert client.post("/applications", json=bad, headers=headers).status_code == 422
    item = application(client, headers, notes="A note")
    path = f"/applications/{item['id']}"
    cleared = client.patch(path, json={"notes": None}, headers=headers)
    assert cleared.status_code == 200
    assert cleared.json()["notes"] is None
    assert client.get(
        "/applications", params={"limit": 101}, headers=headers
    ).status_code == 422


def test_duplicate_email(client):
    account(client, "owner@example.com")
    response = client.post(
        "/auth/register",
        json={"email": "owner@example.com", "password": "Example-password-123"},
    )
    assert response.status_code == 409