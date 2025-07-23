from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from extensions.sqlalchemy import get_db
from modules.ranking.models import RankingModel, RankingResponse
from .router import router


@router.get("/{id}", response_model=RankingResponse)
async def get_ranking(id: int, db: Session = Depends(get_db)):
    """Get a specific team by ID"""
    team = db.query(RankingModel).filter(RankingModel.id == id).first()
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

    return RankingResponse(
        id=team.id,
        name=team.name,
        description=team.description,
        players=players
    )
