from fastapi import Depends
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from extensions.sqlalchemy import get_db
from project_helpers.dependencies import JwtRequired
from modules.tournament.models.tournament_model import TournamentModel
from modules.tournament.models.tournament_schemas import TournamentResourcesResponse

from .router import router


@router.get("/resources", response_model=TournamentResourcesResponse)
async def get_tournament_resources(
    db: Session = Depends(get_db),
    current_user=Depends(JwtRequired()),
):
    tournaments = (
        db.query(TournamentModel)
        .options(joinedload(TournamentModel.leagues))
        .order_by(func.lower(TournamentModel.name))
        .all()
    )

    for tournament in tournaments:
        sorted_leagues = sorted(
            tournament.leagues or [],
            key=lambda league: (
                league.relevanceOrder is None,
                league.relevanceOrder or 0,
                (league.name or "").lower(),
            )
        )
        tournament.leagues = sorted_leagues

    return TournamentResourcesResponse(tournaments=tournaments)
