from fastapi import Depends
from sqlalchemy.orm import Session

from constants.platform_roles import PlatformRoles
from extensions import get_db
from project_helpers.db import apply_search
from project_helpers.dependencies import JwtRequired
from modules.user.models.user_schemas import UserListParams, UserListResponse
from modules.user.models.user_model import UserModel
from .router import router


@router.get('', response_model=UserListResponse)
async def get_all_users(
    params: UserListParams = Depends(),
    db: Session = Depends(get_db),
    current_user=Depends(JwtRequired(roles=[PlatformRoles.ADMIN])),
):
    employerQuery = db.query(UserModel)

    employerQuery = apply_search(employerQuery, UserModel.name, params.search)
    return UserListResponse(data=params.apply(employerQuery).all())
