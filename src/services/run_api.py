import logging
import os
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware

from extensions.sqlalchemy import init_db, DBSessionMiddleware
from modules import authRouter, userRouter, matchRouter, teamRouter, playerRouter, tournamentRouter, rankingRouter, emailRouter, notificationsRouter
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


def parse_allowed_origins() -> list[str]:
    raw = os.getenv("ALLOWED_ORIGINS", "*").strip()
    if raw == "*":
        return ["*"]
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


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
    yield


# â”€â”€â”€ 1) Create the app â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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
    lifespan=lifespan,
)

# â”€â”€â”€ 2) Install your DBSessionMiddleware at import time â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
api.add_middleware(DBSessionMiddleware)



# â”€â”€â”€ 3) CORS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
api.add_middleware(
    CORSMiddleware,
    allow_origins=parse_allowed_origins(),
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
for router in (userRouter, matchRouter, teamRouter, playerRouter, tournamentRouter, rankingRouter, emailRouter, notificationsRouter, authRouter):
    api.include_router(router, responses=common_responses)


# â”€â”€â”€ 7) Optional CLI for local dev â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 8000
    uvicorn.run("services.run_api:api", host="0.0.0.0", port=port, reload=True, app_dir="src")


if __name__ == "__main__":
    main()



