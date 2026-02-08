from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from extensions.sqlalchemy import get_db
from project_helpers.dependencies import JwtRequired
from modules.ranking.models import RankingModel, RankingResponse
from .router import router


@router.get("/{id}", response_model=RankingResponse, dependencies=[Depends(JwtRequired())])
async def get_ranking(
    id: int,
    db: Session = Depends(get_db),
):
    """Get a specific team by ID"""
    ranking = (
        db.query(RankingModel)
        .options(joinedload(RankingModel.team))
        .filter(RankingModel.id == id)
        .first()
    )
    if not ranking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )

    return ranking
