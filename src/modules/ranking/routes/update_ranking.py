from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from extensions.sqlalchemy import get_db
from modules.ranking.models import RankingModel, RankingUpdate, RankingResponse
from .router import router


@router.put("/{id}", response_model=RankingResponse)
async def update_team(id: int, team_data: RankingUpdate, db: Session = Depends(get_db)):
    """Update a team"""
    team = db.query(RankingModel).filter(RankingModel.id == id).first()
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )

    if team_data.name:
        team.name = team_data.name

    if team_data.description is not None:
        team.description = team_data.description

    db.commit()
    db.refresh(team)

    return RankingResponse(
        id=team.id,
        name=team.name,
        description=team.description,
        players=[]
    )
