from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from extensions.sqlachemy.init import get_db
from modules.user.models.user_model import UserModel

router = APIRouter()


@router.post("/users/")
def create_user(user: UserAdd, db: Session = Depends(get_db)):
    password = "fotbal@2025"
    user = UserModel(**user.model_dump(), password=password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
