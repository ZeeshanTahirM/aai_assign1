# utils/jsonl_logger.py
import os, json

def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def write_tick_conversation(base_dir: str, strategy: str, run_id: str, tick: int, conversation_lines):
    """
    conversation_lines: list of dicts like:
      {"role":"system","content":"..."}
      {"role":"user","content":"..."}
      {"role":"assistant","content":"Thought: ..."}
      {"role":"assistant","content":"FINAL_JSON: {...}"}
    """
    dirpath = os.path.join(base_dir, f"strategy={strategy}", f"run={run_id}")
    ensure_dir(dirpath)
    fn = os.path.join(dirpath, f"tick{tick:03d}.jsonl")
    with open(fn, "w", encoding="utf-8") as f:
        for line in conversation_lines:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")
