from .infer_intent import IntentClassifier
from .infer_ner import NERTagger
from .normalize import normalize_query, canonicalize_season
import re, datetime

intent_model = IntentClassifier("models/intent")
ner_model = NERTagger("models/ner")

def detect_intent_slots(user_text: str):
    t = normalize_query(user_text)
    intent, conf = intent_model.predict(t)
    ents = ner_model.extract(t)

    slots = {"player": None, "team": None, "league": None, "season": None, "last_n_matches": None}
    for e in ents:
        if e["label"]=="PLAYER": slots["player"]=e["text"]
        elif e["label"]=="TEAM": slots["team"]=e["text"]
        elif e["label"]=="LEAGUE": slots["league"]=e["text"]
        elif e["label"]=="SEASON": slots["season"]=canonicalize_season(e["text"])
        elif e["label"]=="N_LAST":
            num = re.sub(r"\D","", e["text"])
            if num: slots["last_n_matches"] = int(num)

    clarify = None
    if intent=="player_goals" and not slots["player"]:
        intent="clarify"; clarify="Despre ce jucător e vorba?"
    if intent=="points_gap_to_leader" and (not slots["team"] or not slots["league"] or not slots["season"]):
        intent="clarify"; clarify="Spune-mi echipa, liga și sezonul (ex: FCSB, Liga 1, 2024-2025)."

    return {"intent": intent, "slots": slots, "confidence": conf, "clarify": clarify}
