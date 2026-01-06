import unicodedata, re, datetime

def strip_diacritics(s: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFD', s or "") if unicodedata.category(c) != 'Mn')

def normalize_query(s: str) -> str:
    s = strip_diacritics(s).lower().strip()
    s = re.sub(r"\s+", " ", s)
    s = s.replace("/", "-")
    return s

def canonicalize_season(s: str, now: datetime.date | None = None) -> str:
    if not s: return s
    s = s.lower().strip()
    now = now or datetime.date.today()
    if "curent" in s or "anul asta" in s:
        return f"{now.year}-{now.year+1}"
    if len(s)==5 and s[2]=='-':  # 24-25 -> 2024-2025
        a=int("20"+s[:2]); b=int("20"+s[3:])
        return f"{a}-{b}"
    return s