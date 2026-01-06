from fastapi import Depends
from extensions.auth_jwt import AuthJWT
from sqlalchemy.orm import Session
from extensions import get_db
from project_helpers.error import Error
from project_helpers.responses import ConfirmationResponse, ErrorResponse
from ...user import UserModel
from .router import router


@router.post("/refresh-token", response_model=ConfirmationResponse)
def refresh_token(auth: AuthJWT = Depends(), db: Session = Depends(get_db)):
    auth.jwt_refresh_token_required()
    rawData = auth.get_raw_jwt()
    user = db.query(UserModel).filter(UserModel.email == rawData.get("sub")).first()
    if user:
        accessToken = auth.create_access_token(user.email, user_claims=user.getClaims())
        refreshToken = auth.create_refresh_token(user.email)
        # Set the JWT cookies in the response
        auth.set_access_cookies(accessToken)
        auth.set_refresh_cookies(refreshToken)
        return ConfirmationResponse()
    else:
        return ErrorResponse(Error.INVALID_TOKEN)
