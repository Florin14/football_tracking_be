from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from constants.notification_type import NotificationType
from constants.platform_roles import PlatformRoles
from extensions.sqlalchemy import get_db
from modules.notifications.models.notifications_schemas import NotificationAdd, NotificationResponse
from modules.notifications.services.notification_service import create_player_notifications
from project_helpers.dependencies import JwtRequired
from .router import router


@router.post("/", response_model=NotificationResponse, dependencies=[Depends(JwtRequired(roles=[PlatformRoles.ADMIN]))])
async def add_notification(
    data: NotificationAdd,
    db: Session = Depends(get_db),
):
    try:
        notification_type = NotificationType(data.type) if data.type else NotificationType.NEW_MATCH
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid notification type: {data.type}",
        )

    notifications = create_player_notifications(
        db=db,
        player_ids=[data.userId],
        name=data.name or "Notification",
        description=data.description or "",
        notification_type=notification_type,
        created_at=data.createdAt,
    )
    db.commit()

    notification = next((item for item in notifications if item.userId == data.userId), None)
    db.refresh(notification)

    return notification


