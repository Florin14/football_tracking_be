from datetime import datetime
from typing import List

from sqlalchemy.orm import Session

from constants.notification_type import NotificationType
from constants.platform_roles import PlatformRoles
from modules.notifications.models.notifications_model import NotificationModel
from modules.user.models.user_model import UserModel


def _get_active_admin_ids(db: Session) -> List[int]:
    rows = (
        db.query(UserModel.id)
        .filter(
            UserModel.role == PlatformRoles.ADMIN,
            UserModel.isDeleted.is_(False),
            UserModel.isAvailable.is_(True),
        )
        .all()
    )
    return [admin_id for (admin_id,) in rows]


def create_player_notifications(
    db: Session,
    player_ids: List[int],
    name: str,
    description: str,
    notification_type: NotificationType,
    created_at: datetime | None = None,
) -> List[NotificationModel]:
    if not player_ids:
        return []

    batch_created_at = created_at or datetime.utcnow()
    recipients = {player_id for player_id in player_ids if player_id is not None}
    recipients.update(_get_active_admin_ids(db))

    notifications = [
        NotificationModel(
            name=name,
            description=description,
            userId=user_id,
            type=notification_type,
            createdAt=batch_created_at,
            isDeleted=False,
        )
        for user_id in recipients
    ]
    db.add_all(notifications)
    return notifications
