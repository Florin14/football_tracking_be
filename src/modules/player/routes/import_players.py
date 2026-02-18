from io import BytesIO

import pandas as pd
from fastapi import BackgroundTasks, Depends, UploadFile
from sqlalchemy.orm import Session

from extensions import get_db
from constants.platform_roles import PlatformRoles
from modules.player.models.player_model import PlayerModel
from project_helpers.dependencies import JwtRequired
from project_helpers.emails_handling import send_welcome_email
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

    for player in players:
        send_welcome_email(bg, db, player, password)

    return ConfirmationResponse()

