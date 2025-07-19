from fastapi import Depends, HTTPException, status
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from constants.match_state import MatchState
from extensions.sqlalchemy import get_db
from modules.match.models import (
    MatchModel, GoalModel
)
from project_helpers.responses import ConfirmationResponse
from .router import router


@router.delete("/{match_id}", response_model=ConfirmationResponse)
async def delete_match(match_id: int, db: Session = Depends(get_db)):
    """Delete a match (only if not finished)"""
    match = db.query(MatchModel).filter(MatchModel.id == match_id).first()
    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found"
        )

    if match.state == MatchState.FINISHED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete a finished match"
        )

    # Delete all goals associated with this match
    db.query(GoalModel).filter(GoalModel.matchId == match_id).delete()

    # Delete the match
    db.delete(match)
    db.commit()

    return ConfirmationResponse(
        success=True,
        message="Match deleted successfully"
    )
