"""Conversational state machine for CRUD operations via the agent."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from modules.agent.models.agent_crud_session_model import AgentCrudSessionModel
from modules.agent.tools import resolve_player, resolve_team, resolve_league, resolve_match


# --- Flow definitions ---
# Each flow defines the fields to collect, in order.
# type: text, int, team, player, match_ref, league, choice, datetime

_FLOWS = {
    "crud_add_match": {
        "label": "Programeaza meci",
        "fields": [
            {"name": "team1", "type": "team", "prompt": "Care e prima echipa (gazda)?", "required": True},
            {"name": "team2", "type": "team", "prompt": "Care e a doua echipa (oaspete)?", "required": True},
            {"name": "timestamp", "type": "datetime", "prompt": "Cand se joaca meciul? (ex: 2026-03-15 18:00)", "required": True},
            {"name": "location", "type": "text", "prompt": "Unde se joaca? (sau scrie 'skip' pentru a sari)", "required": False},
            {"name": "league", "type": "league", "prompt": "In ce liga? (sau scrie 'skip' pentru amical)", "required": False},
        ],
    },
    "crud_edit_match": {
        "label": "Modifica meci",
        "fields": [
            {"name": "match", "type": "match_ref", "prompt": "Ce meci vrei sa modifici? (scrie 'Echipa A vs Echipa B' sau ID-ul)", "required": True},
            {"name": "field_to_edit", "type": "choice", "prompt": "Ce vrei sa modifici?\n1. Locatie\n2. Data/Ora\n3. Liga", "choices": ["locatie", "data", "liga"], "required": True},
            {"name": "new_value", "type": "dynamic", "prompt": "Care e noua valoare?", "required": True},
        ],
    },
    "crud_add_team": {
        "label": "Adauga echipa",
        "fields": [
            {"name": "name", "type": "text", "prompt": "Cum se numeste echipa?", "required": True},
            {"name": "league", "type": "league", "prompt": "In ce liga sa fie adaugata?", "required": True},
            {"name": "description", "type": "text", "prompt": "O scurta descriere? (sau scrie 'skip')", "required": False},
        ],
    },
    "crud_edit_team": {
        "label": "Modifica echipa",
        "fields": [
            {"name": "team", "type": "team", "prompt": "Ce echipa vrei sa modifici?", "required": True},
            {"name": "field_to_edit", "type": "choice", "prompt": "Ce vrei sa modifici?\n1. Nume\n2. Descriere", "choices": ["nume", "descriere"], "required": True},
            {"name": "new_value", "type": "dynamic", "prompt": "Care e noua valoare?", "required": True},
        ],
    },
    "crud_add_goal": {
        "label": "Adauga gol",
        "fields": [
            {"name": "match", "type": "match_ref", "prompt": "In ce meci? (scrie 'Echipa A vs Echipa B' sau ID-ul)", "required": True},
            {"name": "player", "type": "player", "prompt": "Cine a marcat?", "required": True},
            {"name": "team", "type": "team", "prompt": "Din ce echipa?", "required": True},
            {"name": "minute", "type": "int", "prompt": "In ce minut? (sau scrie 'skip')", "required": False},
            {"name": "assist", "type": "player", "prompt": "Cine a pasat? (sau scrie 'skip')", "required": False},
        ],
    },
    "crud_add_card": {
        "label": "Adauga cartonas",
        "fields": [
            {"name": "match", "type": "match_ref", "prompt": "In ce meci? (scrie 'Echipa A vs Echipa B' sau ID-ul)", "required": True},
            {"name": "player", "type": "player", "prompt": "Cine a primit cartonasul?", "required": True},
            {"name": "team", "type": "team", "prompt": "Din ce echipa?", "required": True},
            {"name": "card_type", "type": "choice", "prompt": "Ce tip de cartonas?\n1. Galben\n2. Rosu", "choices": ["galben", "rosu"], "required": True},
            {"name": "minute", "type": "int", "prompt": "In ce minut? (sau scrie 'skip')", "required": False},
        ],
    },
}

_SKIP_WORDS = {"skip", "sari", "treci", "nu stiu", "-", "n/a"}
_CONFIRM_YES = {"da", "yes", "confirm", "confirma", "ok", "sigur", "corect"}
_CONFIRM_NO = {"nu", "no", "anuleaza", "cancel", "renunt", "renunta", "stop"}


def _is_skip(text: str) -> bool:
    return text.strip().lower() in _SKIP_WORDS


def _is_confirm(text: str) -> Optional[bool]:
    t = text.strip().lower()
    if t in _CONFIRM_YES:
        return True
    if t in _CONFIRM_NO:
        return False
    return None


def _get_next_field(flow_def: dict, collected: dict) -> Optional[dict]:
    """Get the next field that hasn't been collected yet."""
    for field in flow_def["fields"]:
        if field["name"] not in collected:
            return field
    return None


