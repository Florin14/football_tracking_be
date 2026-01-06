from sqlalchemy import text
from sqlalchemy.orm import Session
from .aliases import alias_lookup

def _fuzzy(db: Session, table: str, col: str, q: str, limit=3):
    sql = text(f"""
      SELECT id, {col} AS name, similarity({col}, :q) AS score
      FROM {table}
      WHERE {col} % :q
      ORDER BY score DESC
      LIMIT :limit
    """)
    rows = db.execute(sql, {"q": q, "limit": limit}).mappings().all()
    if not rows:
        rows = db.execute(text(f"""
          SELECT id, {col} AS name, 0.5 AS score
          FROM {table}
          WHERE lower({col}) LIKE :like
          LIMIT :limit
        """), {"like": f"%{q}%", "limit": limit}).mappings().all()
    return [dict(r) for r in rows]

def resolve_player(db: Session, raw: str, limit=3):
    if not raw: return []
    a = alias_lookup("player", raw)
    if a: raw = a
    sql = text("""
      SELECT p.id AS id, u.name AS name, similarity(u.name, :q) AS score
      FROM players p
      JOIN users u ON u.id = p.id
      WHERE u.name % :q
      ORDER BY score DESC
      LIMIT :limit
    """)
    rows = db.execute(sql, {"q": raw.lower().strip(), "limit": limit}).mappings().all()
    if not rows:
        rows = db.execute(text("""
          SELECT p.id AS id, u.name AS name, 0.5 AS score
          FROM players p JOIN users u ON u.id = p.id
          WHERE lower(u.name) LIKE :like
          LIMIT :limit
        """), {"like": f"%{raw.lower().strip()}%", "limit": limit}).mappings().all()
    return [dict(r) for r in rows]

def resolve_team(db: Session, raw: str, limit=3):
    if not raw: return []
    a = alias_lookup("team", raw)
    if a: raw = a
    return _fuzzy(db, "teams", "name", raw.lower().strip(), limit)

def resolve_league(db: Session, raw: str, season: str | None, limit=3):
    if not raw: return []
    a = alias_lookup("league", raw)
    if a: raw = a
    # dacă avem sezon, filtrăm întâi pe el
    if season:
      sql = text("""
        SELECT id, name, similarity(name, :q) AS score
        FROM leagues
        WHERE season = :season AND name % :q
        ORDER BY score DESC
        LIMIT :limit
      """)
      rows = db.execute(sql, {"q": raw.lower().strip(), "season": season, "limit": limit}).mappings().all()
      if rows: return [dict(r) for r in rows]
    return _fuzzy(db, "leagues", "name", raw.lower().strip(), limit)
