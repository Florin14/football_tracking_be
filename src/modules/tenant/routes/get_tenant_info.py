from fastapi import Depends
from sqlalchemy.orm import Session

from extensions.sqlalchemy import get_db
from modules.tenant.models.tenant_model import TenantModel
from modules.tenant.models.tenant_schemas import TenantInfoResponse
from project_helpers.error import Error
from project_helpers.responses import ErrorResponse
from .router import router


@router.get("/{slug}/info", response_model=TenantInfoResponse)
async def get_tenant_info(slug: str, db: Session = Depends(get_db)):
    tenant = db.query(TenantModel).filter(
        TenantModel.slug == slug,
        TenantModel.is_active.is_(True),
    ).first()

    if not tenant:
        return ErrorResponse(Error.DB_MODEL_INSTANCE_DOES_NOT_EXISTS, statusCode=404, message=f"Tenant '{slug}' not found")

    return TenantInfoResponse(
        slug=tenant.slug,
        name=tenant.name,
        logo_url=tenant.logo_url,
        primary_color=tenant.primary_color,
        config=tenant.config,
    )
