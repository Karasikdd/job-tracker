from fastapi import APIRouter, HTTPException
from sqlalchemy import select, update

from app.enums import EmailDeliveryStatus
from app.models import (
    EmailDelivery,
    Notification,
    NotificationSettings,
    User,
)
from app.schemas import (
    NotificationSettingsPatch,
    NotificationSettingsRead,
)
from app.security import CurrentUser, Db


router = APIRouter(
    prefix="/users/me/notification-settings",
    tags=["notification-settings"],
)


@router.get(
    "",
    response_model=NotificationSettingsRead,
)
def get_notification_settings(
    db: Db,
    user: CurrentUser,
):
    settings = db.get(NotificationSettings, user.id)

    return NotificationSettingsRead(
        email_enabled=(
            settings.email_enabled
            if settings is not None
            else False
        ),
    )


@router.patch(
    "",
    response_model=NotificationSettingsRead,
)
def update_notification_settings(
    payload: NotificationSettingsPatch,
    db: Db,
    user: CurrentUser,
):
    try:
        owner_id = db.scalar(
            select(User.id)
            .where(User.id == user.id)
            .with_for_update()
        )

        if owner_id is None:
            raise HTTPException(
                status_code=401,
                detail="User account is no longer available",
            )

        settings = db.scalar(
            select(NotificationSettings)
            .where(NotificationSettings.user_id == owner_id)
            .execution_options(populate_existing=True)
        )

        if settings is None:
            settings = NotificationSettings(
                user_id=owner_id,
                email_enabled=payload.email_enabled,
            )
            db.add(settings)
        else:
            settings.email_enabled = payload.email_enabled

        if not payload.email_enabled:
            owned_notification_ids = select(Notification.id).where(
                Notification.user_id == owner_id,
            )

            db.execute(
                update(EmailDelivery)
                .where(
                    EmailDelivery.notification_id.in_(
                        owned_notification_ids
                    ),
                    EmailDelivery.status
                    == EmailDeliveryStatus.pending,
                )
                .values(
                    status=EmailDeliveryStatus.cancelled,
                )
                .execution_options(synchronize_session=False)
            )

        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(settings)

    return NotificationSettingsRead(
        email_enabled=settings.email_enabled,
    )