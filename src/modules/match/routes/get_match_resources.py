from fastapi import Depends
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from extensions.sqlalchemy import get_db
from project_helpers.dependencies import JwtRequired
from modules.match.models import (
    MatchResourcesResponse
)
from modules.match.models.match_model import MatchModel
from modules.team.models.team_model import TeamModel
from modules.tournament.models.league_model import LeagueModel
from .router import router


@router.get("-resources", response_model=MatchResourcesResponse, dependencies=[Depends(JwtRequired())])
def get_matches_resources(
    db: Session = Depends(get_db),
):
    leagues = (
        db.query(LeagueModel)
        .options(selectinload(LeagueModel.teams))
        .order_by(func.lower(LeagueModel.name))
        .all()
    )

    # Get max round per league
    max_rounds = dict(
        db.query(MatchModel.leagueId, func.max(MatchModel.round))
        .filter(MatchModel.leagueId.isnot(None), MatchModel.round.isnot(None))
        .group_by(MatchModel.leagueId)
        .all()
    )

    league_out = []
    for league in leagues:
        league.maxRound = max_rounds.get(league.id)
        league_out.append(league)

    all_teams = (
        db.query(TeamModel)
        .order_by(func.lower(TeamModel.name))
        .all()
    )

    return MatchResourcesResponse(leagues=league_out, allTeams=all_teams)
