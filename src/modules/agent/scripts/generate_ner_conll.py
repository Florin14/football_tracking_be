# scripts/generate_ner_conll.py
import random, re
from pathlib import Path
random.seed(42)

PLAYERS = ["Lionel Messi","Cristiano Ronaldo","Kylian Mbappe","Erling Haaland",
           "Florinel Coman","Denis Alibec","Octavian Popescu","Radu Dragusin"]
TEAMS = ["FCSB","Dinamo Bucuresti","Rapid Bucuresti","CFR Cluj","Universitatea Craiova","U Cluj","Farul Constanta"]
LEAGUES = ["Liga 1","Premier League","La Liga","Serie A","Bundesliga","UEFA Champions League"]
SEASONS = ["2023-2024","2024-2025","2025-2026"]

def tok(s): return s.split()

def tag_line(tokens, spans):
    # spans = [(start_idx, end_idx, label)] token-indexed
    tags = ["O"]*len(tokens)
    for (a,b,lab) in spans:
        tags[a] = "B-"+lab
        for i in range(a+1,b): tags[i] = "I-"+lab
    return "\n".join(f"{tokens[i]} {tags[i]}" for i in range(len(tokens))) + "\n\n"

def find_span(tokens, phrase):
    words = tok(phrase)
    for i in range(len(tokens)-len(words)+1):
        if tokens[i:i+len(words)] == words:
            return i, i+len(words)
    return None

def add_sample(buff, template, labels):
    sent = template.format(**labels)
    tokens = tok(sent)
    spans = []
    for lab, text in [("PLAYER", labels.get("player")),
                      ("TEAM", labels.get("team")),
                      ("LEAGUE", labels.get("league")),
                      ("SEASON", labels.get("season")),
                      ("N_LAST", labels.get("n_last"))]:
        if text:
            text = str(text)
            sp = find_span(tokens, text)
            if sp: spans.append((*sp, lab))
    buff.append(tag_line(tokens, spans))

def main():
    outdir = Path("data"); outdir.mkdir(exist_ok=True, parents=True)
    templates = [
        "cate goluri are {player} in {season}",
        "{team} cate puncte fata de lider in {league} {season}",
        "cate goluri are {player} in {league} {season}",
        "cate puncte sunt intre {team} si lider in {league} {season}",
        "cate goluri are {player} in ultimele {n_last} meciuri",
    ]
    buf = []
    for _ in range(5000):
        t = random.choice(templates)
        labels = {
            "player": random.choice(PLAYERS),
            "team": random.choice(TEAMS),
            "league": random.choice(LEAGUES),
            "season": random.choice(SEASONS),
            "n_last": random.choice([None,"3","5","10"])
        }
        # optional: nu toate sloturile apar în fiecare template
        if "{player}" not in t: labels["player"] = None
        if "{team}" not in t: labels["team"] = None
        if "{league}" not in t: labels["league"] = None
        if "{season}" not in t: labels["season"] = None
        if "{n_last}" not in t: labels["n_last"] = None
        add_sample(buf, t, labels)

    # split 85/15
    cut = int(0.85*len(buf))
    with open(outdir/"ner_train.conll","w",encoding="utf-8") as f: f.write("".join(buf[:cut]))
    with open(outdir/"ner_val.conll","w",encoding="utf-8") as f: f.write("".join(buf[cut:]))
    print("NER CoNLL generated.")

if __name__ == "__main__":
    main()
