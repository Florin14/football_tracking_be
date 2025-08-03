import logging
import sys

import uvicorn
from fastapi import FastAPI
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware

from extensions.sqlalchemy import init_db, DBSessionMiddleware
from modules import userRouter, matchRouter, teamRouter, playerRouter, tournamentRouter
from project_helpers.error import Error
from project_helpers.responses import ErrorResponse
from project_helpers.schemas import ErrorSchema


async def http_400_handler(request: Request, exc):
    return ErrorResponse(Error.INVALID_JSON_FORMAT, message=getattr(exc, "detail", None) or str(exc))


async def http_401_handler(request: Request, exc):
    return ErrorResponse(Error.INVALID_TOKEN, message=getattr(exc, "detail", None) or str(exc))


async def http_404_handler(request: Request, exc):
    return ErrorResponse(Error.SERVER_ERROR, message=getattr(exc, "detail", None) or str(exc))


async def http_422_handler(request: Request, exc):
    return ErrorResponse(Error.SERVER_ERROR, message=getattr(exc, "detail", None) or str(exc))


async def http_500_handler(request: Request, exc):
    return ErrorResponse(Error.SERVER_ERROR, message=getattr(exc, "detail", None) or str(exc))


# ─── 1) Create the app ─────────────────────────────────────────────────────────
api = FastAPI(
    exception_handlers={
        400: http_400_handler,
        401: http_401_handler,
        404: http_404_handler,
        422: http_422_handler,
        500: http_500_handler,
    },
    title="Football Tracking API",
    version="0.1.0",
)

# ─── 2) Install your DBSessionMiddleware at import time ────────────────────────
api.add_middleware(DBSessionMiddleware)

# ─── 3) CORS ─────────────────────────────────────────────────────────────────
api.add_middleware(
    CORSMiddleware,
    allow_origins=["*", "http://localhost:3000", "https://deploy-football-tracking-fe.onrender.com/"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── 4) Startup event (you can keep on_event or switch to lifespan) ───────────
@api.on_event("startup")
def on_startup():
    logging.basicConfig(
        format="%(asctime)s - [%(levelname)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.INFO,
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    init_db()


# ─── 5) Include routers ──────────────────────────────────────────────────────
common_responses = {
    500: {"model": ErrorSchema},
    401: {"model": ErrorSchema},
    422: {"model": ErrorSchema},
    404: {"model": ErrorSchema},
}
for router in (userRouter, matchRouter, teamRouter, playerRouter, tournamentRouter):
    api.include_router(router, responses=common_responses)


# ─── 7) Optional CLI for local dev ────────────────────────────────────────────
def main(port: int = 8002):
    uvicorn.run(api, host="0.0.0.0", port=port)


if __name__ == "__main__":
    # allow `python run_api.py` or `python run_api.py 8002`

    port = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 8002
    main(port)
