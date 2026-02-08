from datetime import timedelta

from fastapi import Depends
from sqlalchemy.orm import Session

from constants.platform_roles import PlatformRoles
from extensions import get_db
from modules.match.models.match_model import MatchModel
from modules.match.models.match_schemas import MatchAdd
from modules.match.routes.router import router
from project_helpers.dependencies import JwtRequired

@router.post("-schedule", dependencies=[Depends(JwtRequired(roles=[PlatformRoles.ADMIN]))])
async def schedule_match(
    match: MatchAdd,
    db: Session = Depends(get_db),
):
    db_match = MatchModel(date=match.date, location=match.location)
    db.add(db_match)
    db.commit()

    # Programare notificare
    notification_time = match.date - timedelta(hours=24)
    # send_notification.apply_async(args=["player@example.com", "You have a match tomorrow!"], eta=notification_time)

    return db_match
