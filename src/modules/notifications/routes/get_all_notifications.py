from fastapi import Depends
from sqlalchemy.orm import Session

from extensions.sqlalchemy import get_db
from project_helpers.db import apply_search
from project_helpers.dependencies import GetCurrentUser
from constants.platform_roles import PlatformRoles
from modules.notifications.models.notifications_schemas import NotificationListResponse, NotificationListParams

from .router import router

from modules.notifications.models.notifications_model import NotificationModel

@router.get("/", response_model=NotificationListResponse)
async def get_notifications(
        params: NotificationListParams = Depends(),
        db: Session = Depends(get_db),
        # current_user=Depends(GetCurrentUser()),
):
    query = db.query(NotificationModel)

    query = apply_search(query, NotificationModel.name, params.search)

    # if current_user.role == PlatformRoles.PLAYER:
    #     query = query.filter(NotificationModel.playerId == current_user.id)

    notifications = params.apply(query).all()

    return NotificationListResponse(data=notifications)