def _validate_and_resolve(db: Session, field_def: dict, value: str) -> dict:
    """Validate and resolve a field value. Returns {"ok": True, "value": ...} or {"ok": False, "error": ...}."""
    field_type = field_def["type"]

    if field_type == "text":
        if not value.strip():
            return {"ok": False, "error": "Valoarea nu poate fi goala."}
        return {"ok": True, "value": value.strip()}

    if field_type == "int":
        try:
            return {"ok": True, "value": int(re.sub(r"\D", "", value))}
        except (ValueError, TypeError):
            return {"ok": False, "error": "Te rog introdu un numar valid."}

    if field_type == "datetime":
        # Try common formats
        for fmt in ("%Y-%m-%d %H:%M", "%d.%m.%Y %H:%M", "%d/%m/%Y %H:%M", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(value.strip(), fmt)
                return {"ok": True, "value": dt.isoformat()}
            except ValueError:
                continue
        return {"ok": False, "error": "Format invalid. Incearca: 2026-03-15 18:00 sau 15.03.2026 18:00"}

    if field_type == "team":
        candidates = resolve_team(db, value)
        if not candidates:
            return {"ok": False, "error": f"Nu am gasit echipa '{value}'. Incearca din nou."}
        best = candidates[0]
        if best.get("score", 0) < 0.3:
            return {"ok": False, "error": f"Nu am gasit echipa '{value}'. Incearca din nou."}
        return {"ok": True, "value": {"id": best["id"], "name": best["name"]}}

    if field_type == "player":
        candidates = resolve_player(db, value)
        if not candidates:
            return {"ok": False, "error": f"Nu am gasit jucatorul '{value}'. Incearca din nou."}
        best = candidates[0]
        if best.get("score", 0) < 0.3:
            return {"ok": False, "error": f"Nu am gasit jucatorul '{value}'. Incearca din nou."}
        return {"ok": True, "value": {"id": best["id"], "name": best["name"]}}

    if field_type == "league":
        candidates = resolve_league(db, value)
        if not candidates:
            return {"ok": False, "error": f"Nu am gasit liga '{value}'. Incearca din nou."}
        best = candidates[0]
        return {"ok": True, "value": {"id": best["id"], "name": best["name"]}}

    if field_type == "match_ref":
        candidates = resolve_match(db, value)
        if not candidates:
            return {"ok": False, "error": f"Nu am gasit meciul '{value}'. Incearca 'Echipa A vs Echipa B' sau ID-ul."}
        best = candidates[0]
        return {"ok": True, "value": {"id": best["id"], "name": best["name"]}}

    if field_type == "choice":
        choices = field_def.get("choices", [])
        value_lower = value.strip().lower()
        # Try numeric selection
        if value_lower.isdigit():
            idx = int(value_lower) - 1
            if 0 <= idx < len(choices):
                return {"ok": True, "value": choices[idx]}
        # Try text match
        for c in choices:
            if c.lower() in value_lower or value_lower in c.lower():
                return {"ok": True, "value": c}
        return {"ok": False, "error": f"Optiune invalida. Alege: {', '.join(choices)}"}

    if field_type == "dynamic":
        return {"ok": True, "value": value.strip()}

    return {"ok": True, "value": value.strip()}


def _format_confirmation(intent: str, collected: dict) -> str:
    """Build a human-readable confirmation message."""
    flow = _FLOWS.get(intent)
    if not flow:
        return "Confirmi operatia?"

    lines = [f"**{flow['label']}** - confirma datele:\n"]
    for field in flow["fields"]:
        name = field["name"]
        if name not in collected:
            continue
        val = collected[name]
        label = field["prompt"].split("?")[0].split("(")[0].strip()
        if isinstance(val, dict):
            display = val.get("name", str(val.get("id", val)))
        else:
            display = str(val)
        lines.append(f"- {label}: **{display}**")

    lines.append("\nScrie **da** pentru a confirma sau **nu** pentru a anula.")
    return "\n".join(lines)


def start_crud_flow(
    db: Session,
    user,
    intent: str,
    conversation_id: int | None,
    initial_entity: str | None,
) -> dict:
    """Start a new CRUD flow. Returns the first prompt."""
    flow = _FLOWS.get(intent)
    if not flow:
        return {
            "type": "answer",
            "text": "Nu stiu cum sa procesez aceasta actiune.",
            "suggestedQuestions": [],
        }

    collected = {}

    # Try to pre-fill from the initial entity if it matches the first field
    if initial_entity and flow["fields"]:
        first_field = flow["fields"][0]
        result = _validate_and_resolve(db, first_field, initial_entity)
        if result["ok"]:
            collected[first_field["name"]] = result["value"]

    # Create session
    session = AgentCrudSessionModel(
        conversationId=conversation_id,
        userId=user.id,
        intent=intent,
        collectedData=collected,
        status="in_progress",
    )

    next_field = _get_next_field(flow, collected)
    if next_field:
        session.pendingField = next_field["name"]
    else:
        session.pendingField = "__confirm__"

    db.add(session)
    db.commit()

    if next_field:
        prompt = next_field["prompt"]
        if collected:
            pre_filled = ", ".join(
                f"{k}: {v.get('name', v) if isinstance(v, dict) else v}"
                for k, v in collected.items()
            )
            prompt = f"Am inteles: {pre_filled}.\n\n{prompt}"
        return {
            "type": "answer",
            "text": f"**{flow['label']}**\n\n{prompt}",
            "suggestedQuestions": ["Anuleaza"] if next_field.get("required") else ["Skip", "Anuleaza"],
        }
    else:
        return {
            "type": "answer",
            "text": _format_confirmation(intent, collected),
            "suggestedQuestions": ["Da", "Nu"],
        }


def continue_crud_flow(db: Session, user, text: str, session: AgentCrudSessionModel) -> dict:
    """Continue an active CRUD flow with the user's response."""
    flow = _FLOWS.get(session.intent)
    if not flow:
        session.status = "cancelled"
        db.commit()
        return {"type": "answer", "text": "Sesiunea CRUD nu mai este valida.", "suggestedQuestions": []}

    collected = dict(session.collectedData or {})

    # Check for cancel
    text_lower = text.strip().lower()
    if text_lower in _CONFIRM_NO or text_lower in {"anuleaza", "cancel", "renunt", "renunta", "stop"}:
        session.status = "cancelled"
        db.commit()
        return {
            "type": "answer",
            "text": "Operatia a fost anulata.",
            "suggestedQuestions": ["Ce poti sa faci?", "Care e clasamentul?"],
        }

    # If pending confirmation
    if session.pendingField == "__confirm__":
        confirm = _is_confirm(text)
        if confirm is True:
            from modules.agent.crud_actions import execute_crud
            result = execute_crud(db, user, session.intent, collected)
            session.status = "completed"
            db.commit()
            if result["success"]:
                return {
                    "type": "answer",
                    "text": f"Gata! {result['message']}",
                    "suggestedQuestions": ["Ce poti sa faci?", "Care e clasamentul?"],
                }
            else:
                return {
                    "type": "answer",
                    "text": f"Eroare: {result['message']}",
                    "suggestedQuestions": ["Ce poti sa faci?"],
                }
        elif confirm is False:
            session.status = "cancelled"
            db.commit()
            return {
                "type": "answer",
                "text": "Operatia a fost anulata.",
                "suggestedQuestions": ["Ce poti sa faci?", "Care e clasamentul?"],
            }
        else:
            return {
                "type": "answer",
                "text": "Scrie **da** pentru a confirma sau **nu** pentru a anula.",
                "suggestedQuestions": ["Da", "Nu"],
            }

    # Find the current pending field
    pending_field = None
    for field in flow["fields"]:
        if field["name"] == session.pendingField:
            pending_field = field
            break

    if not pending_field:
        session.status = "cancelled"
        db.commit()
        return {"type": "answer", "text": "Eroare interna. Sesiunea a fost anulata.", "suggestedQuestions": []}

    # Handle skip for optional fields
    if not pending_field["required"] and _is_skip(text):
        # Move to next field
        pass
    else:
        # Validate and resolve
        result = _validate_and_resolve(db, pending_field, text)
        if not result["ok"]:
            return {
                "type": "answer",
                "text": result["error"],
                "suggestedQuestions": ["Anuleaza"] if pending_field.get("required") else ["Skip", "Anuleaza"],
            }
        collected[pending_field["name"]] = result["value"]

    # Update session
    session.collectedData = collected

    # Find next field
    next_field = _get_next_field(flow, collected)
    if next_field:
        session.pendingField = next_field["name"]
        db.commit()
        return {
            "type": "answer",
            "text": next_field["prompt"],
            "suggestedQuestions": ["Anuleaza"] if next_field.get("required") else ["Skip", "Anuleaza"],
        }
    else:
        # All fields collected - ask for confirmation
        session.pendingField = "__confirm__"
        db.commit()
        return {
            "type": "answer",
            "text": _format_confirmation(session.intent, collected),
            "suggestedQuestions": ["Da", "Nu"],
        }
