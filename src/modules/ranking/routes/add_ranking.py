from fastapi import Depends, status
from sqlalchemy.orm import Session

from extensions.sqlalchemy import get_db
from modules.ranking.models import RankingModel, RankingAdd, RankingResponse
from .router import router


@router.post("/", response_model=RankingResponse)
async def add_ranking(data: RankingAdd, db: Session = Depends(get_db)):
    ranking = RankingModel(
        name=data.name,
        description=data.description
    )
    db.add(ranking)
    db.commit()
    db.refresh(ranking)

    return RankingResponse(
        id=ranking.id,
        name=ranking.name,
        description=ranking.description,
    )
