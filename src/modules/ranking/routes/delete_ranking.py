from fastapi import Depends
from sqlalchemy.orm import Session

from constants.platform_roles import PlatformRoles
from extensions.sqlalchemy import get_db
from modules.player.models.player_model import PlayerModel
from modules.ranking.models import RankingModel
from project_helpers.dependencies import GetInstanceFromPath, GetCurrentUser
from project_helpers.responses import ConfirmationResponse
from .router import router


@router.delete("/{id}", response_model=ConfirmationResponse)
async def delete_ranking(
    tournament: RankingModel = Depends(GetInstanceFromPath(RankingModel)),
    db: Session = Depends(get_db),
    current_user=Depends(GetCurrentUser(roles=[PlatformRoles.ADMIN])),
):
    """Delete a tournament"""
    # Remove all players from team first
    db.query(PlayerModel).filter(PlayerModel.teamId == tournament.id).update({"teamId": None})

    # Delete the tournament
    db.delete(tournament)
    db.commit()

    return ConfirmationResponse(
        success=True,
        message=f"tournament {tournament.name} deleted successfully"
    )
