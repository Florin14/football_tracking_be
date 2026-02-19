from fastapi import Depends
from sqlalchemy.orm import Session

from constants.platform_roles import PlatformRoles
from extensions.sqlalchemy import get_db
from modules.tournament.models import LeagueModel, LeagueUpdate, LeagueDetail
from project_helpers.dependencies import GetInstanceFromPath, JwtRequired
from .router import router


@router.put("/leagues/{id}", response_model=LeagueDetail, dependencies=[Depends(JwtRequired(roles=[PlatformRoles.ADMIN]))])
async def update_league(
    data: LeagueUpdate,
    league: LeagueModel = Depends(GetInstanceFromPath(LeagueModel)),
    db: Session = Depends(get_db),
):
    if data.logo is not None:
        league.logo = data.logo

    db.commit()
    db.refresh(league)

    return league
