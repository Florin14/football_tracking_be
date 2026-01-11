import os
from pathlib import Path

from dotenv import load_dotenv

from fastapi import Request
from sqlalchemy import create_engine
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
    if not is_docker and (app_env == "local" or os.getenv("DATABASE_URL_LOCAL")):
        local_url = os.getenv("DATABASE_URL_LOCAL")
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
        "For APP_ENV=local, use DATABASE_URL_LOCAL or POSTGRESQL_LOCAL_*."
    )


DATABASE_URL = build_database_url()
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
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


class DBSessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request.state.db = SessionLocal()
        response = await call_next(request)
        request.state.db.close()
        return response
