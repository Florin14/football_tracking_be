import json
import random
from datetime import datetime, timedelta

from fastapi import Body, Depends, HTTPException, status
from sqlalchemy.orm import Session

from constants.platform_roles import PlatformRoles
from extensions.sqlalchemy import get_db
from project_helpers.dependencies import JwtRequired
from modules.tournament.models.tournament_knockout_config_model import TournamentKnockoutConfigModel
from modules.tournament.models.tournament_knockout_match_model import TournamentKnockoutMatchModel
from modules.tournament.models.tournament_schemas import (
    TournamentKnockoutAutoRequest,
    TournamentKnockoutBulkCreateRequest,
    TournamentKnockoutConfig,
    TournamentKnockoutGenerateRequest,
    TournamentStructureResponse,
)
from modules.tournament.routes.tournament_structure import (
    _validate_teams_belong_to_tournament,
    get_tournament_structure,
)

from .router import router
from .tournament_group_routes import get_group_standings
from .tournament_group_scheduling_helpers import (
    _create_knockout_match,
    _create_match,
    _delete_knockout_matches,
    _ensure_unique_manual_pairs,
    _get_group_completion_map,
    _get_knockout_losers,
    _get_knockout_winners,
    _get_league_or_404,
    _get_tournament_or_404,
    _load_groups_with_teams,
    _load_knockout_entries,
    _load_team_league_map,
    _normalize_pairing_config,
    _normalize_pairing_mode,
    _parse_seed_index,
    _parse_seed_label,
    _resolve_match_league_id,
)


@router.post("/{tournament_id}/knockout-matches/bulk", response_model=TournamentStructureResponse, dependencies=[Depends(JwtRequired(roles=[PlatformRoles.ADMIN]))])
async def create_knockout_matches_bulk(
    tournament_id: int,
    data: TournamentKnockoutBulkCreateRequest,
    db: Session = Depends(get_db),
):
    _get_tournament_or_404(db, tournament_id)
    team_ids = [team_id for entry in data.matches for team_id in (entry.team1Id, entry.team2Id)]
    team_leagues = _load_team_league_map(db, tournament_id, team_ids)

    if data.replaceExisting:
        _delete_knockout_matches(db, tournament_id)

    for entry in data.matches:
        _validate_teams_belong_to_tournament(db, tournament_id, [entry.team1Id, entry.team2Id])
        league_id = _resolve_match_league_id(team_leagues, entry.team1Id, entry.team2Id, None)
        match = _create_match(
            db,
            team1_id=entry.team1Id,
            team2_id=entry.team2Id,
            timestamp=entry.timestamp,
            league_id=league_id,
            location=entry.location,
        )
        _create_knockout_match(
            db,
            tournament_id=tournament_id,
            match_id=match.id,
            round_label=entry.round,
            order=entry.order,
        )

    db.commit()
    return await get_tournament_structure(tournament_id, db)


