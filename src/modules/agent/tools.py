"""Database query tools for the agent. Pure SQLAlchemy, no Redis."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import func, or_, select, text
from sqlalchemy.orm import Session, aliased

from constants.card_type import CardType
from constants.match_state import MatchState
from constants.attendance_scope import AttendanceScope
from constants.attendance_status import AttendanceStatus
from modules.match.models.goal_model import GoalModel
from modules.match.models.match_model import MatchModel
from modules.match.models.card_model import CardModel
from modules.player.models.player_model import PlayerModel
from modules.ranking.models.ranking_model import RankingModel
from modules.team.models.team_model import TeamModel
from modules.tournament.models.league_model import LeagueModel
from modules.user.models.user_model import UserModel
from modules.attendance.models.attendance_model import AttendanceModel


def _get_default_team(db: Session) -> TeamModel | None:
    team = db.query(TeamModel).filter(TeamModel.isDefault.is_(True)).first()
    if not team:
        team = db.query(TeamModel).first()
    return team


def _finished_filter():
    return or_(
        MatchModel.state == MatchState.FINISHED,
        MatchModel.scoreTeam1.isnot(None) & MatchModel.scoreTeam2.isnot(None),
    )


def get_top_scorers(db: Session, league_id: int | None = None, limit: int = 5) -> dict:
    q = (
        db.query(
            GoalModel.playerId,
            func.count(GoalModel.id).label("goals"),
        )
        .filter(GoalModel.playerId.isnot(None))
    )
    if league_id:
        q = q.join(MatchModel, MatchModel.id == GoalModel.matchId).filter(
            MatchModel.leagueId == league_id
        )
    q = q.group_by(GoalModel.playerId).order_by(func.count(GoalModel.id).desc()).limit(limit)
    rows = q.all()

    if not rows:
        return {"found": False, "players": []}

    player_ids = [r.playerId for r in rows]
    players = {
        p.id: p.name
        for p in db.query(PlayerModel).filter(PlayerModel.id.in_(player_ids)).all()
    }
    result = []
    for r in rows:
        result.append({
            "name": players.get(r.playerId, "Necunoscut"),
            "goals": r.goals,
            "playerId": r.playerId,
        })
    return {"found": True, "players": result}


def get_top_assists(db: Session, league_id: int | None = None, limit: int = 5) -> dict:
    q = (
        db.query(
            GoalModel.assistPlayerId,
            func.count(GoalModel.id).label("assists"),
        )
        .filter(GoalModel.assistPlayerId.isnot(None))
    )
    if league_id:
        q = q.join(MatchModel, MatchModel.id == GoalModel.matchId).filter(
            MatchModel.leagueId == league_id
        )
    q = q.group_by(GoalModel.assistPlayerId).order_by(func.count(GoalModel.id).desc()).limit(limit)
    rows = q.all()

    if not rows:
        return {"found": False, "players": []}

    player_ids = [r.assistPlayerId for r in rows]
    players = {
        p.id: p.name
        for p in db.query(PlayerModel).filter(PlayerModel.id.in_(player_ids)).all()
    }
    result = []
    for r in rows:
        result.append({
            "name": players.get(r.assistPlayerId, "Necunoscut"),
            "assists": r.assists,
            "playerId": r.assistPlayerId,
        })
    return {"found": True, "players": result}


def get_player_goals(db: Session, player_id: int, league_id: int | None = None) -> dict:
    q = select(func.count()).select_from(GoalModel).where(GoalModel.playerId == player_id)
    if league_id:
        q = q.join(MatchModel, MatchModel.id == GoalModel.matchId).where(
            MatchModel.leagueId == league_id
        )
    total = db.execute(q).scalar_one()
    return {"goals": int(total)}


def get_player_stats(db: Session, player_id: int) -> dict:
    player = db.query(PlayerModel).filter(PlayerModel.id == player_id).first()
    if not player:
        return {"found": False}

    goals = int(player.goalsCount or 0)
    yellow = int(player.yellowCardsCount or 0)
    red = int(player.redCardsCount or 0)
    appearances = int(player.appearancesCount or 0)

    # Count assists
    assists = db.query(func.count(GoalModel.id)).filter(
        GoalModel.assistPlayerId == player_id
    ).scalar() or 0

    return {
        "found": True,
        "name": player.name,
        "position": player.position.value if player.position else "N/A",
        "team": player.teamName or "N/A",
        "shirtNumber": player.shirtNumber,
        "rating": player.rating,
        "goals": goals,
        "assists": int(assists),
        "yellowCards": yellow,
        "redCards": red,
        "appearances": appearances,
        "playerId": player.id,
    }


def get_standings(db: Session, league_id: int | None = None) -> dict:
    if not league_id:
        # Get the most recent league
        league = db.query(LeagueModel).order_by(LeagueModel.id.desc()).first()
        if not league:
            return {"found": False, "rankings": []}
        league_id = league.id
        league_name = league.name
        season = league.season
    else:
        league = db.query(LeagueModel).filter(LeagueModel.id == league_id).first()
        league_name = league.name if league else "N/A"
        season = league.season if league else "N/A"

    rankings = (
        db.query(RankingModel)
        .filter(RankingModel.leagueId == league_id)
        .order_by(RankingModel.points.desc(), (RankingModel.goalsScored - RankingModel.goalsConceded).desc())
        .all()
    )
    if not rankings:
        return {"found": False, "rankings": [], "leagueName": league_name}

    result = []
    for i, r in enumerate(rankings, 1):
        team = db.query(TeamModel).filter(TeamModel.id == r.teamId).first()
        result.append({
            "position": i,
            "team": team.name if team else "N/A",
            "points": r.points,
            "played": r.gamesPlayed,
            "won": r.gamesWon,
            "drawn": r.gamesTied,
            "lost": r.gamesLost,
            "gf": r.goalsScored,
            "ga": r.goalsConceded,
            "gd": r.goalsScored - r.goalsConceded,
        })
    return {"found": True, "rankings": result, "leagueName": league_name, "season": season}


def get_next_matches(db: Session, team_id: int | None = None, limit: int = 5) -> dict:
    now = datetime.utcnow()
    q = db.query(MatchModel).filter(
        MatchModel.state == MatchState.SCHEDULED,
        MatchModel.scoreTeam1.is_(None),
        MatchModel.timestamp > now,
    )
    if team_id:
        q = q.filter(or_(MatchModel.team1Id == team_id, MatchModel.team2Id == team_id))

    matches = q.order_by(MatchModel.timestamp.asc()).limit(limit).all()
    if not matches:
        return {"found": False, "matches": []}

    result = []
    for m in matches:
        league_name = None
        if m.league:
            league_name = m.league.name
        result.append({
            "id": m.id,
            "team1": m.team1.name if m.team1 else "N/A",
            "team2": m.team2.name if m.team2 else "N/A",
            "date": m.timestamp.strftime("%d %b %Y, %H:%M"),
            "league": league_name,
        })
    return {"found": True, "matches": result}


def get_recent_results(db: Session, team_id: int | None = None, limit: int = 5) -> dict:
    q = db.query(MatchModel).filter(_finished_filter())
    if team_id:
        q = q.filter(or_(MatchModel.team1Id == team_id, MatchModel.team2Id == team_id))

    matches = q.order_by(MatchModel.timestamp.desc()).limit(limit).all()
    if not matches:
        return {"found": False, "matches": []}

    result = []
    for m in matches:
        s1 = m.scoreTeam1 if m.scoreTeam1 is not None else 0
        s2 = m.scoreTeam2 if m.scoreTeam2 is not None else 0
        league_name = m.league.name if m.league else None
        result.append({
            "id": m.id,
            "team1": m.team1.name if m.team1 else "N/A",
            "team2": m.team2.name if m.team2 else "N/A",
            "score": f"{s1}-{s2}",
            "date": m.timestamp.strftime("%d %b %Y"),
            "league": league_name,
        })
    return {"found": True, "matches": result}


def get_most_cards(db: Session, card_type: CardType | None = None, limit: int = 5) -> dict:
    q = db.query(
        CardModel.playerId,
        func.count(CardModel.id).label("cards"),
    )
    if card_type:
        q = q.filter(CardModel.cardType == card_type)
    q = q.group_by(CardModel.playerId).order_by(func.count(CardModel.id).desc()).limit(limit)
    rows = q.all()

    if not rows:
        return {"found": False, "players": []}

    player_ids = [r.playerId for r in rows]
    players = {
        p.id: p.name
        for p in db.query(PlayerModel).filter(PlayerModel.id.in_(player_ids)).all()
    }

    type_label = ""
    if card_type == CardType.YELLOW:
        type_label = " galbene"
    elif card_type == CardType.RED:
        type_label = " rosii"

    result = []
    for r in rows:
        result.append({
            "name": players.get(r.playerId, "Necunoscut"),
            "cards": r.cards,
            "playerId": r.playerId,
        })
    return {"found": True, "players": result, "typeLabel": type_label}


def get_team_info(db: Session, team_id: int | None = None) -> dict:
    if team_id:
        team = db.query(TeamModel).filter(TeamModel.id == team_id).first()
    else:
        team = _get_default_team(db)

    if not team:
        return {"found": False}

    player_count = db.query(func.count(PlayerModel.id)).filter(
        PlayerModel.teamId == team.id
    ).scalar() or 0

    return {
        "found": True,
        "name": team.name,
        "location": team.location,
        "playerCount": int(player_count),
        "teamId": team.id,
    }


def resolve_player(db: Session, raw: str, limit: int = 3) -> list[dict]:
    if not raw:
        return []
    raw = raw.strip()
    # Try pg_trgm similarity first
    try:
        rows = db.execute(text("""
            SELECT p.id AS id, u.name AS name, similarity(u.name, :q) AS score
            FROM players p
            JOIN users u ON u.id = p.id
            WHERE u.name % :q
            ORDER BY score DESC
            LIMIT :limit
        """), {"q": raw, "limit": limit}).mappings().all()
        if rows:
            return [dict(r) for r in rows]
    except Exception:
        pass

    # Fallback: ILIKE
    rows = db.execute(text("""
        SELECT p.id AS id, u.name AS name, 0.5 AS score
        FROM players p
        JOIN users u ON u.id = p.id
        WHERE lower(u.name) LIKE :like
        LIMIT :limit
    """), {"like": f"%{raw.lower()}%", "limit": limit}).mappings().all()
    return [dict(r) for r in rows]


def resolve_league(db: Session, raw: str, limit: int = 3) -> list[dict]:
    if not raw:
        return []
    raw = raw.strip()
    try:
        rows = db.execute(text("""
            SELECT id, name, similarity(name, :q) AS score
            FROM leagues
            WHERE name % :q
            ORDER BY score DESC
            LIMIT :limit
        """), {"q": raw, "limit": limit}).mappings().all()
        if rows:
            return [dict(r) for r in rows]
    except Exception:
        pass

    rows = db.execute(text("""
        SELECT id, name, 0.5 AS score
        FROM leagues
        WHERE lower(name) LIKE :like
        LIMIT :limit
    """), {"like": f"%{raw.lower()}%", "limit": limit}).mappings().all()
    return [dict(r) for r in rows]


def resolve_match(db: Session, raw: str, limit: int = 3) -> list[dict]:
    """Resolve a match by 'Team A vs Team B' pattern or by direct ID."""
    if not raw:
        return []
    raw = raw.strip()

    # Try direct ID
    if raw.isdigit():
        match = db.query(MatchModel).filter(MatchModel.id == int(raw)).first()
        if match:
            t1 = match.team1.name if match.team1 else "N/A"
            t2 = match.team2.name if match.team2 else "N/A"
            return [{"id": match.id, "name": f"{t1} vs {t2}", "score": 1.0}]
        return []

    # Try "Team A vs Team B" pattern
    import re
    parts = re.split(r'\s+(?:vs\.?|contra|impotriva|-)\s+', raw, maxsplit=1, flags=re.IGNORECASE)
    if len(parts) == 2:
        team1_candidates = resolve_team(db, parts[0].strip(), limit=1)
        team2_candidates = resolve_team(db, parts[1].strip(), limit=1)
        if team1_candidates and team2_candidates:
            t1_id = team1_candidates[0]["id"]
            t2_id = team2_candidates[0]["id"]
            matches = (
                db.query(MatchModel)
                .filter(
                    or_(
                        (MatchModel.team1Id == t1_id) & (MatchModel.team2Id == t2_id),
                        (MatchModel.team1Id == t2_id) & (MatchModel.team2Id == t1_id),
                    )
                )
                .order_by(MatchModel.timestamp.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "id": m.id,
                    "name": f"{m.team1.name if m.team1 else 'N/A'} vs {m.team2.name if m.team2 else 'N/A'} ({m.timestamp.strftime('%d %b %Y')})",
                    "score": 0.9,
                }
                for m in matches
            ]

    return []


def resolve_team(db: Session, raw: str, limit: int = 3) -> list[dict]:
    if not raw:
        return []
    raw = raw.strip()
    try:
        rows = db.execute(text("""
            SELECT id, name, similarity(name, :q) AS score
            FROM teams
            WHERE name % :q
            ORDER BY score DESC
            LIMIT :limit
        """), {"q": raw, "limit": limit}).mappings().all()
        if rows:
            return [dict(r) for r in rows]
    except Exception:
        pass

    rows = db.execute(text("""
        SELECT id, name, 0.5 AS score
        FROM teams
        WHERE lower(name) LIKE :like
        LIMIT :limit
    """), {"like": f"%{raw.lower()}%", "limit": limit}).mappings().all()
    return [dict(r) for r in rows]
