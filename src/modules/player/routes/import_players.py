import logging
from io import BytesIO

import pandas as pd
from fastapi import BackgroundTasks, Depends, UploadFile
from sqlalchemy.orm import Session

from extensions import get_db
from constants.platform_roles import PlatformRoles
from modules.player.models.player_model import PlayerModel
from project_helpers.dependencies import JwtRequired
from project_helpers.emails_handling import (
    SendEmailRequest as EmailSendRequest,
    build_message,
    send_via_gmail_oauth2_safe,
    validate_config,
    FRONTEND_URL,
)
from project_helpers.responses import ConfirmationResponse
from .router import router


@router.post("-import", response_model=ConfirmationResponse, dependencies=[Depends(JwtRequired(roles=[PlatformRoles.ADMIN]))])
async def import_players(
    file: UploadFile,
    bg: BackgroundTasks,
    db: Session = Depends(get_db),
):
    password = "fotbal@2025"
    contents = await file.read()
    df = pd.read_excel(BytesIO(contents), sheet_name="Sheet1")

    has_email_column = "Email" in df.columns

    players = []
    for index, row in df.iterrows():
        email = row["Email"] if has_email_column and pd.notna(row.get("Email")) else f"player{index}@generated.local"
        player = PlayerModel(
            name=row["Name"],
            rating=row["Value"],
            position=row["Position"].upper(),
            email=email,
            password=password,
            role=PlatformRoles.PLAYER,
        )
        players.append(player)

    db.add_all(players)
    db.commit()

    email_enabled = False
    try:
        validate_config()
        email_enabled = True
    except RuntimeError as exc:
        logging.warning("Welcome emails not sent for import: %s", exc)

    if email_enabled:
        for player in players:
            if player.email and not player.email.endswith("@generated.local"):
                template_data = {
                    "player_name": player.name,
                    "email": player.email,
                    "password": password,
                    "platform_url": FRONTEND_URL,
                }
                email_req = EmailSendRequest(
                    to=[player.email],
                    subject="Welcome to Football Tracking!",
                )
                msg = build_message(email_req, template_data=template_data, template_name="welcome_player.html")
                bg.add_task(send_via_gmail_oauth2_safe, msg)

    return ConfirmationResponse()

