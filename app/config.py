from typing import Literal, Self

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(repr=False)
    secret_key: str = Field(min_length=32, repr=False)

    broker_url: str = Field(
        default="redis://127.0.0.1:6379/0",
        repr=False,
    )

    email_delivery_enabled: bool = False
    email_transport: Literal["mailpit", "smtp"] = "mailpit"

    smtp_host: str = Field(default="127.0.0.1", min_length=1)
    smtp_port: int = Field(default=1025, ge=1, le=65535)
    smtp_security: Literal["none", "starttls", "ssl"] = "none"

    smtp_username: str | None = Field(default=None, repr=False)
    smtp_password: SecretStr | None = Field(default=None, repr=False)

    email_from: str = Field(
        default="jobtracker@example.test",
        min_length=1,
    )
    smtp_timeout_seconds: float = Field(
        default=10,
        gt=0,
        allow_inf_nan=False,
    )

    frontend_url: str = Field(
        default="http://127.0.0.1:5173",
        pattern=r"^https?://[^\s]+$",
    )
    email_allowlist: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_email_configuration(self) -> Self:
        if self.email_transport == "mailpit":
            local_hosts = {
                "localhost",
                "127.0.0.1",
                "::1",
                "mailpit",
            }

            if self.smtp_host.lower() not in local_hosts:
                raise ValueError(
                    "Mailpit transport requires a local Mailpit host"
                )

            if self.smtp_username is not None or self.smtp_password is not None:
                raise ValueError(
                    "Mailpit transport does not use SMTP credentials"
                )

        if self.email_transport == "smtp":
            required_fields = {
                "smtp_host",
                "smtp_port",
                "smtp_security",
                "email_from",
            }

            if not required_fields.issubset(self.model_fields_set):
                raise ValueError(
                    "SMTP transport requires explicit host, port, "
                    "security, and sender settings"
                )

            if self.smtp_security == "none":
                raise ValueError(
                    "SMTP transport requires STARTTLS or SSL"
                )

            has_username = bool(self.smtp_username)
            has_password = (
                self.smtp_password is not None
                and bool(self.smtp_password.get_secret_value())
            )

            if has_username != has_password:
                raise ValueError(
                    "SMTP username and password must be provided together"
                )

            if self.email_delivery_enabled and not self.email_allowlist:
                raise ValueError(
                    "SMTP delivery requires a non-empty email allowlist"
                )

        return self


settings = Settings()