from typing import Optional

from fastapi import Depends
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from extensions.sqlalchemy import get_db
from modules.tournament.models.league_model import LeagueModel
from modules.tournament.models.tournament_schemas import LeaguesListResponse

from .router import router


@router.get("/leagues", response_model=LeaguesListResponse)
async def get_all_leagues(
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        tournament_id: Optional[int] = None,
        db: Session = Depends(get_db)
):
    query = db.query(LeagueModel)

    if search:
        query = query.filter(LeagueModel.name.ilike(f"%{search}%"))
    if tournament_id:
        query = query.filter(LeagueModel.tournamentId == tournament_id)

    query = query.order_by(
        LeagueModel.relevanceOrder.is_(None),
        LeagueModel.relevanceOrder,
        func.lower(LeagueModel.name),
    )

    leagues = query.offset(skip).limit(limit).all()

    leagues_items = []
    for league in leagues:
        leagues_items.append({
            "id": league.id,
            "name": league.name,
            "relevanceOrder": league.relevanceOrder,
            "tournamentId": league.tournamentId,
        })

    return LeaguesListResponse(data=leagues_items)
