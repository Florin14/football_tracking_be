from fastapi import Depends
from sqlalchemy.orm import Session

from constants.platform_roles import PlatformRoles
from extensions.sqlalchemy import get_db
from modules.tournament.models import TournamentModel
from project_helpers.dependencies import GetInstanceFromPath, JwtRequired
from project_helpers.responses import ConfirmationResponse
from .router import router


@router.delete("/{id}", response_model=ConfirmationResponse, dependencies=[Depends(JwtRequired(roles=[PlatformRoles.ADMIN]))])
async def delete_tournament(
    tournament: TournamentModel = Depends(GetInstanceFromPath(TournamentModel)),
    db: Session = Depends(get_db),
):
    db.delete(tournament)
    db.commit()

    return ConfirmationResponse(
        success=True,
        message=f"tournament {tournament.name} deleted successfully"
    )
