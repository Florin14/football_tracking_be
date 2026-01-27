from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from constants.match_state import MatchState
from extensions.sqlalchemy import get_db
from modules.match.models import (
    MatchModel, MatchAdd, MatchResponse
)
from modules.team.models import TeamModel
from modules.tournament.models.league_model import LeagueModel
from modules.tournament.models.league_team_model import LeagueTeamModel
from .router import router


@router.post("/", response_model=MatchResponse, status_code=status.HTTP_201_CREATED)
async def add_match(data: MatchAdd, db: Session = Depends(get_db)):
    if data.team1Id == data.team2Id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A team cannot play against itself"
        )

    team_ids = {data.team1Id, data.team2Id}
    teams = db.query(TeamModel).filter(TeamModel.id.in_(team_ids)).all()
    if len(teams) != 2:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or more teams not found",
        )

    league_id = data.leagueId
    if league_id:
        league = db.query(LeagueModel).filter(LeagueModel.id == league_id).first()
        if not league:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"League with ID {league_id} not found",
            )
        membership = (
            db.query(LeagueTeamModel)
            .filter(
                LeagueTeamModel.leagueId == league_id,
                LeagueTeamModel.teamId.in_(team_ids),
            )
            .all()
        )
        if len(membership) != 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Both teams must belong to the selected league",
            )
    else:
        league_ids = (
            db.query(LeagueTeamModel.leagueId)
            .filter(LeagueTeamModel.teamId == data.team1Id)
            .all()
        )
        league_ids_1 = {league_id for (league_id,) in league_ids}
        league_ids = (
            db.query(LeagueTeamModel.leagueId)
            .filter(LeagueTeamModel.teamId == data.team2Id)
            .all()
        )
        league_ids_2 = {league_id for (league_id,) in league_ids}
        common = league_ids_1.intersection(league_ids_2)
        if len(common) == 1:
            league_id = next(iter(common))
        elif len(common) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Teams do not share a league. Provide leagueId.",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Teams share multiple leagues. Provide leagueId.",
            )

    match = MatchModel(
        team1Id=data.team1Id,
        team2Id=data.team2Id,
        location=data.location,
        timestamp=data.timestamp,
        leagueId=league_id,
    )

    db.add(match)
    db.commit()

    match = (
        db.query(MatchModel)
        .options(
            joinedload(MatchModel.team1),
            joinedload(MatchModel.team2),
            joinedload(MatchModel.league),
        )
        .filter(MatchModel.id == match.id)
        .first()
    )

    return MatchResponse(
        id=match.id,
        team1=match.team1,
        team2=match.team2,
        league=match.league,
        location=match.location,
        timestamp=match.timestamp,
        scoreTeam1=match.scoreTeam1,
        scoreTeam2=match.scoreTeam2,
        state=match.state.value,
        goals=[]
    )
