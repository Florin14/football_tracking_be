from fastapi import Depends
from sqlalchemy.orm import Session

from constants.platform_roles import PlatformRoles
from extensions.sqlalchemy import get_db
from modules.training.models import TrainingSessionModel, TrainingSessionResponse, TrainingSessionUpdate
from project_helpers.dependencies import GetInstanceFromPath, JwtRequired
from .router import router


def _get_training_session(
    training_session_id: int,
    db: Session = Depends(get_db),
):
    return GetInstanceFromPath(TrainingSessionModel)(training_session_id, db)


@router.put("/{training_session_id}", response_model=TrainingSessionResponse)
async def update_training_session(
    data: TrainingSessionUpdate,
    session: TrainingSessionModel = Depends(_get_training_session),
    db: Session = Depends(get_db),
    current_user=Depends(JwtRequired(roles=[PlatformRoles.ADMIN])),
):
    if data.timestamp is not None:
        session.timestamp = data.timestamp
    if data.location is not None:
        session.location = data.location
    if data.details is not None:
        session.details = data.details

    db.commit()
    db.refresh(session)

    return session
