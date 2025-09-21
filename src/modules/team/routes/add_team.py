from fastapi import Depends, status
from sqlalchemy.orm import Session

from extensions.sqlalchemy import get_db
from modules.team.models import TeamModel, TeamAdd, TeamResponse
from .router import router


@router.post("/", response_model=TeamResponse)
async def add_team(data: TeamAdd, db: Session = Depends(get_db)):
    team = TeamModel(
        name=data.name,
        description=data.description,
        logo=data.logo,
    )
    db.add(team)
    db.commit()
    db.refresh(team)

    return TeamResponse(
        id=team.id,
        name=team.name,
        logo=team.logo,
        description=team.description,
        players=[]
    )
