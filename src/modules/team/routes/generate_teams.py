from fastapi import Depends
from sqlalchemy.orm import Session

from extensions import get_db
from modules.player.models.player_model import PlayerModel
from .helpers import generate_teams
from .router import router


@router.post("-generate")
async def create_teams(playerIds: list[int], db: Session = Depends(get_db)):
    players = db.query(PlayerModel).filter(PlayerModel.id.in_(playerIds)).all()
    team1, team2 = generate_teams(players)
    return {"team1": [p.name for p in team1], "team2": [p.name for p in team2]}
