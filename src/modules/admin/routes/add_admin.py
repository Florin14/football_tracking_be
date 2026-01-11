from fastapi import Depends
from sqlalchemy.orm import Session

from extensions import get_db
from modules.admin.models.admin_model import AdminModel
from modules.admin.models.admin_schemas import AdminAdd, AdminResponse
from .router import router


@router.post("", response_model=AdminResponse)
async def create_admin(admin: AdminAdd, db: Session = Depends(get_db)):
    password = admin.password if admin.password else "fotbal@2025"
    admin = AdminModel(**admin.model_dump(), password=password)
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin