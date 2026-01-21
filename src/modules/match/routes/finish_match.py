from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from constants.match_state import MatchState
from extensions.sqlalchemy import get_db
from modules.match.models import (
    MatchModel
)
from modules.ranking.services import recalculate_match_rankings
from project_helpers.responses import ConfirmationResponse
from .router import router


@router.post("/{match_id}/finish", response_model=ConfirmationResponse)
async def finish_match(match_id: int, db: Session = Depends(get_db)):
    """Mark a match as finished"""
    match = db.query(MatchModel).filter(MatchModel.id == match_id).first()
    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found"
        )

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
    db.commit()

    return ConfirmationResponse(
        success=True,
        message="Match marked as finished"
    )
