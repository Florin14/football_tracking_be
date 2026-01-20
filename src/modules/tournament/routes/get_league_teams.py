from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from extensions.sqlalchemy import get_db
from modules.team.models import TeamModel
from modules.tournament.models.league_model import LeagueModel
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
        db.query(TeamModel)
        .options(joinedload(TeamModel.players))
        .filter(TeamModel.leagueId == league_id)
        .order_by(TeamModel.name)
        .all()
    )

    team_items = []
    for team in teams:
        team_items.append({
            "id": team.id,
            "name": team.name,
            "description": team.description,
            "logo": team.logo,
            "playerCount": len(team.players) if team.players else 0,
        })

    return LeagueTeamsResponse(
        league={
            "id": league.id,
            "name": league.name,
            "description": league.description,
            "season": league.season,
            "relevanceOrder": league.relevanceOrder,
            "tournamentId": league.tournamentId,
        },
        teams=team_items,
    )
