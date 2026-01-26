from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from extensions.sqlalchemy import get_db
from modules.ranking.models.ranking_model import RankingModel
from modules.team.models import TeamModel
from modules.tournament.models.league_model import LeagueModel
from modules.tournament.models.league_team_model import LeagueTeamModel
from modules.tournament.models.tournament_schemas import LeagueTeamsResponse

from .router import router


@router.get("/leagues/{league_id}/teams", response_model=LeagueTeamsResponse)
async def get_league_teams(league_id: int, db: Session = Depends(get_db)):
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
        team_items.append({
            "id": team.id,
            "name": team.name,
            "description": team.description,
            "logo": team.logo,
            "playerCount": len(team.players) if team.players else 0,
            "points": ranking.points if ranking else 0,
            "goalsFor": ranking.goalsScored if ranking else 0,
            "goalsAgainst": ranking.goalsConceded if ranking else 0,
            "wins": ranking.gamesWon if ranking else 0,
            "draws": ranking.gamesTied if ranking else 0,
            "losses": ranking.gamesLost if ranking else 0,
        })

    return LeagueTeamsResponse(
        league={
            "id": league.id,
            "name": league.name,
            "description": league.description,
            "logo": league.logo,
            "season": league.season,
            "relevanceOrder": league.relevanceOrder,
            "tournamentId": league.tournamentId,
        },
        teams=team_items,
    )
