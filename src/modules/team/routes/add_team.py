from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from constants.platform_roles import PlatformRoles
from extensions.sqlalchemy import get_db
from modules.ranking.models.ranking_model import RankingModel
from modules.team.models import TeamModel, TeamAdd, TeamResponse
from modules.tournament.models.league_model import LeagueModel
from modules.tournament.models.league_team_model import LeagueTeamModel
from project_helpers.dependencies import GetCurrentUser
from .router import router


@router.post("/", response_model=TeamResponse)
async def add_team(
    data: TeamAdd,
    db: Session = Depends(get_db),
    current_user=Depends(GetCurrentUser(roles=[PlatformRoles.ADMIN])),
):
    league = db.query(LeagueModel).filter(LeagueModel.id == data.leagueId).first()
    if not league:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"League with ID {data.leagueId} not found",
        )

    team = TeamModel(
        name=data.name,
        description=data.description,
        logo=data.logo,
    )
    db.add(team)
    db.flush()

    db.add(LeagueTeamModel(leagueId=league.id, teamId=team.id))
    exists = db.query(RankingModel).filter_by(teamId=team.id, leagueId=league.id).first()
    if not exists:
        db.add(RankingModel(teamId=team.id, leagueId=league.id))

    db.commit()
    db.refresh(team)

    return team
