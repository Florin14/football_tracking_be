import csv

from fastapi import UploadFile
from sqlalchemy.orm import Session

from modules.player.models.player_model import PlayerModel
from .router import router


# @router.post("-import")
# async def import_players(file: UploadFile, db: Session):
#     contents = file.file.read().decode("utf-8").splitlines()
#     reader = csv.DictReader(contents)
#     players = []
#     for row in reader:
#         player = PlayerModel(name=row["name"], position=row["position"], rating=row["rating"])
#         players.append(player)
#
#     db.add_all(players)
#     db.commit()
#     return {"message": "Players imported successfully"}
