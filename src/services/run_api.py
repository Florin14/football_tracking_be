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
from extensions.fastapi import run_api, api
from extensions.sqlachemy.init import init_db, DBSessionMiddleware

try:
    import logging
    from fastapi.middleware.cors import CORSMiddleware
    from extensions import run_api, api
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
    init_db()
    # init_scheduler(engine, starter_callback=auto_jobs_starter)


def shutdown():
    pass
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
