from fastapi import Depends
from sqlalchemy.orm import Session

from extensions.sqlalchemy import get_db
from project_helpers.dependencies import JwtRequired
from project_helpers.schemas import PaginationParams
from modules.training.models import TrainingSessionListResponse, TrainingSessionModel
from .router import router


@router.get("/", response_model=TrainingSessionListResponse)
async def get_training_sessions(
    params: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    current_user=Depends(JwtRequired()),
):
    sessions = params.apply(
        db.query(TrainingSessionModel).order_by(TrainingSessionModel.timestamp.desc())
    ).all()

    return TrainingSessionListResponse(data=sessions)
