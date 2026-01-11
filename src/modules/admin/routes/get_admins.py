from sqlalchemy.orm import Session
from .router import router
from fastapi import Depends
from extensions import get_db
from modules.user.models.user_schemas import UserFilter, UserListResponse
from modules.user.models.user_model import UserModel


@router.get('', response_model=UserListResponse)
async def get_all_users(query: UserFilter = Depends(), db: Session = Depends(get_db)):
    employerQuery = db.query(UserModel)

    # employerQuery = employerQuery.order_by(getattr(getattr(UserModel, query.sortBy), query.sortType)())
    # qty = employerQuery.count()
    # if None not in [query.offset, query.limit]:
    #     employerQuery = employerQuery.offset(query.offset).limit(query.limit)
    return UserListResponse(data=employerQuery.all())
