from transformers import AutoTokenizer, AutoModelForTokenClassification
import torch

class NERTagger:
    def __init__(self, path="models/ner"):
        self.tok = AutoTokenizer.from_pretrained(path)
        self.model = AutoModelForTokenClassification.from_pretrained(path)
        self.model.eval()
        self.id2label = self.model.config.id2label

    def extract(self, text: str):
        tokens = self.tok(text, return_tensors="pt", truncation=True, max_length=128)
        with torch.no_grad():
            logits = self.model(**tokens).logits[0]
            probs = torch.softmax(logits, dim=-1)
            ids = torch.argmax(probs, dim=-1).tolist()
        wp = self.tok.convert_ids_to_tokens(tokens["input_ids"][0])
        ents, cur = [], None
        for i, lab_id in enumerate(ids):
            lab = self.id2label[str(lab_id)] if isinstance(lab_id,str) else self.id2label[lab_id]
            tok = self.tok.convert_tokens_to_string([wp[i]]).strip()
            if lab.startswith("B-"):
                if cur: ents.append(cur)
                cur = {"label": lab[2:], "text": tok, "score": float(probs[i, lab_id])}
            elif lab.startswith("I-") and cur and cur["label"] == lab[2:]:
                cur["text"] += " " + tok
                cur["score"] = max(cur["score"], float(probs[i, lab_id]))
            else:
                if cur: ents.append(cur); cur=None
        if cur: ents.append(cur)
        for e in ents: e["text"] = " ".join(e["text"].split())
        return ents
