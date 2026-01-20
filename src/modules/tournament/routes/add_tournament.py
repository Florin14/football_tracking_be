from fastapi import Depends, status
from sqlalchemy.orm import Session

from extensions.sqlalchemy import get_db
from modules.tournament.models import TournamentModel, TournamentAdd, TournamentResponse
from modules.tournament.models.league_model import LeagueModel
from .router import router


@router.post("/", response_model=TournamentResponse)
async def add_tournament(data: TournamentAdd, db: Session = Depends(get_db)):
    tournament = TournamentModel(
        name=data.name,
        description=data.description,
        formatType=data.formatType,
        groupCount=data.groupCount,
        teamsPerGroup=data.teamsPerGroup,
        hasKnockout=data.hasKnockout,
    )
    db.add(tournament)
    db.flush()

    if data.leagues:
        for index, league_data in enumerate(data.leagues, start=1):
            relevance_order = league_data.relevanceOrder
            if relevance_order is None:
                relevance_order = index
            db.add(LeagueModel(
                name=league_data.name,
                description=league_data.description,
                startDate=league_data.startDate,
                endDate=league_data.endDate,
                season=league_data.season,
                relevanceOrder=relevance_order,
                tournamentId=tournament.id,
            ))

    db.commit()
    db.refresh(tournament)

    return TournamentResponse(
        id=tournament.id,
        name=tournament.name,
        description=tournament.description,
        formatType=tournament.formatType,
        groupCount=tournament.groupCount,
        teamsPerGroup=tournament.teamsPerGroup,
        hasKnockout=tournament.hasKnockout,
    )
