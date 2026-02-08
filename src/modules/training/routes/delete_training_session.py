from fastapi import Depends
from sqlalchemy.orm import Session

from constants.platform_roles import PlatformRoles
from extensions.sqlalchemy import get_db
from project_helpers.dependencies import GetInstanceFromPath, JwtRequired
from project_helpers.responses import ConfirmationResponse
from modules.training.models.training_session_model import TrainingSessionModel
from .router import router


@router.delete("/{id}", response_model=ConfirmationResponse)
async def delete_training_session(
    training_session: TrainingSessionModel = Depends(GetInstanceFromPath(TrainingSessionModel)),
    db: Session = Depends(get_db),
    current_user=Depends(JwtRequired(roles=[PlatformRoles.ADMIN])),
):
    """Delete a training session"""
    db.delete(training_session)
    db.commit()

    return ConfirmationResponse(
        success=True,
        message=f"training session {training_session.id} deleted successfully"
    )
