from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from constants.platform_roles import PlatformRoles
from constants.match_state import MatchState
from extensions.sqlalchemy import get_db
from modules.match.models import (
    MatchModel, GoalModel, ScoreUpdate
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
from modules.team.models import TeamModel
from constants.notification_type import NotificationType
from modules.notifications.services.notification_service import create_player_notifications
from project_helpers.dependencies import GetInstanceFromPath, JwtRequired
from project_helpers.responses import ConfirmationResponse
from .router import router


@router.post("/{id}/score", response_model=ConfirmationResponse, dependencies=[Depends(JwtRequired(roles=[PlatformRoles.ADMIN]))])
async def update_match_score(
        data: ScoreUpdate,
        match: MatchModel = Depends(GetInstanceFromPath(MatchModel)),
        db: Session = Depends(get_db),

):
    from modules.player.models.player_model import PlayerModel

    for goal in data.goals:
        player = db.query(PlayerModel).filter(PlayerModel.id == goal.playerId).first()
        if not player:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Player with ID {goal.playerId} not found"
            )

        team = db.query(TeamModel).filter(TeamModel.id == goal.teamId).first()
        if not team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Team with ID {goal.teamId} not found"
            )

        if goal.teamId not in [match.team1Id, match.team2Id]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Team {team.name} is not participating in this match"
            )

        if player.teamId != goal.teamId:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Player {player.name} does not belong to team {team.name}"
            )

        assist_player = None
        if goal.assistPlayerId is not None:
            assist_player = db.query(PlayerModel).filter(PlayerModel.id == goal.assistPlayerId).first()
            if not assist_player:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Assist player with ID {goal.assistPlayerId} not found"
                )
            if assist_player.teamId != goal.teamId:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Assist player {assist_player.name} does not belong to team {team.name}"
                )

        goal = GoalModel(
            matchId=match.id,
            playerId=goal.playerId,
            playerNameSnapshot=player.name,
            assistPlayerId=goal.assistPlayerId,
            assistPlayerNameSnapshot=assist_player.name if assist_player else None,
            teamId=goal.teamId,
            minute=goal.minute,
            description=goal.description
        )
        db.add(goal)

    # Goal notifications
    default_team = db.query(TeamModel).filter(TeamModel.isDefault.is_(True)).first()
    default_team_id = default_team.id if default_team else None
    default_player_ids = []
    if default_team_id and default_team_id in (match.team1Id, match.team2Id):
        default_player_ids = [
            pid for (pid,) in db.query(PlayerModel.id)
            .filter(PlayerModel.teamId == default_team_id)
            .all()
        ]

    for g in data.goals:
        scorer = db.query(PlayerModel).filter(PlayerModel.id == g.playerId).first()
        scorer_name = scorer.name if scorer else "Unknown"
        # GOAL_SCORED for the scorer
        create_player_notifications(
            db, [g.playerId],
            "notification.goalScored",
            "",
            NotificationType.GOAL_SCORED,
            params={
                "minute": str(g.minute or "?"),
                "matchId": match.id,
            },
        )
        # GOAL_CONCEDED for default team players (if the opponent scored against them)
        if default_team_id and g.teamId != default_team_id and default_team_id in (match.team1Id, match.team2Id):
            conceded_ids = [pid for pid in default_player_ids if pid != g.playerId]
            create_player_notifications(
                db, conceded_ids,
                "notification.goalConceded",
                "",
                NotificationType.GOAL_CONCEDED,
                params={
                    "scorer": scorer_name,
                    "minute": str(g.minute or "?"),
                    "matchId": match.id,
                },
            )

    team1_goals = len([g for g in data.goals if g.teamId == match.team1Id])
    team2_goals = len([g for g in data.goals if g.teamId == match.team2Id])

    if match.scoreTeam1 is None:
        match.scoreTeam1 = 0
    if match.scoreTeam2 is None:
        match.scoreTeam2 = 0

    match.scoreTeam1 += team1_goals
    match.scoreTeam2 += team2_goals

    if match.state == MatchState.SCHEDULED:
        match.state = MatchState.FINISHED

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
        message=f"Successfully added {len(data.goals)} goal(s) to the match"
    )
