# app/db_session.py
from sqlalchemy.orm import Session
from app.models import TeamModel, PlayerModel, LeagueModel, UserModel  # importă-ți modelele reale
from sqlalchemy import text, func, or_, select

# —— Normalizare text ——
import unicodedata, re
def strip_diacritics(s: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFD', s)
                   if unicodedata.category(c) != 'Mn')
def norm(s: str) -> str:
    s = strip_diacritics(s or "").lower().strip()
    s = re.sub(r"\s+", " ", s)
    return s

# —— Fuzzy pe TEAMS ——
def resolve_team_by_name(db: Session, raw: str, limit: int = 3):
    q = norm(raw)
    sql = text("""
      SELECT id, name, similarity(name, :q) AS score
      FROM teams
      WHERE name % :q
      ORDER BY score DESC
      LIMIT :limit
    """)
    rows = db.execute(sql, {"q": q, "limit": limit}).mappings().all()
    if not rows:  # fallback: LIKE
        rows = db.execute(text("""
            SELECT id, name, 0.5 AS score
            FROM teams WHERE lower(name) LIKE :like
            LIMIT :limit
        """), {"like": f"%{q}%", "limit": limit}).mappings().all()
    return [dict(r) for r in rows]

# —— Fuzzy pe LEAGUES ——
def resolve_league_by_name(db: Session, raw: str, limit: int = 3):
    q = norm(raw)
    rows = db.execute(text("""
      SELECT id, name, similarity(name, :q) AS score
      FROM leagues
      WHERE name % :q
      ORDER BY score DESC
      LIMIT :limit
    """), {"q": q, "limit": limit}).mappings().all()
    return [dict(r) for r in rows]

# —— Fuzzy pe PLAYERS (PlayerModel moștenește UserModel) ——
# Presupunem că UserModel are fullName; altfel combină firstName + lastName.
def resolve_player_by_name(db: Session, raw: str, limit: int = 3):
    q = norm(raw)
    # Creează un index trgm în users pe fullName dacă se potrivește la tine:
    # CREATE INDEX IF NOT EXISTS idx_users_fullname_trgm ON users USING gin (full_name gin_trgm_ops);
    rows = db.execute(text("""
      SELECT p.id, u.full_name AS name, similarity(u.full_name, :q) AS score
      FROM players p
      JOIN users u ON u.id = p.id
      WHERE u.full_name % :q
      ORDER BY score DESC
      LIMIT :limit
    """), {"q": q, "limit": limit}).mappings().all()

    if not rows:
        rows = db.execute(text("""
          SELECT p.id, u.full_name AS name, 0.5 AS score
          FROM players p JOIN users u ON u.id = p.id
          WHERE lower(u.full_name) LIKE :like
          LIMIT :limit
        """), {"like": f"%{q}%", "limit": limit}).mappings().all()
    return [dict(r) for r in rows]
