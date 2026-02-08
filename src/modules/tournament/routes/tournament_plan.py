import json

from fastapi import Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from extensions.sqlalchemy import get_db
from project_helpers.dependencies import GetCurrentUser
from modules.team.models import TeamModel
from modules.tournament.models.tournament_group_match_model import TournamentGroupMatchModel
from modules.tournament.models.tournament_group_model import TournamentGroupModel
from modules.tournament.models.tournament_group_team_model import TournamentGroupTeamModel
from modules.tournament.models.tournament_knockout_config_model import TournamentKnockoutConfigModel
from modules.tournament.models.tournament_knockout_match_model import TournamentKnockoutMatchModel
from modules.tournament.models.tournament_model import TournamentModel
from modules.tournament.models.tournament_schemas import (
    TournamentGroupMatchItem,
    TournamentGroupItem,
    TournamentKnockoutConfig,
    TournamentKnockoutMatchItem,
    TournamentPlanResponse,
)

from .router import router

DEFAULT_PAIRING_CONFIG = {
    "RO16": "CROSS",
    "QF": "CROSS",
    "SF": "CROSS",
    "3P": "CROSS",
    "F": "CROSS",
}


@router.get("/{tournament_id}/plan", response_model=TournamentPlanResponse)
async def get_tournament_plan(
    tournament_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(GetCurrentUser()),
):
    tournament = db.query(TournamentModel).filter(TournamentModel.id == tournament_id).first()
    if not tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tournament with ID {tournament_id} not found",
        )

    groups = (
        db.query(TournamentGroupModel)
        .options(
            joinedload(TournamentGroupModel.teams)
            .joinedload(TournamentGroupTeamModel.team)
            .joinedload(TeamModel.players)
        )
        .filter(TournamentGroupModel.tournamentId == tournament_id)
        .order_by(
            TournamentGroupModel.order.is_(None),
            TournamentGroupModel.order,
            func.lower(TournamentGroupModel.name),
        )
        .all()
    )

    group_items: list[TournamentGroupItem] = []
    for group in groups:
        team_items = []
        for group_team in group.teams:
            team = group_team.team
            team_items.append({
                "id": team.id,
                "name": team.name,
                "description": team.description,
                "logo": team.logo,
                "playerCount": len(team.players) if team.players else 0,
            })
        group_items.append({
            "id": group.id,
            "name": group.name,
            "order": group.order,
            "teams": team_items,
        })

    group_matches = (
        db.query(TournamentGroupMatchModel)
        .options(joinedload(TournamentGroupMatchModel.match))
        .filter(TournamentGroupMatchModel.groupId.in_([g.id for g in groups]))
        .order_by(
            TournamentGroupMatchModel.order.is_(None),
            TournamentGroupMatchModel.order,
            TournamentGroupMatchModel.id,
        )
        .all()
        if groups
        else []
    )

    group_match_items: list[TournamentGroupMatchItem] = []
    for item in group_matches:
        match = item.match
        if not match:
            continue
        group_match_items.append(TournamentGroupMatchItem(
            id=item.id,
            groupId=item.groupId,
            matchId=match.id,
            round=item.round,
            order=item.order,
            team1Id=match.team1Id,
            team2Id=match.team2Id,
            scoreTeam1=match.scoreTeam1,
            scoreTeam2=match.scoreTeam2,
            state=match.state.value if hasattr(match.state, "value") else str(match.state),
            timestamp=match.timestamp,
        ))

    knockout_matches = (
        db.query(TournamentKnockoutMatchModel)
        .options(joinedload(TournamentKnockoutMatchModel.match))
        .filter(TournamentKnockoutMatchModel.tournamentId == tournament_id)
        .order_by(
            TournamentKnockoutMatchModel.order.is_(None),
            TournamentKnockoutMatchModel.order,
            TournamentKnockoutMatchModel.id,
        )
        .all()
    )

    knockout_items: list[TournamentKnockoutMatchItem] = []
    for knockout in knockout_matches:
        match = knockout.match
        if not match:
            continue
        knockout_items.append(TournamentKnockoutMatchItem(
            id=knockout.id,
            matchId=match.id,
            round=knockout.round,
            order=knockout.order,
            team1Id=match.team1Id,
            team2Id=match.team2Id,
            scoreTeam1=match.scoreTeam1,
            scoreTeam2=match.scoreTeam2,
            state=match.state.value if hasattr(match.state, "value") else str(match.state),
            timestamp=match.timestamp,
        ))

    config = (
        db.query(TournamentKnockoutConfigModel)
        .filter(TournamentKnockoutConfigModel.tournamentId == tournament_id)
        .first()
    )
    config_payload = None
    if config:
        manual_pairs = []
        if config.manualPairs:
            try:
                manual_pairs = json.loads(config.manualPairs)
            except json.JSONDecodeError:
                manual_pairs = []
        pairing_config = None
        if config.pairingConfig:
            try:
                pairing_config = json.loads(config.pairingConfig)
            except json.JSONDecodeError:
                pairing_config = None
        manual_pairs_by_phase = None
        if config.manualPairsByPhase:
            try:
                manual_pairs_by_phase = json.loads(config.manualPairsByPhase)
            except json.JSONDecodeError:
                manual_pairs_by_phase = None
        if pairing_config is None:
            pairing_config = DEFAULT_PAIRING_CONFIG.copy()
        config_payload = TournamentKnockoutConfig(
            qualifiersPerGroup=config.qualifiersPerGroup,
            pairingMode=config.pairingMode,
            manualPairs=manual_pairs,
            pairingConfig=pairing_config,
            manualPairsByPhase=manual_pairs_by_phase,
        )
    else:
        config_payload = TournamentKnockoutConfig(
            pairingConfig=DEFAULT_PAIRING_CONFIG.copy(),
            manualPairs=[],
            manualPairsByPhase=None,
        )

    return TournamentPlanResponse(
        tournamentId=tournament.id,
        formatType=tournament.formatType,
        groupCount=tournament.groupCount,
        teamsPerGroup=tournament.teamsPerGroup,
        hasKnockout=tournament.hasKnockout,
        groups=group_items,
        groupMatches=group_match_items,
        knockoutConfig=config_payload,
        knockoutMatches=knockout_items,
    )
