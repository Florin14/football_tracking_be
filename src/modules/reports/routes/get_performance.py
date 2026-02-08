from datetime import date, datetime, time
from typing import Optional

from fastapi import Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from constants.player_positions import PlayerPositions
from extensions.sqlalchemy import get_db
from project_helpers.dependencies import JwtRequired
from modules.match.models.match_model import MatchModel
from modules.match.services.match_status import match_is_completed_expr
from modules.match.models.goal_model import GoalModel
from modules.player.models.player_model import PlayerModel
from modules.reports.models.report_schemas import (
    PerformanceMonthlyWins,
    PerformancePlayerStat,
    PerformancePositionStat,
    PerformanceReportResponse,
    PerformanceSummary,
    PerformanceTrendItem,
    ReportTeamItem,
)
from modules.team.models.team_model import TeamModel
from .router import router


def _resolve_team(db: Session, team_id: Optional[int]) -> TeamModel:
    team = None
    if team_id is not None:
        team = db.query(TeamModel).filter(TeamModel.id == team_id).first()
    if not team:
        team = db.query(TeamModel).filter(TeamModel.isDefault.is_(True)).first()
    if not team:
        team = db.query(TeamModel).filter(func.lower(TeamModel.name) == "base camp").first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team


def _build_date_range(from_date: Optional[date], to_date: Optional[date]) -> tuple[Optional[datetime], Optional[datetime]]:
    start_dt = datetime.combine(from_date, time.min) if from_date else None
    end_dt = datetime.combine(to_date, time.max) if to_date else None
    return start_dt, end_dt


