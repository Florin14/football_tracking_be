from fastapi import Depends, HTTPException, status
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from constants.match_state import MatchState
from extensions.sqlalchemy import get_db
from modules.match.models import (
    MatchModel, MatchUpdate, MatchResponse
)
from .router import router


@router.put("/{match_id}", response_model=MatchResponse)
async def update_match(match_id: int, match_data: MatchUpdate, db: Session = Depends(get_db)):
    """Update match details (location, timestamp, scores, state)"""
    match = db.query(MatchModel).options(
        joinedload(MatchModel.team1),
        joinedload(MatchModel.team2)
    ).filter(MatchModel.id == match_id).first()

    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found"
        )

    if match_data.location:
        match.location = match_data.location

    if match_data.timestamp:
        match.timestamp = match_data.timestamp

    if match_data.scoreTeam1 is not None:
        match.scoreTeam1 = match_data.scoreTeam1

    if match_data.scoreTeam2 is not None:
        match.scoreTeam2 = match_data.scoreTeam2

    if match_data.state:
        try:
            match.state = MatchState(match_data.state.upper())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid match state"
            )

    db.commit()
    db.refresh(match)

    return MatchResponse(
        id=match.id,
        team1Id=match.team1Id,
        team2Id=match.team2Id,
        team1Name=match.team1.name,
        team2Name=match.team2.name,
        location=match.location,
        timestamp=match.timestamp,
        scoreTeam1=match.scoreTeam1,
        scoreTeam2=match.scoreTeam2,
        state=match.state.value,
        goals=[]
    )
