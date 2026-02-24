import logging
import os
import re
from pathlib import Path

from dotenv import load_dotenv

from fastapi import Request
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker, configure_mappers
from starlette.middleware.base import BaseHTTPMiddleware

from .base_model import BaseModel

load_dotenv(".env", override=False)
local_env_path = Path(".env.local")
is_docker = Path("/.dockerenv").exists()
if not is_docker and local_env_path.exists():
    load_dotenv(local_env_path, override=True)


def build_database_url() -> str:
    app_env = os.getenv("APP_ENV", "").strip().lower()
    is_docker = Path("/.dockerenv").exists()
    if not is_docker and (app_env == "local" or os.getenv("DATABASE_URL")):
        local_url = os.getenv("DATABASE_URL")
        if local_url:
            return local_url

        host = os.getenv("POSTGRESQL_LOCAL_HOST") or os.getenv("POSTGRESQL_HOST")
        database = os.getenv("POSTGRESQL_LOCAL_DATABASE") or os.getenv("POSTGRESQL_DATABASE")
        username = os.getenv("POSTGRESQL_LOCAL_USERNAME") or os.getenv("POSTGRESQL_USERNAME")
        password = os.getenv("POSTGRESQL_LOCAL_PASSWORD") or os.getenv("POSTGRESQL_PASSWORD")
        port = os.getenv("POSTGRESQL_LOCAL_PORT") or os.getenv("POSTGRESQL_PORT", "5432")
        if all([host, database, username, password]):
            return f"postgresql+psycopg2://{username}:{password}@{host}:{port}/{database}"

    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url

    host = os.getenv("POSTGRESQL_HOST")
    database = os.getenv("POSTGRESQL_DATABASE")
    username = os.getenv("POSTGRESQL_USERNAME")
    password = os.getenv("POSTGRESQL_PASSWORD")
    port = os.getenv("POSTGRESQL_PORT", "5432")
    if all([host, database, username, password]):
        return f"postgresql+psycopg2://{username}:{password}@{host}:{port}/{database}"

    raise RuntimeError(
        "DATABASE_URL or POSTGRESQL_* env vars are required. "
        "For APP_ENV=local, use DATABASE_URL or POSTGRESQL_LOCAL_*."
    )


DATABASE_URL = build_database_url()
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    pool_recycle=300,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class DBSession:
    def __enter__(self):
        self.db = SessionLocal()
        return self.db

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.db:
            self.db.close()


def init_db():
    configure_mappers()
    BaseModel.metadata.create_all(bind=engine)


def get_db(request: Request):
    return request.state.db


_SAFE_IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]{0,62}$")


def _resolve_tenant(db, tenant_slug: str):
    """Lookup tenant by slug in public.tenants and return the row or None."""
    from modules.tenant.models.tenant_model import TenantModel
    return (
        db.query(TenantModel)
        .filter(TenantModel.slug == tenant_slug, TenantModel.is_active.is_(True))
        .first()
    )


class DBSessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        db = SessionLocal()
        request.state.db = db
        request.state.tenant = None

        tenant_slug = request.headers.get("x-tenant")
        if tenant_slug and _SAFE_IDENTIFIER.match(tenant_slug):
            tenant = _resolve_tenant(db, tenant_slug)
            if tenant:
                request.state.tenant = tenant
                schema = tenant.schema_name
                if _SAFE_IDENTIFIER.match(schema):
                    db.execute(text(f'SET search_path TO "{schema}", public'))

        try:
            response = await call_next(request)
        except OperationalError:
            logging.warning("DB connection lost, retrying with fresh session")
            db.close()
            engine.dispose()
            db = SessionLocal()
            request.state.db = db
            response = await call_next(request)
        finally:
            db.close()
        return response
