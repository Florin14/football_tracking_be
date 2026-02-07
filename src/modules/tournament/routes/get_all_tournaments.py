from fastapi import Depends
from sqlalchemy.orm import Session

from extensions.sqlalchemy import get_db
from project_helpers.db import apply_search
from modules.tournament.models.tournament_model import TournamentModel
from modules.tournament.models.tournament_schemas import TournamentListResponse, TournamentListParams

from .router import router


@router.get("/", response_model=TournamentListResponse)
async def get_tournaments(
        params: TournamentListParams = Depends(),
        db: Session = Depends(get_db)
):
    query = db.query(TournamentModel)

    query = apply_search(query, TournamentModel.name, params.search)

    tournaments = params.apply(query).all()

    return TournamentListResponse(data=tournaments)
