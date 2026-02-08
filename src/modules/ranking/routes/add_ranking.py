from fastapi import Depends, status
from sqlalchemy.orm import Session

from constants.platform_roles import PlatformRoles
from extensions.sqlalchemy import get_db
from modules.ranking.models import RankingModel, RankingAdd, RankingResponse
from project_helpers.dependencies import GetCurrentUser
from .router import router


@router.post("/", response_model=RankingResponse)
async def add_ranking(
    data: RankingAdd,
    db: Session = Depends(get_db),
    current_user=Depends(GetCurrentUser(roles=[PlatformRoles.ADMIN])),
):
    ranking = RankingModel(description=data.description)
    if data.name:
        ranking.name = data.name
    db.add(ranking)
    db.commit()
    db.refresh(ranking)

    return ranking
