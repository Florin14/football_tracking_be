from fastapi import Depends
from sqlalchemy.orm import Session

from constants.platform_roles import PlatformRoles
from extensions import get_db
from extensions.auth_jwt import AuthJWT
from modules.user.models.user_model import UserModel
from project_helpers.error import Error
from project_helpers.exceptions import ErrorException


class GetCurrentUser:
    def __init__(self, userModel: type[UserModel] = UserModel, roles: list[PlatformRoles] | None = None):
        self.userModel = userModel
        self.roles = set(roles) if roles else None

    def __call__(self, auth: AuthJWT = Depends(), db: Session = Depends(get_db)):
        auth.jwt_required()
        claims = auth.get_raw_jwt() or {}
        user_id = claims.get("userId")
        if not user_id:
            raise ErrorException(error=Error.INVALID_TOKEN, statusCode=401)

        user = db.query(self.userModel).get(user_id)
        if not user:
            raise ErrorException(error=Error.USER_NOT_FOUND, statusCode=404)

        if getattr(user, "isAvailable", True) is False:
            raise ErrorException(error=Error.USER_ACCOUNT_IS_DEACTIVATED, statusCode=403)

        if getattr(user, "isDeleted", False):
            raise ErrorException(error=Error.USER_UNAUTHORIZED, statusCode=403)

        if self.roles and user.role not in self.roles:
            raise ErrorException(error=Error.USER_UNAUTHORIZED, statusCode=403)

        return user