@router.get("/performance", response_model=PerformanceReportResponse, dependencies=[Depends(JwtRequired())])
async def get_performance_report(
    team_id: Optional[int] = Query(None, alias="teamId"),
    league_id: Optional[int] = Query(None, alias="leagueId"),
    from_date: Optional[date] = Query(None, alias="from"),
    to_date: Optional[date] = Query(None, alias="to"),
    db: Session = Depends(get_db),
):
    team = _resolve_team(db, team_id)

    start_dt, end_dt = _build_date_range(from_date, to_date)

    finished_filter = match_is_completed_expr(MatchModel)
    query = db.query(MatchModel).filter(
        finished_filter,
        or_(MatchModel.team1Id == team.id, MatchModel.team2Id == team.id),
    )
    if league_id is not None:
        query = query.filter(MatchModel.leagueId == league_id)
    if start_dt is not None:
        query = query.filter(MatchModel.timestamp >= start_dt)
    if end_dt is not None:
        query = query.filter(MatchModel.timestamp <= end_dt)

    matches = query.order_by(MatchModel.timestamp.asc()).all()

    wins = draws = losses = 0
    goals_for = goals_against = 0
    clean_sheets = 0
    biggest_win = None
    biggest_loss = None
    biggest_win_diff = None
    biggest_loss_diff = None

    trend = []
    for match in matches:
        score1 = match.scoreTeam1 or 0
        score2 = match.scoreTeam2 or 0
        if match.team1Id == team.id:
            gf, ga = score1, score2
        else:
            gf, ga = score2, score1
        goals_for += gf
        goals_against += ga
        if ga == 0:
            clean_sheets += 1
        if gf > ga:
            wins += 1
            diff = gf - ga
            if biggest_win_diff is None or diff > biggest_win_diff:
                biggest_win_diff = diff
                biggest_win = f"{gf}-{ga}"
        elif gf < ga:
            losses += 1
            diff = ga - gf
            if biggest_loss_diff is None or diff > biggest_loss_diff:
                biggest_loss_diff = diff
                biggest_loss = f"{gf}-{ga}"
        else:
            draws += 1

        trend.append(PerformanceTrendItem(
            label=match.timestamp.strftime("%d %b"),
            goalsFor=gf,
            goalsAgainst=ga,
        ))

    matches_played = len(matches)
    avg_goals_for = round(goals_for / matches_played, 2) if matches_played else 0.0
    avg_goals_against = round(goals_against / matches_played, 2) if matches_played else 0.0

    form_last5 = []
    for match in sorted(matches, key=lambda m: m.timestamp, reverse=True)[:5]:
        score1 = match.scoreTeam1 or 0
        score2 = match.scoreTeam2 or 0
        if match.team1Id == team.id:
            gf, ga = score1, score2
        else:
            gf, ga = score2, score1
        if gf > ga:
            form_last5.append("W")
        elif gf < ga:
            form_last5.append("L")
        else:
            form_last5.append("D")

    match_ids = [match.id for match in matches]
    goal_rows = []
    if match_ids:
        goal_rows = (
            db.query(
                GoalModel.playerId,
                func.count(GoalModel.id).label("goals"),
            )
            .filter(
                GoalModel.teamId == team.id,
                GoalModel.matchId.in_(match_ids),
            )
            .group_by(GoalModel.playerId)
            .all()
        )

    player_ids = [row[0] for row in goal_rows]
    players_by_id = {
        player.id: player
        for player in db.query(PlayerModel).filter(PlayerModel.id.in_(player_ids)).all()
    } if player_ids else {}

    top_scorers = sorted(
        [
            PerformancePlayerStat(
                playerId=player_id,
                name=(players_by_id.get(player_id).name if players_by_id.get(player_id) else "Unknown"),
                goals=goals,
            )
            for player_id, goals in goal_rows
        ],
        key=lambda item: item.goals,
        reverse=True,
    )[:5]

    team_players = db.query(PlayerModel).filter(PlayerModel.teamId == team.id).all()
    position_counts = {
        PlayerPositions.GOALKEEPER.value: 0,
        PlayerPositions.DEFENDER.value: 0,
        PlayerPositions.MIDFIELDER.value: 0,
        PlayerPositions.FORWARD.value: 0,
    }
    for player in team_players:
        position_counts[player.position.value] = position_counts.get(player.position.value, 0) + 1

    goals_by_position = {
        PlayerPositions.GOALKEEPER.value: 0,
        PlayerPositions.DEFENDER.value: 0,
        PlayerPositions.MIDFIELDER.value: 0,
        PlayerPositions.FORWARD.value: 0,
    }
    if match_ids:
        rows = (
            db.query(PlayerModel.position, func.count(GoalModel.id))
            .join(GoalModel, GoalModel.playerId == PlayerModel.id)
            .filter(
                GoalModel.teamId == team.id,
                GoalModel.matchId.in_(match_ids),
            )
            .group_by(PlayerModel.position)
            .all()
        )
        for position, goals in rows:
            goals_by_position[position.value] = goals

    position_label_map = {
        PlayerPositions.GOALKEEPER.value: "Goalkeeper",
        PlayerPositions.DEFENDER.value: "Defender",
        PlayerPositions.MIDFIELDER.value: "Midfielder",
        PlayerPositions.FORWARD.value: "Forward",
    }
    position_stats = [
        PerformancePositionStat(
            position=position_label_map[position_key],
            goals=goals_by_position.get(position_key, 0),
            players=position_counts.get(position_key, 0),
        )
        for position_key in [
            PlayerPositions.GOALKEEPER.value,
            PlayerPositions.DEFENDER.value,
            PlayerPositions.MIDFIELDER.value,
            PlayerPositions.FORWARD.value,
        ]
    ]

    monthly_wins = {}
    for match in matches:
        score1 = match.scoreTeam1 or 0
        score2 = match.scoreTeam2 or 0
        if match.team1Id == team.id:
            gf, ga = score1, score2
        else:
            gf, ga = score2, score1
        if gf <= ga:
            continue
        month_key = match.timestamp.strftime("%Y-%m")
        monthly_wins[month_key] = monthly_wins.get(month_key, 0) + 1

    monthly_wins_items = [
        PerformanceMonthlyWins(
            month=month,
            label=datetime.strptime(month, "%Y-%m").strftime("%b %y"),
            wins=wins_count,
        )
        for month, wins_count in sorted(monthly_wins.items())
    ]

    summary = PerformanceSummary(
        matchesPlayed=matches_played,
        wins=wins,
        draws=draws,
        losses=losses,
        goalsFor=goals_for,
        goalsAgainst=goals_against,
        goalDiff=goals_for - goals_against,
        cleanSheets=clean_sheets,
        avgGoalsFor=avg_goals_for,
        avgGoalsAgainst=avg_goals_against,
        biggestWin=biggest_win,
        biggestLoss=biggest_loss,
        formLast5=form_last5,
    )

    return PerformanceReportResponse(
        team=ReportTeamItem(id=team.id, name=team.name),
        summary=summary,
        trend=trend,
        positionStats=position_stats,
        topScorers=top_scorers,
        topAssists=[],
        monthlyWins=monthly_wins_items,
    )
