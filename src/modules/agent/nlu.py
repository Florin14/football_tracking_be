# app/agent/nlu.py
import os, json
from openai import OpenAI

key = os.getenv("OPENAI_API_KEY")
if not key:
    raise RuntimeError(
        "OPENAI_API_KEY is not set. Define it as an environment variable "
        "(e.g., in PowerShell: $env:OPENAI_API_KEY='sk-...') or use a .env file."
    )

client = OpenAI(api_key=key)
SYSTEM = """Ești un parser NL->JSON (română). Întoarce STRICT:
{"intent":"player_goals|points_gap_to_leader|clarify|other",
 "slots":{"player?":str,"team?":str,"league?":str,"season?":str,"last_n_matches?":int},
 "confidence": float,
 "clarify?": str}
Reguli: fii tolerant la greșeli; dacă lipsesc entități esențiale -> intent=clarify cu întrebare scurtă."""
def detect_intent(user_text: str) -> dict:
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"system","content":SYSTEM},
                  {"role":"user","content":user_text}],
        response_format={"type":"json_object"},
        temperature=0
    )
    try: return json.loads(resp.choices[0].message.content)
    except: return {"intent":"clarify","slots":{},"confidence":0.0,"clarify":"Poți reformula puțin?"}
