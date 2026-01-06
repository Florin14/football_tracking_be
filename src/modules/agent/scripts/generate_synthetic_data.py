# scripts/generate_synthetic_data.py
import csv, random, os, itertools, re
from pathlib import Path

random.seed(42)

PLAYERS = [
    "Lionel Messi","Cristiano Ronaldo","Kylian Mbappe","Erling Haaland",
    "Karim Benzema","Neymar","Robert Lewandowski","Jude Bellingham",
    "Florinel Coman","Denis Alibec","Andrei Ivan","Claudiu Petrila",
    "Rares Ilie","Olaru Darius","Octavian Popescu","Radu Dragusin"
]
TEAMS = [
    "FCSB","Dinamo Bucuresti","Rapid Bucuresti","CFR Cluj","Universitatea Craiova",
    "Farul Constanta","UTA Arad","U Cluj","Sepsi OSK","Petrolul Ploiesti"
]
LEAGUES = [
    "Liga 1","Premier League","La Liga","Serie A","Bundesliga","Ligue 1",
    "UEFA Champions League"
]
SEASONS = ["2023-2024","2024-2025","2025-2026"]

ABBR = {
    "prem": "Premier League",
    "liga1": "Liga 1",
    "ucl": "UEFA Champions League",
    "seriea": "Serie A",
    "bundes": "Bundesliga"
}

def noisy(s: str):
    s2 = s
    if random.random() < 0.25:
        s2 = s2.replace("ă","a").replace("â","a").replace("î","i").replace("ș","s").replace("ț","t")
    if random.random() < 0.2:
        s2 = s2.lower()
    if random.random() < 0.15:
        s2 = re.sub(r"[aeiou]", lambda m: random.choice([m.group(0),""]), s2, count=1)
    return s2

def gen_player_goals(n=2000):
    out = []
    templates = [
        "cate goluri are {player} in {season}",
        "cate goluri a marcat {player} in {league} {season}",
        "{player} cate goluri are in {league} {season}",
        "goluri {player} {season}",
        "cate goluri are {player}"
    ]
    for _ in range(n):
        t = random.choice(templates)
        p = random.choice(PLAYERS)
        l = random.choice(LEAGUES + list(ABBR.values()))
        s = random.choice(SEASONS)
        q = t.format(player=noisy(p), league=noisy(l), season=noisy(s))
        out.append([q, "player_goals"])
    return out

def gen_gap_to_leader(n=2000):
    out = []
    templates = [
        "{team} cate puncte fata de lider in {league} {season}",
        "cate puncte sunt intre {team} si lider in {league} {season}",
        "diferenta de puncte {team} lider {league} {season}",
        "cat e gapul de puncte pentru {team} in {league} {season}"
    ]
    leagues = LEAGUES[:1] + ["Liga 1","Premier League","La Liga","Serie A"]
    for _ in range(n):
        t = random.choice(templates)
        team = random.choice(TEAMS)
        league = random.choice(leagues + list(ABBR.values()))
        season = random.choice(SEASONS)
        q = t.format(team=noisy(team), league=noisy(league), season=noisy(season))
        out.append([q, "points_gap_to_leader"])
    return out

def gen_other(n=1000):
    others = [
        "care e vremea azi", "fa-mi un ceai", "cati km are maratonul",
        "ce ora este", "pretul la btc", "arata-mi programul de azi"
    ]
    out = []
    for _ in range(n):
        out.append([noisy(random.choice(others)), "other"])
    return out

def write_csv(path, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["text","intent"])
        w.writerows(rows)

def main():
    outdir = Path("data"); outdir.mkdir(parents=True, exist_ok=True)
    rows = gen_player_goals(2500) + gen_gap_to_leader(2500) + gen_other(1200)
    random.shuffle(rows)
    cut = int(0.85*len(rows))
    train, val = rows[:cut], rows[cut:]
    write_csv(outdir/"intent_train.csv", train)
    write_csv(outdir/"intent_val.csv", val)
    print(f"Intent: train={len(train)}, val={len(val)}")

if __name__ == "__main__":
    main()


