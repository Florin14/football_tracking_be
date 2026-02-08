from fastapi import Depends, Request
from sqlalchemy.orm import Session

from extensions.sqlalchemy import get_db

from project_helpers.dependencies import JwtRequired

from project_helpers.responses import ConfirmationResponse
from .router import router

from modules.notifications.models.notifications_model import NotificationModel

@router.put("-mark-all-as-read", response_model=ConfirmationResponse, dependencies=[Depends(JwtRequired())])
async def mark_all_as_read_notifications(
    request: Request,
    db: Session = Depends(get_db),
):
    auth_user = request.state.user
    db.query(NotificationModel).filter(
        NotificationModel.playerId == auth_user.id,
        NotificationModel.isDeleted == False
    ).update(
        {NotificationModel.isDeleted: True},
        synchronize_session=False
    )

    db.commit()

    return ConfirmationResponse()
