from fastapi import Depends
from sqlalchemy.orm import Session

from constants.platform_roles import PlatformRoles
from extensions.sqlalchemy import get_db
from modules.ranking.models.ranking_model import RankingModel
from modules.notifications.models.notifications_schemas import  NotificationAdd, NotificationResponse
from project_helpers.dependencies import JwtRequired
from .router import router
from modules.notifications.models.notifications_model import NotificationModel


@router.post("/", response_model=NotificationResponse, dependencies=[Depends(JwtRequired(roles=[PlatformRoles.ADMIN]))])
async def add_notification(
    data: NotificationAdd,
    db: Session = Depends(get_db),
):
    notification = NotificationModel(
        name=data.name,
        description=data.description,
        leagueId=1,
    )
    db.add(notification)
    db.flush()

    exists = db.query(RankingModel).filter_by(teamId=notification.id, leagueId=notification.leagueId).first()
    if not exists:
        db.add(RankingModel(teamId=notification.id, leagueId=notification.leagueId))

    db.commit()
    db.refresh(notification)

    return notification
