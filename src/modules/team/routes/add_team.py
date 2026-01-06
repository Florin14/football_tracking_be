from fastapi import Depends
from sqlalchemy.orm import Session

from extensions.sqlalchemy import get_db
from modules.ranking.models.ranking_model import RankingModel
from modules.team.models import TeamModel, TeamAdd, TeamResponse
from .router import router


@router.post("/", response_model=TeamResponse)
async def add_team(data: TeamAdd, db: Session = Depends(get_db)):
    team = TeamModel(
        name=data.name,
        description=data.description,
        logo=data.logo,
        leagueId=1,
    )
    db.add(team)
    db.flush()

    exists = db.query(RankingModel).filter_by(teamId=team.id, leagueId=team.leagueId).first()
    if not exists:
        db.add(RankingModel(teamId=team.id, leagueId=team.leagueId))

    db.commit()
    db.refresh(team)

    return TeamResponse(
        id=team.id,
        name=team.name,
        logo=team.logo,
        description=team.description,
        players=[]
    )
