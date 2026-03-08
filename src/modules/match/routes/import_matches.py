from datetime import datetime
from io import BytesIO
from typing import List, Optional

import pandas as pd
from fastapi import Depends, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from constants.match_state import MatchState
from constants.platform_roles import PlatformRoles
from extensions.sqlalchemy import get_db
from modules.match.models.match_model import MatchModel
from modules.ranking.services import recalculate_match_rankings
from modules.team.models.team_model import TeamModel
from modules.tournament.models.league_model import LeagueModel
from modules.tournament.models.league_team_model import LeagueTeamModel
from project_helpers.dependencies import JwtRequired
from project_helpers.schemas import BaseSchema
from .router import router


class ImportMatchesResponse(BaseSchema):
    importedCount: int
    skippedCount: int
    errors: List[str] = []


def _normalize(name: str) -> str:
    return " ".join(name.strip().split()).lower()


_FORFEIT_DATE_STR = "01.01.1970"
_FORFEIT_LOCATION = "neprezentare"


def _is_forfeit_row(raw_date, raw_location) -> bool:
    """Detect forfeit: date is 01.01.1970 or location contains NEPREZENTARE."""
    date_str = str(raw_date).strip() if pd.notna(raw_date) else ""
    loc_str = str(raw_location).strip().lower() if pd.notna(raw_location) else ""
    return date_str == _FORFEIT_DATE_STR or _FORFEIT_LOCATION in loc_str


