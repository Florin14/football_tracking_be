from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from constants.platform_roles import PlatformRoles
from constants.match_state import MatchState
from extensions.sqlalchemy import get_db
from modules.match.models import (
    MatchModel, MatchUpdate, MatchResponse, GoalModel
)
from modules.ranking.services import recalculate_match_rankings
from modules.tournament.services.knockout_service import auto_advance_knockout
from modules.team.models import TeamModel
from project_helpers.dependencies import GetInstanceFromPath, JwtRequired
from .router import router


def _get_match(
    match_id: int,
    db: Session = Depends(get_db),
):
    return GetInstanceFromPath(MatchModel)(match_id, db)


@router.put("/{match_id}", response_model=MatchResponse, dependencies=[Depends(JwtRequired(roles=[PlatformRoles.ADMIN]))])
async def update_match(
    match_data: MatchUpdate,
    match: MatchModel = Depends(_get_match),
    db: Session = Depends(get_db),
):
    """Update match details (location, timestamp, scores, state)"""
    from modules.player.models.player_model import PlayerModel

    if match_data.location:
        match.location = match_data.location

    if match_data.timestamp:
        match.timestamp = match_data.timestamp

    if match_data.youtubeUrl is not None:
        match.youtubeUrl = match_data.youtubeUrl if match_data.youtubeUrl != "" else None

    if match_data.round is not None:
        if not match.leagueId:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Round can only be set for league matches",
            )
        match.round = match_data.round

    scores_updated = False
    if match_data.scoreTeam1 is not None:
        match.scoreTeam1 = match_data.scoreTeam1
        scores_updated = True

    if match_data.scoreTeam2 is not None:
        match.scoreTeam2 = match_data.scoreTeam2
        scores_updated = True

    if match_data.goals is not None:
        scores_updated = True
        player_names_by_id = {}
        assist_names_by_id = {}
        for goal in match_data.goals:
            player = db.query(PlayerModel).filter(PlayerModel.id == goal.playerId).first()
            if not player:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Player with ID {goal.playerId} not found"
                )

            team = db.query(TeamModel).filter(TeamModel.id == goal.teamId).first()
            if not team:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Team with ID {goal.teamId} not found"
                )

            if goal.teamId not in [match.team1Id, match.team2Id]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Team {team.name} is not participating in this match"
                )

            if player.teamId != goal.teamId:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Player {player.name} does not belong to team {team.name}"
                )
            player_names_by_id[goal.playerId] = player.name

            if goal.assistPlayerId is not None:
                assist_player = db.query(PlayerModel).filter(PlayerModel.id == goal.assistPlayerId).first()
                if not assist_player:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Assist player with ID {goal.assistPlayerId} not found"
                    )
                if assist_player.teamId != goal.teamId:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Assist player {assist_player.name} does not belong to team {team.name}"
                    )
                assist_names_by_id[goal.assistPlayerId] = assist_player.name

        db.query(GoalModel).filter(GoalModel.matchId == match.id).delete()

        team1_goals = 0
        team2_goals = 0
        for goal in match_data.goals:
            db.add(GoalModel(
                matchId=match.id,
                playerId=goal.playerId,
                playerNameSnapshot=player_names_by_id.get(goal.playerId),
                assistPlayerId=goal.assistPlayerId,
                assistPlayerNameSnapshot=assist_names_by_id.get(goal.assistPlayerId),
                teamId=goal.teamId,
                minute=goal.minute,
                description=goal.description
            ))
            if goal.teamId == match.team1Id:
                team1_goals += 1
            elif goal.teamId == match.team2Id:
                team2_goals += 1

        if match_data.scoreTeam1 is not None and match_data.scoreTeam1 != team1_goals:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Score for team1 does not match provided goals"
            )
        if match_data.scoreTeam2 is not None and match_data.scoreTeam2 != team2_goals:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Score for team2 does not match provided goals"
            )

        if match_data.scoreTeam1 is None:
            match.scoreTeam1 = team1_goals
        if match_data.scoreTeam2 is None:
            match.scoreTeam2 = team2_goals

    if match_data.state:
        try:
            match.state = MatchState(match_data.state.upper())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid match state"
            )
    elif scores_updated:
        if (
            match.state == MatchState.SCHEDULED
            and match.scoreTeam1 is not None
            and match.scoreTeam2 is not None
        ):
            match.state = MatchState.FINISHED

    recalculate_match_rankings(db, match)
    auto_advance_knockout(db, match)
    db.commit()
    db.refresh(match)

    return match
