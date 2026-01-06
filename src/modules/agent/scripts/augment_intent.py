# scripts/augment_intent.py
import csv, random, re, unicodedata
from pathlib import Path
random.seed(123)

ABBR = {"prem":"Premier League","ucl":"UEFA Champions League","liga1":"Liga 1","seriea":"Serie A","bundes":"Bundesliga"}

def strip_diac(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c)!='Mn')

def typo1(s):
    return re.sub(r"[aeiou]", lambda m: random.choice([m.group(0),""]), s, count=1)

def aug_row(text):
    outs = set([text])
    if random.random()<0.7: outs.add(strip_diac(text))
    if random.random()<0.5: outs.add(typo1(text))
    for k,v in ABBR.items():
        if v.lower() in text.lower():
            outs.add(text.lower().replace(v.lower(), k))
    return list(outs)

def main():
    inp = Path("data/intent_train.csv")
    out = Path("data/intent_train_aug.csv")
    rows = []
    with open(inp, "r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            variants = aug_row(row["text"])
            for v in variants:
                rows.append([v, row["intent"]])
    random.shuffle(rows)
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["text","intent"])
        w.writerows(rows)
    print(f"Augmented rows: {len(rows)} -> {out}")

if __name__ == "__main__":
    main()
