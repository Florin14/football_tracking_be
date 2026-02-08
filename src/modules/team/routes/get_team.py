from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from extensions.sqlalchemy import get_db
from modules.team.models import TeamModel, TeamResponse
from project_helpers.dependencies import JwtRequired
from .router import router


@router.get("/{id}", response_model=TeamResponse)
async def get_team(
    id: int,
    db: Session = Depends(get_db),
    current_user=Depends(JwtRequired()),
):
    """Get a specific team by ID"""
    team = db.query(TeamModel).options(joinedload(TeamModel.players)).filter(TeamModel.id == id).first()
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )

    return team
