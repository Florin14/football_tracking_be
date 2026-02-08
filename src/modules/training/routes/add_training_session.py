from fastapi import Depends, status
from sqlalchemy.orm import Session

from constants.platform_roles import PlatformRoles
from extensions.sqlalchemy import get_db
from modules.training.models import TrainingSessionAdd, TrainingSessionModel, TrainingSessionResponse
from project_helpers.dependencies import GetCurrentUser
from .router import router


@router.post("/", response_model=TrainingSessionResponse, status_code=status.HTTP_201_CREATED)
async def add_training_session(
    data: TrainingSessionAdd,
    db: Session = Depends(get_db),
    current_user=Depends(GetCurrentUser(roles=[PlatformRoles.ADMIN])),
):
    session = TrainingSessionModel(
        timestamp=data.timestamp,
        location=data.location,
        details=data.details
    )
    db.add(session)
    db.commit()

    return session
