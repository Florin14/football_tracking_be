import os

from fastapi import Request
from sqlalchemy import create_engine
from sqlalchemy.orm import configure_mappers, sessionmaker
from starlette.middleware.base import BaseHTTPMiddleware

from extensions.sqlachemy.base_model import BaseModel


DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

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
