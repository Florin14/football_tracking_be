import argparse
from datasets import Dataset
from transformers import AutoTokenizer, AutoModelForSequenceClassification, TrainingArguments, Trainer
from sklearn.metrics import accuracy_score, f1_score
import numpy as np
from inspect import signature

INTENTS = ["player_goals","points_gap_to_leader","other"]

def make_training_args(output_dir, **kwargs):
    sig = signature(TrainingArguments.__init__)
    allowed = {k: v for k, v in kwargs.items() if k in sig.parameters}
    # if eval strategy isn't supported, don't request best-model-at-end
    if "evaluation_strategy" not in sig.parameters and allowed.get("load_best_model_at_end"):
        allowed["load_best_model_at_end"] = False
    return TrainingArguments(output_dir=output_dir, **allowed)

def compute_metrics(p):
    logits, labels = p
    preds = logits.argmax(axis=-1)
    return {"accuracy": accuracy_score(labels,preds), "f1_macro": f1_score(labels,preds,average="macro")}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="xlm-roberta-base")
    ap.add_argument("--train", required=True)
    ap.add_argument("--val", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    train = Dataset.from_csv(args.train)
    val   = Dataset.from_csv(args.val)
    label2id = {l:i for i,l in enumerate(INTENTS)}
    id2label = {i:l for l,i in label2id.items()}
    train = train.map(lambda ex: {"label": label2id.get(ex["intent"],2)})
    val   = val.map(lambda ex: {"label": label2id.get(ex["intent"],2)})

    tok = AutoTokenizer.from_pretrained(args.model)
    def tokf(ex): return tok(ex["text"], truncation=True, max_length=128)
    train = train.map(tokf, batched=True); val = val.map(tokf, batched=True)

    model = AutoModelForSequenceClassification.from_pretrained(args.model, num_labels=3, id2label=id2label, label2id=label2id)
    args_t = make_training_args(
    output_dir=args.output,
    learning_rate=2e-5,
    per_device_train_batch_size=16,
    per_device_eval_batch_size=32,
    num_train_epochs=3,
    evaluation_strategy="epoch",  # auto-ignored if unsupported
    save_strategy="epoch",
    load_best_model_at_end=True,  # auto-turned off if eval unsupported
    metric_for_best_model="f1_macro",
    logging_steps=50,
    save_total_limit=2,
    seed=42,
)
    tr = Trainer(model=model, args=args_t, train_dataset=train, eval_dataset=val, tokenizer=tok, compute_metrics=compute_metrics)
    tr.train(); tr.save_model(args.output); tok.save_pretrained(args.output)

if __name__=="__main__":
    main()

# python src/modules/agent/training/train_ner.py --model xlm-roberta-base --train data/ner_train.conll --val  src/modules/agent/data/ner_val.conll --output src/modules/agent/models/ner
