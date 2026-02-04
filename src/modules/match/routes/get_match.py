from fastapi import Depends
from sqlalchemy.orm import Session, joinedload

from extensions.sqlalchemy import get_db
from modules.match.models import (
    MatchModel, MatchResponse, GoalModel
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
            joinedload(MatchModel.goals).joinedload(GoalModel.player),
            joinedload(MatchModel.goals).joinedload(GoalModel.team),
        )
        .filter(MatchModel.id == match.id)
        .first()
    )

    goals = []
    for goal in match.goals or []:
        goals.append({
            "id": goal.id,
            "matchId": goal.matchId,
            "playerId": goal.playerId,
            "playerName": goal.player.name if goal.player else "Unknown",
            "teamId": goal.teamId,
            "teamName": goal.team.name if goal.team else "Unknown",
            "minute": goal.minute,
            "timestamp": goal.timestamp,
            "description": goal.description,
        })

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
        goals=goals
    )
