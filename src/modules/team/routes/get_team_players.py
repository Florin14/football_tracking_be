from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from constants.platform_roles import PlatformRoles
from extensions.sqlalchemy import get_db
from modules.player.models.player_model import PlayerModel
from modules.team.models import TeamModel, AddPlayerToTeam
from project_helpers.dependencies import GetCurrentUser
from project_helpers.responses import ConfirmationResponse
from .router import router


@router.post("/{id}/players", response_model=ConfirmationResponse)
async def add_player_to_team(
        id: int,
        player_data: AddPlayerToTeam,
        db: Session = Depends(get_db),
        current_user=Depends(GetCurrentUser(roles=[PlatformRoles.ADMIN])),
):
    """Add a player to a team"""
    # Check if team exists
    team = db.query(TeamModel).filter(TeamModel.id == id).first()
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )

    # Check if player exists
    player = db.query(PlayerModel).filter(PlayerModel.id == player_data.playerId).first()
    if not player:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Player not found"
        )

    # Check if player is already in a team
    if player.teamId:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Player is already assigned to a team"
        )

    # Add player to team
    player.teamId = id
    db.commit()

    return ConfirmationResponse(
        success=True,
        message=f"Player {player.name} added to team {team.name} successfully"
    )
