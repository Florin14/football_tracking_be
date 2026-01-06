from sqlalchemy import select, func
from sqlalchemy.orm import Session, aliased

from modules.match.models.goal_model import GoalModel
from modules.match.models.match_model import MatchModel
from modules.ranking.models.ranking_model import RankingModel
from modules.team.models.team_model import TeamModel
from modules.tournament.models.league_model import LeagueModel
# Cache (bonus)
from .cache import cache_get, cache_set


# from .db import TeamModel, LeagueModel, MatchModel, GoalModel, RankingModel


def get_player_goals(db: Session, player_id: int, season: str | None = None, league_id: int | None = None):
    key = f"pg:{player_id}:{season or 'all'}:{league_id or 'all'}"
    cached = cache_get(key)
    if cached:
        import json;
        return json.loads(cached)

    q = select(func.count()).select_from(GoalModel).where(GoalModel.playerId == player_id)
    if season or league_id:
        # alăturăm MatchModel pentru a filtra după ligă și (implicit) sezon prin LeagueModel
        q = q.join(MatchModel, MatchModel.id == GoalModel.matchId)
        if league_id:
            # MatchModel nu are leagueId coloană directă; folosim echipa 1
            T1 = aliased(TeamModel)
            q = q.join(T1, T1.id == MatchModel.team1Id).where(T1.leagueId == league_id)
        if season:
            # filtrăm prin LeagueModel (sezonul este pe ligă). Dacă vrei ligă specifică + sezon, rezolvăm league_id deja.
            L1 = aliased(LeagueModel)
            T1 = aliased(TeamModel)
            q = q.join(T1, T1.id == MatchModel.team1Id)
            q = q.join(L1, L1.id == T1.leagueId).where(L1.season == season)

    total = int(db.execute(q).scalar_one())
    scope = f"sezon {season}" if season else "all-time"
    if league_id: scope += " • liga selectată"
    res = {"goals": total, "scope": scope}
    cache_set(key, res, ttl=60)
    return res


def get_points_gap_to_leader(db: Session, league_id: int):
    # RankingModel nu are sezon; sezonalitatea e pe LeagueModel (id-ul ligii E sezonul).
    # Deci primim direct league_id pentru liga (numele+sezonul deja rezolvate).
    key = f"gap:{league_id}"
    cached = cache_get(key)
    if cached:
        import json;
        return json.loads(cached)

    # leader: points DESC, tie-breaker goal diff (goalsScored - goalsConceded)
    diff = (RankingModel.goalsScored - RankingModel.goalsConceded).label("gd")
    leader_q = (select(RankingModel.teamId, RankingModel.points, diff)
                .where(RankingModel.leagueId == league_id)
                .order_by(RankingModel.points.desc(), diff.desc())
                .limit(1))
    leader = db.execute(leader_q).first()
    if not leader:
        return {"found": False}

    res = {"found": True, "leaderTeamId": int(leader.teamId), "leaderPoints": int(leader.points)}
    cache_set(key, res, ttl=30)
    return res


def get_team_points(db: Session, league_id: int, team_id: int):
    row = db.execute(
        select(RankingModel.points)
        .where(RankingModel.leagueId == league_id, RankingModel.teamId == team_id)
    ).first()
    return int(row.points) if row else None
