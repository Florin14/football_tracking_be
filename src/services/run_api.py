import logging
import os
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import DataError, DBAPIError, IntegrityError, OperationalError, ProgrammingError, SQLAlchemyError

from extensions.auth_jwt import AuthJWT
from extensions.sqlalchemy import init_db, DBSessionMiddleware, SessionLocal
from modules import authRouter, attendanceRouter, userRouter, matchRouter, adminRouter, teamRouter, playerRouter, tournamentRouter, rankingRouter, emailRouter, notificationsRouter, trainingRouter
from modules.attendance.events import backfill_attendance_for_existing_scopes
from modules.user.models.user_model import UserModel
from modules.admin.models.admin_model import AdminModel
from project_helpers.error import Error
from project_helpers.exceptions import ErrorException
from project_helpers.responses import ErrorResponse
from project_helpers.schemas import ErrorSchema


def _safe_exc_message(exc: Exception) -> str:
    if hasattr(exc, "detail") and getattr(exc, "detail"):
        return str(getattr(exc, "detail"))
    return str(exc) if str(exc) else exc.__class__.__name__


def _validation_fields(exc: RequestValidationError) -> list[str]:
    fields: list[str] = []
    for err in exc.errors():
        loc = ".".join(str(p) for p in err.get("loc", []) if p is not None)
        msg = err.get("msg")
        if loc and msg:
            fields.append(f"{loc}: {msg}")
        elif loc:
            fields.append(loc)
        elif msg:
            fields.append(msg)
    return fields


async def error_exception_handler(request: Request, exc: ErrorException):
    return ErrorResponse(
        exc.error,
        statusCode=getattr(exc, "statusCode", 500),
        message=getattr(exc, "message", None),
        fields=getattr(exc, "fields", None),
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    status_code = exc.status_code or 500
    if status_code == 400:
        error = Error.INVALID_JSON_FORMAT
    elif status_code == 401:
        error = Error.INVALID_TOKEN
    elif status_code == 422:
        error = Error.INVALID_QUERY_FORMAT
    else:
        error = Error.SERVER_ERROR
    return ErrorResponse(error, statusCode=status_code, message=_safe_exc_message(exc))


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return ErrorResponse(
        Error.INVALID_QUERY_FORMAT,
        statusCode=422,
        message="Validation error",
        fields=_validation_fields(exc),
    )


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    message = _safe_exc_message(exc)
    if isinstance(exc, DBAPIError) and getattr(exc, "orig", None):
        message = _safe_exc_message(exc.orig)
    if isinstance(exc, IntegrityError):
        error = Error.DB_INSERT_ERROR
    elif isinstance(exc, DataError):
        error = Error.DB_INSERT_ERROR
    elif isinstance(exc, (OperationalError, ProgrammingError, DBAPIError)):
        error = Error.DB_ACCESS_ERROR
    else:
        error = Error.DB_ACCESS_ERROR
    logging.exception("SQLAlchemy error during request")
    return ErrorResponse(error, statusCode=500, message=message)


async def unhandled_exception_handler(request: Request, exc: Exception):
    logging.exception("Unhandled exception during request")
    return ErrorResponse(Error.SERVER_ERROR, statusCode=500, message=_safe_exc_message(exc))


def parse_allowed_origins() -> list[str]:
    raw = os.getenv("ALLOWED_ORIGINS", "*").strip()
    if raw == "*":
        return ["*"]
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def _get_jwt_config() -> list[tuple[str, str | list[str] | None]]:
    token_location = os.getenv("AUTHJWT_TOKEN_LOCATION")
    if token_location:
        locations = [item.strip() for item in token_location.split(",") if item.strip()]
    else:
        locations = None
    return [
        ("AUTHJWT_SECRET_KEY", os.getenv("AUTHJWT_SECRET_KEY")),
        ("AUTHJWT_TOKEN_LOCATION", locations),
    ]


def _ensure_default_admin_user(db: SessionLocal) -> None:
    default_email = "admin@gmail.com"
    exists = db.query(UserModel).filter(UserModel.email == default_email).first()
    if exists:
        return
    admin = AdminModel(
        name="Admin",
        email=default_email,
        password="parola1234",
    )
    db.add(admin)
    db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup logic
    logging.basicConfig(
        format="%(asctime)s - [%(levelname)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.INFO,
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    init_db()
    db = SessionLocal()
    try:
        backfill_attendance_for_existing_scopes(db)
        _ensure_default_admin_user(db)
    finally:
        db.close()
    yield


# â”€â”€â”€ 1) Create the app â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
api = FastAPI(
    exception_handlers={
        ErrorException: error_exception_handler,
        HTTPException: http_exception_handler,
        RequestValidationError: validation_exception_handler,
        SQLAlchemyError: sqlalchemy_exception_handler,
        Exception: unhandled_exception_handler,
    },
    title="Football Tracking API",
    version="0.1.0",
    lifespan=lifespan,
)

AuthJWT.load_config(_get_jwt_config)
_allowed_origins = parse_allowed_origins()


@api.middleware("http")
async def force_cors_headers(request: Request, call_next):
    response = await call_next(request)
    origin = request.headers.get("origin")
    if origin:
        if "*" in _allowed_origins or origin in _allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Vary"] = "Origin"
            response.headers["Access-Control-Allow-Credentials"] = "true"
    return response

# â”€â”€â”€ 2) Install your DBSessionMiddleware at import time â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
api.add_middleware(DBSessionMiddleware)



# â”€â”€â”€ 3) CORS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
api.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@api.get("/health")
def health():
    return {"status": "ok"}


# â”€â”€â”€ 4) Startup event (you can keep on_event or switch to lifespan) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# â”€â”€â”€ 5) Include routers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
common_responses = {
    500: {"model": ErrorSchema},
    401: {"model": ErrorSchema},
    422: {"model": ErrorSchema},
    404: {"model": ErrorSchema},
}
for router in (userRouter, adminRouter, matchRouter, teamRouter, playerRouter, tournamentRouter, rankingRouter, emailRouter, notificationsRouter, attendanceRouter, trainingRouter, authRouter):
    api.include_router(router, responses=common_responses)


# â”€â”€â”€ 7) Optional CLI for local dev â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 8000
    uvicorn.run("services.run_api:api", host="0.0.0.0", port=port, reload=True, app_dir="src")


if __name__ == "__main__":
    main()



