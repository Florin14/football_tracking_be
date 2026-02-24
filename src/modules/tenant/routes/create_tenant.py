import re

from fastapi import Depends
from sqlalchemy.orm import Session

from constants.platform_roles import PlatformRoles
from extensions.sqlalchemy import get_db
from modules.tenant.models.tenant_model import TenantModel
from modules.tenant.models.tenant_schemas import TenantCreate, TenantResponse
from modules.tenant.schema_manager import create_tenant_schema, seed_tenant_defaults
from project_helpers.dependencies import JwtRequired
from project_helpers.error import Error
from project_helpers.responses import ErrorResponse
from .router import router


def _slug_to_schema_name(slug: str) -> str:
    safe = re.sub(r"[^a-z0-9_]", "_", slug.lower().strip())
    return f"tenant_{safe}"


@router.post("", response_model=TenantResponse, dependencies=[Depends(JwtRequired(roles=[PlatformRoles.ADMIN]))])
async def create_tenant(data: TenantCreate, db: Session = Depends(get_db)):
    existing = db.query(TenantModel).filter(TenantModel.slug == data.slug).first()
    if existing:
        return ErrorResponse(Error.DB_INSERT_ERROR, statusCode=409, message="Tenant slug already exists")

    schema_name = _slug_to_schema_name(data.slug)

    tenant = TenantModel(
        slug=data.slug,
        name=data.name,
        schema_name=schema_name,
        logo_url=data.logo_url,
        primary_color=data.primary_color,
        config=data.config or {},
    )
    db.add(tenant)
    db.flush()

    create_tenant_schema(db, schema_name)
    seed_tenant_defaults(
        db,
        schema_name=schema_name,
        tenant_name=data.name,
        admin_email=data.admin_email,
        admin_password=data.admin_password,
    )

    db.commit()
    db.refresh(tenant)

    return TenantResponse(
        id=tenant.id,
        slug=tenant.slug,
        name=tenant.name,
        schema_name=tenant.schema_name,
        logo_url=tenant.logo_url,
        primary_color=tenant.primary_color,
        is_active=tenant.is_active,
        config=tenant.config,
    )
