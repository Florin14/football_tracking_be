from fastapi import Depends, status
from sqlalchemy.orm import Session

from constants.platform_roles import PlatformRoles
from extensions.sqlalchemy import get_db
from modules.tournament.models import TournamentModel, TournamentAdd, TournamentResponse
from modules.tournament.models.league_model import LeagueModel
from project_helpers.dependencies import JwtRequired
from .router import router


@router.post("/", response_model=TournamentResponse, dependencies=[Depends(JwtRequired(roles=[PlatformRoles.ADMIN]))])
async def add_tournament(
    data: TournamentAdd,
    db: Session = Depends(get_db),
):
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
                logo=league_data.logo,
                startDate=league_data.startDate,
                endDate=league_data.endDate,
                season=league_data.season,
                relevanceOrder=relevance_order,
                tournamentId=tournament.id,
            ))

    db.commit()
    db.refresh(tournament)

    return tournament
