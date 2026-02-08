from fastapi import Depends
from sqlalchemy.orm import Session

from constants.platform_roles import PlatformRoles
from extensions import get_db
from modules.player.models.player_model import PlayerModel
from project_helpers.dependencies import JwtRequired
from .helpers import generate_teams
from .router import router


@router.post("-generate", dependencies=[Depends(JwtRequired(roles=[PlatformRoles.ADMIN]))])
async def create_teams(
    playerIds: list[int],
    db: Session = Depends(get_db),
):
    players = db.query(PlayerModel).filter(PlayerModel.id.in_(playerIds)).all()
    team1, team2 = generate_teams(players)
    return {"team1": [p.name for p in team1], "team2": [p.name for p in team2]}
