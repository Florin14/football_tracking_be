from fastapi import Depends
from sqlalchemy.orm import Session

from extensions import get_db
from modules.player.models.player_model import PlayerModel
from modules.player.models.player_schemas import PlayerResponse
from project_helpers.dependencies import GetCurrentUser
from .router import router


@router.get("/{id}", response_model=PlayerResponse)
async def get_player(
    id: int,
    db: Session = Depends(get_db),
    current_user=Depends(GetCurrentUser()),
):
    """Get a specific player by ID"""
    player = db.query(PlayerModel).filter(PlayerModel.id == id).first()

    return player
