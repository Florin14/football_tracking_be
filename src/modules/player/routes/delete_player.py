from fastapi import Depends
from sqlalchemy.orm import Session

from constants.platform_roles import PlatformRoles
from extensions import get_db
from modules.player.models.player_model import PlayerModel
from project_helpers.dependencies import GetInstanceFromPath, JwtRequired
from project_helpers.responses import ConfirmationResponse
from .router import router


@router.delete("/{id:int}", response_model=ConfirmationResponse, dependencies=[Depends(JwtRequired(roles=[PlatformRoles.ADMIN]))])
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
        message=f"Player {player.name} deleted successfully"
    )
