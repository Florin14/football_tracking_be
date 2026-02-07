from fastapi import Depends
from sqlalchemy.orm import Session, joinedload

from extensions.sqlalchemy import get_db
from project_helpers.db import apply_search
from modules.ranking.models.ranking_model import RankingModel
from modules.team.models import TeamModel, TeamListResponse, TeamListParams
from modules.tournament.models.league_model import LeagueModel
from modules.tournament.models.league_team_model import LeagueTeamModel
from .router import router


@router.get("/", response_model=TeamListResponse)
async def get_teams(
        params: TeamListParams = Depends(),
        db: Session = Depends(get_db)
):
    include_ranking = params.leagueId is not None
    if include_ranking:
        query = (
            db.query(TeamModel, RankingModel)
            .outerjoin(
                RankingModel,
                (RankingModel.teamId == TeamModel.id)
                & (RankingModel.leagueId == params.leagueId),
            )
            .options(joinedload(TeamModel.players))
        )
    else:
        query = db.query(TeamModel).options(joinedload(TeamModel.players))

    query = apply_search(query, TeamModel.name, params.search)
    if params.leagueId or params.excludeLeagueId or params.tournamentId or params.excludeTournamentId:
        query = query.join(LeagueTeamModel, LeagueTeamModel.teamId == TeamModel.id)
        query = query.join(LeagueModel, LeagueModel.id == LeagueTeamModel.leagueId)
        if params.leagueId:
            query = query.filter(LeagueTeamModel.leagueId == params.leagueId)
        if params.excludeLeagueId:
            query = query.filter(LeagueTeamModel.leagueId != params.excludeLeagueId)
        if params.tournamentId:
            query = query.filter(LeagueModel.tournamentId == params.tournamentId)
        if params.excludeTournamentId:
            query = query.filter(LeagueModel.tournamentId != params.excludeTournamentId)

    teams = params.apply(query.distinct(TeamModel.id)).all()

    team_items = []
    for row in teams:
        if include_ranking:
            team, ranking = row
            team._ranking = ranking
        else:
            team = row
        team_items.append(team)

    return TeamListResponse(data=team_items)
