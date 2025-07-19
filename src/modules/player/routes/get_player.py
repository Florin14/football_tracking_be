from typing import Optional

from fastapi import Depends
from sqlalchemy.orm import Session

from extensions import get_db
from modules.player.models.player_model import PlayerModel
from modules.player.models.player_schemas import PlayerFilter, PlayerListResponse, PlayerResponse
from .router import router


@router.get("/{id}", response_model=PlayerResponse)
async def get_player(id: int, db: Session = Depends(get_db)):
    """Get a specific player by ID"""
    player = db.query(PlayerModel).filter(PlayerModel.id == id).first()

    return PlayerResponse(
        id=player.id,
        name=player.name,
        email=player.email,
        position=player.position.value if player.position else None,
        rating=player.rating,
        teamId=player.teamId,
        teamName=player.team.name if player.team else None
    )
