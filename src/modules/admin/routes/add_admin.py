from fastapi import Depends
from sqlalchemy.orm import Session

from constants.platform_roles import PlatformRoles
from extensions import get_db
from modules.admin.models.admin_model import AdminModel
from modules.admin.models.admin_schemas import AdminAdd, AdminResponse
from project_helpers.dependencies import GetCurrentUser
from .router import router


@router.post("", response_model=AdminResponse)
async def create_admin(
    admin: AdminAdd,
    db: Session = Depends(get_db),
    current_user=Depends(GetCurrentUser(roles=[PlatformRoles.ADMIN])),
):
    password = admin.password if admin.password else "fotbal@2025"
    admin = AdminModel(**admin.model_dump(), password=password)
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin
