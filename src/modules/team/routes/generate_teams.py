from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

router = APIRouter()

@router.post("/generate-teams/")
def create_teams(player_ids: list[int], db: Session = Depends(get_db)):
    players = db.query(Player).filter(Player.id.in_(player_ids)).all()
    team1, team2 = generate_teams(players)
    return {"team1": [p.name for p in team1], "team2": [p.name for p in team2]}