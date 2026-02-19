"""Keyword-based NLU for Romanian football queries.

No external API dependency - uses regex patterns and keyword scoring.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Optional


def _strip_diacritics(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    )


def _normalize(s: str) -> str:
    s = _strip_diacritics(s or "").lower().strip()
    return re.sub(r"\s+", " ", s)


# (regex_pattern, intent_name, priority) - higher priority wins
_INTENT_PATTERNS: list[tuple[str, str, int]] = [
    # --- Greeting ---
    (r"\b(salut|buna|hello|hey|hei|yo|servus|neata|ceau|salutare)\b", "greeting", 10),

    # --- Help ---
    (r"\b(ajut|help|ce (stii|poti)|cum func|ce intreb|ce (sa|pot) (te )?intreb)", "help", 10),

    # --- Top scorers ---
    (r"(top|cel mai|cele mai|cine)\b.{0,25}(gol|marcator|golgheter|inscris)", "top_scorers", 8),
    (r"\b(golgheter|top.?scorer)", "top_scorers", 9),
    (r"cine a (dat|marcat|inscris).{0,20}(gol|mai mult)", "top_scorers", 8),
    (r"cine.{0,15}(marcheaza|inscrie|da gol)", "top_scorers", 7),
    (r"(cei mai buni|cel mai bun)\b.{0,15}(marcator|atacant)", "top_scorers", 8),

    # --- Player goals (needs player entity) ---
    (r"(cate|câte|cat|cât)\b.{0,15}\bgol", "player_goals", 7),
    (r"\bgol(uri)?\b.{0,10}\bare\b", "player_goals", 6),

    # --- Player stats ---
    (r"\b(statistic[ia]?|stats|performant[ea]?|detalii|profil)\b", "player_stats", 6),
    (r"cum (a |s-?a )?(jucat|descurcat|performant|evoluat)", "player_stats", 7),
    (r"(info|detalii|date)\b.{0,15}(despre|desp|lui|al lui)", "player_stats", 7),

    # --- Top assists ---
    (r"(top|cel mai|cele mai|cine)\b.{0,25}(assist|pase? de gol|pasa decisiv|pasator)", "top_assists", 8),
    (r"\b(assist(uri)?|pase de gol|pasator)", "top_assists", 6),

    # --- Standings / Rankings ---
    (r"\b(clasament|standings?|ranking|tabel|ierarhie)", "standings", 8),
    (r"(pe ce loc|locul cat|locul câ|poziti)", "standings", 8),
    (r"\bpunct(e|aj)?\b", "standings", 4),

    # --- Next matches ---
    (r"(urmatoru[l]?|viitor|urmator)\b.{0,15}(meci|joc|partid)", "next_matches", 9),
    (r"cand\b.{0,20}(meci|joc|jucam|juca)", "next_matches", 8),
    (r"ce meci(uri)?\b.{0,15}(urmeaz|vine|vin)", "next_matches", 8),
    (r"\bprogram(ul)?\b.{0,10}(meci|joc)?", "next_matches", 5),

    # --- Recent results ---
    (r"ultim(ul|ele|a|ii)\b.{0,20}(meci|rezultat|scor|joc|partid)", "recent_results", 9),
    (r"\b(rezultat)(e|ul|ele|uri|urile)?\b", "recent_results", 6),
    (r"\bscor(ul|uri|urile)?\b", "recent_results", 6),
    (r"(cum s-?a|s-?a terminat)", "recent_results", 8),

    # --- Most cards ---
    (r"(cel mai|cele mai|cine)\b.{0,25}(cartonas|card)", "most_cards", 8),
    (r"\b(cartonas|card)(e|uri|ul)?\b", "most_cards", 6),
    (r"\b(galben|rosu|avertisment|eliminare|eliminat)\b", "most_cards", 5),

    # --- Team info ---
    (r"(cati|câti|cati|cate)\b.{0,15}(jucator|membr)", "team_info", 8),
    (r"(info\w*|detalii|componen).{0,15}(echip|team|lot)", "team_info", 7),
    (r"\b(echip|team|lot|squad)\b.{0,15}(noastr|mea|principal)", "team_info", 7),
]

# Words to strip when extracting entity names
_STOP_WORDS = {
    "cate", "câte", "cat", "cât", "goluri", "gol", "are", "a", "avut", "dat",
    "marcat", "inscris", "mai", "cele", "cel", "multe", "multi", "este",
    "e", "lui", "al", "ale", "din", "de", "la", "pe", "cu", "in", "despre",
    "pt", "pentru", "sa", "si", "sau", "ori", "ca", "ce", "cum", "cine",
    "cand", "unde", "care", "acesta", "aceasta", "acest", "acel", "spune",
    "zi", "arata", "du", "te", "ma", "mi", "imi", "ne", "va", "le", "se",
    "fie", "fi", "fost", "era", "rog", "te rog", "poti", "stii",
    "statistici", "stats", "performanta", "detalii", "profil", "info",
    "cartonas", "cartonase", "carduri", "galben", "galbene", "rosu", "rosii",
    "echipa", "echipei", "team", "jucator", "jucatori", "meciuri", "meci",
    "ultimele", "ultimul", "ultima", "urmatorul", "viitorul", "clasament",
    "clasamentul", "ranking", "puncte", "assist", "assisturi", "pase",
    "sezon", "sezonul", "liga", "imi", "eu",
}


def detect_intent(text: str) -> str:
    normalized = _normalize(text)
    best_intent = None
    best_priority = -1

    for pattern, intent, priority in _INTENT_PATTERNS:
        if re.search(pattern, normalized) and priority > best_priority:
            best_intent = intent
            best_priority = priority

    return best_intent or "unknown"


def extract_entity_name(text: str, intent: str) -> Optional[str]:
    """Try to extract a player/team name from the message."""
    normalized = _normalize(text)

    # Try quoted strings first: "Popescu" or «Popescu»
    quoted = re.findall(r'["\u201c\u201e](.+?)["\u201d\u201f]', text)
    if quoted:
        return quoted[0].strip()

    # Remove stop words and intent keywords, keep what's left
    words = normalized.split()
    remaining = [w for w in words if w not in _STOP_WORDS and len(w) > 1]

    if not remaining:
        return None

    # Look for capitalized words in original text (likely proper nouns)
    original_words = text.split()
    capitalized = [w for w in original_words if w[0].isupper() and len(w) > 1
                   and _normalize(w) not in _STOP_WORDS]
    if capitalized:
        return " ".join(capitalized)

    # Fallback: return the remaining non-stop words joined
    if remaining:
        return " ".join(remaining)

    return None
