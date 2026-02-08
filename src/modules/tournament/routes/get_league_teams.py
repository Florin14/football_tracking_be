from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from extensions.sqlalchemy import get_db
from project_helpers.dependencies import JwtRequired
from modules.ranking.models.ranking_model import RankingModel
from modules.team.models import TeamModel
from modules.tournament.models.league_model import LeagueModel
from modules.tournament.models.league_team_model import LeagueTeamModel
from modules.tournament.models.tournament_schemas import LeagueTeamsResponse

from .router import router


@router.get("/leagues/{league_id}/teams", response_model=LeagueTeamsResponse, dependencies=[Depends(JwtRequired())])
async def get_league_teams(
    league_id: int,
    db: Session = Depends(get_db),
):
    league = db.query(LeagueModel).filter(LeagueModel.id == league_id).first()
    if not league:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"League with ID {league_id} not found",
        )

    teams = (
        db.query(TeamModel, RankingModel)
        .outerjoin(
            RankingModel,
            (RankingModel.teamId == TeamModel.id)
            & (RankingModel.leagueId == league_id),
        )
        .join(LeagueTeamModel, LeagueTeamModel.teamId == TeamModel.id)
        .options(joinedload(TeamModel.players))
        .filter(LeagueTeamModel.leagueId == league_id)
        .order_by(TeamModel.name)
        .all()
    )

    team_items = []
    for team, ranking in teams:
        team._ranking = ranking
        team_items.append(team)

    return LeagueTeamsResponse(
        league=league,
        teams=team_items,
    )
