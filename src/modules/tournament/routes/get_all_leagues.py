from fastapi import Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from extensions.sqlalchemy import get_db
from project_helpers.db import apply_search
from project_helpers.dependencies import JwtRequired
from modules.tournament.models.league_model import LeagueModel
from modules.tournament.models.tournament_schemas import LeaguesListResponse, LeagueListParams

from .router import router


@router.get("/leagues", response_model=LeaguesListResponse, dependencies=[Depends(JwtRequired())])
async def get_all_leagues(
        params: LeagueListParams = Depends(),
        db: Session = Depends(get_db),
):
    query = db.query(LeagueModel)

    query = apply_search(query, LeagueModel.name, params.search)
    if params.tournamentId:
        query = query.filter(LeagueModel.tournamentId == params.tournamentId)

    query = query.order_by(
        LeagueModel.relevanceOrder.is_(None),
        LeagueModel.relevanceOrder,
        func.lower(LeagueModel.name),
    )

    leagues = params.apply(query).all()

    return LeaguesListResponse(data=leagues)
