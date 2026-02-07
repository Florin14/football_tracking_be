from typing import Optional

from fastapi import Depends, HTTPException, status
from datetime import datetime
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
    query = db.query(MatchModel).options(
        joinedload(MatchModel.team1),
        joinedload(MatchModel.team2),
        joinedload(MatchModel.league),
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

    query = query.order_by(
        MatchModel.timestamp.asc(),
    )

    matches = query.offset(skip).limit(limit).all()

    return MatchListResponse(data=matches)