@router.post(
    "/import-matches",
    response_model=ImportMatchesResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(JwtRequired(roles=[PlatformRoles.ADMIN]))],
)
async def import_matches(
    file: UploadFile,
    leagueId: int = Query(..., description="League to import matches into"),
    db: Session = Depends(get_db),
):
    # Validate league
    league = db.query(LeagueModel).filter(LeagueModel.id == leagueId).first()
    if not league:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="League not found",
        )

    # Read Excel file
    contents = await file.read()
    try:
        df = pd.read_excel(BytesIO(contents), sheet_name=0)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not read the Excel file. Make sure it is a valid .xlsx or .xls file.",
        )

    # Normalize column names: strip whitespace, lowercase
    df.columns = [str(c).strip() for c in df.columns]

    # Map possible column names (Romanian + English)
    col_map: dict[str, Optional[str]] = {
        "etapa": None,
        "echipa 1": None,
        "echipa 2": None,
        "data": None,
        "ora": None,
        "locatie": None,
        "scor echipa 1": None,
        "scor echipa 2": None,
    }

    aliases = {
        "etapa": ["etapa", "round", "runda", "etapă"],
        "echipa 1": ["echipa 1", "echipa1", "team 1", "team1", "gazda", "gazdă", "home"],
        "echipa 2": ["echipa 2", "echipa2", "team 2", "team2", "oaspete", "away"],
        "data": ["data", "date", "dată"],
        "ora": ["ora", "time", "oră", "hour"],
        "locatie": ["locatie", "locație", "location", "loc", "venue", "teren"],
        "scor echipa 1": ["scor echipa 1", "scor1", "score 1", "score1", "scor gazda", "scor gazdă"],
        "scor echipa 2": ["scor echipa 2", "scor2", "score 2", "score2", "scor oaspete"],
    }

    lower_cols = {c.lower(): c for c in df.columns}
    for key, possible_names in aliases.items():
        for alias in possible_names:
            if alias.lower() in lower_cols:
                col_map[key] = lower_cols[alias.lower()]
                break

    # Validate required columns (ora is optional - defaults to 20:00)
    missing = []
    for req in ["etapa", "echipa 1", "echipa 2", "data"]:
        if col_map[req] is None:
            missing.append(req)
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required columns: {', '.join(missing)}. "
                   f"Found columns: {', '.join(df.columns.tolist())}",
        )

    # Build team name lookup for this league
    league_teams = (
        db.query(TeamModel)
        .join(LeagueTeamModel, LeagueTeamModel.teamId == TeamModel.id)
        .filter(LeagueTeamModel.leagueId == leagueId)
        .all()
    )
    team_lookup: dict[str, TeamModel] = {}
    for team in league_teams:
        team_lookup[_normalize(team.name)] = team

    errors: list[str] = []
    new_matches: list[MatchModel] = []
    skipped = 0

    for idx, row in df.iterrows():
        row_num = idx + 2  # Excel row (1-indexed header + data)

        # Parse round
        raw_round = row.get(col_map["etapa"])
        if pd.isna(raw_round):
            errors.append(f"Row {row_num}: missing round (etapa)")
            skipped += 1
            continue
        try:
            match_round = int(float(raw_round))
        except (ValueError, TypeError):
            errors.append(f"Row {row_num}: invalid round '{raw_round}'")
            skipped += 1
            continue

        # Parse teams
        raw_team1 = str(row.get(col_map["echipa 1"], "")).strip()
        raw_team2 = str(row.get(col_map["echipa 2"], "")).strip()
        if not raw_team1 or raw_team1 == "nan":
            errors.append(f"Row {row_num}: missing team 1")
            skipped += 1
            continue
        if not raw_team2 or raw_team2 == "nan":
            errors.append(f"Row {row_num}: missing team 2")
            skipped += 1
            continue

        team1 = team_lookup.get(_normalize(raw_team1))
        team2 = team_lookup.get(_normalize(raw_team2))
        if not team1:
            errors.append(f"Row {row_num}: team '{raw_team1}' not found in league")
            skipped += 1
            continue
        if not team2:
            errors.append(f"Row {row_num}: team '{raw_team2}' not found in league")
            skipped += 1
            continue
        if team1.id == team2.id:
            errors.append(f"Row {row_num}: team cannot play against itself")
            skipped += 1
            continue

        # Detect forfeit (neprezentare)
        raw_date = row.get(col_map["data"])
        raw_location = row.get(col_map["locatie"]) if col_map["locatie"] else None
        is_forfeit = _is_forfeit_row(raw_date, raw_location)

        # Parse date + time
        raw_time = row.get(col_map["ora"]) if col_map["ora"] else None

        if is_forfeit:
            # Forfeit: use epoch date as a marker, the date doesn't really matter
            timestamp = datetime(1970, 1, 1, 0, 0, 0)
        else:
            timestamp = _parse_datetime(raw_date, raw_time)
            if timestamp is None:
                errors.append(f"Row {row_num}: could not parse date '{raw_date}' / time '{raw_time}'")
                skipped += 1
                continue

        # Parse location (optional)
        location = None
        if col_map["locatie"]:
            raw_loc = row.get(col_map["locatie"])
            if pd.notna(raw_loc) and str(raw_loc).strip() and str(raw_loc).strip().lower() != "nan":
                loc_val = str(raw_loc).strip()
                # Don't store "NEPREZENTARE" as location
                if loc_val.lower() != _FORFEIT_LOCATION:
                    location = loc_val

        # Parse scores and determine state
        score_team1 = None
        score_team2 = None
        match_state = MatchState.SCHEDULED

        if is_forfeit:
            # Forfeit: determine winner from scores in the row
            raw_s1 = row.get(col_map["scor echipa 1"]) if col_map["scor echipa 1"] else None
            raw_s2 = row.get(col_map["scor echipa 2"]) if col_map["scor echipa 2"] else None
            if pd.notna(raw_s1) and pd.notna(raw_s2):
                try:
                    score_team1 = int(float(raw_s1))
                    score_team2 = int(float(raw_s2))
                except (ValueError, TypeError):
                    # Default forfeit: team1 wins 3-0 (will be adjusted below)
                    score_team1 = 3
                    score_team2 = 0
            else:
                # No scores specified for forfeit, default 3-0 for team1
                score_team1 = 3
                score_team2 = 0
            match_state = MatchState.FINISHED
        else:
            # Normal match: check if scores exist
            if col_map["scor echipa 1"] and col_map["scor echipa 2"]:
                raw_s1 = row.get(col_map["scor echipa 1"])
                raw_s2 = row.get(col_map["scor echipa 2"])
                if pd.notna(raw_s1) and pd.notna(raw_s2):
                    try:
                        score_team1 = int(float(raw_s1))
                        score_team2 = int(float(raw_s2))
                        match_state = MatchState.FINISHED
                    except (ValueError, TypeError):
                        pass  # Leave as SCHEDULED, scores will be added later

        match = MatchModel(
            team1Id=team1.id,
            team2Id=team2.id,
            leagueId=leagueId,
            round=match_round,
            timestamp=timestamp,
            location=location,
            scoreTeam1=score_team1,
            scoreTeam2=score_team2,
            state=match_state,
        )
        new_matches.append(match)

    if not new_matches and errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No matches could be imported. Errors: {'; '.join(errors[:10])}",
        )

    db.add_all(new_matches)
    db.flush()

    # Recalculate rankings for finished matches
    for match in new_matches:
        if match.state == MatchState.FINISHED and match.scoreTeam1 is not None and match.scoreTeam2 is not None:
            recalculate_match_rankings(db, match)

    db.commit()

    return ImportMatchesResponse(
        importedCount=len(new_matches),
        skippedCount=skipped,
        errors=errors[:20],  # Return first 20 errors at most
    )


