from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from constants.platform_roles import PlatformRoles
from extensions.sqlalchemy import get_db
from project_helpers.dependencies import JwtRequired
from project_helpers.responses import ConfirmationResponse
from .router import router
from modules.notifications.models.notifications_model import NotificationModel


@router.delete("/{id}", response_model=ConfirmationResponse, dependencies=[Depends(JwtRequired(roles=[PlatformRoles.ADMIN]))])
async def delete_notification(
    id: int,
    db: Session = Depends(get_db),
):
    notification = db.query(NotificationModel).filter(NotificationModel.id == id).first()
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )

    db.delete(notification)
    db.commit()

    return ConfirmationResponse(
        success=True,
        message=f"Notification {notification.name} deleted successfully"
    )
