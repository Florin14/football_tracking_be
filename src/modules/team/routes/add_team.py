from fastapi import Depends, status
from sqlalchemy.orm import Session

from extensions.sqlalchemy import get_db
from modules.team.models import TeamModel, TeamAdd, TeamResponse
from .router import router


@router.post("/", response_model=TeamResponse)
async def add_team(team_data: TeamAdd, db: Session = Depends(get_db)):
    team = TeamModel(
        name=team_data.name,
        description=team_data.description
    )
    db.add(team)
    db.commit()
    db.refresh(team)

    return TeamResponse(
        id=team.id,
        name=team.name,
        description=team.description,
        players=[]
    )
