import base64
import logging
import os
from email.message import EmailMessage
from pathlib import Path
from time import time
from typing import List, Optional, Dict, Any

import aiosmtplib
import requests
from dotenv import load_dotenv
from fastapi import HTTPException
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import BaseModel, EmailStr, Field

# ----------------- Setup & Config -----------------
ROOT_DIR = Path(__file__).resolve().parents[3]
load_dotenv(ROOT_DIR / ".env", override=False)
load_dotenv(ROOT_DIR / ".env.local", override=False)

# Required env vars (no hardcoding)
DEFAULT_FROM = os.getenv("DEFAULT_FROM", "Match Notifier <no-reply@example.com>")
GMAIL_SENDER = os.getenv("GMAIL_SENDER")  # e.g. "you@gmail.com"

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REFRESH_TOKEN = os.getenv("GOOGLE_REFRESH_TOKEN")

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))

TOKEN_URL = "https://oauth2.googleapis.com/token"

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
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

TEMPLATE_DIR = Path(__file__).resolve().parents[3] / "templates"
jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=select_autoescape(["html", "xml"])
)
TEMPLATE_NAME = "match_notification.html"
DEFAULT_TEMPLATE_DATA = {
    "lang": "ro",
    "team1_name": "Echipa 1",
    "team2_name": "Echipa 2",
    "team1_logo": None,
    "team2_logo": None,
    "match_datetime": "De stabilit",
    "location": "De stabilit",
    "league_name": "De stabilit",
    "round": None,
    "match_url": None,
    "base_camp_logo": None,
    "platform_url": FRONTEND_URL,
}

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
def render_template(data: Dict[str, Any], template_name: str = TEMPLATE_NAME) -> str:
    try:
        template = jinja_env.get_template(template_name)
        return template.render(**data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Template error: {e}")

# ----------------- Message Builder -----------------
def build_message(
    req: SendEmailRequest,
    template_data: Optional[Dict[str, Any]] = None,
    template_name: Optional[str] = None,
) -> EmailMessage:
    if template_name:
        data = template_data or {}
        html_body = render_template(data, template_name=template_name)
        text_body = "Please view this email in an HTML-capable client."
    else:
        data = DEFAULT_TEMPLATE_DATA.copy()
        if template_data:
            data.update({key: value for key, value in template_data.items() if value is not None})
        html_body = render_template(data)
        text_body = "You have a new match. Please view this email in HTML."
    logging.info("Building email with subject '%s' for recipients: %s, cc: %s, reply_to: %s, attachments: %d", req.subject, req.to, req.cc or [], req.reply_to or [], len(req.attachments or []))

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

    # Build the XOAUTH2 SASL string: user=<email>\x01auth=Bearer <token>\x01\x01
    xoauth2_string = f"user={GMAIL_SENDER}\x01auth=Bearer {access_token}\x01\x01"
    xoauth2_b64 = base64.b64encode(xoauth2_string.encode()).decode()

    try:
        smtp = aiosmtplib.SMTP(
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            start_tls=True,
            timeout=30,
        )
        await smtp.connect()
        await smtp.execute_command(b"AUTH", b"XOAUTH2 " + xoauth2_b64.encode())
        await smtp.send_message(msg)
    except aiosmtplib.errors.SMTPResponseException as e:
        detail = f"SMTP error {e.code}: {getattr(e, 'message', '')}"
        raise HTTPException(status_code=502, detail=detail)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"SMTP failed: {e}")

async def send_via_gmail_oauth2_safe(msg: EmailMessage):
    try:
        await send_via_gmail_oauth2(msg)
    except Exception as exc:
        logging.exception("Email send failed: %s", exc)


# ----------------- High-Level Helpers -----------------
def _get_base_camp_logo(db) -> Optional[str]:
    from modules.team.models.team_model import TeamModel
    default_team = db.query(TeamModel).filter(TeamModel.isDefault.is_(True)).first()
    if default_team and default_team.logo:
        return base64.b64encode(default_team.logo).decode("utf-8")
    return None


def send_welcome_email(bg, db, player, password: str = "fotbal@2025"):
    """Queue a welcome email for a player. Skips generated emails and missing config."""
    if not player.email or player.email.endswith("@generated.local"):
        return

    try:
        validate_config()
    except RuntimeError as exc:
        logging.warning("Welcome email not sent for player %s: %s", player.id, exc)
        return

    from modules.player.models.player_preferences_model import PlayerPreferencesModel
    prefs = db.query(PlayerPreferencesModel).filter(PlayerPreferencesModel.playerId == player.id).first()
    lang = prefs.preferredLanguage.value.lower() if prefs and prefs.preferredLanguage else "ro"

    base_camp_logo = _get_base_camp_logo(db)
    subject = "Welcome to Base Camp Football!" if lang == "en" else "Bine ai venit la Base Camp Football!"
    template_data = {
        "lang": lang,
        "player_name": player.name,
        "email": player.email,
        "password": password,
        "platform_url": FRONTEND_URL,
        "base_camp_logo": base_camp_logo,
    }
    email_req = SendEmailRequest(to=[player.email], subject=subject)
    msg = build_message(email_req, template_data=template_data, template_name="welcome_player.html")
    bg.add_task(send_via_gmail_oauth2_safe, msg)


def send_match_notification_emails(bg, db, match, lang_groups: Dict[str, List[str]]):
    """Queue match notification emails grouped by language. Skips if no recipients or missing config."""
    if not lang_groups:
        return

    try:
        validate_config()
    except RuntimeError as exc:
        logging.warning("Email not sent for match %s: %s", match.id, exc)
        return

    base_camp_logo = _get_base_camp_logo(db)
    team1_logo = base64.b64encode(match.team1.logo).decode("utf-8") if match.team1.logo else None
    team2_logo = base64.b64encode(match.team2.logo).decode("utf-8") if match.team2.logo else None
    match_url = f"{FRONTEND_URL}/matches/{match.id}"

    for lang, emails in lang_groups.items():
        if lang == "en":
            fmt_datetime = match.timestamp.strftime("%A, %B %d, %Y at %H:%M")
            subject = f"New match: {match.team1.name} vs {match.team2.name}"
        else:
            days_ro = ["Luni", "Marti", "Miercuri", "Joi", "Vineri", "Sambata", "Duminica"]
            months_ro = ["", "ianuarie", "februarie", "martie", "aprilie", "mai", "iunie",
                         "iulie", "august", "septembrie", "octombrie", "noiembrie", "decembrie"]
            dt = match.timestamp
            fmt_datetime = f"{days_ro[dt.weekday()]}, {dt.day} {months_ro[dt.month]} {dt.year}, ora {dt.strftime('%H:%M')}"
            subject = f"Meci nou: {match.team1.name} vs {match.team2.name}"

        template_data = {
            "lang": lang,
            "team1_name": match.team1.name,
            "team2_name": match.team2.name,
            "team1_logo": team1_logo,
            "team2_logo": team2_logo,
            "match_datetime": fmt_datetime,
            "location": match.location or ("TBD" if lang == "en" else "De stabilit"),
            "league_name": match.league.name if match.league else ("TBD" if lang == "en" else "De stabilit"),
            "round": match.round,
            "match_url": match_url,
            "base_camp_logo": base_camp_logo,
            "platform_url": FRONTEND_URL,
        }
        email_req = SendEmailRequest(to=sorted(emails), subject=subject)
        msg = build_message(email_req, template_data=template_data)
        bg.add_task(send_via_gmail_oauth2_safe, msg)
