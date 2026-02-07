from fastapi import Depends
from sqlalchemy.orm import Session

from extensions.sqlalchemy import get_db
from modules.notifications.models.notifications_schemas import NotificationUpdate, NotificationResponse

from project_helpers.dependencies import GetInstanceFromPath
from .router import router

from modules.notifications.models.notifications_model import NotificationModel

@router.put("/{id}", response_model=NotificationResponse)
async def update_notification(data: NotificationUpdate, notification: NotificationModel = Depends(GetInstanceFromPath(NotificationModel)), db: Session = Depends(get_db)):
    if data.name:
        notification.name = data.name

    if data.description is not None:
        notification.description = data.description

    db.commit()
    db.refresh(notification)

    return notification
