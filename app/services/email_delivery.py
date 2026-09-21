import smtplib
import ssl
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.enums import EmailDeliveryStatus
from app.models import (
    EmailDelivery,
    Notification,
    NotificationSettings,
    User,
)
from app.services.email_sender import send_notification_email


MAX_ATTEMPTS = 5
LEASE_DURATION = timedelta(minutes=2)
RETRY_DELAYS = (
    timedelta(seconds=30),
    timedelta(minutes=2),
    timedelta(minutes=5),
    timedelta(minutes=15),
)


@dataclass(frozen=True)
class ClaimedDelivery:
    delivery_id: int
    lease_token: str
    recipient: str
    title: str
    body: str
    application_id: int


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def require_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("A timezone-aware datetime is required")

    return value.astimezone(timezone.utc)


def clear_lease(delivery: EmailDelivery) -> None:
    delivery.lease_until = None
    delivery.lease_token = None


def claim_email_delivery(
    db: Session,
    delivery_id: int,
    now: datetime,
) -> ClaimedDelivery | None:
    now = require_utc(now)

    if not settings.email_delivery_enabled:
        return None

    owner_id = db.scalar(
        select(Notification.user_id)
        .join(
            EmailDelivery,
            EmailDelivery.notification_id == Notification.id,
        )
        .where(EmailDelivery.id == delivery_id)
    )

    if owner_id is None:
        return None

    user = db.scalar(
        select(User)
        .where(User.id == owner_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )

    if user is None:
        return None

    delivery = db.scalar(
        select(EmailDelivery)
        .where(EmailDelivery.id == delivery_id)
        .with_for_update(skip_locked=True)
        .execution_options(populate_existing=True)
    )

    if delivery is None:
        return None

    if delivery.status in {
        EmailDeliveryStatus.sent,
        EmailDeliveryStatus.failed,
        EmailDeliveryStatus.cancelled,
    }:
        return None

    if delivery.status == EmailDeliveryStatus.processing:
        if (
            delivery.lease_until is not None
            and require_utc(delivery.lease_until) > now
        ):
            return None

    if delivery.status == EmailDeliveryStatus.pending:
        if require_utc(delivery.next_attempt_at) > now:
            return None

    notification = db.scalar(
        select(Notification)
        .where(Notification.id == delivery.notification_id)
        .execution_options(populate_existing=True)
    )

    if notification is None or notification.user_id != user.id:
        delivery.status = EmailDeliveryStatus.cancelled
        delivery.last_error_code = "notification_unavailable"
        clear_lease(delivery)
        db.flush()
        return None

    email_enabled = db.scalar(
        select(NotificationSettings.email_enabled).where(
            NotificationSettings.user_id == user.id,
        )
    )

    if not email_enabled:
        delivery.status = EmailDeliveryStatus.cancelled
        delivery.last_error_code = "email_disabled"
        clear_lease(delivery)
        db.flush()
        return None

    if delivery.attempts >= MAX_ATTEMPTS:
        delivery.status = EmailDeliveryStatus.failed
        delivery.last_error_code = "attempt_limit_reached"
        clear_lease(delivery)
        db.flush()
        return None

    lease_token = str(uuid4())

    delivery.status = EmailDeliveryStatus.processing
    delivery.attempts += 1
    delivery.lease_token = lease_token
    delivery.lease_until = now + LEASE_DURATION
    delivery.last_error_code = None

    db.flush()

    return ClaimedDelivery(
        delivery_id=delivery.id,
        lease_token=lease_token,
        recipient=user.email,
        title=notification.title,
        body=notification.body,
        application_id=notification.application_id,
    )


def finish_email_delivery(
    db: Session,
    claim: ClaimedDelivery,
    now: datetime,
    *,
    error_code: str | None = None,
    retryable: bool = False,
) -> bool:
    now = require_utc(now)

    delivery = db.scalar(
        select(EmailDelivery)
        .where(EmailDelivery.id == claim.delivery_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )

    if delivery is None:
        return False

    if (
        delivery.status != EmailDeliveryStatus.processing
        or delivery.lease_token != claim.lease_token
    ):
        return False

    clear_lease(delivery)

    if error_code is None:
        delivery.status = EmailDeliveryStatus.sent
        delivery.sent_at = now
        delivery.last_error_code = None
    else:
        delivery.last_error_code = error_code

        if retryable and delivery.attempts < MAX_ATTEMPTS:
            delivery.status = EmailDeliveryStatus.pending
            delivery.next_attempt_at = (
                now + RETRY_DELAYS[delivery.attempts - 1]
            )
        else:
            delivery.status = EmailDeliveryStatus.failed

    db.flush()

    return True


def classify_email_error(error: Exception) -> tuple[str, bool]:
    if isinstance(error, smtplib.SMTPAuthenticationError):
        return "smtp_authentication_failed", False

    if isinstance(error, ssl.SSLCertVerificationError):
        return "smtp_certificate_invalid", False

    if isinstance(error, smtplib.SMTPRecipientsRefused):
        codes = [
            response[0]
            for response in error.recipients.values()
        ]

        retryable = bool(codes) and all(
            400 <= code < 500 for code in codes
        )

        return "smtp_recipient_refused", retryable

    if isinstance(error, smtplib.SMTPResponseException):
        code = error.smtp_code

        return f"smtp_response_{code}", 400 <= code < 500

    if isinstance(error, smtplib.SMTPServerDisconnected):
        return "smtp_disconnected", True

    if isinstance(error, TimeoutError):
        return "smtp_timeout", True

    if isinstance(error, OSError):
        return "smtp_network_error", True

    if isinstance(error, smtplib.SMTPException):
        return "smtp_error", False

    if isinstance(error, (ValueError, RuntimeError)):
        return "email_configuration_error", False

    return "unexpected_email_error", False


def deliver_email(delivery_id: int) -> str:
    with SessionLocal.begin() as db:
        claim = claim_email_delivery(
            db,
            delivery_id,
            utc_now(),
        )

    if claim is None:
        return "skipped"

    error_code = None
    retryable = False

    try:
        send_notification_email(
            recipient=claim.recipient,
            title=claim.title,
            body=claim.body,
            application_id=claim.application_id,
            delivery_id=claim.delivery_id,
        )
    except Exception as error:
        error_code, retryable = classify_email_error(error)

        with SessionLocal.begin() as db:
            applied = finish_email_delivery(
                db,
                claim,
                utc_now(),
                error_code=error_code,
                retryable=retryable,
            )

        if not applied:
            return "stale"

        if error_code == "unexpected_email_error":
            raise

        return "send_failed"

    with SessionLocal.begin() as db:
        applied = finish_email_delivery(
            db,
            claim,
            utc_now(),
        )

    return "sent" if applied else "stale"