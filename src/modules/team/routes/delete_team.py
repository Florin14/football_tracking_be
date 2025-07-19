from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from extensions.sqlalchemy import get_db
from modules.player.models import PlayerModel
from modules.team.models import TeamModel
from project_helpers.responses import ConfirmationResponse
from .router import router


@router.delete("/{id}", response_model=ConfirmationResponse)
async def delete_team(id: int, db: Session = Depends(get_db)):
    """Delete a team"""
    team = db.query(TeamModel).filter(TeamModel.id == id).first()
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )

    # Remove all players from team first
    db.query(PlayerModel).filter(PlayerModel.teamId == id).update({"teamId": None})

    # Delete the team
    db.delete(team)
    db.commit()

    return ConfirmationResponse(
        success=True,
        message=f"Team {team.name} deleted successfully"
    )