@router.post("/{tournament_id}/knockout-matches/auto", response_model=TournamentStructureResponse, dependencies=[Depends(JwtRequired(roles=[PlatformRoles.ADMIN]))])
async def create_knockout_matches_auto(
    tournament_id: int,
    data: TournamentKnockoutAutoRequest,
    db: Session = Depends(get_db),
):
    _get_tournament_or_404(db, tournament_id)
    groups = _load_groups_with_teams(db, tournament_id)
    if not groups:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No groups found for this tournament",
        )

    standings_response = await get_group_standings(tournament_id, db)
    standings_by_group = {item.groupId: item.teams for item in standings_response.groups}
    ordered_groups = sorted(groups, key=lambda g: (g.order is None, g.order or 0, g.name.lower()))
    group_completion = _get_group_completion_map(db, [group.id for group in ordered_groups])

    _get_league_or_404(db, tournament_id, data.leagueId)

    if data.pairingStrategy not in {"cross", "seeded", "random"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="pairingStrategy must be 'cross', 'seeded' or 'random'",
        )

    if data.pairingStrategy in {"seeded", "random"}:
        incomplete_groups = [group.name for group in ordered_groups if not group_completion.get(group.id)]
        if incomplete_groups:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot generate knockout matches until all groups are finished",
            )

    pairs_with_order: list[tuple[int, int, int]] = []
    order_index = 1
    if data.pairingStrategy == "cross":
        if len(ordered_groups) % 2 != 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cross pairing requires an even number of groups",
            )
        if data.qualifiersPerGroup > 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cross pairing supports up to 2 qualifiers per group",
            )
        for i in range(0, len(ordered_groups), 2):
            group_a = ordered_groups[i]
            group_b = ordered_groups[i + 1]
            group_a_ready = group_completion.get(group_a.id, False)
            group_b_ready = group_completion.get(group_b.id, False)
            if not (group_a_ready and group_b_ready):
                order_index += 1 if data.qualifiersPerGroup == 1 else 2
                continue
            group_a_standings = standings_by_group.get(group_a.id, [])
            group_b_standings = standings_by_group.get(group_b.id, [])
            if len(group_a_standings) < data.qualifiersPerGroup or len(group_b_standings) < data.qualifiersPerGroup:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Not enough teams to qualify {data.qualifiersPerGroup} team(s) for {group_a.name}/{group_b.name}",
                )
            if data.qualifiersPerGroup == 1:
                pairs_with_order.append((order_index, group_a_standings[0].id, group_b_standings[0].id))
                order_index += 1
            else:
                pairs_with_order.append((order_index, group_a_standings[0].id, group_b_standings[1].id))
                order_index += 1
                pairs_with_order.append((order_index, group_b_standings[0].id, group_a_standings[1].id))
                order_index += 1
    else:
        qualifiers = []
        for group in ordered_groups:
            group_standings = standings_by_group.get(group.id, [])
            if len(group_standings) < data.qualifiersPerGroup:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Not enough teams to qualify {data.qualifiersPerGroup} team(s) for {group.name}",
                )
            qualifiers.append(group_standings[: data.qualifiersPerGroup])

        pairs: list[tuple[int, int]] = []
        if data.pairingStrategy == "seeded":
            flat = []
            for group in qualifiers:
                flat.extend(group)
            ordered = [team.id for team in flat]
            while len(ordered) >= 2:
                pairs.append((ordered.pop(0), ordered.pop(-1)))
        else:
            flat = []
            for group in qualifiers:
                flat.extend(group)
            ordered = [team.id for team in flat]
            random.shuffle(ordered)
            while len(ordered) >= 2:
                pairs.append((ordered.pop(0), ordered.pop(0)))

        for team1_id, team2_id in pairs:
            pairs_with_order.append((order_index, team1_id, team2_id))
            order_index += 1

    team_ids_all = [team_id for _, team_id, _ in pairs_with_order] + [team_id for _, _, team_id in pairs_with_order]
    team_leagues = _load_team_league_map(db, tournament_id, team_ids_all)

    if data.replaceExisting:
        _delete_knockout_matches(db, tournament_id)

    round_label = data.round
    existing_orders = set()
    if not data.replaceExisting:
        existing_query = db.query(TournamentKnockoutMatchModel.order).filter(
            TournamentKnockoutMatchModel.tournamentId == tournament_id
        )
        if round_label is None:
            existing_query = existing_query.filter(TournamentKnockoutMatchModel.round.is_(None))
        else:
            existing_query = existing_query.filter(TournamentKnockoutMatchModel.round == round_label)
        existing_orders = {row[0] for row in existing_query.all()}

    interval = timedelta(minutes=data.intervalMinutes)
    for order, team1_id, team2_id in pairs_with_order:
        if order in existing_orders:
            continue
        league_id = _resolve_match_league_id(team_leagues, team1_id, team2_id, data.leagueId)
        match = _create_match(
            db,
            team1_id=team1_id,
            team2_id=team2_id,
            timestamp=data.startTimestamp + interval * (order - 1),
            league_id=league_id,
        )
        _create_knockout_match(
            db,
            tournament_id=tournament_id,
            match_id=match.id,
            round_label=round_label,
            order=order,
        )

    db.commit()
    return await get_tournament_structure(tournament_id, db)


