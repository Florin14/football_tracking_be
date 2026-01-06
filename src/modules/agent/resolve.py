# app/nlp/resolve.py
from sqlalchemy import text

from extensions import SessionLocal


def fuzzy_candidates(table: str, col: str, q: str, limit=3):
    sql = text(f"""
      SELECT id, {col} AS name, similarity({col}, :q) AS score
      FROM {table}
      WHERE {col} % :q
      ORDER BY score DESC
      LIMIT :limit
    """)
    with SessionLocal() as s:
        return [dict(r) for r in s.execute(sql, {"q": q, "limit": limit}).mappings().all()]

def alias_first(entity_type: str, raw: str):
    sql = text("""
      SELECT na.entity_id AS id, na.alias AS name, 1.0 AS score
      FROM name_aliases na
      WHERE na.entity_type=:etype AND na.alias ILIKE :raw
      LIMIT 1
    """)
    with SessionLocal() as s:
        r = s.execute(sql, {"etype": entity_type, "raw": raw}).mappings().first()
        return dict(r) if r else None

def resolve_entity(entity_type: str, raw: str):
    table = {"player":"players", "team":"teams", "league":"leagues"}[entity_type]
    col   = "name"
    # 1) alias exact
    a = alias_first(entity_type, raw)
    if a: return {"status":"resolved","id":a["id"],"name":a["name"],"score":1.0}
    # 2) fuzzy
    cands = fuzzy_candidates(table, col, raw, 3)
    if not cands: return {"status":"not_found","q":raw}
    top = cands[0]
    if top["score"] >= 0.85: return {"status":"resolved", **top}
    if top["score"] >= 0.60: return {"status":"ambiguous", "options": cands}
    return {"status":"low_conf","q":raw}
