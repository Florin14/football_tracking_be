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
async def add_match(data: MatchAdd, db: Session = Depends(get_db)):
    if data.team1Id == data.team2Id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A team cannot play against itself"
        )
    print(data)

    match = MatchModel(
        team1Id=data.team1Id,
        team2Id=data.team2Id,
        location=data.location,
        timestamp=data.timestamp,
    )

    db.add(match)
    print("before commit")
    db.commit()
    print("after commit")

    return MatchResponse(
        id=match.id,
        location=match.location,
        # team1Id=match.team1Id,
        # team2Id=match.team2Id,
        # location=match.location,
        timestamp=match.timestamp,
        # scoreTeam1=match.scoreTeam1,
        # scoreTeam2=match.scoreTeam2,
        state=match.state.value
    )
