from fastapi import Depends
from sqlalchemy.orm import Session, joinedload

from extensions.sqlalchemy import get_db
from modules.ranking.models import RankingModel, RankingListResponse
from modules.team.models.team_model import (TeamModel)
from .router import router


@router.get("/", response_model=RankingListResponse)
async def get_all_rankings(
        db: Session = Depends(get_db)
):
    gd = (RankingModel.goalsScored - RankingModel.goalsConceded)

    rankings_query = (
        db.query(RankingModel)
        .join(RankingModel.team)
        .options(joinedload(RankingModel.team))
        .order_by(
            RankingModel.points.desc(),
            gd.desc(),
            RankingModel.goalsScored.desc(),
            TeamModel.name.asc()
        )
    )

    return RankingListResponse(data=rankings_query.all())
