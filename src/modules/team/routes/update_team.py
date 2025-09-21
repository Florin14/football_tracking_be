from fastapi import Depends
from sqlalchemy.orm import Session

from extensions.sqlalchemy import get_db
from modules.team.models import TeamModel, TeamUpdate, TeamResponse
from project_helpers.dependencies import GetInstanceFromPath
from .router import router


@router.put("/{id}", response_model=TeamResponse)
async def update_team(data: TeamUpdate, team: TeamModel = Depends(GetInstanceFromPath(TeamModel)), db: Session = Depends(get_db)):
    if data.name:
        team.name = data.name

    if data.description is not None:
        team.description = data.description

    if data.logo is not None:
        team.logo = data.logo

    db.commit()
    db.refresh(team)

    return TeamResponse(
        id=team.id,
        name=team.name,
        description=team.description,
        logo=team.logo
    )
