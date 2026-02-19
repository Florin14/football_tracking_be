"""Agent orchestrator - handles user messages and returns responses."""
from __future__ import annotations

from sqlalchemy.orm import Session

from constants.card_type import CardType
from modules.agent.nlu import detect_intent, extract_entity_name
from modules.agent.tools import (
    get_top_scorers,
    get_top_assists,
    get_player_goals,
    get_player_stats,
    get_standings,
    get_next_matches,
    get_recent_results,
    get_most_cards,
    get_team_info,
    resolve_player,
    resolve_team,
    _get_default_team,
)


def _pick_best(candidates: list[dict]) -> dict | None:
    if not candidates:
        return None
    top = candidates[0]
    if top.get("score", 0) >= 0.4:
        return top
    return None


def _suggested_for(intent: str) -> list[str]:
    """Return contextual follow-up questions."""
    mapping = {
        "greeting": [
            "Cine e golgheterul?",
            "Care e clasamentul?",
            "Cand e urmatorul meci?",
            "Ce poti sa faci?",
        ],
        "help": [
            "Cine are cele mai multe goluri?",
            "Care e clasamentul?",
            "Cand e urmatorul meci?",
            "Rezultatele ultimelor meciuri",
        ],
        "top_scorers": [
            "Cine are cele mai multe assisturi?",
            "Care e clasamentul?",
            "Cine are cele mai multe cartonase?",
        ],
        "top_assists": [
            "Cine e golgheterul?",
            "Care e clasamentul?",
            "Rezultatele ultimelor meciuri",
        ],
        "standings": [
            "Cine e golgheterul?",
            "Cand e urmatorul meci?",
            "Rezultatele ultimelor meciuri",
        ],
        "next_matches": [
            "Rezultatele ultimelor meciuri",
            "Care e clasamentul?",
            "Informatii despre echipa",
        ],
        "recent_results": [
            "Cand e urmatorul meci?",
            "Cine e golgheterul?",
            "Care e clasamentul?",
        ],
        "most_cards": [
            "Cine e golgheterul?",
            "Cine are cele mai multe assisturi?",
            "Care e clasamentul?",
        ],
        "player_goals": [
            "Cine e golgheterul?",
            "Care e clasamentul?",
            "Rezultatele ultimelor meciuri",
        ],
        "player_stats": [
            "Cine e golgheterul?",
            "Care e clasamentul?",
            "Rezultatele ultimelor meciuri",
        ],
        "team_info": [
            "Cine e golgheterul?",
            "Cand e urmatorul meci?",
            "Care e clasamentul?",
        ],
    }
    return mapping.get(intent, [
        "Cine e golgheterul?",
        "Care e clasamentul?",
        "Cand e urmatorul meci?",
    ])


