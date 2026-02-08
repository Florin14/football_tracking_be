from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from constants.platform_roles import PlatformRoles
from extensions.sqlalchemy import get_db
from modules.player.models.player_model import PlayerModel
from modules.team.models import TeamModel
from project_helpers.dependencies import GetInstanceFromPath, GetCurrentUser
from project_helpers.responses import ConfirmationResponse
from .router import router


@router.delete("/{id}/players/{player_id}", response_model=ConfirmationResponse)
async def remove_player_from_team(
        player_id: int,
        team: TeamModel = Depends(GetInstanceFromPath(TeamModel)),
        db: Session = Depends(get_db),
        current_user=Depends(GetCurrentUser(roles=[PlatformRoles.ADMIN])),
):
    """Remove a player from a team"""
    # Check if player exists and is in this team
    player = db.query(PlayerModel).filter(
        PlayerModel.id == player_id,
        PlayerModel.teamId == team.id
    ).first()
    if not player:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Player not found in this team"
        )

    # Remove player from team
    player.teamId = None
    db.commit()

    return ConfirmationResponse(
        success=True,
        message=f"Player {player.name} removed from team {team.name} successfully"
    )
