from datetime import datetime
from fastapi import Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from constants.match_state import MatchState
from extensions.sqlalchemy import get_db
from project_helpers.dependencies import GetCurrentUser
from modules.match.models import (
    MatchModel, MatchListResponse, MatchListParams
)
from .router import router


@router.get("/", response_model=MatchListResponse)
async def get_matches(
        params: MatchListParams = Depends(),
        db: Session = Depends(get_db),
        current_user=Depends(GetCurrentUser()),
):
    query = db.query(MatchModel).options(
        joinedload(MatchModel.team1),
        joinedload(MatchModel.team2),
        joinedload(MatchModel.league),
    )

    if params.teamId:
        query = query.filter(
            or_(MatchModel.team1Id == params.teamId, MatchModel.team2Id == params.teamId)
        )

    if params.state:
        try:
            match_state = MatchState(params.state.upper())
            query = query.filter(MatchModel.state == match_state)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid match state"
            )

    query = query.order_by(
        MatchModel.timestamp.is_(None),
        MatchModel.timestamp,
        MatchModel.id,
    )

    matches = params.apply(query).all()
    matches = sorted(
        matches,
        key=lambda match: (
            match.timestamp is None,
            match.timestamp or datetime.max,
            match.id or 0,
        ),
    )

    return MatchListResponse(data=matches)
