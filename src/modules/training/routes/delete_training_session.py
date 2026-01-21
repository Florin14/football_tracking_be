from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from extensions.sqlalchemy import get_db
from project_helpers.responses import ConfirmationResponse
from modules.training.models.training_session_model import TrainingSessionModel
from .router import router


@router.delete("/{id}", response_model=ConfirmationResponse)
async def delete_training_session(id: int, db: Session = Depends(get_db)):
    """Delete a training session"""
    training_session = db.query(TrainingSessionModel).filter(TrainingSessionModel.id == id).first()
    if not training_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Training session not found"
        )


    db.delete(training_session)
    db.commit()

    return ConfirmationResponse(
        success=True,
        message=f"training session {training_session.id} deleted successfully"
    )
