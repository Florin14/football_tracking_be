from sqlalchemy.orm import Session

from modules.match.models import MatchModel
from modules.match.services.match_status import match_is_completed_expr
from modules.ranking.models import RankingModel


def _ensure_ranking_row(db: Session, league_id: int, team_id: int) -> RankingModel:
    ranking = (
        db.query(RankingModel)
        .filter(RankingModel.teamId == team_id, RankingModel.leagueId == league_id)
        .first()
    )
    if not ranking:
        ranking = RankingModel(teamId=team_id, leagueId=league_id)
        db.add(ranking)
        db.flush()
    return ranking


def _recalculate_team_ranking(db: Session, league_id: int, team_id: int) -> None:
    matches = (
        db.query(MatchModel)
        .filter(
            match_is_completed_expr(MatchModel),
            MatchModel.leagueId == league_id,
            (MatchModel.team1Id == team_id) | (MatchModel.team2Id == team_id),
        )
        .all()
    )

    wins = 0
    draws = 0
    losses = 0
    goals_for = 0
    goals_against = 0

    for match in matches:
        score_team1 = match.scoreTeam1 or 0
        score_team2 = match.scoreTeam2 or 0

        if match.team1Id == team_id:
            gf = score_team1
            ga = score_team2
        else:
            gf = score_team2
            ga = score_team1

        goals_for += gf
        goals_against += ga

        if gf > ga:
            wins += 1
        elif gf < ga:
            losses += 1
        else:
            draws += 1

    ranking = _ensure_ranking_row(db, league_id, team_id)
    ranking.gamesPlayed = len(matches)
    ranking.gamesWon = wins
    ranking.gamesLost = losses
    ranking.gamesTied = draws
    ranking.goalsScored = goals_for
    ranking.goalsConceded = goals_against
    ranking.points = wins * 3 + draws


def recalculate_match_rankings(db: Session, match: MatchModel) -> None:
    league_id = match.leagueId
    if league_id is None:
        return

    _recalculate_team_ranking(db, league_id, match.team1Id)
    _recalculate_team_ranking(db, league_id, match.team2Id)
