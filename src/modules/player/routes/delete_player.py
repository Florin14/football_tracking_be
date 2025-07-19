from typing import Optional

from fastapi import Depends
from sqlalchemy.orm import Session

from extensions import get_db
from modules.player.models.player_model import PlayerModel
from modules.player.models.player_schemas import PlayerFilter, PlayerListResponse, PlayerResponse
from project_helpers.responses import ConfirmationResponse
from .router import router


@router.delete("/{id}", response_model=ConfirmationResponse)
async def delete_player(id: int, db: Session = Depends(get_db)):
    """Delete a player"""
    player = db.query(PlayerModel).filter(PlayerModel.id == id).first()

    # Remove player from any team
    if player.teamId:
        player.teamId = None
        db.commit()

    # Delete the player
    db.delete(player)
    db.commit()

    return ConfirmationResponse(
        success=True,
        message=f"Player {player.name} deleted successfully"
    )
