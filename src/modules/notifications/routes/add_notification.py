from datetime import datetime

from fastapi import Depends
from sqlalchemy.orm import Session

from constants.platform_roles import PlatformRoles
from extensions.sqlalchemy import get_db
from modules.notifications.models.notifications_schemas import NotificationAdd, NotificationResponse
from project_helpers.dependencies import JwtRequired
from .router import router
from modules.notifications.models.notifications_model import NotificationModel


@router.post("/", response_model=NotificationResponse, dependencies=[Depends(JwtRequired(roles=[PlatformRoles.ADMIN]))])
async def add_notification(
    data: NotificationAdd,
    db: Session = Depends(get_db),
):
    notification = NotificationModel(
        name=data.name,
        description=data.description,
        playerId=data.playerId,
        type=data.type,
        createdAt=data.createdAt or datetime.utcnow(),
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)

    return notification


