from fastapi import Depends
from sqlalchemy.orm import Session

from extensions.sqlalchemy import get_db
from modules.training.models import TrainingSessionListResponse, TrainingSessionModel, TrainingSessionResponse
from .router import router


@router.get("/", response_model=TrainingSessionListResponse)
async def get_training_sessions(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    sessions = db.query(TrainingSessionModel).order_by(
        TrainingSessionModel.timestamp.desc()
    ).offset(skip).limit(limit).all()

    items = []
    for session in sessions:
        items.append(TrainingSessionResponse(
            id=session.id,
            timestamp=session.timestamp,
            location=session.location,
            details=session.details
        ))

    return TrainingSessionListResponse(data=items)
