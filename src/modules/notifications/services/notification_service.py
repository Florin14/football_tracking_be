from datetime import datetime
from typing import List

from sqlalchemy.orm import Session

from constants.notification_type import NotificationType
from modules.notifications.models.notifications_model import NotificationModel


def create_player_notifications(
    db: Session,
    player_ids: List[int],
    name: str,
    description: str,
    notification_type: NotificationType,
) -> None:
    if not player_ids:
        return
    batch_created_at = datetime.utcnow()
    notifications = [
        NotificationModel(
            name=name,
            description=description,
            playerId=player_id,
            type=notification_type,
            createdAt=batch_created_at,
            isDeleted=False,
        )
        for player_id in player_ids
    ]
    db.bulk_save_objects(notifications)
