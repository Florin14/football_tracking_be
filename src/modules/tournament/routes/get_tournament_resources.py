from fastapi import Depends
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from extensions.sqlalchemy import get_db
from modules.tournament.models.tournament_model import TournamentModel
from modules.tournament.models.tournament_schemas import TournamentResourcesResponse

from .router import router


@router.get("/resources", response_model=TournamentResourcesResponse)
async def get_tournament_resources(db: Session = Depends(get_db)):
    tournaments = (
        db.query(TournamentModel)
        .options(joinedload(TournamentModel.leagues))
        .order_by(func.lower(TournamentModel.name))
        .all()
    )

    tournament_items = []
    for tournament in tournaments:
        leagues_items = []
        sorted_leagues = sorted(
            tournament.leagues or [],
            key=lambda league: (
                league.relevanceOrder is None,
                league.relevanceOrder or 0,
                (league.name or "").lower(),
            )
        )
        for league in sorted_leagues:
            leagues_items.append({
                "id": league.id,
                "name": league.name,
                "relevanceOrder": league.relevanceOrder,
                "tournamentId": league.tournamentId,
            })

        tournament_items.append({
            "id": tournament.id,
            "name": tournament.name,
            "description": tournament.description,
            "formatType": tournament.formatType,
            "groupCount": tournament.groupCount,
            "teamsPerGroup": tournament.teamsPerGroup,
            "hasKnockout": tournament.hasKnockout,
            "leagues": leagues_items,
        })

    return TournamentResourcesResponse(tournaments=tournament_items)
