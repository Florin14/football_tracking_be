from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from constants.platform_roles import PlatformRoles
from constants.match_state import MatchState
from constants.notification_type import NotificationType
from extensions.sqlalchemy import get_db
from modules.match.models import (
    MatchModel
)
from modules.notifications.services.notification_service import create_player_notifications
from modules.team.models.team_model import TeamModel
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


@router.post("/{match_id}/finish", response_model=ConfirmationResponse, dependencies=[Depends(JwtRequired(roles=[PlatformRoles.ADMIN]))])
async def finish_match(
    match: MatchModel = Depends(_get_match),
    db: Session = Depends(get_db),
):
    """Mark a match as finished"""
    if match.state == MatchState.FINISHED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Match is already finished"
        )

    match.state = MatchState.FINISHED

    from modules.player.models.player_model import PlayerModel

    # Ensure scores are set (default to 0 if not set)
    if match.scoreTeam1 is None:
        match.scoreTeam1 = 0
    if match.scoreTeam2 is None:
        match.scoreTeam2 = 0

    # MATCH_RESULT notifications for default team players
    default_team = db.query(TeamModel).filter(TeamModel.isDefault.is_(True)).first()
    if default_team and default_team.id in (match.team1Id, match.team2Id):
        team1 = db.query(TeamModel).filter(TeamModel.id == match.team1Id).first()
        team2 = db.query(TeamModel).filter(TeamModel.id == match.team2Id).first()
        team1_name = team1.name if team1 else "Team 1"
        team2_name = team2.name if team2 else "Team 2"
        default_player_ids = [
            pid for (pid,) in db.query(PlayerModel.id)
            .filter(PlayerModel.teamId == default_team.id)
            .all()
        ]
        create_player_notifications(
            db, default_player_ids,
            f"Result: {team1_name} {match.scoreTeam1}-{match.scoreTeam2} {team2_name}",
            "Match has been marked as finished",
            NotificationType.MATCH_RESULT,
        )

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
