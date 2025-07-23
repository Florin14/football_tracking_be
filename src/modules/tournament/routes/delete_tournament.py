from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from extensions.sqlalchemy import get_db
from modules.player.models import PlayerModel
from modules.tournament.models import TournamentModel
from project_helpers.responses import ConfirmationResponse
from .router import router


@router.delete("/{id}", response_model=ConfirmationResponse)
async def delete_tournament(id: int, db: Session = Depends(get_db)):
    """Delete a tournament"""
    tournament = db.query(TournamentModel).filter(TournamentModel.id == id).first()
    if not tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )

    # Remove all players from team first
    db.query(PlayerModel).filter(PlayerModel.teamId == id).update({"teamId": None})

    # Delete the tournament
    db.delete(tournament)
    db.commit()

    return ConfirmationResponse(
        success=True,
        message=f"tournament {tournament.name} deleted successfully"
    )
