from fastapi import Depends, HTTPException, status
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from extensions.sqlalchemy import get_db
from modules.match.models import (
    MatchModel, MatchResponse
)
from modules.player.models import PlayerModel
from modules.team.models import TeamModel
from .router import router


@router.get("/{match_id}", response_model=MatchResponse)
async def get_match(match_id: int, db: Session = Depends(get_db)):
    """Get a specific match by ID"""
    match = db.query(MatchModel).options(
        joinedload(MatchModel.team1),
        joinedload(MatchModel.team2),
        joinedload(MatchModel.goals)
    ).filter(MatchModel.id == match_id).first()

    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found"
        )

    goals = []
    if match.goals:
        for goal in match.goals:
            player = db.query(PlayerModel).filter(PlayerModel.id == goal.playerId).first()
            team = db.query(TeamModel).filter(TeamModel.id == goal.teamId).first()
            goals.append({
                "id": goal.id,
                "playerId": goal.playerId,
                "playerName": player.name if player else "Unknown",
                "teamId": goal.teamId,
                "teamName": team.name if team else "Unknown",
                "minute": goal.minute,
                "timestamp": goal.timestamp,
                "description": goal.description
            })

    return MatchResponse(
        id=match.id,
        team1Id=match.team1Id,
        team2Id=match.team2Id,
        team1Name=match.team1.name,
        team2Name=match.team2.name,
        location=match.location,
        timestamp=match.timestamp,
        scoreTeam1=match.scoreTeam1,
        scoreTeam2=match.scoreTeam2,
        state=match.state.value,
        goals=goals
    )
