# Id: fastapi.py 202305 11/05/2023
#
# backend
# Copyright (c) 2011-2013 IntegraSoft S.R.L. All rights reserved.
#
# Author: cicada
#   Rev: 202305
#   Date: 11/05/2023
#
# License description...
import logging
from typing import List
import uvicorn
from fastapi import FastAPI, APIRouter, Request
from project_helpers.error import Error
from project_helpers.responses import ErrorResponse


async def http_400_handler(request: Request, exc):
    return ErrorResponse(Error.INVALID_JSON_FORMAT, message=exc.detail)


async def http_401_handler(request: Request, exc):
    return ErrorResponse(Error.INVALID_TOKEN, message=exc.detail)


async def http_404_handler(request: Request, exc):
    return ErrorResponse(Error.SERVER_ERROR, message=exc.detail)


async def http_422_handler(request: Request, exc):
    return ErrorResponse(Error.SERVER_ERROR, message=exc.detail)


async def http_500_handler(request: Request, exc):
    return ErrorResponse(Error.SERVER_ERROR, message=exc.detail)


api = FastAPI(
    exception_handlers={
        400: http_400_handler,
        401: http_401_handler,
        404: http_404_handler,
        422: http_422_handler,
        500: http_500_handler,
    }
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


def run_api(host, port, routers: List[APIRouter], responses: dict = None):
    for route in routers:
        api.include_router(route, responses=responses)
    # uvicorn.config.LOGGING_CONFIG = None
    # uvicorn.config.LOGGING = "logging.config.dictConfig"
    # logger = logging.getLogger("uvicorn.access")
    # logger.addFilter(FilterHealthCheck())
    uvicorn.run(api, host=host, port=port, log_config=None)
