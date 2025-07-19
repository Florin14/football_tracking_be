from typing import Optional

from fastapi import Depends
from sqlalchemy.orm import Session

from extensions.sqlalchemy import get_db
from modules.match.models import (
    GoalModel, GoalListResponse, GoalResponse
)
from modules.player.models import PlayerModel
from modules.team.models import TeamModel
from .router import router


@router.get("/goals/", response_model=GoalListResponse)
async def get_goals(
        skip: int = 0,
        limit: int = 100,
        match_id: Optional[int] = None,
        player_id: Optional[int] = None,
        team_id: Optional[int] = None,
        db: Session = Depends(get_db)
):
    """Get goals with optional filters"""
    query = db.query(GoalModel)

    if match_id:
        query = query.filter(GoalModel.matchId == match_id)

    if player_id:
        query = query.filter(GoalModel.playerId == player_id)

    if team_id:
        query = query.filter(GoalModel.teamId == team_id)

    goals = query.offset(skip).limit(limit).all()

    goal_items = []
    for goal in goals:
        player = db.query(PlayerModel).filter(PlayerModel.id == goal.playerId).first()
        team = db.query(TeamModel).filter(TeamModel.id == goal.teamId).first()

        goal_items.append(GoalResponse(
            id=goal.id,
            matchId=goal.matchId,
            playerId=goal.playerId,
            playerName=player.name if player else "Unknown",
            teamId=goal.teamId,
            teamName=team.name if team else "Unknown",
            minute=goal.minute,
            timestamp=goal.timestamp,
            description=goal.description
        ))

    return GoalListResponse(data=goal_items)
