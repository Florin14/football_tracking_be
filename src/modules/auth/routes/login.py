from fastapi import Depends
from sqlalchemy.orm import Session

# from constants.citizen_status import CitizenStatusEnum
from extensions import get_db
from extensions.auth_jwt import AuthJWT
from modules.auth.models.auth_schemas import LoginBody, LoginResponse
from modules.auth.models.login_attempt_model import LoginAttemptModel
from modules.user.models.user_model import UserModel
from project_helpers.error import Error
from project_helpers.functions import verify_password
from project_helpers.responses import ErrorResponse
# from .dependencies import VerifyRecaptcha
from .router import router


@router.post("/login", response_model=LoginResponse, dependencies=[])
def login(body: LoginBody, auth: AuthJWT = Depends(), db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.email == body.email).first()

    if not user or not verify_password(user.password, body.password):
        return ErrorResponse(Error.INVALID_CREDENTIALS, statusCode=401)

    if user.isAvailable is False:
        return ErrorResponse(Error.USER_ACCOUNT_IS_DEACTIVATED, statusCode=403)

    accessToken = auth.create_access_token(user.email, user_claims=user.getClaims())
    refreshToken = auth.create_refresh_token(user.email)
    # Set the JWT cookies in the response
    auth.set_access_cookies(accessToken)
    auth.set_refresh_cookies(refreshToken)

    # remove email login attempts
    db.query(LoginAttemptModel).filter(LoginAttemptModel.email == user.email).delete(synchronize_session="fetch")
    db.commit()

    return LoginResponse(
        id=user.id,
        name=user.name,
        role=user.role,
        isAvailable=user.isAvailable,
        accessToken=accessToken,
        refreshToken=refreshToken,
    )
