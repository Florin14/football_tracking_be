from typing import Optional

from fastapi import Depends
from sqlalchemy.orm import Session, joinedload

from extensions.sqlalchemy import get_db
from modules.ranking.models.ranking_model import RankingModel
from modules.team.models import TeamModel, TeamListResponse
from modules.tournament.models.league_model import LeagueModel
from modules.tournament.models.league_team_model import LeagueTeamModel
from .router import router


@router.get("/", response_model=TeamListResponse)
async def get_teams(
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        leagueId: Optional[int] = None,
        excludeLeagueId: Optional[int] = None,
        tournamentId: Optional[int] = None,
        excludeTournamentId: Optional[int] = None,
        db: Session = Depends(get_db)
):
    include_ranking = leagueId is not None
    if include_ranking:
        query = (
            db.query(TeamModel, RankingModel)
            .outerjoin(
                RankingModel,
                (RankingModel.teamId == TeamModel.id)
                & (RankingModel.leagueId == leagueId),
            )
            .options(joinedload(TeamModel.players))
        )
    else:
        query = db.query(TeamModel).options(joinedload(TeamModel.players))

    if search:
        query = query.filter(TeamModel.name.ilike(f"%{search}%"))
    if leagueId or excludeLeagueId or tournamentId or excludeTournamentId:
        query = query.join(LeagueTeamModel, LeagueTeamModel.teamId == TeamModel.id)
        query = query.join(LeagueModel, LeagueModel.id == LeagueTeamModel.leagueId)
        if leagueId:
            query = query.filter(LeagueTeamModel.leagueId == leagueId)
        if excludeLeagueId:
            query = query.filter(LeagueTeamModel.leagueId != excludeLeagueId)
        if tournamentId:
            query = query.filter(LeagueModel.tournamentId == tournamentId)
        if excludeTournamentId:
            query = query.filter(LeagueModel.tournamentId != excludeTournamentId)

    teams = query.distinct(TeamModel.id).offset(skip).limit(limit).all()

    team_items = []
    for row in teams:
        if include_ranking:
            team, ranking = row
            team._ranking = ranking
        else:
            team = row
        team_items.append(team)

    return TeamListResponse(data=team_items)
