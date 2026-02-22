"""Execute CRUD operations from collected agent data."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from constants.card_type import CardType
from constants.match_state import MatchState
from modules.match.models.card_model import CardModel
from modules.match.models.goal_model import GoalModel
from modules.match.models.match_model import MatchModel
from modules.player.models.player_model import PlayerModel
from modules.team.models.team_model import TeamModel
from modules.tournament.models.league_model import LeagueModel
from modules.tournament.models.league_team_model import LeagueTeamModel
from modules.ranking.models.ranking_model import RankingModel


def execute_crud(db: Session, user, intent: str, data: dict) -> dict:
    """Route to the correct executor based on intent."""
    executors = {
        "crud_add_match": _execute_create_match,
        "crud_edit_match": _execute_update_match,
        "crud_add_team": _execute_create_team,
        "crud_edit_team": _execute_update_team,
        "crud_add_goal": _execute_add_goal,
        "crud_add_card": _execute_add_card,
    }
    executor = executors.get(intent)
    if not executor:
        return {"success": False, "message": f"Intent necunoscut: {intent}", "id": None}
    try:
        return executor(db, data)
    except Exception as e:
        db.rollback()
        return {"success": False, "message": str(e), "id": None}


def _execute_create_match(db: Session, data: dict) -> dict:
    team1_info = data["team1"]  # {"id": ..., "name": ...}
    team2_info = data["team2"]

    team1 = db.query(TeamModel).filter(TeamModel.id == team1_info["id"]).first()
    team2 = db.query(TeamModel).filter(TeamModel.id == team2_info["id"]).first()
    if not team1 or not team2:
        return {"success": False, "message": "Una din echipe nu a fost gasita.", "id": None}
    if team1.id == team2.id:
        return {"success": False, "message": "Echipele trebuie sa fie diferite.", "id": None}

    timestamp = datetime.fromisoformat(data["timestamp"])

    league_id = None
    if data.get("league"):
        league_info = data["league"]
        league = db.query(LeagueModel).filter(LeagueModel.id == league_info["id"]).first()
        if league:
            league_id = league.id

    location = data.get("location") if isinstance(data.get("location"), str) else None

    match = MatchModel(
        team1Id=team1.id,
        team2Id=team2.id,
        timestamp=timestamp,
        leagueId=league_id,
        state=MatchState.SCHEDULED,
    )
    if location:
        match.location = location
    db.add(match)
    db.commit()
    db.refresh(match)

    return {
        "success": True,
        "message": f"Meciul {team1.name} vs {team2.name} a fost programat pe {timestamp.strftime('%d %b %Y, %H:%M')}.",
        "id": match.id,
    }


def _execute_update_match(db: Session, data: dict) -> dict:
    match_info = data["match"]
    match = db.query(MatchModel).filter(MatchModel.id == match_info["id"]).first()
    if not match:
        return {"success": False, "message": "Meciul nu a fost gasit.", "id": None}

    field = data.get("field_to_edit", "")
    new_value = data.get("new_value", "")

    if field == "locatie":
        match.location = new_value
    elif field == "data":
        for fmt in ("%Y-%m-%d %H:%M", "%d.%m.%Y %H:%M", "%d/%m/%Y %H:%M"):
            try:
                match.timestamp = datetime.strptime(new_value, fmt)
                break
            except ValueError:
                continue
        else:
            return {"success": False, "message": "Format data invalid.", "id": match.id}
    elif field == "liga":
        from modules.agent.tools import resolve_league
        candidates = resolve_league(db, new_value)
        if candidates:
            match.leagueId = candidates[0]["id"]
        else:
            return {"success": False, "message": f"Nu am gasit liga '{new_value}'.", "id": match.id}
    else:
        return {"success": False, "message": f"Camp necunoscut: {field}", "id": match.id}

    db.commit()
    return {"success": True, "message": f"Meciul a fost actualizat ({field}).", "id": match.id}


def _execute_create_team(db: Session, data: dict) -> dict:
    name = data["name"]

    # Check uniqueness
    existing = db.query(TeamModel).filter(TeamModel.name == name).first()
    if existing:
        return {"success": False, "message": f"Exista deja o echipa cu numele '{name}'.", "id": None}

    league_info = data.get("league")
    if not league_info:
        return {"success": False, "message": "Liga este obligatorie.", "id": None}

    league = db.query(LeagueModel).filter(LeagueModel.id == league_info["id"]).first()
    if not league:
        return {"success": False, "message": "Liga nu a fost gasita.", "id": None}

    team = TeamModel(
        name=name,
        description=data.get("description") if isinstance(data.get("description"), str) else None,
    )
    db.add(team)
    db.flush()

    # Link to league
    league_team = LeagueTeamModel(leagueId=league.id, teamId=team.id)
    db.add(league_team)

    # Create ranking entry
    ranking = RankingModel(
        leagueId=league.id,
        teamId=team.id,
        gamesPlayed=0,
        gamesWon=0,
        gamesTied=0,
        gamesLost=0,
        goalsScored=0,
        goalsConceded=0,
        points=0,
    )
    db.add(ranking)

    db.commit()
    db.refresh(team)

    return {
        "success": True,
        "message": f"Echipa '{name}' a fost creata si adaugata in liga '{league.name}'.",
        "id": team.id,
    }


def _execute_update_team(db: Session, data: dict) -> dict:
    team_info = data["team"]
    team = db.query(TeamModel).filter(TeamModel.id == team_info["id"]).first()
    if not team:
        return {"success": False, "message": "Echipa nu a fost gasita.", "id": None}

    field = data.get("field_to_edit", "")
    new_value = data.get("new_value", "")

    if field == "nume":
        existing = db.query(TeamModel).filter(TeamModel.name == new_value, TeamModel.id != team.id).first()
        if existing:
            return {"success": False, "message": f"Exista deja o echipa cu numele '{new_value}'.", "id": team.id}
        team.name = new_value
    elif field == "descriere":
        team.description = new_value
    else:
        return {"success": False, "message": f"Camp necunoscut: {field}", "id": team.id}

    db.commit()
    return {"success": True, "message": f"Echipa '{team.name}' a fost actualizata ({field}).", "id": team.id}


def _execute_add_goal(db: Session, data: dict) -> dict:
    match_info = data["match"]
    player_info = data["player"]
    team_info = data["team"]

    match = db.query(MatchModel).filter(MatchModel.id == match_info["id"]).first()
    if not match:
        return {"success": False, "message": "Meciul nu a fost gasit.", "id": None}

    player = db.query(PlayerModel).filter(PlayerModel.id == player_info["id"]).first()
    if not player:
        return {"success": False, "message": "Jucatorul nu a fost gasit.", "id": None}

    team = db.query(TeamModel).filter(TeamModel.id == team_info["id"]).first()
    if not team:
        return {"success": False, "message": "Echipa nu a fost gasita.", "id": None}

    # Validate team is in the match
    if team.id not in (match.team1Id, match.team2Id):
        return {"success": False, "message": f"Echipa '{team.name}' nu joaca in acest meci.", "id": None}

    minute = data.get("minute")
    assist_info = data.get("assist")
    assist_player_id = assist_info["id"] if assist_info and isinstance(assist_info, dict) else None

    goal = GoalModel(
        matchId=match.id,
        playerId=player.id,
        playerNameSnapshot=player.name,
        teamId=team.id,
        minute=minute if isinstance(minute, int) else None,
        assistPlayerId=assist_player_id,
        assistPlayerNameSnapshot=(
            db.query(PlayerModel).filter(PlayerModel.id == assist_player_id).first().name
            if assist_player_id else None
        ),
        timestamp=datetime.utcnow(),
    )
    db.add(goal)

    # Update match score
    if team.id == match.team1Id:
        match.scoreTeam1 = (match.scoreTeam1 or 0) + 1
    else:
        match.scoreTeam2 = (match.scoreTeam2 or 0) + 1

    # Mark match as finished if it was scheduled
    if match.state == MatchState.SCHEDULED:
        match.state = MatchState.ONGOING

    db.commit()
    db.refresh(goal)

    msg = f"Gol inregistrat: {player.name}"
    if minute and isinstance(minute, int):
        msg += f" (min. {minute})"
    msg += f" - {match.team1.name if match.team1 else 'N/A'} vs {match.team2.name if match.team2 else 'N/A'}"

    return {"success": True, "message": msg, "id": goal.id}


def _execute_add_card(db: Session, data: dict) -> dict:
    match_info = data["match"]
    player_info = data["player"]
    team_info = data["team"]

    match = db.query(MatchModel).filter(MatchModel.id == match_info["id"]).first()
    if not match:
        return {"success": False, "message": "Meciul nu a fost gasit.", "id": None}

    player = db.query(PlayerModel).filter(PlayerModel.id == player_info["id"]).first()
    if not player:
        return {"success": False, "message": "Jucatorul nu a fost gasit.", "id": None}

    team = db.query(TeamModel).filter(TeamModel.id == team_info["id"]).first()
    if not team:
        return {"success": False, "message": "Echipa nu a fost gasita.", "id": None}

    if team.id not in (match.team1Id, match.team2Id):
        return {"success": False, "message": f"Echipa '{team.name}' nu joaca in acest meci.", "id": None}

    card_type_str = data.get("card_type", "galben").lower()
    card_type = CardType.RED if card_type_str in ("rosu", "red") else CardType.YELLOW

    minute = data.get("minute")

    card = CardModel(
        matchId=match.id,
        playerId=player.id,
        teamId=team.id,
        cardType=card_type,
        minute=minute if isinstance(minute, int) else None,
        timestamp=datetime.utcnow(),
    )
    db.add(card)
    db.commit()
    db.refresh(card)

    card_label = "rosu" if card_type == CardType.RED else "galben"
    msg = f"Cartonas {card_label} pentru {player.name}"
    if minute and isinstance(minute, int):
        msg += f" (min. {minute})"

    return {"success": True, "message": msg, "id": card.id}
