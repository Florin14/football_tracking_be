
from typing import Optional

from fastapi import Depends
from sqlalchemy.orm import Session, joinedload

from extensions import get_db
from modules.player.models.player_model import PlayerModel
from modules.player.models.player_schemas import PlayerFilter, PlayerListResponse
from .router import router


@router.get("/free-agents/", response_model=PlayerListResponse)
async def get_free_agents(
        skip: int = 0,
        limit: int = 100,
        position: Optional[str] = None,
        db: Session = Depends(get_db)
):
    """Get players without a team (free agents)"""
    query = db.query(PlayerModel).options(joinedload(PlayerModel.team)).filter(PlayerModel.teamId == None)

    if position:
        query = query.filter(PlayerModel.position == position)

    players = query.offset(skip).limit(limit).all()

    return PlayerListResponse(data=players)
