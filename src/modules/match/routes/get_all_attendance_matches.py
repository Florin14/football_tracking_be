from fastapi import Depends
from sqlalchemy import or_
from sqlalchemy import desc
from sqlalchemy.orm import Session, joinedload

from extensions.sqlalchemy import get_db
from modules.match.models import (
    MatchModel, MatchListResponse
)
from modules.team.models.team_model import TeamModel
from .router import router


@router.get("-attendance", response_model=MatchListResponse)
async def get_matches(
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(get_db)
):
    query = db.query(MatchModel).options(
        joinedload(MatchModel.team1),
        joinedload(MatchModel.team2),
        joinedload(MatchModel.league),
    )

    default_team = db.query(TeamModel).filter(TeamModel.isDefault.is_(True)).first()
    if default_team:
        query = query.filter(
            or_(MatchModel.team1Id == default_team.id, MatchModel.team2Id == default_team.id)
        )
    
    query = query.order_by(
        MatchModel.timestamp.is_(None),
        MatchModel.timestamp,
    )

    matches = query.offset(skip).limit(limit).all()

    match_items = []
    for match in matches:
        match_items.append({
            "id": match.id,
            "team1Name": match.team1.name,
            "team2Name": match.team2.name,
            "team1Logo": match.team1.logo,
            "team2Logo": match.team2.logo,
            "leagueId": match.league.id if match.league else None,
            "leagueName": match.league.name if match.league else None,
            "leagueLogo": match.league.logo if match.league else None,
            "location": match.location,
            "timestamp": match.timestamp,
            "scoreTeam1": match.scoreTeam1,
            "scoreTeam2": match.scoreTeam2,
            "state": match.state.value
        })

    return MatchListResponse(data=match_items)