def _parse_datetime(raw_date, raw_time) -> Optional[datetime]:
    """Try to parse a date + time into a datetime object."""
    # If raw_date is already a datetime/Timestamp
    if isinstance(raw_date, (datetime, pd.Timestamp)):
        dt = pd.Timestamp(raw_date)
        time_parsed = _parse_time(raw_time)
        if time_parsed:
            return dt.replace(hour=time_parsed[0], minute=time_parsed[1], second=0, microsecond=0).to_pydatetime()
        # If no time column/value, default to 20:00
        if dt.hour == 0 and dt.minute == 0:
            return dt.replace(hour=20, minute=0, second=0, microsecond=0).to_pydatetime()
        return dt.to_pydatetime()

    raw_date_str = str(raw_date).strip()
    if not raw_date_str or raw_date_str == "nan":
        return None

    # Try common date formats
    date_formats = [
        "%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y",
        "%d.%m.%y", "%d/%m/%y", "%Y/%m/%d",
    ]
    parsed_date = None
    for fmt in date_formats:
        try:
            parsed_date = datetime.strptime(raw_date_str, fmt)
            break
        except ValueError:
            continue

    if parsed_date is None:
        return None

    time_parsed = _parse_time(raw_time)
    if time_parsed:
        parsed_date = parsed_date.replace(hour=time_parsed[0], minute=time_parsed[1])
    else:
        # Default to 20:00 if no time provided
        parsed_date = parsed_date.replace(hour=20, minute=0)

    return parsed_date


def _parse_time(raw_time) -> Optional[tuple]:
    """Try to parse a time value, returns (hour, minute) or None."""
    if raw_time is None or (isinstance(raw_time, float) and pd.isna(raw_time)):
        return None

    # If it's a datetime/Timestamp (Excel sometimes stores time as datetime)
    if isinstance(raw_time, (datetime, pd.Timestamp)):
        ts = pd.Timestamp(raw_time)
        return (ts.hour, ts.minute)

    raw_str = str(raw_time).strip()
    if not raw_str or raw_str == "nan":
        return None

    # Try HH:MM or HH.MM
    for sep in [":", "."]:
        if sep in raw_str:
            parts = raw_str.split(sep)
            try:
                return (int(parts[0]), int(parts[1]))
            except (ValueError, IndexError):
                continue

    # Try as a plain number (e.g. 2000 -> 20:00)
    try:
        num = int(float(raw_str))
        if 0 <= num <= 2359:
            return (num // 100, num % 100)
    except (ValueError, TypeError):
        pass

    return None
