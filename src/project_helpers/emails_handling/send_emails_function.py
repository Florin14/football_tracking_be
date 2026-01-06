import base64
import os
from email.message import EmailMessage
from time import time
from typing import List, Optional, Dict, Any

import aiosmtplib
import requests
from dotenv import load_dotenv
from fastapi import HTTPException
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import BaseModel, EmailStr, Field

# ----------------- Setup & Config -----------------
load_dotenv()  # loads from .env if present

# Required env vars (no hardcoding)
DEFAULT_FROM = os.getenv("DEFAULT_FROM", "Match Notifier <no-reply@example.com>")
GMAIL_SENDER = os.getenv("GMAIL_SENDER")  # e.g. "you@gmail.com"

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REFRESH_TOKEN = os.getenv("GOOGLE_REFRESH_TOKEN")

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
TOKEN_URL = "https://oauth2  .googleapis.com/token"
def validate_config():

    if not all([GMAIL_SENDER, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN]):
        missing = [k for k, v in {
            "GMAIL_SENDER": GMAIL_SENDER,
            "GOOGLE_CLIENT_ID": GOOGLE_CLIENT_ID,
            "GOOGLE_CLIENT_SECRET": GOOGLE_CLIENT_SECRET,
            "GOOGLE_REFRESH_TOKEN": GOOGLE_REFRESH_TOKEN,
        }.items() if not v]
        raise RuntimeError(f"Missing required env vars: {', '.join(missing)}")

FROM_NAME = os.getenv("FROM_NAME", "Match Notifier")

jinja_env = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape(["html", "xml"])
)
TEMPLATE_NAME = "match_notification.html"

# ----------------- Models -----------------
class Attachment(BaseModel):
    filename: str
    content_base64: str
    mime_type: str = "application/octet-stream"

class SendEmailRequest(BaseModel):
    to: List[EmailStr] = Field(..., description="List of recipients")
    subject: str = Field(..., description="Email subject")
    cc: Optional[List[EmailStr]] = None
    bcc: Optional[List[EmailStr]] = None
    reply_to: Optional[EmailStr] = None
    attachments: Optional[List[Attachment]] = None

# ----------------- Template Rendering -----------------
def render_template(data: Dict[str, Any]) -> str:
    try:
        template = jinja_env.get_template(TEMPLATE_NAME)
        return template.render(**data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Template error: {e}")

# ----------------- Message Builder -----------------
def build_message(req: SendEmailRequest) -> EmailMessage:
    html_body = render_template({"user_name": "florin", "total": 10})
    text_body = "You have a new match. Please view this email in HTML."

    msg = EmailMessage()
    msg["Subject"] = req.subject
    msg["From"] = DEFAULT_FROM
    msg["To"] = ", ".join(req.to)
    if req.cc:
        msg["Cc"] = ", ".join(req.cc)
    if req.reply_to:
        msg["Reply-To"] = str(req.reply_to)

    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")

    if req.attachments:
        for att in req.attachments:
            try:
                data = base64.b64decode(att.content_base64)
            except Exception:
                raise HTTPException(status_code=400, detail=f"Attachment {att.filename} is not valid base64")
            maintype, _, subtype = att.mime_type.partition("/")
            if not subtype:
                maintype, subtype = "application", "octet-stream"
            msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=att.filename)

    return msg

# ----------------- OAuth2 Token Handling -----------------
_access_token_cache = {"token": None, "exp": 0}

def get_access_token() -> str:
    now = int(time())
    if _access_token_cache["token"] and now < _access_token_cache["exp"] - 30:
        return _access_token_cache["token"]

    try:
        resp = requests.post(
            TOKEN_URL,
            data={
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "refresh_token": GOOGLE_REFRESH_TOKEN,
                "grant_type": "refresh_token",
            },
            timeout=15,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Token refresh request failed: {e}")

    if not resp.ok:
        raise HTTPException(status_code=502, detail=f"Token refresh failed: {resp.text}")

    data = resp.json()
    token = data["access_token"]
    expires_in = int(data.get("expires_in", 3600))
    _access_token_cache["token"] = token
    _access_token_cache["exp"] = now + expires_in
    return token

# ----------------- SMTP Send (XOAUTH2) -----------------
async def send_via_gmail_oauth2(msg: EmailMessage):
    # Consolidate recipients (To, Cc, Bcc)
    validate_config()
    recipients = []
    for key in ("To", "Cc", "Bcc"):
        if msg.get(key):
            recipients += [x.strip() for x in msg.get(key).split(",") if x.strip()]
    # Bcc should not be transmitted as a header
    if "Bcc" in msg:
        del msg["Bcc"]

    access_token = get_access_token()

    try:
        await aiosmtplib.send(
            msg,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            start_tls=True,
            username=GMAIL_SENDER,
            # XOAUTH2 uses the access token in the "password" field
            password=access_token,
            auth_mechanism="XOAUTH2",
            timeout=30,
        )
    except aiosmtplib.errors.SMTPResponseException as e:
        detail = f"SMTP error {e.code}: {getattr(e, 'message', '')}"
        raise HTTPException(status_code=502, detail=detail)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"SMTP failed: {e}")
