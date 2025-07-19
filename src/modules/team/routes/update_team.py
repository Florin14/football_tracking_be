from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from extensions.sqlalchemy import get_db
from modules.team.models import TeamModel, TeamUpdate, TeamResponse
from .router import router


@router.put("/{id}", response_model=TeamResponse)
async def update_team(id: int, team_data: TeamUpdate, db: Session = Depends(get_db)):
    """Update a team"""
    team = db.query(TeamModel).filter(TeamModel.id == id).first()
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

    return TeamResponse(
        id=team.id,
        name=team.name,
        description=team.description,
        players=[]
    )
