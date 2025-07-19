from fastapi import Depends, HTTPException, status
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from constants.match_state import MatchState
from extensions.sqlalchemy import get_db
from modules.match.models import (
    MatchModel, MatchAdd, MatchResponse
)
from modules.team.models import TeamModel
from .router import router


@router.post("/", response_model=MatchResponse, status_code=status.HTTP_201_CREATED)
async def add_match(match_data: MatchAdd, db: Session = Depends(get_db)):
    """Schedule a new match"""
    # Validate teams exist
    team1 = db.query(TeamModel).filter(TeamModel.id == match_data.team1Id).first()
    team2 = db.query(TeamModel).filter(TeamModel.id == match_data.team2Id).first()

    if not team1:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team 1 not found"
        )
    if not team2:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team 2 not found"
        )

    if match_data.team1Id == match_data.team2Id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A team cannot play against itself"
        )

    match = MatchModel(
        team1Id=match_data.team1Id,
        team2Id=match_data.team2Id,
        location=match_data.location,
        timestamp=match_data.timestamp,
        state=MatchState.SCHEDULED
    )

    db.add(match)
    db.commit()
    db.refresh(match)

    return MatchResponse(
        id=match.id,
        team1Id=match.team1Id,
        team2Id=match.team2Id,
        team1Name=team1.name,
        team2Name=team2.name,
        location=match.location,
        timestamp=match.timestamp,
        scoreTeam1=match.scoreTeam1,
        scoreTeam2=match.scoreTeam2,
        state=match.state.value,
        goals=[]
    )
