import argparse, numpy as np
from datasets import Dataset
from transformers import AutoTokenizer, AutoModelForTokenClassification, DataCollatorForTokenClassification, TrainingArguments, Trainer
from seqeval.metrics import classification_report

TAGS = ["O","B-PLAYER","I-PLAYER","B-TEAM","I-TEAM","B-LEAGUE","I-LEAGUE","B-SEASON","I-SEASON","B-N_LAST","I-N_LAST"]
tag2id = {t:i for i,t in enumerate(TAGS)}; id2tag = {i:t for t,i in tag2id.items()}

def read_conll(path):
    sents, tags = [], []; words, labels = [], []
    with open(path,"r",encoding="utf-8") as f:
        for line in f:
            line=line.strip()
            if not line:
                if words: sents.append(words); tags.append(labels); words,labels=[],[]
                continue
            w,t=line.split()
            words.append(w); labels.append(t)
    if words: sents.append(words); tags.append(labels)
    return {"tokens": sents, "ner_tags": tags}

def align(tok, ex):
    t = tok(ex["tokens"], is_split_into_words=True, truncation=True, max_length=128)
    labs=[]
    for i,lab in enumerate(ex["ner_tags"]):
        ids = t.word_ids(i); prev=None; out=[]
        for wid in ids:
            if wid is None: out.append(-100)
            elif wid!=prev: out.append(tag2id[lab[wid]])
            else:
                L=lab[wid]; out.append(tag2id["I-"+L[2:]] if L.startswith("B-") else tag2id[L])
            prev=wid
        labs.append(out)
    t["labels"]=labs; return t

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--model", default="xlm-roberta-base")
    ap.add_argument("--train", required=True)
    ap.add_argument("--val", required=True)
    ap.add_argument("--output", required=True)
    a=ap.parse_args()

    tr_raw=read_conll(a.train); va_raw=read_conll(a.val)
    tr=Dataset.from_dict(tr_raw); va=Dataset.from_dict(va_raw)
    tok=AutoTokenizer.from_pretrained(a.model)
    tr=tr.map(lambda ex: align(tok,ex), batched=True); va=va.map(lambda ex: align(tok,ex), batched=True)
    coll=DataCollatorForTokenClassification(tok)
    m=AutoModelForTokenClassification.from_pretrained(a.model, num_labels=len(TAGS), id2label=id2tag, label2id=tag2id)
    args_t=TrainingArguments(output_dir=a.output, learning_rate=3e-5, per_device_train_batch_size=16,
                             per_device_eval_batch_size=32, num_train_epochs=4, evaluation_strategy="epoch",
                             save_strategy="epoch", load_best_model_at_end=True)
    def metrics(p):
        preds=np.argmax(p.predictions,axis=-1); true=p.label_ids
        P,T=[],[]
        for pr,tr in zip(preds,true):
            p_tags=[]; t_tags=[]
            for pi,ti in zip(pr,tr):
                if ti==-100: continue
                p_tags.append(id2tag[pi]); t_tags.append(id2tag[ti])
            P.append(p_tags); T.append(t_tags)
        print("\n"+classification_report(T,P,digits=4,zero_division=0)+"\n")
        return {}
    trn=Trainer(model=m,args=args_t,train_dataset=tr,eval_dataset=va,tokenizer=tok,data_collator=coll,compute_metrics=metrics)
    trn.train(); trn.save_model(a.output); tok.save_pretrained(a.output)

if __name__=="__main__": main()
