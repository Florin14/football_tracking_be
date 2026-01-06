# app/agent/agent.py
from modules.agent.nlu import detect_intent
from modules.agent.resolve import resolve_entity
from modules.agent.tools import get_player_goals, gap_to_leader

def canonicalize_season(s: str, now_year: int) -> str:
    s = s.lower().strip()
    if "curent" in s or "anul asta" in s:
        # simplificare: sezon european care începe în anul curent
        return f"{now_year}-{now_year+1}"
    if "-" in s: return s
    if len(s)==4: return s  # 2025
    # 24-25 -> 2024-2025
    if len(s)==5 and s[2]=='-':
        a=int("20"+s[:2]); b=int("20"+s[3:])
        return f"{a}-{b}"
    return s

def make_clarify(missing, ambiguous):
    if ambiguous.get("player"):
        opts = [o["name"] for o in ambiguous["player"][:2]]
        return f"Te referi la { ' sau '.join(opts) }?"
    if ambiguous.get("team"):
        opts = [o["name"] for o in ambiguous["team"][:2]]
        return f"Te referi la { ' sau '.join(opts) }?"
    if missing.get("player"): return "Despre ce jucător e vorba?"
    if missing.get("team"):   return "Despre ce echipă e vorba?"
    if missing.get("league"): return "Pentru ce ligă (ex. Liga 1, Premier League)?"
    if missing.get("season"): return "Pentru ce sezon (ex. 2024-2025 sau sezonul curent)?"
    return "Poți clarifica puțin?"

def handle_message(user_text: str, user_ctx: dict):
    parsed = detect_intent(user_text)
    intent = parsed.get("intent"); slots = parsed.get("slots",{})
    if intent == "clarify":
        return {"type":"clarify","text": parsed.get("clarify","Poți clarifica?")}

    # normalize season
    if slots.get("season"):
        slots["season"] = canonicalize_season(slots["season"], user_ctx.get("now_year", 2025))

    missing, ambiguous, resolved = {}, {}, {}
    # player_goals
    if intent == "player_goals":
        if slots.get("player"):
            rp = resolve_entity("player", slots["player"])
            if rp["status"]=="resolved": resolved["player"]=rp
            elif rp["status"]=="ambiguous": ambiguous["player"]=rp["options"]
            else: missing["player"]=True
        else: missing["player"]=True
        # league este opțional, dar dacă există îl rezolvăm
        if slots.get("league"):
            rl = resolve_entity("league", slots["league"])
            if rl["status"]=="resolved": resolved["league"]=rl
            elif rl["status"]=="ambiguous": ambiguous["league"]=rl["options"]

    # points_gap_to_leader
    if intent == "points_gap_to_leader":
        for k in ["team","league","season"]:
            if k=="season":
                if not slots.get("season"): missing["season"]=True
            else:
                if slots.get(k):
                    r = resolve_entity(k, slots[k])
                    if r["status"]=="resolved": resolved[k]=r
                    elif r["status"]=="ambiguous": ambiguous[k]=r["options"]
                    else: missing[k]=True
                else: missing[k]=True

    if missing or ambiguous:
        return {"type":"clarify","text": make_clarify(missing, ambiguous),
                "state": {"intent": intent, "slots": slots, "missing": list(missing.keys()),
                          "ambiguous": {k:[o["name"] for o in v] for k,v in ambiguous.items()}}}

    # call tools
    if intent == "player_goals":
        res = get_player_goals(player_id=resolved["player"]["id"],
                               season=slots.get("season"),
                               league_id=resolved.get("league",{}).get("id"))
        return {"type":"answer",
                "text": f"🔢 {resolved['player']['name']} are {res['goals']} goluri ({res['scope']})."}

    if intent == "points_gap_to_leader":
        res = gap_to_leader(league_id=resolved["league"]["id"],
                            season=slots["season"], team_id=resolved["team"]["id"])
        if not res.get("found"):
            return {"type":"answer","text":"Nu am găsit clasamentul cerut."}
        gap = res["gap"]
        if gap>0: msg=f"📊 {resolved['team']['name']} e la {gap}p de lider."
        elif gap==0: msg=f"📊 {resolved['team']['name']} e la egalitate cu liderul."
        else: msg=f"📊 {resolved['team']['name']} e peste lider cu {-gap}p."
        return {"type":"answer","text": f"{msg} ({slots['season']})."}

    return {"type":"answer","text":"Încă nu știu să răspund la întrebarea asta."}
