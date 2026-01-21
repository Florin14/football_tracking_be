import logging
import uvicorn
from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import DataError, DBAPIError, IntegrityError, OperationalError, ProgrammingError, SQLAlchemyError
from project_helpers.error import Error
from project_helpers.exceptions import ErrorException
from project_helpers.responses import ErrorResponse


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


api = FastAPI(
    exception_handlers={
        ErrorException: error_exception_handler,
        HTTPException: http_exception_handler,
        RequestValidationError: validation_exception_handler,
        SQLAlchemyError: sqlalchemy_exception_handler,
        Exception: unhandled_exception_handler,
    },
)


class FilterHealthCheck(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if "/health" in record.getMessage() or "OPTIONS" in record.getMessage():
            return False
        return True


@api.get(
    "/-/health",
    tags=["Healthy Check"],
    summary="Healthy check use by load balancer service to check if the api-service is healty",
)
def health():
    return "ok"


def run_api(host, port, routers, responses: dict = None):
    for route in routers:
        api.include_router(route, responses=responses)
    uvicorn.config.LOGGING_CONFIG = None
    uvicorn.config.LOGGING = "logging.config.dictConfig"
    uvicorn.run(api, host=host, port=port, log_config=None)
