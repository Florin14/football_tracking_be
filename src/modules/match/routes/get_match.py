from fastapi import Depends
from sqlalchemy.orm import Session, joinedload

from extensions.sqlalchemy import get_db
from modules.match.models import (
    MatchModel, MatchResponse, GoalModel
)
from project_helpers.dependencies import GetInstanceFromPath, JwtRequired
from .router import router


@router.get("/{id}", response_model=MatchResponse, dependencies=[Depends(JwtRequired())])
async def get_match(
    match: MatchModel = Depends(GetInstanceFromPath(MatchModel)),
    db: Session = Depends(get_db),
):
    match = (
        db.query(MatchModel)
        .options(
            joinedload(MatchModel.team1),
            joinedload(MatchModel.team2),
            joinedload(MatchModel.league),
            joinedload(MatchModel.goals).joinedload(GoalModel.player),
            joinedload(MatchModel.goals).joinedload(GoalModel.team),
        )
        .filter(MatchModel.id == match.id)
        .first()
    )

    return match
