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

    return TournamentListResponse(data=tournaments)
