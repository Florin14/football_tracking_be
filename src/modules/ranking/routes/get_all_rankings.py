from typing import Optional

from fastapi import Depends
from sqlalchemy.orm import Session

from extensions.sqlalchemy import get_db
from modules.ranking.models import RankingModel, RankingListResponse
from .router import router


@router.get("/", response_model=RankingListResponse)
async def get_all_rankings(
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        db: Session = Depends(get_db)
):
    """Get all teams with optional search"""
    query = db.query(RankingModel)

    if search:
        query = query.filter(RankingModel.name.ilike(f"%{search}%"))

    teams = query.offset(skip).limit(limit).all()

    team_items = []
    for team in teams:
        team_items.append({
            "id": team.id,
            "name": team.name,
            "description": team.description,
            "playerCount": len(team.players) if team.players else 0
        })

    return RankingListResponse(data=team_items)
