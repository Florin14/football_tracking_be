import csv
from io import TextIOWrapper, BytesIO

import pandas as pd
from fastapi import Depends
from fastapi import UploadFile
from sqlalchemy.orm import Session

from extensions import get_db
from constants.platform_roles import PlatformRoles
from modules.player.models.player_model import PlayerModel
from project_helpers.dependencies import JwtRequired
from project_helpers.responses import ConfirmationResponse
from .router import router


@router.post("-import", response_model=ConfirmationResponse, dependencies=[Depends(JwtRequired(roles=[PlatformRoles.ADMIN]))])
async def import_players(
    file: UploadFile,
    db: Session = Depends(get_db),
):
    # decoded_file = TextIOWrapper(file.file, encoding="utf-8", errors="replace")
    # reader = csv.DictReader(decoded_file)
    password = "fotbal@2025"
    contents = await file.read()
    df = pd.read_excel(BytesIO(contents), sheet_name="Sheet1")

    players = []
    index = 0
    for _, row in df.iterrows():
        player = PlayerModel(
            name=row["Name"],
            rating=row["Value"],
            position=row["Position"].upper(),
            # email=row["Email"]
            email=f"cont{index}@gmail.com",
            password=password,
            role=PlatformRoles.PLAYER,
        )
        players.append(player)
        index += 1

    db.add_all(players)
    db.commit()
    return ConfirmationResponse
