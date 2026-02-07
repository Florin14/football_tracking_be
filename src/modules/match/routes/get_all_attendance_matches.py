from fastapi import Depends
from datetime import datetime
from sqlalchemy import or_
from sqlalchemy import desc
from sqlalchemy.orm import Session, joinedload

from extensions.sqlalchemy import get_db
from modules.match.models import (
    MatchModel, MatchListResponse
)
from modules.team.models.team_model import TeamModel
from .router import router


@router.get("-attendance", response_model=MatchListResponse)
async def get_matches(
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(get_db)
):
    query = db.query(MatchModel).options(
        joinedload(MatchModel.team1),
        joinedload(MatchModel.team2),
        joinedload(MatchModel.league),
    )

    default_team = db.query(TeamModel).filter(TeamModel.isDefault.is_(True)).first()
    if default_team:
        query = query.filter(
            or_(MatchModel.team1Id == default_team.id, MatchModel.team2Id == default_team.id)
        )
    
    query = query.order_by(
        MatchModel.timestamp.is_(None),
        MatchModel.timestamp,
        MatchModel.id,
    )

    matches = query.offset(skip).limit(limit).all()
    matches = sorted(
        matches,
        key=lambda match: (
            match.timestamp is None,
            match.timestamp or datetime.max,
        ),
    )

    return MatchListResponse(data=matches)
