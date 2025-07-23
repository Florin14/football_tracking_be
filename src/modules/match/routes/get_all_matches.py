from typing import Optional

from fastapi import Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from constants.match_state import MatchState
from extensions.sqlalchemy import get_db
from modules.match.models import (
    MatchModel, MatchListResponse
)
from .router import router


@router.get("/", response_model=MatchListResponse)
async def get_matches(
        skip: int = 0,
        limit: int = 100,
        team_id: Optional[int] = None,
        state: Optional[str] = None,
        db: Session = Depends(get_db)
):
    """Get all matches with optional filters"""
    query = db.query(MatchModel).options(
        joinedload(MatchModel.team1),
        joinedload(MatchModel.team2)
    )

    if team_id:
        query = query.filter(
            or_(MatchModel.team1Id == team_id, MatchModel.team2Id == team_id)
        )

    if state:
        try:
            match_state = MatchState(state.upper())
            query = query.filter(MatchModel.state == match_state)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid match state"
            )

    matches = query.offset(skip).limit(limit).all()

    match_items = []
    for match in matches:
        match_items.append({
            "id": match.id,
            "team1Name": match.team1.name,
            "team2Name": match.team2.name,
            "location": match.location,
            "timestamp": match.timestamp,
            "scoreTeam1": match.scoreTeam1,
            "scoreTeam2": match.scoreTeam2,
            "state": match.state.value
        })

    return MatchListResponse(data=match_items)
