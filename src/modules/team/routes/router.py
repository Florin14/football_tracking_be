# Created by: cicada
# Date: Mon 02/03/2025
# Time: 14:11:47.00

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from extensions.sqlalchemy import get_db
from modules.team.models import TeamModel, TeamAdd, TeamUpdate, TeamResponse, TeamListResponse, AddPlayerToTeam
from modules.player.models import PlayerModel
from project_helpers.responses import ConfirmationResponse


router = APIRouter(prefix='/team', tags=['Team'])


@router.post("/", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
async def create_team(team_data: TeamAdd, db: Session = Depends(get_db)):
    """Create a new team"""
    # Check if team name already exists
    existing_team = db.query(TeamModel).filter(TeamModel.name == team_data.name).first()
    if existing_team:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Team with this name already exists"
        )
    
    team = TeamModel(
        name=team_data.name,
        description=team_data.description
    )
    db.add(team)
    db.commit()
    db.refresh(team)
    
    return TeamResponse(
        id=team.id,
        name=team.name,
        description=team.description,
        players=[]
    )


@router.get("/", response_model=TeamListResponse)
async def get_teams(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all teams with optional search"""
    query = db.query(TeamModel).options(joinedload(TeamModel.players))
    
    if search:
        query = query.filter(TeamModel.name.ilike(f"%{search}%"))
    
    teams = query.offset(skip).limit(limit).all()
    
    team_items = []
    for team in teams:
        team_items.append({
            "id": team.id,
            "name": team.name,
            "description": team.description,
            "playerCount": len(team.players) if team.players else 0
        })
    
    return TeamListResponse(data=team_items)


@router.get("/{team_id}", response_model=TeamResponse)
async def get_team(team_id: int, db: Session = Depends(get_db)):
    """Get a specific team by ID"""
    team = db.query(TeamModel).options(joinedload(TeamModel.players)).filter(TeamModel.id == team_id).first()
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )
    
    players = []
    if team.players:
        for player in team.players:
            players.append({
                "id": player.id,
                "name": player.name,
                "email": player.email,
                "position": player.position.value if player.position else None,
                "rating": player.rating
            })
    
    return TeamResponse(
        id=team.id,
        name=team.name,
        description=team.description,
        players=players
    )


@router.put("/{team_id}", response_model=TeamResponse)
async def update_team(team_id: int, team_data: TeamUpdate, db: Session = Depends(get_db)):
    """Update a team"""
    team = db.query(TeamModel).filter(TeamModel.id == team_id).first()
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )
    
    if team_data.name:
        # Check if new name already exists (excluding current team)
        existing_team = db.query(TeamModel).filter(
            TeamModel.name == team_data.name,
            TeamModel.id != team_id
        ).first()
        if existing_team:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Team with this name already exists"
            )
        team.name = team_data.name
    
    if team_data.description is not None:
        team.description = team_data.description
    
    db.commit()
    db.refresh(team)
    
    return TeamResponse(
        id=team.id,
        name=team.name,
        description=team.description,
        players=[]
    )


@router.post("/{team_id}/players", response_model=ConfirmationResponse)
async def add_player_to_team(
    team_id: int,
    player_data: AddPlayerToTeam,
    db: Session = Depends(get_db)
):
    """Add a player to a team"""
    # Check if team exists
    team = db.query(TeamModel).filter(TeamModel.id == team_id).first()
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )
    
    # Check if player exists
    player = db.query(PlayerModel).filter(PlayerModel.id == player_data.playerId).first()
    if not player:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Player not found"
        )
    
    # Check if player is already in a team
    if player.teamId:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Player is already assigned to a team"
        )
    
    # Add player to team
    player.teamId = team_id
    db.commit()
    
    return ConfirmationResponse(
        success=True,
        message=f"Player {player.name} added to team {team.name} successfully"
    )


@router.delete("/{team_id}/players/{player_id}", response_model=ConfirmationResponse)
async def remove_player_from_team(
    team_id: int,
    player_id: int,
    db: Session = Depends(get_db)
):
    """Remove a player from a team"""
    # Check if team exists
    team = db.query(TeamModel).filter(TeamModel.id == team_id).first()
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )
    
    # Check if player exists and is in this team
    player = db.query(PlayerModel).filter(
        PlayerModel.id == player_id,
        PlayerModel.teamId == team_id
    ).first()
    if not player:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Player not found in this team"
        )
    
    # Remove player from team
    player.teamId = None
    db.commit()
    
    return ConfirmationResponse(
        success=True,
        message=f"Player {player.name} removed from team {team.name} successfully"
    )


@router.delete("/{team_id}", response_model=ConfirmationResponse)
async def delete_team(team_id: int, db: Session = Depends(get_db)):
    """Delete a team"""
    team = db.query(TeamModel).filter(TeamModel.id == team_id).first()
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )
    
    # Remove all players from team first
    db.query(PlayerModel).filter(PlayerModel.teamId == team_id).update({"teamId": None})
    
    # Delete the team
    db.delete(team)
    db.commit()
    
    return ConfirmationResponse(
        success=True,
        message=f"Team {team.name} deleted successfully"
    )


@router.get("/nordic-lions", response_model=TeamResponse)
async def get_nordic_lions_team(db: Session = Depends(get_db)):
    """Get the Nordic Lions team (default team)"""
    team = db.query(TeamModel).options(joinedload(TeamModel.players)).filter(
        TeamModel.isDefault.is_(True)
    ).first()
    
    if not team:
        # Create the team if it doesn't exist
        team = TeamModel(
            name="Nordic Lions",
            description="The default team for the Nordic Lions football club",
            isDefault=True  # Assuming you want to mark it as default
        )
        db.add(team)
        db.commit()
        db.refresh(team)
    
    players = []
    if team.players:
        for player in team.players:
            players.append({
                "id": player.id,
                "name": player.name,
                "email": player.email,
                "position": player.position.value if player.position else None,
                "rating": player.rating
            })
    
    return TeamResponse(
        id=team.id,
        name=team.name,
        description=team.description,
        players=players
    )

