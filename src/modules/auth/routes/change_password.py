import re

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from extensions import get_db
from modules.auth.models.auth_schemas import ChangePasswordBody
from modules.user.models.user_model import UserModel
from project_helpers.dependencies.jwt_required import JwtRequired
from project_helpers.error import Error
from project_helpers.functions import verify_password
from project_helpers.responses import ConfirmationResponse, ErrorResponse
from .router import router

PASSWORD_PATTERN = re.compile(
    r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^a-zA-Z0-9]).{8,}$'
)


@router.put("/change-password", response_model=ConfirmationResponse)
def change_password(
    body: ChangePasswordBody,
    request: Request,
    user: UserModel = Depends(JwtRequired()),
    db: Session = Depends(get_db),
):
    if not verify_password(user.password, body.currentPassword):
        return ErrorResponse(Error.INVALID_CREDENTIALS, statusCode=400)

    if not PASSWORD_PATTERN.match(body.newPassword):
        return ErrorResponse(
            Error.INVALID_CREDENTIALS,
            statusCode=422,
            message="Password must be at least 8 characters and include uppercase, lowercase, digit, and special character",
        )

    user.password = body.newPassword
    db.commit()

    return ConfirmationResponse(message="Password changed successfully")
