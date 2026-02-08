from fastapi import Depends
from sqlalchemy.orm import Session

from extensions.sqlalchemy import get_db

from project_helpers.dependencies import GetCurrentUser

from project_helpers.responses import ConfirmationResponse
from .router import router

from modules.notifications.models.notifications_model import NotificationModel

@router.put("-mark-all-as-read", response_model=ConfirmationResponse)
async def mark_all_as_read_notifications(
    db: Session = Depends(get_db),
    current_user=Depends(GetCurrentUser()),
):
    db.query(NotificationModel).filter(
        NotificationModel.playerId == current_user.id,
        NotificationModel.isDeleted == False
    ).update(
        {NotificationModel.isDeleted: True},
        synchronize_session=False
    )

    db.commit()

    return ConfirmationResponse()
