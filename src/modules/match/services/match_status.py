from __future__ import annotations

from sqlalchemy import and_, or_
from typing import TYPE_CHECKING

from constants.match_state import MatchState

if TYPE_CHECKING:
    from modules.match.models.match_model import MatchModel


def match_is_completed_expr(match_cls=MatchModel):
    return or_(
        match_cls.state == MatchState.FINISHED,
        and_(
            match_cls.state == MatchState.SCHEDULED,
            match_cls.scoreTeam1.isnot(None),
            match_cls.scoreTeam2.isnot(None),
        ),
    )


def is_match_completed(match: MatchModel | None) -> bool:
    if not match:
        return False
    if match.state == MatchState.FINISHED:
        return True
    return (
        match.state == MatchState.SCHEDULED
        and match.scoreTeam1 is not None
        and match.scoreTeam2 is not None
    )
