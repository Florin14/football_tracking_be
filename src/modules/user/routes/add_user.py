from fastapi import Depends
from sqlalchemy.orm import Session

from extensions import get_db
from modules.user.models.user_model import UserModel
from modules.user.models.user_schemas import UserAdd, UserResponse
from .router import router


@router.post("", response_model=UserResponse)
async def create_user(user: UserAdd, db: Session = Depends(get_db)):
    password = user.password if user.password else "fotbal@2025"
    user = UserModel(**user.model_dump(), password=password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
