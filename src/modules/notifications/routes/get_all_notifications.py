from fastapi import Depends, Request
from sqlalchemy.orm import Session

from extensions.sqlalchemy import get_db
from project_helpers.db import apply_search
from constants.platform_roles import PlatformRoles
from modules.notifications.models.notifications_schemas import NotificationListResponse, NotificationListParams
from project_helpers.dependencies.jwt_required import JwtRequired

from .router import router

from modules.notifications.models.notifications_model import NotificationModel

@router.get("/", response_model=NotificationListResponse, dependencies=[Depends(JwtRequired(roles=[PlatformRoles.ADMIN, PlatformRoles.PLAYER]))])
async def get_notifications(
        request: Request,
        params: NotificationListParams = Depends(),
        db: Session = Depends(get_db),
):
    query = (
        db.query(NotificationModel)
        .filter(
            NotificationModel.isDeleted == False,
            NotificationModel.userId == request.state.user.id,
        )
        .order_by(NotificationModel.createdAt.desc(), NotificationModel.id.desc())
    )

    query = apply_search(query, NotificationModel.name, params.search)
    notifications = params.apply(query).all()

    return NotificationListResponse(data=notifications)


