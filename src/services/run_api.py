# Id: fast_api.py 202305 10/05/2023
#
# backend
# Copyright (c) 2011-2013 IntegraSoft S.R.L. All rights reserved.
#
# Author: cicada
#   Rev: 202305
#   Date: 10/05/2023
#
# License description...

import os
import sys
from argparse import Namespace

from alembic import command
from alembic.config import Config
from sqlalchemy import text

from extensions.sqlalchemy import SessionLocal

try:
    import logging
    from fastapi.middleware.cors import CORSMiddleware
    from extensions import run_api, api, init_db, DBSessionMiddleware, SqlBaseModel
    from modules import (
        userRouter,
        matchRouter,
        teamRouter,
        playerRouter,
    )
    from project_helpers.schemas import ErrorSchema

except Exception as e:
    logging.error(str(e))
    exit(1)


def startup():
    streamHandler = logging.StreamHandler(sys.stdout)

    handlers = [
        streamHandler
    ]
    logging.basicConfig(format='%(asctime)s - [%(levelname)s]: %(message)s (%(pathname)s:%(lineno)d)',
                        datefmt='%Y-%m-%d %H:%M:%S',
                        level="INFO", handlers=handlers)
    init_db()


#     # init_scheduler(engine, starter_callback=auto_jobs_starter)
#
#
# def shutdown():
#     pass
# scheduler.shutdown()

if __name__ == "__main__":
    try:
        api.add_event_handler("startup", startup)
        api.add_event_handler("shutdown", startup)
        api.add_middleware(DBSessionMiddleware)
        api.add_middleware(
            CORSMiddleware,
            allow_origins=[
                "*",
                "http://localhost:3000",
            ],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        run_api(
            host="localhost",
            port=8002,
            routers=[
                userRouter,
                matchRouter,
                teamRouter,
                playerRouter,
            ],
            responses={
                500: {"model": ErrorSchema},
                401: {"model": ErrorSchema},
                422: {"model": ErrorSchema},
                404: {"model": ErrorSchema},
            },
        )
    except Exception as e:
        logging.error(str(e))
        exit(1)
