from datetime import datetime, timezone
import os
from typing import List

from fastapi import Depends, Response, Request
from sqlalchemy.orm import Session

from constants.platform_roles import PlatformRoles
from extensions import get_db
from extensions.auth_jwt import AuthJWT
from modules.user.models.user_model import UserModel
from project_helpers.error import Error
from project_helpers.exceptions import ErrorException


TOKEN_EXPIRATION = int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", 3600))
IMPLICIT_REFRESH_THRESHOLD = 60


class JwtRequired:
    def __init__(self, userModel: type[UserModel] = UserModel, roles: List[PlatformRoles] | None = None):
        self.userModel = userModel
        self.roles = {str(r) for r in roles} if roles else None

    def __call__(self, request: Request, response: Response, auth: AuthJWT = Depends(), db: Session = Depends(get_db)):
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

        if self.roles and str(user.role) not in self.roles:
            raise ErrorException(
                error=Error.USER_UNAUTHORIZED,
                statusCode=403,
                message=f"User must have one of the following roles: {sorted(self.roles)}, but you have: {user.role}!",
            )

        # Validate tenant consistency: JWT tenant must match request tenant
        jwt_tenant = claims.get("tenant_slug")
        request_tenant = getattr(getattr(request, "state", None), "tenant", None)
        if jwt_tenant and request_tenant and jwt_tenant != request_tenant.slug:
            raise ErrorException(
                error=Error.INVALID_TOKEN,
                statusCode=401,
                message="Token tenant mismatch",
            )

        # Handle token refresh if close to expiry
        exp_timestamp = claims.get("exp")
        if exp_timestamp:
            exp = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
            seconds_until_expire = int((exp - datetime.now(timezone.utc)).total_seconds())
            if (TOKEN_EXPIRATION - seconds_until_expire) > IMPLICIT_REFRESH_THRESHOLD:
                subject = user.email or user.id
                refresh_claims = user.getClaims()
                if jwt_tenant:
                    refresh_claims["tenant_slug"] = jwt_tenant
                new_token = auth.create_access_token(subject=subject, user_claims=refresh_claims)
                auth.set_access_cookies(new_token, response)

        request.state.user = user
        return user
