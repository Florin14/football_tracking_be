# Created by: cicada
# Date: Mon 02/03/2025
# Time: 14:11:47.00

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from extensions.sqlalchemy import get_db
from modules.player.models import (
    PlayerModel, PlayerAdd, PlayerUpdate, PlayerResponse, PlayerListResponse
)
from modules.team.models import TeamModel
from constants.player_positions import PlayerPositions
from constants.platform_roles import PlatformRoles
from project_helpers.responses import ConfirmationResponse
from project_helpers.functions.generate_password import hash_password


router = APIRouter(prefix='/player', tags=['Player'])


@router.post("/", response_model=PlayerResponse, status_code=status.HTTP_201_CREATED)
async def create_player(player_data: PlayerAdd, db: Session = Depends(get_db)):
    """Create a new player"""
    # Check if email already exists
    existing_player = db.query(PlayerModel).filter(PlayerModel.email == player_data.email).first()
    if existing_player:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Player with this email already exists"
        )
    
    # Validate position
    try:
        position = PlayerPositions(player_data.position.upper())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid player position"
        )
    
    # Hash password
    hashed_password = hash_password(player_data.password)
    
    player = PlayerModel(
        name=player_data.name,
        email=player_data.email,
        password=hashed_password,
        position=position,
        rating=player_data.rating,
        role=PlatformRoles.PLAYER
    )
    
    db.add(player)
    db.commit()
    db.refresh(player)
    
    return PlayerResponse(
        id=player.id,
        name=player.name,
        email=player.email,
        position=player.position.value if player.position else None,
        rating=player.rating,
        teamId=player.teamId,
        teamName=None
    )


@router.get("/", response_model=PlayerListResponse)
async def get_players(
    skip: int = 0,
    limit: int = 100,
    team_id: Optional[int] = None,
    position: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all players with optional filters"""
    query = db.query(PlayerModel).options(joinedload(PlayerModel.team))
    
    if team_id:
        query = query.filter(PlayerModel.teamId == team_id)
    
    if position:
        try:
            position_enum = PlayerPositions(position.upper())
            query = query.filter(PlayerModel.position == position_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid player position"
            )
    
    if search:
        query = query.filter(PlayerModel.name.ilike(f"%{search}%"))
    
    players = query.offset(skip).limit(limit).all()
    
    player_items = []
    for player in players:
        player_items.append({
            "id": player.id,
            "name": player.name,
            "email": player.email,
            "position": player.position.value if player.position else None,
            "rating": player.rating,
            "teamName": player.team.name if player.team else None
        })
    
    return PlayerListResponse(data=player_items)


@router.get("/{player_id}", response_model=PlayerResponse)
async def get_player(player_id: int, db: Session = Depends(get_db)):
    """Get a specific player by ID"""
    player = db.query(PlayerModel).options(joinedload(PlayerModel.team)).filter(PlayerModel.id == player_id).first()
    if not player:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Player not found"
        )
    
    return PlayerResponse(
        id=player.id,
        name=player.name,
        email=player.email,
        position=player.position.value if player.position else None,
        rating=player.rating,
        teamId=player.teamId,
        teamName=player.team.name if player.team else None
    )


@router.put("/{player_id}", response_model=PlayerResponse)
async def update_player(player_id: int, player_data: PlayerUpdate, db: Session = Depends(get_db)):
    """Update a player"""
    player = db.query(PlayerModel).options(joinedload(PlayerModel.team)).filter(PlayerModel.id == player_id).first()
    if not player:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Player not found"
        )
    
    if player_data.name:
        player.name = player_data.name
    
    if player_data.email:
        # Check if new email already exists (excluding current player)
        existing_player = db.query(PlayerModel).filter(
            PlayerModel.email == player_data.email,
            PlayerModel.id != player_id
        ).first()
        if existing_player:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Player with this email already exists"
            )
        player.email = player_data.email
    
    if player_data.position:
        try:
            position = PlayerPositions(player_data.position.upper())
            player.position = position
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid player position"
            )
    
    if player_data.rating is not None:
        player.rating = player_data.rating
    
    db.commit()
    db.refresh(player)
    
    return PlayerResponse(
        id=player.id,
        name=player.name,
        email=player.email,
        position=player.position.value if player.position else None,
        rating=player.rating,
        teamId=player.teamId,
        teamName=player.team.name if player.team else None
    )


@router.delete("/{player_id}", response_model=ConfirmationResponse)
async def delete_player(player_id: int, db: Session = Depends(get_db)):
    """Delete a player"""
    player = db.query(PlayerModel).filter(PlayerModel.id == player_id).first()
    if not player:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Player not found"
        )
    
    # Remove player from any team
    if player.teamId:
        player.teamId = None
        db.commit()
    
    # Delete the player
    db.delete(player)
    db.commit()
    
    return ConfirmationResponse(
        success=True,
        message=f"Player {player.name} deleted successfully"
    )


@router.get("/free-agents/", response_model=PlayerListResponse)
async def get_free_agents(
    skip: int = 0,
    limit: int = 100,
    position: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get players without a team (free agents)"""
    query = db.query(PlayerModel).filter(PlayerModel.teamId == None)
    
    if position:
        try:
            position_enum = PlayerPositions(position.upper())
            query = query.filter(PlayerModel.position == position_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid player position"
            )
    
    players = query.offset(skip).limit(limit).all()
    
    player_items = []
    for player in players:
        player_items.append({
            "id": player.id,
            "name": player.name,
            "email": player.email,
            "position": player.position.value if player.position else None,
            "rating": player.rating,
            "teamName": None
        })
    
    return PlayerListResponse(data=player_items)

