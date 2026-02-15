from typing import List, Optional

from fastapi import BackgroundTasks, HTTPException
from pydantic import EmailStr, Field

from modules.match.routes.router import emailRouter
from project_helpers.emails_handling import build_message, send_via_gmail_oauth2_safe, validate_config
from project_helpers.schemas import BaseSchema


class Attachment(BaseSchema):
    filename: str
    content_base64: str
    mime_type: str = "application/octet-stream"


class SendEmailRequest(BaseSchema):
    to: List[EmailStr] = Field(..., description="List of recipients")
    subject: str = Field(..., description="Email subject")
    cc: Optional[List[EmailStr]] = None
    bcc: Optional[List[EmailStr]] = None
    reply_to: Optional[EmailStr] = None
    attachments: Optional[List[Attachment]] = None


@emailRouter.post("-send")
async def send_email(
    req: SendEmailRequest,
    bg: BackgroundTasks,
):
    try:
        validate_config()
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    msg = build_message(req)
    bg.add_task(send_via_gmail_oauth2_safe, msg)
    return {"status": "queued"}
