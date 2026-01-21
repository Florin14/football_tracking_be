from fastapi import Depends
from sqlalchemy.orm import Session

from extensions.sqlalchemy import get_db
from modules.ranking.models import RankingModel, RankingUpdate, RankingResponse
from project_helpers.dependencies import GetInstanceFromPath
from .router import router


@router.put("/{id}", response_model=RankingResponse)
async def update_team(
    team_data: RankingUpdate,
    team: RankingModel = Depends(GetInstanceFromPath(RankingModel)),
    db: Session = Depends(get_db),
):
    """Update a team"""
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
