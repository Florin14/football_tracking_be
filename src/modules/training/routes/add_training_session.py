from fastapi import Depends, status
from sqlalchemy.orm import Session

from extensions.sqlalchemy import get_db
from modules.training.models import TrainingSessionAdd, TrainingSessionModel, TrainingSessionResponse
from .router import router


@router.post("/", response_model=TrainingSessionResponse, status_code=status.HTTP_201_CREATED)
async def add_training_session(data: TrainingSessionAdd, db: Session = Depends(get_db)):
    session = TrainingSessionModel(
        timestamp=data.timestamp,
        location=data.location,
        details=data.details
    )
    db.add(session)
    db.commit()

    return session
