from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from extensions.sqlalchemy import get_db
from modules.training.models import TrainingSessionModel, TrainingSessionResponse, TrainingSessionUpdate
from .router import router


@router.put("/{training_session_id}", response_model=TrainingSessionResponse)
async def update_training_session(
    training_session_id: int,
    data: TrainingSessionUpdate,
    db: Session = Depends(get_db),
):
    session = db.query(TrainingSessionModel).filter(TrainingSessionModel.id == training_session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Training session with ID {training_session_id} not found",
        )

    if data.timestamp is not None:
        session.timestamp = data.timestamp
    if data.location is not None:
        session.location = data.location
    if data.details is not None:
        session.details = data.details

    db.commit()
    db.refresh(session)

    return TrainingSessionResponse(
        id=session.id,
        timestamp=session.timestamp,
        location=session.location,
        details=session.details,
    )
