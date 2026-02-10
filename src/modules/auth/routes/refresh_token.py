from fastapi import Depends
from extensions.auth_jwt import AuthJWT
from sqlalchemy.orm import Session
from extensions import get_db
from project_helpers.error import Error
from project_helpers.responses import ErrorResponse
from modules.auth.models.auth_schemas import RefreshTokenResponse
from .router import router


@router.post("/refresh-token", response_model=RefreshTokenResponse)
def refresh_token(auth: AuthJWT = Depends(), db: Session = Depends(get_db)):
    from modules.user.models.user_model import UserModel

    auth.jwt_refresh_token_required()
    rawData = auth.get_raw_jwt()
    user = db.query(UserModel).filter(UserModel.email == rawData.get("sub")).first()
    if user:
        accessToken = auth.create_access_token(user.email, user_claims=user.getClaims())
        refreshToken = auth.create_refresh_token(user.email)
        # Set the JWT cookies in the response
        auth.set_access_cookies(accessToken)
        auth.set_refresh_cookies(refreshToken)
        return RefreshTokenResponse(accessToken=accessToken, refreshToken=refreshToken)
    else:
        return ErrorResponse(Error.INVALID_TOKEN)
