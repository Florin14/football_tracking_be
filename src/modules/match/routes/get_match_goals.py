from typing import Optional

from fastapi import Depends
from sqlalchemy.orm import Session

from extensions.sqlalchemy import get_db
from modules.match.models import GoalModel, GoalListResponse
from project_helpers.dependencies import JwtRequired
from .router import router


@router.get("/goals/", response_model=GoalListResponse, dependencies=[Depends(JwtRequired())])
async def get_goals(
        skip: int = 0,
        limit: int = 100,
        match_id: Optional[int] = None,
        player_id: Optional[int] = None,
        team_id: Optional[int] = None,
        db: Session = Depends(get_db)
):
    query = db.query(GoalModel)

    if match_id:
        query = query.filter(GoalModel.matchId == match_id)

    if player_id:
        query = query.filter(GoalModel.playerId == player_id)

    if team_id:
        query = query.filter(GoalModel.teamId == team_id)

    goals = query.offset(skip).limit(limit).all()

    return GoalListResponse(data=goals)