def handle_message(db: Session, user_text: str) -> dict:
    intent = detect_intent(user_text)
    entity_name = extract_entity_name(user_text, intent)

    # --- Greeting ---
    if intent == "greeting":
        return {
            "type": "answer",
            "text": "Salut! Sunt asistentul tau de fotbal. Intreaba-ma despre goluri, clasamente, meciuri, sau orice legat de echipa ta!",
            "suggestedQuestions": _suggested_for("greeting"),
        }

    # --- Help ---
    if intent == "help":
        return {
            "type": "answer",
            "text": (
                "Pot sa te ajut cu urmatoarele:\n\n"
                "- Cine e golgheterul? (top marcatori)\n"
                "- Cate goluri are [jucator]?\n"
                "- Statistici [jucator]\n"
                "- Care e clasamentul?\n"
                "- Cand e urmatorul meci?\n"
                "- Rezultatele ultimelor meciuri\n"
                "- Cine are cele mai multe cartonase?\n"
                "- Cine are cele mai multe assisturi?\n"
                "- Informatii despre echipa"
            ),
            "suggestedQuestions": _suggested_for("help"),
        }

    # --- Top scorers ---
    if intent == "top_scorers":
        data = get_top_scorers(db)
        if not data["found"]:
            return {
                "type": "answer",
                "text": "Nu am gasit goluri inregistrate inca.",
                "suggestedQuestions": _suggested_for("top_scorers"),
            }
        lines = []
        for i, p in enumerate(data["players"], 1):
            emoji = ["", "", ""][i - 1] if i <= 3 else f"{i}."
            lines.append(f"{emoji} {p['name']} - {p['goals']} goluri")
        return {
            "type": "answer",
            "text": "Top marcatori:\n\n" + "\n".join(lines),
            "suggestedQuestions": _suggested_for("top_scorers"),
            "links": [{"label": "Vezi jucatorii", "url": "/my-squad"}],
        }

    # --- Top assists ---
    if intent == "top_assists":
        data = get_top_assists(db)
        if not data["found"]:
            return {
                "type": "answer",
                "text": "Nu am gasit assisturi inregistrate inca.",
                "suggestedQuestions": _suggested_for("top_assists"),
            }
        lines = []
        for i, p in enumerate(data["players"], 1):
            emoji = ["", "", ""][i - 1] if i <= 3 else f"{i}."
            lines.append(f"{emoji} {p['name']} - {p['assists']} assisturi")
        return {
            "type": "answer",
            "text": "Top pasatori decisivi:\n\n" + "\n".join(lines),
            "suggestedQuestions": _suggested_for("top_assists"),
            "links": [{"label": "Vezi jucatorii", "url": "/my-squad"}],
        }

    # --- Player goals ---
    if intent == "player_goals":
        if not entity_name:
            return {
                "type": "clarify",
                "text": "Despre ce jucator vorbesti? Scrie numele jucatorului.",
                "suggestedQuestions": _suggested_for("player_goals"),
            }
        candidates = resolve_player(db, entity_name)
        player = _pick_best(candidates)
        if not player:
            return {
                "type": "clarify",
                "text": f"Nu am gasit niciun jucator cu numele \"{entity_name}\". Poti incerca din nou?",
                "suggestedQuestions": ["Cine e golgheterul?", "Informatii despre echipa"],
            }
        data = get_player_goals(db, player["id"])
        return {
            "type": "answer",
            "text": f"{player['name']} are {data['goals']} goluri.",
            "suggestedQuestions": [
                f"Statistici {player['name']}",
                "Cine e golgheterul?",
                "Care e clasamentul?",
            ],
            "links": [{"label": f"Profil {player['name']}", "url": f"/my-squad/{player['id']}"}],
        }

    # --- Player stats ---
    if intent == "player_stats":
        if not entity_name:
            return {
                "type": "clarify",
                "text": "Despre ce jucator vorbesti? Scrie numele jucatorului.",
                "suggestedQuestions": _suggested_for("player_stats"),
            }
        candidates = resolve_player(db, entity_name)
        player = _pick_best(candidates)
        if not player:
            return {
                "type": "clarify",
                "text": f"Nu am gasit niciun jucator cu numele \"{entity_name}\". Poti incerca din nou?",
                "suggestedQuestions": ["Cine e golgheterul?", "Informatii despre echipa"],
            }
        data = get_player_stats(db, player["id"])
        if not data["found"]:
            return {
                "type": "answer",
                "text": f"Nu am gasit statistici pentru {player['name']}.",
                "suggestedQuestions": _suggested_for("player_stats"),
            }
        lines = [
            f"Statistici {data['name']}:\n",
            f"Pozitie: {data['position']}",
            f"Echipa: {data['team']}",
        ]
        if data["shirtNumber"]:
            lines.append(f"Numar tricou: #{data['shirtNumber']}")
        if data["rating"]:
            lines.append(f"Rating: {data['rating']}")
        lines.append(f"Goluri: {data['goals']}")
        lines.append(f"Assisturi: {data['assists']}")
        lines.append(f"Cartonase galbene: {data['yellowCards']}")
        lines.append(f"Cartonase rosii: {data['redCards']}")
        lines.append(f"Prezente: {data['appearances']}")

        return {
            "type": "answer",
            "text": "\n".join(lines),
            "suggestedQuestions": [
                f"Cate goluri are {data['name']}?",
                "Cine e golgheterul?",
                "Care e clasamentul?",
            ],
            "links": [{"label": f"Profil {data['name']}", "url": f"/my-squad/{data['playerId']}"}],
        }

    # --- Standings ---
    if intent == "standings":
        data = get_standings(db)
        if not data["found"]:
            return {
                "type": "answer",
                "text": "Nu am gasit clasamente inca.",
                "suggestedQuestions": _suggested_for("standings"),
            }
        header = f"Clasament {data['leagueName']}"
        if data.get("season"):
            header += f" ({data['season']})"
        header += ":\n"
        lines = [header]
        for r in data["rankings"][:10]:
            gd = f"+{r['gd']}" if r["gd"] > 0 else str(r["gd"])
            lines.append(
                f"{r['position']}. {r['team']} - {r['points']}p "
                f"({r['won']}V {r['drawn']}E {r['lost']}I, {gd})"
            )
        return {
            "type": "answer",
            "text": "\n".join(lines),
            "suggestedQuestions": _suggested_for("standings"),
            "links": [{"label": "Vezi clasamentul complet", "url": "/rankings"}],
        }

    # --- Next matches ---
    if intent == "next_matches":
        team = _get_default_team(db)
        team_id = team.id if team else None
        data = get_next_matches(db, team_id=team_id)
        if not data["found"]:
            return {
                "type": "answer",
                "text": "Nu sunt meciuri programate in viitor.",
                "suggestedQuestions": _suggested_for("next_matches"),
            }
        lines = ["Urmatoarele meciuri:\n"]
        for m in data["matches"]:
            line = f"  {m['team1']} vs {m['team2']} - {m['date']}"
            if m.get("league"):
                line += f" ({m['league']})"
            lines.append(line)
        return {
            "type": "answer",
            "text": "\n".join(lines),
            "suggestedQuestions": _suggested_for("next_matches"),
            "links": [{"label": "Vezi calendarul", "url": "/matches"}],
        }

    # --- Recent results ---
    if intent == "recent_results":
        team = _get_default_team(db)
        team_id = team.id if team else None
        data = get_recent_results(db, team_id=team_id)
        if not data["found"]:
            return {
                "type": "answer",
                "text": "Nu am gasit rezultate recente.",
                "suggestedQuestions": _suggested_for("recent_results"),
            }
        lines = ["Rezultate recente:\n"]
        for m in data["matches"]:
            line = f"  {m['team1']} {m['score']} {m['team2']} ({m['date']})"
            if m.get("league"):
                line += f" - {m['league']}"
            lines.append(line)
        return {
            "type": "answer",
            "text": "\n".join(lines),
            "suggestedQuestions": _suggested_for("recent_results"),
            "links": [{"label": "Vezi meciurile", "url": "/matches"}],
        }

    # --- Most cards ---
    if intent == "most_cards":
        # Detect if asking specifically about yellow or red
        text_lower = user_text.lower()
        card_type = None
        if "galben" in text_lower:
            card_type = CardType.YELLOW
        elif "rosu" in text_lower or "rosii" in text_lower:
            card_type = CardType.RED

        data = get_most_cards(db, card_type=card_type)
        if not data["found"]:
            label = f"cartonase{data.get('typeLabel', '')}" if data.get("typeLabel") else "cartonase"
            return {
                "type": "answer",
                "text": f"Nu am gasit {label} inregistrate.",
                "suggestedQuestions": _suggested_for("most_cards"),
            }
        type_label = data.get("typeLabel", "")
        lines = [f"Jucatori cu cele mai multe cartonase{type_label}:\n"]
        for i, p in enumerate(data["players"], 1):
            lines.append(f"{i}. {p['name']} - {p['cards']} cartonase")
        return {
            "type": "answer",
            "text": "\n".join(lines),
            "suggestedQuestions": _suggested_for("most_cards"),
            "links": [{"label": "Vezi jucatorii", "url": "/my-squad"}],
        }

    # --- Team info ---
    if intent == "team_info":
        data = get_team_info(db)
        if not data["found"]:
            return {
                "type": "answer",
                "text": "Nu am gasit informatii despre echipa.",
                "suggestedQuestions": _suggested_for("team_info"),
            }
        lines = [
            f"Echipa: {data['name']}",
        ]
        if data.get("location"):
            lines.append(f"Locatie: {data['location']}")
        lines.append(f"Numar jucatori: {data['playerCount']}")
        return {
            "type": "answer",
            "text": "\n".join(lines),
            "suggestedQuestions": _suggested_for("team_info"),
            "links": [
                {"label": "Vezi echipele", "url": "/teams"},
                {"label": "Vezi jucatorii", "url": "/my-squad"},
            ],
        }

    # --- Unknown intent ---
    return {
        "type": "answer",
        "text": "Nu am inteles intrebarea. Incearca sa ma intrebi despre goluri, clasament, meciuri sau jucatori!",
        "suggestedQuestions": [
            "Cine e golgheterul?",
            "Care e clasamentul?",
            "Cand e urmatorul meci?",
            "Ce poti sa faci?",
        ],
    }