@router.post("/{tournament_id}/knockout-config", response_model=TournamentKnockoutConfig, dependencies=[Depends(JwtRequired(roles=[PlatformRoles.ADMIN]))])
async def set_knockout_config(
    tournament_id: int,
    data: TournamentKnockoutConfig,
    db: Session = Depends(get_db),
):
    _get_tournament_or_404(db, tournament_id)
    pairing_mode = _normalize_pairing_mode(data.pairingMode)
    if pairing_mode not in {"cross", "random", "manual", "seeded"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="pairingMode must be 'CROSS', 'RANDOM', 'SEEDED' or 'MANUAL'",
        )

    manual_pairs = data.manualPairs or []
    manual_pairs_by_phase = data.manualPairsByPhase or None
    if pairing_mode == "manual":
        if not manual_pairs:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="manualPairs is required when pairingMode is MANUAL",
            )
        _ensure_unique_manual_pairs(manual_pairs)

    config = (
        db.query(TournamentKnockoutConfigModel)
        .filter(TournamentKnockoutConfigModel.tournamentId == tournament_id)
        .first()
    )
    payload = TournamentKnockoutConfigModel(
        tournamentId=tournament_id,
        qualifiersPerGroup=data.qualifiersPerGroup,
        pairingMode=pairing_mode,
        manualPairs=json.dumps([pair.model_dump() for pair in manual_pairs]) if manual_pairs else None,
        pairingConfig=json.dumps(data.pairingConfig) if data.pairingConfig else None,
        manualPairsByPhase=(
            json.dumps({
                phase: [pair.model_dump() for pair in pairs]
                for phase, pairs in manual_pairs_by_phase.items()
            })
            if manual_pairs_by_phase
            else None
        ),
    )
    if config:
        config.qualifiersPerGroup = payload.qualifiersPerGroup
        config.pairingMode = payload.pairingMode
        config.manualPairs = payload.manualPairs
        config.pairingConfig = payload.pairingConfig
        config.manualPairsByPhase = payload.manualPairsByPhase
    else:
        db.add(payload)
    db.commit()

    return TournamentKnockoutConfig(
        qualifiersPerGroup=payload.qualifiersPerGroup,
        pairingMode=payload.pairingMode,
        manualPairs=manual_pairs,
        pairingConfig=data.pairingConfig,
        manualPairsByPhase=manual_pairs_by_phase,
    )


