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
    db_match = MatchModel(
        team1Id=match.team1Id,
        team2Id=match.team2Id,
        leagueId=match.leagueId,
        round=match.round,
        timestamp=match.timestamp,
    )
    db_match.location = match.location
    db.add(db_match)
    db.commit()
    db.refresh(db_match)

    return db_match


