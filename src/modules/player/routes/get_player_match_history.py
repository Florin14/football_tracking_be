"""Return all Base Camp matches with player-specific stats (attendance, goals, assists, cards)."""
from __future__ import annotations

from typing import List, Optional

from fastapi import Depends
from pydantic import BaseModel as PydanticBaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from constants.attendance_scope import AttendanceScope
from constants.attendance_status import AttendanceStatus
from constants.card_type import CardType
from constants.match_state import MatchState
from extensions import get_db
from modules.attendance.models.attendance_model import AttendanceModel
from modules.match.models.card_model import CardModel
from modules.match.models.goal_model import GoalModel
from modules.match.models.match_model import MatchModel
from modules.player.models.player_model import PlayerModel
from modules.team.models.team_model import TeamModel
from project_helpers.dependencies import JwtRequired
from .router import router


# --- Response schemas ---

class PlayerMatchGoal(PydanticBaseModel):
    minute: Optional[int] = None
    isAssist: bool = False


class PlayerMatchCard(PydanticBaseModel):
    cardType: str  # "YELLOW" or "RED"
    minute: Optional[int] = None


class PlayerMatchHistoryItem(PydanticBaseModel):
    matchId: int
    date: str
    team1Name: str
    team2Name: str
    scoreTeam1: Optional[int] = None
    scoreTeam2: Optional[int] = None
    isFinished: bool
    baseCampSide: Optional[str] = None  # "team1" or "team2"
    result: Optional[str] = None  # "W", "D", "L" or None
    leagueName: Optional[str] = None
    location: Optional[str] = None
    attendanceStatus: Optional[str] = None  # "PRESENT", "ABSENT", etc.
    goals: List[PlayerMatchGoal] = []
    cards: List[PlayerMatchCard] = []


class PlayerMatchHistoryResponse(PydanticBaseModel):
    matches: List[PlayerMatchHistoryItem]


# --- Endpoint ---

@router.get(
    "/{id:int}/match-history",
    response_model=PlayerMatchHistoryResponse,
    dependencies=[Depends(JwtRequired())],
)
async def get_player_match_history(id: int, db: Session = Depends(get_db)):
    """Get all Base Camp matches (past) with player-specific stats."""
    player = db.query(PlayerModel).filter(PlayerModel.id == id).first()
    if not player:
        return PlayerMatchHistoryResponse(matches=[])

    # Find Base Camp team (the default team)
    base_camp = db.query(TeamModel).filter(TeamModel.isDefault.is_(True)).first()
    if not base_camp:
        base_camp = db.query(TeamModel).first()
    if not base_camp:
        return PlayerMatchHistoryResponse(matches=[])

    bc_id = base_camp.id

    # Fetch all matches involving Base Camp, ordered most recent first
    matches = (
        db.query(MatchModel)
        .filter(or_(MatchModel.team1Id == bc_id, MatchModel.team2Id == bc_id))
        .order_by(MatchModel.timestamp.desc())
        .all()
    )

    if not matches:
        return PlayerMatchHistoryResponse(matches=[])

    match_ids = [m.id for m in matches]

    # Batch-fetch player attendance for all these matches
    attendance_rows = (
        db.query(AttendanceModel)
        .filter(
            AttendanceModel.playerId == id,
            AttendanceModel.scope == AttendanceScope.MATCH,
            AttendanceModel.matchId.in_(match_ids),
        )
        .all()
    )
    attendance_map = {a.matchId: a.status.value if a.status else None for a in attendance_rows}

    # Batch-fetch player goals (scored + assists)
    goal_rows = (
        db.query(GoalModel)
        .filter(
            GoalModel.matchId.in_(match_ids),
            or_(GoalModel.playerId == id, GoalModel.assistPlayerId == id),
        )
        .all()
    )
    # Group by match
    goals_map: dict[int, list] = {}
    for g in goal_rows:
        mid = g.matchId
        if mid not in goals_map:
            goals_map[mid] = []
        if g.playerId == id:
            goals_map[mid].append(PlayerMatchGoal(minute=g.minute, isAssist=False))
        if g.assistPlayerId == id:
            goals_map[mid].append(PlayerMatchGoal(minute=g.minute, isAssist=True))

    # Batch-fetch player cards
    card_rows = (
        db.query(CardModel)
        .filter(
            CardModel.matchId.in_(match_ids),
            CardModel.playerId == id,
        )
        .all()
    )
    cards_map: dict[int, list] = {}
    for c in card_rows:
        mid = c.matchId
        if mid not in cards_map:
            cards_map[mid] = []
        cards_map[mid].append(PlayerMatchCard(
            cardType=c.cardType.value if c.cardType else "YELLOW",
            minute=c.minute,
        ))

    # Build response
    items = []
    for m in matches:
        is_finished = (
            m.state == MatchState.FINISHED
            or (m.scoreTeam1 is not None and m.scoreTeam2 is not None)
        )

        bc_side = "team1" if m.team1Id == bc_id else "team2"

        result = None
        if is_finished and m.scoreTeam1 is not None and m.scoreTeam2 is not None:
            bc_score = m.scoreTeam1 if bc_side == "team1" else m.scoreTeam2
            opp_score = m.scoreTeam2 if bc_side == "team1" else m.scoreTeam1
            if bc_score > opp_score:
                result = "W"
            elif bc_score < opp_score:
                result = "L"
            else:
                result = "D"

        att_status = attendance_map.get(m.id)

        items.append(PlayerMatchHistoryItem(
            matchId=m.id,
            date=m.timestamp.isoformat(),
            team1Name=m.team1.name if m.team1 else "N/A",
            team2Name=m.team2.name if m.team2 else "N/A",
            scoreTeam1=m.scoreTeam1,
            scoreTeam2=m.scoreTeam2,
            isFinished=is_finished,
            baseCampSide=bc_side,
            result=result,
            leagueName=m.league.name if m.league else None,
            location=m.location,
            attendanceStatus=att_status,
            goals=goals_map.get(m.id, []),
            cards=cards_map.get(m.id, []),
        ))

    return PlayerMatchHistoryResponse(matches=items)
