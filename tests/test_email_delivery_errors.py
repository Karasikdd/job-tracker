import smtplib

import pytest

from app.services.email_delivery import classify_email_error


@pytest.mark.parametrize(
    "error,expected_code,expected_retryable",
    [
        (
            TimeoutError(),
            "smtp_timeout",
            True,
        ),
        (
            ConnectionRefusedError(),
            "smtp_network_error",
            True,
        ),
        (
            smtplib.SMTPServerDisconnected("Disconnected"),
            "smtp_disconnected",
            True,
        ),
        (
            smtplib.SMTPDataError(451, b"Try later"),
            "smtp_response_451",
            True,
        ),
        (
            smtplib.SMTPDataError(550, b"Rejected"),
            "smtp_response_550",
            False,
        ),
        (
            smtplib.SMTPAuthenticationError(535, b"Rejected"),
            "smtp_authentication_failed",
            False,
        ),
        (
            smtplib.SMTPRecipientsRefused(
                {"test@example.com": (450, b"Try later")}
            ),
            "smtp_recipient_refused",
            True,
        ),
        (
            smtplib.SMTPRecipientsRefused(
                {"test@example.com": (550, b"Unknown recipient")}
            ),
            "smtp_recipient_refused",
            False,
        ),
        (
            ValueError("Invalid configuration"),
            "email_configuration_error",
            False,
        ),
    ],
)
def test_email_error_classification(
    error,
    expected_code,
    expected_retryable,
):
    assert classify_email_error(error) == (
        expected_code,
        expected_retryable,
    )