@router.post("/{tournament_id}/knockout-generate", response_model=TournamentStructureResponse, dependencies=[Depends(JwtRequired(roles=[PlatformRoles.ADMIN]))])
async def generate_knockout_matches_from_config(
    tournament_id: int,
    data: TournamentKnockoutGenerateRequest = Body(default_factory=TournamentKnockoutGenerateRequest),
    db: Session = Depends(get_db),
):
    tournament = _get_tournament_or_404(db, tournament_id)
    config = (
        db.query(TournamentKnockoutConfigModel)
        .filter(TournamentKnockoutConfigModel.tournamentId == tournament_id)
        .first()
    )
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knockout config not found",
        )

    qualifiers_per_group = config.qualifiersPerGroup
    if qualifiers_per_group is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="qualifiersPerGroup is required in knockout config",
        )
    if tournament.teamsPerGroup and qualifiers_per_group > tournament.teamsPerGroup:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="qualifiersPerGroup cannot exceed teamsPerGroup",
        )

    groups = _load_groups_with_teams(db, tournament_id)
    if not groups:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No groups found for this tournament",
        )

    pairing_config_raw = None
    if config.pairingConfig:
        try:
            pairing_config_raw = json.loads(config.pairingConfig)
        except json.JSONDecodeError:
            pairing_config_raw = None
    pairing_config = _normalize_pairing_config(pairing_config_raw, config.pairingMode)

    manual_pairs_by_phase = None
    if config.manualPairsByPhase:
        try:
            manual_pairs_by_phase = json.loads(config.manualPairsByPhase)
        except json.JSONDecodeError:
            manual_pairs_by_phase = None

    standings_response = await get_group_standings(tournament_id, db)
    standings_by_group = {item.groupId: item.teams for item in standings_response.groups}
    ordered_groups = sorted(groups, key=lambda g: (g.order is None, g.order or 0, g.name.lower()))
    group_completion = _get_group_completion_map(db, [group.id for group in ordered_groups])

    _get_league_or_404(db, tournament_id, data.leagueId)

    if data.replaceExisting:
        _delete_knockout_matches(db, tournament_id)

    total_qualifiers = len(ordered_groups) * qualifiers_per_group
    if total_qualifiers not in {2, 4, 8, 16}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Qualifiers count must be 2, 4, 8, or 16 to generate knockout phases",
        )

    initial_phase = {16: "RO16", 8: "QF", 4: "SF", 2: "F"}[total_qualifiers]
    initial_pairing = pairing_config.get(initial_phase, "CROSS")
    if manual_pairs_by_phase is None and config.manualPairs:
        try:
            legacy_pairs = json.loads(config.manualPairs)
        except json.JSONDecodeError:
            legacy_pairs = []
        manual_pairs_by_phase = {initial_phase: legacy_pairs} if legacy_pairs else None

    # Build matches for later phases based on qualifiers from the previous round.
    def create_matches_for_phase(
        phase: str,
        participants: list[int],
        pairing_value: str,
        start_time: datetime,
        interval: timedelta,
    ) -> None:
        if not participants or len(participants) < 2:
            return
        pairs: list[tuple[int, int]] = []
        if len(participants) == 2:
            pairs.append((participants[0], participants[1]))
        elif pairing_value == "RANDOM":
            ordered = list(participants)
            random.shuffle(ordered)
            while len(ordered) >= 2:
                pairs.append((ordered.pop(0), ordered.pop(0)))
        elif pairing_value in {"SEEDED", "CROSS"}:
            ordered = list(participants)
            while len(ordered) >= 2:
                pairs.append((ordered.pop(0), ordered.pop(-1)))
        elif pairing_value == "MANUAL":
            phase_pairs = (manual_pairs_by_phase or {}).get(phase) or []
            if not phase_pairs:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"manualPairs are required for phase {phase}. Provide manualPairsByPhase['{phase}']",
                )
            for pair in phase_pairs:
                # Manual seed indices are 1-based into the current participants list.
                home_index = _parse_seed_index(pair["home"])
                away_index = _parse_seed_index(pair["away"])
                if home_index > len(participants) or away_index > len(participants):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"manualPairs seed index out of range for phase {phase}",
                    )
                pairs.append((participants[home_index - 1], participants[away_index - 1]))
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported pairing mode for phase {phase}",
            )

        existing_orders = {
            row[0]
            for row in db.query(TournamentKnockoutMatchModel.order)
            .filter(
                TournamentKnockoutMatchModel.tournamentId == tournament_id,
                TournamentKnockoutMatchModel.round == phase,
            )
            .all()
        }
        team_leagues = _load_team_league_map(
            db, tournament_id, [team_id for pair in pairs for team_id in pair]
        )
        for idx, (team1_id, team2_id) in enumerate(pairs, start=1):
            if idx in existing_orders:
                continue
            league_id = _resolve_match_league_id(team_leagues, team1_id, team2_id, data.leagueId)
            match = _create_match(
                db,
                team1_id=team1_id,
                team2_id=team2_id,
                timestamp=start_time + interval * (idx - 1),
                league_id=league_id,
            )
            _create_knockout_match(
                db,
                tournament_id=tournament_id,
                match_id=match.id,
                round_label=phase,
                order=idx,
            )

    def build_initial_participants() -> list[tuple[int, int, int]]:
        # Initial phase depends on group standings and pairing mode configuration.
        pairs_with_order: list[tuple[int, int, int]] = []
        order_index = 1
        if initial_pairing == "CROSS":
            if len(ordered_groups) % 2 != 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cross pairing requires an even number of groups",
                )
            if qualifiers_per_group > 2:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cross pairing supports up to 2 qualifiers per group",
                )
            for i in range(0, len(ordered_groups), 2):
                group_a = ordered_groups[i]
                group_b = ordered_groups[i + 1]
                group_a_ready = group_completion.get(group_a.id, False)
                group_b_ready = group_completion.get(group_b.id, False)
                if not (group_a_ready and group_b_ready):
                    order_index += 1 if qualifiers_per_group == 1 else 2
                    continue
                group_a_standings = standings_by_group.get(group_a.id, [])
                group_b_standings = standings_by_group.get(group_b.id, [])
                if len(group_a_standings) < qualifiers_per_group or len(group_b_standings) < qualifiers_per_group:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Not enough teams to qualify {qualifiers_per_group} team(s) for {group_a.name}/{group_b.name}",
                    )
                if qualifiers_per_group == 1:
                    pairs_with_order.append((order_index, group_a_standings[0].id, group_b_standings[0].id))
                    order_index += 1
                else:
                    pairs_with_order.append((order_index, group_a_standings[0].id, group_b_standings[1].id))
                    order_index += 1
                    pairs_with_order.append((order_index, group_b_standings[0].id, group_a_standings[1].id))
                    order_index += 1
        elif initial_pairing in {"RANDOM", "SEEDED"}:
            incomplete_groups = [group.name for group in ordered_groups if not group_completion.get(group.id)]
            if incomplete_groups:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Cannot generate knockout matches until all groups are finished",
                )
            qualifiers = []
            for group in ordered_groups:
                group_standings = standings_by_group.get(group.id, [])
                if len(group_standings) < qualifiers_per_group:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Not enough teams to qualify {qualifiers_per_group} team(s) for {group.name}",
                    )
                qualifiers.append(group_standings[: qualifiers_per_group])
            flat = []
            for group in qualifiers:
                flat.extend(group)
            ordered = [team.id for team in flat]
            if initial_pairing == "RANDOM":
                random.shuffle(ordered)
            pairs: list[tuple[int, int]] = []
            if initial_pairing == "SEEDED":
                while len(ordered) >= 2:
                    pairs.append((ordered.pop(0), ordered.pop(-1)))
            else:
                while len(ordered) >= 2:
                    pairs.append((ordered.pop(0), ordered.pop(0)))
            for team1_id, team2_id in pairs:
                pairs_with_order.append((order_index, team1_id, team2_id))
                order_index += 1
        elif initial_pairing == "MANUAL":
            manual_pairs = (manual_pairs_by_phase or {}).get(initial_phase) or []
            if not manual_pairs:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"manualPairs are required for phase {initial_phase}",
                )
            group_by_name = {group.name.lower(): group for group in ordered_groups}
            for pair in manual_pairs:
                group_name, rank = _parse_seed_label(pair["home"])
                group = group_by_name.get(group_name.lower())
                if not group:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Unknown group in label: {pair['home']}",
                    )
                if not group_completion.get(group.id, False):
                    order_index += 1
                    continue
                group_standings = standings_by_group.get(group.id, [])
                if len(group_standings) < rank:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Not enough teams in group for label: {pair['home']}",
                    )
                home_team = group_standings[rank - 1].id
                group_name, rank = _parse_seed_label(pair["away"])
                group = group_by_name.get(group_name.lower())
                if not group:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Unknown group in label: {pair['away']}",
                    )
                if not group_completion.get(group.id, False):
                    order_index += 1
                    continue
                group_standings = standings_by_group.get(group.id, [])
                if len(group_standings) < rank:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Not enough teams in group for label: {pair['away']}",
                    )
                away_team = group_standings[rank - 1].id
                pairs_with_order.append((order_index, home_team, away_team))
                order_index += 1
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported pairing mode for phase {initial_phase}",
            )
        return pairs_with_order

    start_time = data.startTimestamp or datetime.utcnow()
    interval = timedelta(minutes=data.intervalMinutes)

    pairs_with_order = build_initial_participants()
    if pairs_with_order:
        team_leagues = _load_team_league_map(
            db,
            tournament_id,
            [team_id for _, team_id, _ in pairs_with_order] + [team_id for _, _, team_id in pairs_with_order],
        )
        existing_orders = {
            row[0]
            for row in db.query(TournamentKnockoutMatchModel.order)
            .filter(
                TournamentKnockoutMatchModel.tournamentId == tournament_id,
                TournamentKnockoutMatchModel.round == initial_phase,
            )
            .all()
        }
        for order, team1_id, team2_id in pairs_with_order:
            if order in existing_orders:
                continue
            league_id = _resolve_match_league_id(team_leagues, team1_id, team2_id, data.leagueId)
            match = _create_match(
                db,
                team1_id=team1_id,
                team2_id=team2_id,
                timestamp=start_time + interval * (order - 1),
                league_id=league_id,
            )
            _create_knockout_match(
                db,
                tournament_id=tournament_id,
                match_id=match.id,
                round_label=initial_phase,
                order=order,
            )

    phase_chain = {
        "RO16": "QF",
        "QF": "SF",
        "SF": "F",
    }
    current_phase = initial_phase
    while current_phase in phase_chain:
        next_phase = phase_chain[current_phase]
        current_entries = _load_knockout_entries(db, tournament_id, current_phase)
        if not current_entries:
            break
        winners = _get_knockout_winners(current_entries)
        if any(winner is None for winner in winners):
            break
        participants = [winner for winner in winners if winner is not None]
        next_pairing = pairing_config.get(next_phase, "CROSS")
        create_matches_for_phase(next_phase, participants, next_pairing, start_time, interval)
        current_phase = next_phase

    sf_entries = _load_knockout_entries(db, tournament_id, "SF")
    if sf_entries:
        sf_losers = _get_knockout_losers(sf_entries)
        if sf_losers and not any(loser is None for loser in sf_losers):
            participants = [loser for loser in sf_losers if loser is not None]
            third_place_pairing = pairing_config.get("3P", "CROSS")
            create_matches_for_phase("3P", participants, third_place_pairing, start_time, interval)

    db.commit()
    return await get_tournament_structure(tournament_id, db)
