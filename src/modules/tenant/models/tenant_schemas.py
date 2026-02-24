from typing import Any, Dict, Optional

from project_helpers.schemas import BaseSchema


class TenantCreate(BaseSchema):
    slug: str
    name: str
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    admin_email: Optional[str] = None
    admin_password: Optional[str] = None


class TenantUpdate(BaseSchema):
    name: Optional[str] = None
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    is_active: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None


class TenantInfoResponse(BaseSchema):
    slug: str
    name: str
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class TenantResponse(BaseSchema):
    id: int
    slug: str
    name: str
    schema_name: str
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    is_active: bool
    config: Optional[Dict[str, Any]] = None
