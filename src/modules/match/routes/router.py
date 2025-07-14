# Created by: cicada
# Date: Mon 02/03/2025
# Time: 14:11:47.00

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_

from extensions.sqlalchemy import get_db
from modules.match.models import (
    MatchModel, MatchAdd, MatchUpdate, MatchResponse, MatchListResponse,
    GoalModel, ScoreUpdate, GoalAdd, GoalListResponse, GoalResponse
)
from modules.team.models import TeamModel
from modules.player.models import PlayerModel
from constants.match_state import MatchState
from project_helpers.responses import ConfirmationResponse


router = APIRouter(prefix='/match', tags=['Match'])


@router.post("/", response_model=MatchResponse, status_code=status.HTTP_201_CREATED)
async def create_match(match_data: MatchAdd, db: Session = Depends(get_db)):
    """Schedule a new match"""
    # Validate teams exist
    team1 = db.query(TeamModel).filter(TeamModel.id == match_data.team1Id).first()
    team2 = db.query(TeamModel).filter(TeamModel.id == match_data.team2Id).first()
    
    if not team1:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team 1 not found"
        )
    if not team2:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team 2 not found"
        )
    
    if match_data.team1Id == match_data.team2Id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A team cannot play against itself"
        )
    
    match = MatchModel(
        team1Id=match_data.team1Id,
        team2Id=match_data.team2Id,
        location=match_data.location,
        timestamp=match_data.timestamp,
        state=MatchState.SCHEDULED
    )
    
    db.add(match)
    db.commit()
    db.refresh(match)
    
    return MatchResponse(
        id=match.id,
        team1Id=match.team1Id,
        team2Id=match.team2Id,
        team1Name=team1.name,
        team2Name=team2.name,
        location=match.location,
        timestamp=match.timestamp,
        scoreTeam1=match.scoreTeam1,
        scoreTeam2=match.scoreTeam2,
        state=match.state.value,
        goals=[]
    )


