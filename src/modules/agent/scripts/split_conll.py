# scripts/split_conll.py
from pathlib import Path
import random
random.seed(11)

def read_sents(path):
    with open(path,"r",encoding="utf-8") as f:
        content = f.read().strip()
    raw = content.split("\n\n")
    return [s+"\n\n" for s in raw if s.strip()]

def main():
    inp = Path("data/ner_all.conll")
    sents = read_sents(inp)
    random.shuffle(sents)
    cut = int(0.85*len(sents))
    Path("data").mkdir(exist_ok=True, parents=True)
    with open("data/ner_train.conll","w",encoding="utf-8") as f: f.writelines(sents[:cut])
    with open("data/ner_val.conll","w",encoding="utf-8") as f: f.writelines(sents[cut:])
    print("Done.")

if __name__ == "__main__":
    main()
