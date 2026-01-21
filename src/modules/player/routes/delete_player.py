from fastapi import Depends
from sqlalchemy.orm import Session

from extensions import get_db
from modules.player.models.player_model import PlayerModel
from project_helpers.dependencies import GetInstanceFromPath
from project_helpers.responses import ConfirmationResponse
from .router import router


@router.delete("/{id}", response_model=ConfirmationResponse)
async def delete_player(
    player: PlayerModel = Depends(GetInstanceFromPath(PlayerModel)),
    db: Session = Depends(get_db),
):
    """Delete a player"""
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
