from datetime import timedelta

from fastapi import Depends, HTTPException, status
from pydantic import Field
from sqlalchemy.orm import Session

from constants.match_state import MatchState
from constants.platform_roles import PlatformRoles
from constants.tournament_format_type import TournamentFormatType
from extensions.sqlalchemy import get_db
from modules.match.models.match_model import MatchModel
from modules.tournament.models.league_model import LeagueModel
from modules.tournament.models.league_team_model import LeagueTeamModel
from project_helpers.dependencies import JwtRequired
from project_helpers.schemas import BaseSchema
from .router import router


class GenerateReturnLegRequest(BaseSchema):
    leagueId: int = Field(..., example=1)


class GenerateReturnLegResponse(BaseSchema):
    generatedCount: int
    message: str


@router.post(
    "/generate-return-leg",
    response_model=GenerateReturnLegResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(JwtRequired(roles=[PlatformRoles.ADMIN]))],
)
def generate_return_leg(
    data: GenerateReturnLegRequest,
    db: Session = Depends(get_db),
):
    # Validate league exists
    league = db.query(LeagueModel).filter(LeagueModel.id == data.leagueId).first()
    if not league:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="League not found",
        )

    # Only allow for LEAGUE format (no groups)
    tournament = league.tournament
    if tournament and tournament.formatType and tournament.formatType != TournamentFormatType.LEAGUE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Return leg generation is only available for league format tournaments (no groups)",
        )

    # Get teams in this league
    league_team_ids = [
        tid for (tid,) in db.query(LeagueTeamModel.teamId)
        .filter(LeagueTeamModel.leagueId == data.leagueId)
        .all()
    ]
    num_teams = len(league_team_ids)
    if num_teams < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="League must have at least 2 teams",
        )

    # Calculate expected number of rounds in "tur" (first leg)
    # Round-robin: each team plays every other team once
    # Number of rounds = num_teams - 1 (if even) or num_teams - 1 (if odd, one team rests each round)
    # Total matches in tur = num_teams * (num_teams - 1) / 2
    expected_tur_matches = num_teams * (num_teams - 1) // 2

    # Get all existing matches for this league
    existing_matches = (
        db.query(MatchModel)
        .filter(MatchModel.leagueId == data.leagueId)
        .order_by(MatchModel.round.asc(), MatchModel.timestamp.asc())
        .all()
    )

    if len(existing_matches) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No matches found in this league. Add first leg matches first.",
        )

    # Determine the max round in existing matches (this is the last round of tur)
    max_round = max(m.round for m in existing_matches if m.round is not None) if any(m.round for m in existing_matches) else 0

    # Identify tur matches (first leg) - rounds 1 to expected tur rounds
    # Round-robin with N teams has N-1 rounds
    expected_tur_rounds = num_teams - 1

    # Tur matches are all matches in rounds 1 through expected_tur_rounds
    tur_matches = [m for m in existing_matches if m.round is not None and m.round <= expected_tur_rounds]

    if len(tur_matches) < expected_tur_matches:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Not all first leg matches have been added. Expected {expected_tur_matches} matches ({expected_tur_rounds} rounds), found {len(tur_matches)}.",
        )

    # Check if return leg matches already exist
    retur_matches = [m for m in existing_matches if m.round is not None and m.round > expected_tur_rounds]
    if len(retur_matches) > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Return leg matches already exist ({len(retur_matches)} found). Delete them first if you want to regenerate.",
        )

    # Find the latest match timestamp in the league
    last_match_timestamp = max(m.timestamp for m in existing_matches)

    # Group tur matches by round to preserve the round structure
    rounds_map: dict[int, list[MatchModel]] = {}
    for m in tur_matches:
        if m.round not in rounds_map:
            rounds_map[m.round] = []
        rounds_map[m.round].append(m)

    # Generate return leg matches
    new_matches = []
    for tur_round_num in sorted(rounds_map.keys()):
        retur_round_num = tur_round_num + expected_tur_rounds
        # Calculate date: last match date + (retur_round_num - expected_tur_rounds) weeks
        week_offset = retur_round_num - expected_tur_rounds
        match_date = last_match_timestamp + timedelta(weeks=week_offset)
        # Set time to 20:00
        match_timestamp = match_date.replace(hour=20, minute=0, second=0, microsecond=0)

        for tur_match in rounds_map[tur_round_num]:
            # Swap home and away teams
            new_match = MatchModel(
                team1Id=tur_match.team2Id,  # Away becomes home
                team2Id=tur_match.team1Id,  # Home becomes away
                leagueId=data.leagueId,
                round=retur_round_num,
                timestamp=match_timestamp,
                location=None,  # Will use team1's default location
                state=MatchState.SCHEDULED,
            )
            new_matches.append(new_match)

    db.add_all(new_matches)
    db.commit()

    return GenerateReturnLegResponse(
        generatedCount=len(new_matches),
        message=f"Successfully generated {len(new_matches)} return leg matches for rounds {expected_tur_rounds + 1}-{expected_tur_rounds * 2}.",
    )