@router.get("/", response_model=MatchListResponse)
async def get_matches(
    skip: int = 0,
    limit: int = 100,
    team_id: Optional[int] = None,
    state: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all matches with optional filters"""
    query = db.query(MatchModel).options(
        joinedload(MatchModel.team1),
        joinedload(MatchModel.team2)
    )
    
    if team_id:
        query = query.filter(
            or_(MatchModel.team1Id == team_id, MatchModel.team2Id == team_id)
        )
    
    if state:
        try:
            match_state = MatchState(state.upper())
            query = query.filter(MatchModel.state == match_state)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid match state"
            )
    
    matches = query.offset(skip).limit(limit).all()
    
    match_items = []
    for match in matches:
        match_items.append({
            "id": match.id,
            "team1Name": match.team1.name,
            "team2Name": match.team2.name,
            "location": match.location,
            "timestamp": match.timestamp,
            "scoreTeam1": match.scoreTeam1,
            "scoreTeam2": match.scoreTeam2,
            "state": match.state.value
        })
    
    return MatchListResponse(data=match_items)


@router.get("/{match_id}", response_model=MatchResponse)
async def get_match(match_id: int, db: Session = Depends(get_db)):
    """Get a specific match by ID"""
    match = db.query(MatchModel).options(
        joinedload(MatchModel.team1),
        joinedload(MatchModel.team2),
        joinedload(MatchModel.goals)
    ).filter(MatchModel.id == match_id).first()
    
    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found"
        )
    
    goals = []
    if match.goals:
        for goal in match.goals:
            player = db.query(PlayerModel).filter(PlayerModel.id == goal.playerId).first()
            team = db.query(TeamModel).filter(TeamModel.id == goal.teamId).first()
            goals.append({
                "id": goal.id,
                "playerId": goal.playerId,
                "playerName": player.name if player else "Unknown",
                "teamId": goal.teamId,
                "teamName": team.name if team else "Unknown",
                "minute": goal.minute,
                "timestamp": goal.timestamp,
                "description": goal.description
            })
    
    return MatchResponse(
        id=match.id,
        team1Id=match.team1Id,
        team2Id=match.team2Id,
        team1Name=match.team1.name,
        team2Name=match.team2.name,
        location=match.location,
        timestamp=match.timestamp,
        scoreTeam1=match.scoreTeam1,
        scoreTeam2=match.scoreTeam2,
        state=match.state.value,
        goals=goals
    )


@router.put("/{match_id}", response_model=MatchResponse)
async def update_match(match_id: int, match_data: MatchUpdate, db: Session = Depends(get_db)):
    """Update match details (location, timestamp, scores, state)"""
    match = db.query(MatchModel).options(
        joinedload(MatchModel.team1),
        joinedload(MatchModel.team2)
    ).filter(MatchModel.id == match_id).first()
    
    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found"
        )
    
    if match_data.location:
        match.location = match_data.location
    
    if match_data.timestamp:
        match.timestamp = match_data.timestamp
    
    if match_data.scoreTeam1 is not None:
        match.scoreTeam1 = match_data.scoreTeam1
    
    if match_data.scoreTeam2 is not None:
        match.scoreTeam2 = match_data.scoreTeam2
    
    if match_data.state:
        try:
            match.state = MatchState(match_data.state.upper())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid match state"
            )
    
    db.commit()
    db.refresh(match)
    
    return MatchResponse(
        id=match.id,
        team1Id=match.team1Id,
        team2Id=match.team2Id,
        team1Name=match.team1.name,
        team2Name=match.team2.name,
        location=match.location,
        timestamp=match.timestamp,
        scoreTeam1=match.scoreTeam1,
        scoreTeam2=match.scoreTeam2,
        state=match.state.value,
        goals=[]
    )


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


@router.post("/{match_id}/finish", response_model=ConfirmationResponse)
async def finish_match(match_id: int, db: Session = Depends(get_db)):
    """Mark a match as finished"""
    match = db.query(MatchModel).filter(MatchModel.id == match_id).first()
    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found"
        )
    
    if match.state == MatchState.FINISHED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Match is already finished"
        )
    
    match.state = MatchState.FINISHED
    
    # Ensure scores are set (default to 0 if not set)
    if match.scoreTeam1 is None:
        match.scoreTeam1 = 0
    if match.scoreTeam2 is None:
        match.scoreTeam2 = 0
    
    db.commit()
    
    return ConfirmationResponse(
        success=True,
        message="Match marked as finished"
    )


@router.delete("/{match_id}", response_model=ConfirmationResponse)
async def delete_match(match_id: int, db: Session = Depends(get_db)):
    """Delete a match (only if not finished)"""
    match = db.query(MatchModel).filter(MatchModel.id == match_id).first()
    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found"
        )
    
    if match.state == MatchState.FINISHED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete a finished match"
        )
    
    # Delete all goals associated with this match
    db.query(GoalModel).filter(GoalModel.matchId == match_id).delete()
    
    # Delete the match
    db.delete(match)
    db.commit()
    
    return ConfirmationResponse(
        success=True,
        message="Match deleted successfully"
    )


@router.get("/goals/", response_model=GoalListResponse)
async def get_goals(
    skip: int = 0,
    limit: int = 100,
    match_id: Optional[int] = None,
    player_id: Optional[int] = None,
    team_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get goals with optional filters"""
    query = db.query(GoalModel)
    
    if match_id:
        query = query.filter(GoalModel.matchId == match_id)
    
    if player_id:
        query = query.filter(GoalModel.playerId == player_id)
    
    if team_id:
        query = query.filter(GoalModel.teamId == team_id)
    
    goals = query.offset(skip).limit(limit).all()
    
    goal_items = []
    for goal in goals:
        player = db.query(PlayerModel).filter(PlayerModel.id == goal.playerId).first()
        team = db.query(TeamModel).filter(TeamModel.id == goal.teamId).first()
        
        goal_items.append(GoalResponse(
            id=goal.id,
            matchId=goal.matchId,
            playerId=goal.playerId,
            playerName=player.name if player else "Unknown",
            teamId=goal.teamId,
            teamName=team.name if team else "Unknown",
            minute=goal.minute,
            timestamp=goal.timestamp,
            description=goal.description
        ))
    
    return GoalListResponse(data=goal_items)

