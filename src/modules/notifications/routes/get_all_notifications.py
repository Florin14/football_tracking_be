from typing import Optional

from fastapi import Depends
from sqlalchemy.orm import Session, joinedload

from extensions.sqlalchemy import get_db
from modules.notifications.models.notifications_schemas import NotificationListResponse

from .router import router

from modules.notifications.models.notifications_model import NotificationModel

@router.get("/", response_model=NotificationListResponse)
async def get_notifications(
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        db: Session = Depends(get_db)
):
    query = db.query(NotificationModel)

    if search:
        query = query.filter(NotificationModel.name.ilike(f"%{search}%"))

    notifications = query.offset(skip).limit(limit).all()

    return NotificationListResponse(data=notifications)
