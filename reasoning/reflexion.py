\
import os, json
from .llm_client import llm_complete

MEM_PATH = "memory.json"

def load_rules():
    if os.path.exists(MEM_PATH):
        try:
            return json.load(open(MEM_PATH))
        except Exception:
            return {"rules":[]}
    return {"rules":[]}

def save_rules(mem):
    json.dump(mem, open(MEM_PATH, "w"), indent=2)

def critique_and_update(transcript: str):
    prompt = (
        "As a crisis ops critic, read the transcript and list exactly 3 mistakes "
        "and 3 concrete rules to apply next phase. One line per item."
    )
    txt = llm_complete(prompt + "\n\nTranscript:\n" + transcript)
    mem = load_rules()
    mem.setdefault("rules", []).append(txt)
    mem["rules"] = mem["rules"][-5:]
    save_rules(mem)
    return txt
