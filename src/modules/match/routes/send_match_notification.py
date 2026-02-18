from fastapi import BackgroundTasks, HTTPException

from modules.match.routes.router import emailRouter
from project_helpers.emails_handling import (
    SendEmailRequest,
    build_message,
    send_via_gmail_oauth2_safe,
    GMAIL_SENDER,
)


@emailRouter.post("-send")
async def send_email(
    req: SendEmailRequest,
    bg: BackgroundTasks,
):
    if not GMAIL_SENDER:
        raise HTTPException(status_code=500, detail="GMAIL_SENDER not configured")
    msg = build_message(req)
    bg.add_task(send_via_gmail_oauth2_safe, msg)
    return {"status": "queued"}
