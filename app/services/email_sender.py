import smtplib
from email.message import EmailMessage
from email.utils import make_msgid

from app.config import settings


def send_notification_email(
    *,
    recipient: str,
    title: str,
    body: str,
    application_id: int,
    delivery_id: int,
) -> None:
    if not settings.email_delivery_enabled:
        raise RuntimeError("Email delivery is disabled")

    if settings.email_transport != "mailpit":
        raise RuntimeError(
            "Only the local Mailpit transport is implemented"
        )

    if settings.smtp_host.lower() not in {
        "localhost",
        "127.0.0.1",
        "::1",
        "mailpit",
    }:
        raise ValueError("Mailpit requires a local SMTP host")

    if settings.smtp_security != "none":
        raise ValueError(
            "Local Mailpit transport requires SMTP_SECURITY=none"
        )

    if application_id < 1 or delivery_id < 1:
        raise ValueError("Application and delivery IDs must be positive")

    for address in (recipient, settings.email_from):
        if not address.strip() or "\r" in address or "\n" in address:
            raise ValueError("Invalid email header value")

    application_url = (
        f"{settings.frontend_url.rstrip('/')}"
        f"/applications/{application_id}"
    )

    message = EmailMessage()
    message["From"] = settings.email_from
    message["To"] = recipient
    message["Subject"] = "Job Tracker reminder"
    message["Message-ID"] = make_msgid(domain="jobtracker.example.test")
    message["X-Job-Tracker-Delivery-ID"] = str(delivery_id)

    message.set_content(
        f"{title}\n\n"
        f"{body}\n\n"
        f"View application:\n{application_url}\n"
    )

    with smtplib.SMTP(
        host=settings.smtp_host,
        port=settings.smtp_port,
        timeout=settings.smtp_timeout_seconds,
    ) as smtp:
        smtp.send_message(
            message,
            from_addr=settings.email_from,
            to_addrs=[recipient],
        )