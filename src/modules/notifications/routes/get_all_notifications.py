from fastapi import Depends
from sqlalchemy.orm import Session

from extensions.sqlalchemy import get_db
from project_helpers.db import apply_search
from modules.notifications.models.notifications_schemas import NotificationListResponse, NotificationListParams

from .router import router

from modules.notifications.models.notifications_model import NotificationModel

@router.get("/", response_model=NotificationListResponse)
async def get_notifications(
        params: NotificationListParams = Depends(),
        db: Session = Depends(get_db)
):
    query = db.query(NotificationModel)

    query = apply_search(query, NotificationModel.name, params.search)

    notifications = params.apply(query).all()

    return NotificationListResponse(data=notifications)
