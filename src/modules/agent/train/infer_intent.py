from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

INTENTS = ["player_goals","points_gap_to_leader","other"]

class IntentClassifier:
    def __init__(self, path="models/intent"):
        self.tok = AutoTokenizer.from_pretrained(path)
        self.model = AutoModelForSequenceClassification.from_pretrained(path)
        self.model.eval()

    def predict(self, text: str):
        inp = self.tok(text, return_tensors="pt", truncation=True, max_length=128)
        with torch.no_grad():
            logits = self.model(**inp).logits
            probs = torch.softmax(logits, dim=-1).squeeze(0).tolist()
        idx = int(max(range(len(probs)), key=lambda i: probs[i]))
        return INTENTS[idx], float(probs[idx])
