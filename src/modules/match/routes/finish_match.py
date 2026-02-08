from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from constants.platform_roles import PlatformRoles
from constants.match_state import MatchState
from extensions.sqlalchemy import get_db
from modules.match.models import (
    MatchModel
)
from modules.ranking.services import recalculate_match_rankings
from modules.tournament.services.knockout_service import auto_advance_knockout
from modules.tournament.models.tournament_knockout_match_model import TournamentKnockoutMatchModel
from modules.tournament.models.tournament_group_match_model import TournamentGroupMatchModel
from modules.tournament.models.tournament_group_model import TournamentGroupModel
from modules.tournament.models.tournament_model import TournamentModel
from modules.tournament.models.tournament_knockout_config_model import TournamentKnockoutConfigModel
from modules.tournament.models.tournament_schemas import TournamentKnockoutGenerateRequest
from modules.tournament.routes.tournament_knockout_routes import generate_knockout_matches_from_config
from project_helpers.dependencies import GetInstanceFromPath, JwtRequired
from project_helpers.responses import ConfirmationResponse
from .router import router


def _get_match(
    match_id: int,
    db: Session = Depends(get_db),
):
    return GetInstanceFromPath(MatchModel)(match_id, db)


@router.post("/{match_id}/finish", response_model=ConfirmationResponse)
async def finish_match(
    match: MatchModel = Depends(_get_match),
    db: Session = Depends(get_db),
    current_user=Depends(JwtRequired(roles=[PlatformRoles.ADMIN])),
):
    """Mark a match as finished"""
    if match.state == MatchState.FINISHED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Match is already finished"
        )

    match.state = MatchState.FINISHED

    # Ensure scores are set (default to 0 if not set)
    if match.scoreTeam1 is None:
        match.scoreTeam1 = 0
    if match.scoreTeam2 is None:
        match.scoreTeam2 = 0

    recalculate_match_rankings(db, match)
    auto_advance_knockout(db, match)
    try:
        tournament_id = None
        knockout_entry = (
            db.query(TournamentKnockoutMatchModel)
            .filter(TournamentKnockoutMatchModel.matchId == match.id)
            .first()
        )
        if knockout_entry:
            tournament_id = knockout_entry.tournamentId
        else:
            group_entry = (
                db.query(TournamentGroupMatchModel)
                .filter(TournamentGroupMatchModel.matchId == match.id)
                .first()
            )
            if group_entry:
                tournament_id = (
                    db.query(TournamentGroupModel.tournamentId)
                    .filter(TournamentGroupModel.id == group_entry.groupId)
                    .scalar()
                )
        if tournament_id:
            tournament = db.query(TournamentModel).filter(TournamentModel.id == tournament_id).first()
            config = (
                db.query(TournamentKnockoutConfigModel)
                .filter(TournamentKnockoutConfigModel.tournamentId == tournament_id)
                .first()
            )
            if tournament and tournament.hasKnockout and config:
                await generate_knockout_matches_from_config(
                    tournament_id,
                    TournamentKnockoutGenerateRequest(
                        replaceExisting=False,
                        leagueId=match.leagueId,
                    ),
                    db,
                )
    except HTTPException:
        pass
    db.commit()

    return ConfirmationResponse(
        success=True,
        message="Match marked as finished"
    )
