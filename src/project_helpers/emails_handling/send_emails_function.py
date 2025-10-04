import base64
import os
import webbrowser
from email.message import EmailMessage
from time import time
from typing import List, Optional, Dict, Any
from urllib.parse import urlencode

import aiosmtplib
import requests
from dotenv import load_dotenv
from fastapi import HTTPException
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import BaseModel, EmailStr, Field

DEFAULT_FROM = "Zimbru Florin <zimbru.florin.4@gmail.com>"
GMAIL_USERNAME = "zimbru.florin.4@gmail.com"
GMAIL_APP_PASSWORD = "REDACTED_GMAIL_APP_PASSWORD"
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
CLIENT_ID = "REDACTED_GOOGLE_CLIENT_ID"
CLIENT_SECRET = "REDACTED_GOOGLE_CLIENT_SECRET"
REDIRECT_URI = "urn:ietf:wg:oauth:2.0:oob"

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPE = "https://mail.google.com/"

params = {
    "client_id": CLIENT_ID,
    "redirect_uri": REDIRECT_URI,
    "response_type": "code",
    "access_type": "offline",
    "prompt": "consent",
    "scope": SCOPE,
}
webbrowser.open(f"{AUTH_URL}?{urlencode(params)}")
print("After granting, paste the 'code' here:")
code = input("> ").strip()
load_dotenv()


def get_refresh_token():
    resp = requests.post(TOKEN_URL, data={
        "code": code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    })
    resp.raise_for_status()
    data = resp.json()

    return data.get("refresh_token")


FROM_NAME = os.getenv("FROM_NAME", "Match Notifier")
GMAIL_SENDER = "zimbru.florin.4@gmail.com"

GOOGLE_CLIENT_ID = "REDACTED_GOOGLE_CLIENT_ID"
GOOGLE_CLIENT_SECRET = "REDACTED_GOOGLE_CLIENT_SECRET"
GOOGLE_REFRESH_TOKEN = get_refresh_token()
TOKEN_URL = "https://oauth2.googleapis.com/token"

if not all([GMAIL_SENDER, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN]):
    raise RuntimeError("Missing Gmail OAuth2 env vars")

jinja_env = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape(["html", "xml"])
)
TEMPLATE_NAME = "match_notification.html"


# --- Models ---
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


def render_template(data: Dict[str, Any]) -> str:
    try:
        template = jinja_env.get_template(TEMPLATE_NAME)
        return template.render(**data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Template error: {e}")


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


_access_token_cache = {"token": None, "exp": 0}


def get_access_token() -> str:
    # simple in-process cache (expires slightly early)
    now = int(time())
    if _access_token_cache["token"] and now < _access_token_cache["exp"] - 30:
        return _access_token_cache["token"]

    resp = requests.post(TOKEN_URL, data={
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "refresh_token": GOOGLE_REFRESH_TOKEN,
        "grant_type": "refresh_token",
    }, timeout=15)
    if not resp.ok:
        raise HTTPException(status_code=500, detail=f"Token refresh failed: {resp.text}")
    data = resp.json()
    token = data["access_token"]
    expires_in = data.get("expires_in", 3600)
    _access_token_cache["token"] = token
    _access_token_cache["exp"] = now + int(expires_in)
    return token


async def send_via_gmail_oauth2(msg: EmailMessage):
    recipients = []
    for key in ("To", "Cc", "Bcc"):
        if msg.get(key):
            recipients += [x.strip() for x in msg.get(key).split(",") if x.strip()]
    if "Bcc" in msg:
        del msg["Bcc"]

    access_token = get_access_token()

    # aiosmtplib supports XOAUTH2 by passing the token as "password"
    # with auth_mechanism="XOAUTH2"
    try:
        await aiosmtplib.send(
            msg,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            start_tls=True,
            username=GMAIL_SENDER,
            password=access_token,
            auth_mechanism="XOAUTH2",
            timeout=30,
        )
    except aiosmtplib.errors.SMTPResponseException as e:
        detail = f"SMTP error {e.code}: {getattr(e, 'message', '')}"
        raise HTTPException(status_code=502, detail=detail)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"SMTP failed: {e}")
