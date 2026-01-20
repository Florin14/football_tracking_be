from typing import Optional

from fastapi import Depends
from sqlalchemy.orm import Session

from extensions.sqlalchemy import get_db
from modules.tournament.models.tournament_model import TournamentModel
from modules.tournament.models.tournament_schemas import TournamentListResponse

from .router import router


@router.get("/", response_model=TournamentListResponse)
async def get_tournaments(
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        db: Session = Depends(get_db)
):
    query = db.query(TournamentModel)

    if search:
        query = query.filter(TournamentModel.name.ilike(f"%{search}%"))

    tournaments = query.offset(skip).limit(limit).all()

    tournament_items = []
    for tournament in tournaments:
        tournament_items.append({
            "id": tournament.id,
            "name": tournament.name,
            "description": tournament.description,
            "formatType": tournament.formatType,
            "groupCount": tournament.groupCount,
            "teamsPerGroup": tournament.teamsPerGroup,
            "hasKnockout": tournament.hasKnockout,
        })

    return TournamentListResponse(data=tournament_items)
