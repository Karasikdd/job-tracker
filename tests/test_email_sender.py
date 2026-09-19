from types import SimpleNamespace

import pytest

from app.services import email_sender


@pytest.fixture
def mail_configuration(monkeypatch):
    configuration = SimpleNamespace(
        email_delivery_enabled=True,
        email_transport="mailpit",
        smtp_host="127.0.0.1",
        smtp_port=1025,
        smtp_security="none",
        smtp_timeout_seconds=10,
        email_from="jobtracker@example.test",
        frontend_url="http://127.0.0.1:5173/",
        secret_key="secret-that-must-not-appear-in-email",
        smtp_password="password-that-must-not-appear-in-email",
    )

    monkeypatch.setattr(email_sender, "settings", configuration)

    return configuration


@pytest.fixture
def smtp_capture(monkeypatch):
    captured = {}

    class FakeSMTP:
        def __init__(self, *, host, port, timeout):
            captured["host"] = host
            captured["port"] = port
            captured["timeout"] = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            captured["closed"] = True
            return False

        def send_message(self, message, *, from_addr, to_addrs):
            captured["message"] = message
            captured["from_addr"] = from_addr
            captured["to_addrs"] = to_addrs
            return {}

    monkeypatch.setattr(email_sender.smtplib, "SMTP", FakeSMTP)

    return captured


def test_email_content_and_connection(
    mail_configuration,
    smtp_capture,
):
    email_sender.send_notification_email(
        recipient="owner@example.com",
        title="Follow up with recruiter",
        body="Ask about the next interview stage.",
        application_id=42,
        delivery_id=7,
    )

    message = smtp_capture["message"]
    content = message.get_content()

    assert message["From"] == "jobtracker@example.test"
    assert message["To"] == "owner@example.com"
    assert message["Subject"] == "Job Tracker reminder"
    assert message["X-Job-Tracker-Delivery-ID"] == "7"
    assert message["Message-ID"] is not None

    assert message.get_content_type() == "text/plain"
    assert "Follow up with recruiter" in content
    assert "Ask about the next interview stage." in content
    assert "http://127.0.0.1:5173/applications/42" in content

    assert smtp_capture["host"] == "127.0.0.1"
    assert smtp_capture["port"] == 1025
    assert smtp_capture["timeout"] == 10
    assert smtp_capture["from_addr"] == "jobtracker@example.test"
    assert smtp_capture["to_addrs"] == ["owner@example.com"]
    assert smtp_capture["closed"] is True

    serialized = message.as_string()

    assert mail_configuration.secret_key not in serialized
    assert mail_configuration.smtp_password not in serialized


def test_title_cannot_add_headers(
    mail_configuration,
    smtp_capture,
):
    email_sender.send_notification_email(
        recipient="owner@example.com",
        title="Reminder\r\nBcc: unwanted@example.com",
        body="Test body",
        application_id=42,
        delivery_id=7,
    )

    message = smtp_capture["message"]

    assert message["Subject"] == "Job Tracker reminder"
    assert message["Bcc"] is None
    assert smtp_capture["to_addrs"] == ["owner@example.com"]


def test_disabled_email_does_not_connect(
    mail_configuration,
    smtp_capture,
):
    mail_configuration.email_delivery_enabled = False

    with pytest.raises(RuntimeError, match="Email delivery is disabled"):
        email_sender.send_notification_email(
            recipient="owner@example.com",
            title="Reminder",
            body="Test body",
            application_id=42,
            delivery_id=7,
        )

    assert smtp_capture == {}


def test_external_transport_is_not_used(
    mail_configuration,
    smtp_capture,
):
    mail_configuration.email_transport = "smtp"

    with pytest.raises(RuntimeError, match="Mailpit"):
        email_sender.send_notification_email(
            recipient="owner@example.com",
            title="Reminder",
            body="Test body",
            application_id=42,
            delivery_id=7,
        )

    assert smtp_capture == {}


def test_recipient_header_injection_is_rejected(
    mail_configuration,
    smtp_capture,
):
    with pytest.raises(ValueError, match="Invalid email header"):
        email_sender.send_notification_email(
            recipient="owner@example.com\r\nBcc: unwanted@example.com",
            title="Reminder",
            body="Test body",
            application_id=42,
            delivery_id=7,
        )

    assert smtp_capture == {}