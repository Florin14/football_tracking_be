from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from constants.match_state import MatchState
from extensions.sqlalchemy import get_db
from modules.match.models import (
    MatchModel
)
from modules.ranking.services import recalculate_match_rankings
from modules.tournament.services.knockout_service import auto_advance_knockout
from project_helpers.dependencies import GetInstanceFromPath
from project_helpers.responses import ConfirmationResponse
from .router import router


def _get_match(
    match_id: int,
    db: Session = Depends(get_db),
):
    return GetInstanceFromPath(MatchModel)(match_id, db)


@router.post("/{match_id}/finish", response_model=ConfirmationResponse)
async def finish_match(
    match: MatchModel = Depends(_get_match),
    db: Session = Depends(get_db),
):
    """Mark a match as finished"""
    if match.state == MatchState.FINISHED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Match is already finished"
        )

    match.state = MatchState.FINISHED

    # Ensure scores are set (default to 0 if not set)
    if match.scoreTeam1 is None:
        match.scoreTeam1 = 0
    if match.scoreTeam2 is None:
        match.scoreTeam2 = 0

    recalculate_match_rankings(db, match)
    auto_advance_knockout(db, match)
    db.commit()

    return ConfirmationResponse(
        success=True,
        message="Match marked as finished"
    )
