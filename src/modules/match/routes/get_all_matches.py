from typing import Optional

from fastapi import Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy import desc
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

    if state and match_state == MatchState.FINISHED:
        query = query.order_by(
            MatchModel.timestamp.is_(None),
            desc(MatchModel.timestamp),
        )
    else:
        query = query.order_by(
            MatchModel.timestamp.is_(None),
            MatchModel.timestamp,
        )

    matches = query.offset(skip).limit(limit).all()

    match_items = []
    for match in matches:
        match_items.append({
            "id": match.id,
            "team1Name": match.team1.name,
            "team2Name": match.team2.name,
            "team1Logo": match.team1.logo,
            "team2Logo": match.team2.logo,
            "leagueId": match.league.id if match.league else None,
            "leagueName": match.league.name if match.league else None,
            "leagueLogo": match.league.logo if match.league else None,
            "location": match.location,
            "timestamp": match.timestamp,
            "scoreTeam1": match.scoreTeam1,
            "scoreTeam2": match.scoreTeam2,
            "state": match.state.value
        })

    return MatchListResponse(data=match_items)
