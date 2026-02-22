from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from extensions.sqlalchemy import get_db
from project_helpers.dependencies import JwtRequired
from project_helpers.responses import ConfirmationResponse
from .router import router
from modules.notifications.models.notifications_model import NotificationModel


@router.put("/{id}/read", response_model=ConfirmationResponse, dependencies=[Depends(JwtRequired())])
async def mark_as_read_notification(
    id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    auth_user = request.state.user
    notification = db.query(NotificationModel).filter(
        NotificationModel.id == id,
        NotificationModel.userId == auth_user.id,
    ).first()
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )

    notification.isDeleted = True
    db.commit()

    return ConfirmationResponse(success=True, message="Notification marked as read")
