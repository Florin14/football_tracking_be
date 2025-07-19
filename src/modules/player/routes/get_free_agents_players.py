
from typing import Optional

from fastapi import Depends
from sqlalchemy.orm import Session

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
    query = db.query(PlayerModel).filter(PlayerModel.teamId == None)

    if position:
        query = query.filter(PlayerModel.position == position)

    players = query.offset(skip).limit(limit).all()

    player_items = []
    for player in players:
        player_items.append({
            "id": player.id,
            "name": player.name,
            "email": player.email,
            "position": player.position.value if player.position else None,
            "rating": player.rating,
            "teamName": None
        })

    return PlayerListResponse(data=player_items)
