from sqlalchemy.orm import Session
from modules.agent.train.nlu_local import detect_intent_slots
from modules.agent.train.resolve_sql import resolve_player, resolve_team, resolve_league
from modules.agent.train.tools_sql import get_player_goals, get_points_gap_to_leader, get_team_points

def _pick(cands):
    if not cands: return None, "missing"
    top = cands[0]
    if top["score"] >= 0.85: return top, "ok"
    if top["score"] >= 0.60: return cands, "ambiguous"
    return None, "missing"

def make_clarify(missing, ambiguous):
    if "player" in ambiguous:
        opts = [o["name"] for o in ambiguous["player"][:2]]
        return f"Te referi la { ' sau '.join(opts) }?"
    if "team" in ambiguous:
        opts = [o["name"] for o in ambiguous["team"][:2]]
        return f"Te referi la { ' sau '.join(opts) }?"
    if "league" in ambiguous:
        opts = [o["name"] for o in ambiguous["league"][:2]]
        return f"Te referi la { ' sau '.join(opts) }?"
    if "player" in missing: return "Despre ce jucător e vorba?"
    if "team" in missing: return "Despre ce echipă e vorba?"
    if "league" in missing: return "Pentru ce ligă (ex: Liga 1, Premier League)?"
    if "season" in missing: return "Pentru ce sezon (ex: 2024-2025)?"
    return "Poți clarifica puțin?"

def handle_message(db: Session, user_text: str):
    parsed = detect_intent_slots(user_text)
    intent = parsed["intent"]; slots = parsed["slots"]

    if intent == "clarify":
        return {"type":"clarify","text": parsed.get("clarify") or "Poți clarifica?"}

    missing, ambiguous, resolved = set(), {}, {}

    if intent == "player_goals":
        p, st = _pick(resolve_player(db, slots.get("player","")))
        if st == "ok": resolved["player"] = p
        elif st == "ambiguous": ambiguous["player"] = p
        else: missing.add("player")

        # league & season sunt opționale
        league_id = None
        if slots.get("league"):
            lcands = resolve_league(db, slots["league"], slots.get("season"))
            l, stl = _pick(lcands)
            if stl == "ok": resolved["league"] = l; league_id = l["id"]
            elif stl == "ambiguous": ambiguous["league"] = l

        res = get_player_goals(db, player_id=resolved["player"]["id"],
                               season=slots.get("season"),
                               league_id=resolved.get("league",{}).get("id"))
        return {"type":"answer", "text": f"🔢 {resolved['player']['name']} are {res['goals']} goluri ({res['scope']})."}

    if intent == "points_gap_to_leader":
        # team
        t, stt = _pick(resolve_team(db, slots.get("team","")))
        if stt == "ok": resolved["team"] = t
        elif stt == "ambiguous": ambiguous["team"] = t
        else: missing.add("team")

        # league by name+season -> concrete league_id
        l, stl = _pick(resolve_league(db, slots.get("league",""), slots.get("season")))
        if stl == "ok": resolved["league"] = l
        elif stl == "ambiguous": ambiguous["league"] = l
        else: missing.add("league")
        if not slots.get("season"): missing.add("season")

        if missing or ambiguous:
            return {"type":"clarify","text": make_clarify(missing, ambiguous),
                    "state":{"intent": intent, "slots": slots,
                             "missing": list(missing),
                             "ambiguous": {k:[o['name'] for o in v] for k,v in ambiguous.items()}}}

        leader = get_points_gap_to_leader(db, league_id=resolved["league"]["id"])
        if not leader.get("found"):
            return {"type":"answer","text":"Nu am găsit clasamentul cerut."}
        my_points = get_team_points(db, league_id=resolved["league"]["id"], team_id=resolved["team"]["id"])
        if my_points is None:
            return {"type":"answer","text":f"Nu am găsit {resolved['team']['name']} în clasamentul ligii selectate."}
        gap = int(leader["leaderPoints"] - my_points)
        if gap > 0: msg = f"{resolved['team']['name']} e la {gap} puncte de lider."
        elif gap == 0: msg = f"{resolved['team']['name']} e la egalitate cu liderul."
        else: msg = f"{resolved['team']['name']} e peste lider cu {-gap} puncte."
        return {"type":"answer","text": f"📊 {msg} ({slots['season']})."}

    return {"type":"answer","text":"Încă nu știu să răspund la tipul acesta de întrebare."}
