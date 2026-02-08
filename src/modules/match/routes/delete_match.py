from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from constants.platform_roles import PlatformRoles
from constants.match_state import MatchState
from extensions.sqlalchemy import get_db
from modules.match.models import (
    MatchModel, GoalModel
)
from project_helpers.dependencies import GetInstanceFromPath, JwtRequired
from project_helpers.responses import ConfirmationResponse
from .router import router


def _get_match(
    match_id: int,
    db: Session = Depends(get_db),
):
    return GetInstanceFromPath(MatchModel)(match_id, db)


@router.delete("/{match_id}", response_model=ConfirmationResponse, dependencies=[Depends(JwtRequired(roles=[PlatformRoles.ADMIN]))])
async def delete_match(
    match: MatchModel = Depends(_get_match),
    db: Session = Depends(get_db),
):
    """Delete a match (only if not finished)"""
    if match.state == MatchState.FINISHED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete a finished match"
        )

    # Delete all goals associated with this match
    db.query(GoalModel).filter(GoalModel.matchId == match.id).delete()

    # Delete the match
    db.delete(match)
    db.commit()

    return ConfirmationResponse(
        success=True,
        message="Match deleted successfully"
    )
