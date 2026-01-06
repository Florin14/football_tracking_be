# app/tools.py
from typing import Optional

from fastapi import Depends
from sqlalchemy import select, func
# from app.db import SessionLocal, t_players, t_matches, t_events, t_standings, t_leagues, t_teams, t_mv_player_season
import redis, json, os
from sqlalchemy.orm import Session

from extensions import SessionLocal, get_db
from modules import MatchModel, GoalModel, RankingModel

r = redis.Redis.from_url(os.getenv("REDIS_URL","redis://localhost:6379"), decode_responses=True)

def cache(key: str, ttl: int, f):
    val = r.get(key)
    if val: return json.loads(val)
    data = f()
    r.setex(key, ttl, json.dumps(data))
    return data

def get_player_goals(player_id: int, season: str | None = None, leagueId: int | None = None, league_id: int | None = None, db: Session = Depends(get_db), ):
    q = select(func.count()).select_from(GoalModel).where(GoalModel.playerId == player_id)
    if season or league_id:
        q = q.join(MatchModel, MatchModel.id == GoalModel.matchId)
        if season:
            q = q.where(MatchModel.leagueId == season)
        if league_id:
            q = q.where(MatchModel.leagueId == league_id)
    total = db.execute(q).scalar_one()
    scope = f"sezon {season}" if season else "all-time"
    if league_id: scope += " • liga selectată"
    return {"goals": int(total), "scope": scope}

def gap_to_leader(league_id: str, season: str, team_id: str):
    key = f"gap:{league_id}:{season}:{team_id}"
    def _q():
        with SessionLocal() as s:
            leader = s.execute(select(RankingModel.teamId, RankingModel.points)
                               .where(RankingModel.leagueId==league_id, RankingModel.season==season)
                               .order_by(RankingModel.points.desc(), RankingModel.goal_diff.desc())
                               .limit(1)).first()
            me = s.execute(select(RankingModel.points).where(
                RankingModel.league_id==league_id, RankingModel.season==season, RankingModel.teamId==team_id
            )).first()
            if not leader or not me: return {"found": False}
            return {"found": True, "leader_team_id": leader.team_id,
                    "gap": int(leader.points - me.points)}
    return cache(key, 30, _q)
