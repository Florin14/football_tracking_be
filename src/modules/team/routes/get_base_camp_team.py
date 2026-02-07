from fastapi import Depends
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from extensions.sqlalchemy import get_db
from modules.attendance.models.attendance_model import AttendanceModel
from modules.team.models import TeamModel, TeamResponse
from .router import router


@router.get("/base-camp", response_model=TeamResponse)
async def get_base_camp_team(db: Session = Depends(get_db)):
    team = db.query(TeamModel).options(joinedload(TeamModel.players)).filter(
        TeamModel.isDefault.is_(True)
    ).first()

    if not team:
        team = TeamModel(
            name="FC Base Camp",
            description="The default team for the Base Camp football club",
            isDefault=True  # Assuming you want to mark it as default
        )
        db.add(team)
        db.commit()
        db.refresh(team)

    if team.players:
        player_ids = [player.id for player in team.players]
        attendance_counts = {}
        if player_ids:
            attendance_counts = dict(
                db.query(AttendanceModel.playerId, func.count(AttendanceModel.id))
                .filter(AttendanceModel.playerId.in_(player_ids))
                .group_by(AttendanceModel.playerId)
                .all()
            )

        for player in team.players:
            player.appearances = int(attendance_counts.get(player.id, 0))

    return team
