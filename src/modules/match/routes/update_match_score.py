from fastapi import Depends, HTTPException, status
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from constants.match_state import MatchState
from extensions.sqlalchemy import get_db
from modules.match.models import (
    MatchModel, GoalModel, ScoreUpdate
)
from modules.player.models import PlayerModel
from modules.team.models import TeamModel
from project_helpers.responses import ConfirmationResponse
from .router import router


@router.post("/{match_id}/score", response_model=ConfirmationResponse)
async def update_match_score(
        match_id: int,
        score_data: ScoreUpdate,
        db: Session = Depends(get_db)
):
    """Update match score by adding goals from your team (Nordic Lions or any team)"""
    match = db.query(MatchModel).filter(MatchModel.id == match_id).first()
    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found"
        )

    # Validate each goal
    for goal_data in score_data.goals:
        # Check if player exists
        player = db.query(PlayerModel).filter(PlayerModel.id == goal_data.playerId).first()
        if not player:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Player with ID {goal_data.playerId} not found"
            )

        # Check if team exists
        team = db.query(TeamModel).filter(TeamModel.id == goal_data.teamId).first()
        if not team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Team with ID {goal_data.teamId} not found"
            )

        # Verify that the team is part of this match
        if goal_data.teamId not in [match.team1Id, match.team2Id]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Team {team.name} is not participating in this match"
            )

        # Verify that the player belongs to the team
        if player.teamId != goal_data.teamId:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Player {player.name} does not belong to team {team.name}"
            )

        # Create the goal
        goal = GoalModel(
            matchId=match_id,
            playerId=goal_data.playerId,
            teamId=goal_data.teamId,
            minute=goal_data.minute,
            description=goal_data.description
        )
        db.add(goal)

    # Update match scores based on goals
    team1_goals = len([g for g in score_data.goals if g.teamId == match.team1Id])
    team2_goals = len([g for g in score_data.goals if g.teamId == match.team2Id])

    # Add to existing scores or initialize
    if match.scoreTeam1 is None:
        match.scoreTeam1 = 0
    if match.scoreTeam2 is None:
        match.scoreTeam2 = 0

    match.scoreTeam1 += team1_goals
    match.scoreTeam2 += team2_goals

    # Update match state to ongoing if it was scheduled
    if match.state == MatchState.SCHEDULED:
        match.state = MatchState.ONGOING

    db.commit()

    return ConfirmationResponse(
        success=True,
        message=f"Successfully added {len(score_data.goals)} goal(s) to the match"
    )
