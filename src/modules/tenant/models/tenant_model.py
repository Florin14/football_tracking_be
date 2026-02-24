from sqlalchemy import BigInteger, Boolean, Column, String, Text
from sqlalchemy.dialects.postgresql import JSON

from extensions import BaseModel


class TenantModel(BaseModel):
    __tablename__ = "tenants"
    __table_args__ = {"schema": "public"}

    id = Column(BigInteger, primary_key=True, index=True)
    slug = Column(String(63), nullable=False, unique=True, index=True)
    name = Column(String(120), nullable=False)
    schema_name = Column(String(63), nullable=False, unique=True)
    logo_url = Column(Text, nullable=True)
    primary_color = Column(String(7), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    config = Column(JSON, nullable=True, default=dict)
