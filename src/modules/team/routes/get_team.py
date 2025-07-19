from fastapi import Depends, HTTPException, status
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from extensions.sqlalchemy import get_db
from modules.team.models import TeamModel, TeamResponse
from .router import router


@router.get("/{id}", response_model=TeamResponse)
async def get_team(id: int, db: Session = Depends(get_db)):
    """Get a specific team by ID"""
    team = db.query(TeamModel).options(joinedload(TeamModel.players)).filter(TeamModel.id == id).first()
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
