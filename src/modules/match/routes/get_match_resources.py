from fastapi import Depends
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from extensions.sqlalchemy import get_db
from project_helpers.dependencies import JwtRequired
from modules.match.models import (
    MatchResourcesResponse
)
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

    return MatchResourcesResponse(leagues=leagues)
