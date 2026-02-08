from fastapi import Depends
from sqlalchemy.orm import Session

from constants.platform_roles import PlatformRoles
from extensions.sqlalchemy import get_db
from modules.ranking.models import RankingModel, RankingUpdate, RankingResponse
from project_helpers.dependencies import GetInstanceFromPath, JwtRequired
from .router import router


@router.put("/{id}", response_model=RankingResponse)
async def update_team(
    team_data: RankingUpdate,
    team: RankingModel = Depends(GetInstanceFromPath(RankingModel)),
    db: Session = Depends(get_db),
    current_user=Depends(JwtRequired(roles=[PlatformRoles.ADMIN])),
):
    """Update a team"""
    if team_data.name:
        team.name = team_data.name

    if team_data.description is not None:
        team.description = team_data.description

    db.commit()
    db.refresh(team)

    return team
