from fastapi import Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from extensions.sqlalchemy import get_db
from project_helpers.dependencies import GetCurrentUser
from modules.match.models.match_model import MatchModel
from modules.match.services.match_status import is_match_completed
from modules.tournament.models.league_model import LeagueModel
from modules.tournament.models.league_team_model import LeagueTeamModel
from modules.tournament.models.tournament_group_match_model import TournamentGroupMatchModel
from modules.tournament.models.tournament_group_model import TournamentGroupModel
from modules.tournament.models.tournament_group_team_model import TournamentGroupTeamModel
from modules.tournament.models.tournament_knockout_match_model import TournamentKnockoutMatchModel
from modules.tournament.models.tournament_model import TournamentModel
from modules.tournament.models.tournament_schemas import (
    LeagueStandingsResponse,
    TournamentGroupStandingsItem,
    TournamentKnockoutMatchItem,
)

from .router import router


def _build_group_standings(
    group: TournamentGroupModel,
    matches: list[MatchModel],
    league_team_ids: set[int],
) -> list[dict]:
    standings: dict[int, dict] = {}
    for group_team in group.teams:
        team = group_team.team
        if not team or team.id not in league_team_ids:
            continue
        standings[team.id] = {
            "id": team.id,
            "name": team.name,
            "description": team.description,
            "logo": team.logo,
            "playerCount": 0,
            "points": 0,
            "goalsFor": 0,
            "goalsAgainst": 0,
            "wins": 0,
            "draws": 0,
            "losses": 0,
        }

    for match in matches:
        if not is_match_completed(match):
            continue
        team1 = standings.get(match.team1Id)
        team2 = standings.get(match.team2Id)
        if not team1 or not team2:
            continue
        score1 = match.scoreTeam1 or 0
        score2 = match.scoreTeam2 or 0
        team1["goalsFor"] += score1
        team1["goalsAgainst"] += score2
        team2["goalsFor"] += score2
        team2["goalsAgainst"] += score1

        if score1 > score2:
            team1["wins"] += 1
            team2["losses"] += 1
            team1["points"] += 3
        elif score2 > score1:
            team2["wins"] += 1
            team1["losses"] += 1
            team2["points"] += 3
        else:
            team1["draws"] += 1
            team2["draws"] += 1
            team1["points"] += 1
            team2["points"] += 1

    def sort_key(item: dict):
        goal_diff = item["goalsFor"] - item["goalsAgainst"]
        return (-item["points"], -goal_diff, -item["goalsFor"], item["name"].lower())

    return sorted(standings.values(), key=sort_key)


@router.get("/leagues/{league_id}/standings", response_model=LeagueStandingsResponse)
async def get_league_standings(
    league_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(GetCurrentUser()),
):
    league = db.query(LeagueModel).filter(LeagueModel.id == league_id).first()
    if not league:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"League with ID {league_id} not found",
        )

    tournament = (
        db.query(TournamentModel)
        .filter(TournamentModel.id == league.tournamentId)
        .first()
    )
    if not tournament:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tournament with ID {league.tournamentId} not found",
        )

    league_team_ids = {
        team_id
        for (team_id,) in db.query(LeagueTeamModel.teamId)
        .filter(LeagueTeamModel.leagueId == league_id)
        .all()
    }

    groups = (
        db.query(TournamentGroupModel)
        .options(
            joinedload(TournamentGroupModel.teams)
            .joinedload(TournamentGroupTeamModel.team)
        )
        .filter(TournamentGroupModel.tournamentId == tournament.id)
        .order_by(
            func.lower(TournamentGroupModel.name),
        )
        .all()
    )

    group_ids = [group.id for group in groups]
    group_matches = (
        db.query(TournamentGroupMatchModel)
        .join(MatchModel, TournamentGroupMatchModel.matchId == MatchModel.id)
        .options(joinedload(TournamentGroupMatchModel.match))
        .filter(
            TournamentGroupMatchModel.groupId.in_(group_ids),
            MatchModel.leagueId == league_id,
        )
        .all()
        if group_ids
        else []
    )
    matches_by_group: dict[int, list[MatchModel]] = {}
    for item in group_matches:
        if not item.match:
            continue
        matches_by_group.setdefault(item.groupId, []).append(item.match)

    group_items = []
    for group in groups:
        standings = _build_group_standings(group, matches_by_group.get(group.id, []), league_team_ids)
        group_items.append(TournamentGroupStandingsItem(
            groupId=group.id,
            groupName=group.name,
            teams=standings,
        ))

    knockout_matches = (
        db.query(TournamentKnockoutMatchModel)
        .join(MatchModel, TournamentKnockoutMatchModel.matchId == MatchModel.id)
        .options(joinedload(TournamentKnockoutMatchModel.match))
        .filter(
            TournamentKnockoutMatchModel.tournamentId == tournament.id,
            MatchModel.leagueId == league_id,
        )
        .order_by(
            TournamentKnockoutMatchModel.order.is_(None),
            TournamentKnockoutMatchModel.order,
            TournamentKnockoutMatchModel.id,
        )
        .all()
    )

    knockout_items = []
    for knockout in knockout_matches:
        match = knockout.match
        if not match:
            continue
        knockout_items.append(TournamentKnockoutMatchItem(
            id=knockout.id,
            matchId=match.id,
            round=knockout.round,
            order=knockout.order,
            team1Id=match.team1Id,
            team2Id=match.team2Id,
            scoreTeam1=match.scoreTeam1,
            scoreTeam2=match.scoreTeam2,
            state=match.state.value if hasattr(match.state, "value") else str(match.state),
            timestamp=match.timestamp,
        ))

    return LeagueStandingsResponse(
        league=league,
        tournamentId=tournament.id,
        formatType=tournament.formatType,
        groupCount=tournament.groupCount,
        teamsPerGroup=tournament.teamsPerGroup,
        hasKnockout=tournament.hasKnockout,
        groups=group_items,
        knockoutMatches=knockout_items,
    )
