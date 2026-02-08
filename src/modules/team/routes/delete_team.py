from fastapi import Depends
from sqlalchemy.orm import Session

from constants.platform_roles import PlatformRoles
from extensions.sqlalchemy import get_db
from modules.player.models.player_model import PlayerModel
from modules.team.models import TeamModel
from project_helpers.dependencies import GetInstanceFromPath, JwtRequired
from project_helpers.responses import ConfirmationResponse
from .router import router


@router.delete("/{id}", response_model=ConfirmationResponse, dependencies=[Depends(JwtRequired(roles=[PlatformRoles.ADMIN]))])
async def delete_team(
    team: TeamModel = Depends(GetInstanceFromPath(TeamModel)),
    db: Session = Depends(get_db),
):
    """Delete a team"""
    # Remove all players from team first
    db.query(PlayerModel).filter(PlayerModel.teamId == team.id).update({"teamId": None})

    # Delete the team
    db.delete(team)
    db.commit()

    return ConfirmationResponse(
        success=True,
        message=f"Team {team.name} deleted successfully"
    )
