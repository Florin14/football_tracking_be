from fastapi import Depends
from sqlalchemy.orm import Session, joinedload

from extensions.sqlalchemy import get_db
from modules.match.models import (
    MatchModel, MatchResponse
)
from project_helpers.dependencies import GetInstanceFromPath
from .router import router


@router.get("/{id}", response_model=MatchResponse)
async def get_match(match: MatchModel = Depends(GetInstanceFromPath(MatchModel)), db: Session = Depends(get_db)):
    match = (
        db.query(MatchModel)
        .options(
            joinedload(MatchModel.team1),
            joinedload(MatchModel.team2),
            joinedload(MatchModel.league),
        )
        .filter(MatchModel.id == match.id)
        .first()
    )

    return MatchResponse(
        id=match.id,
        team1=match.team1,
        team2=match.team2,
        league=match.league,
        location=match.location,
        timestamp=match.timestamp,
        scoreTeam1=match.scoreTeam1,
        scoreTeam2=match.scoreTeam2,
        state=match.state.value,
        goals=[]
    )
