# reasoning/plan_execute.py
from typing import Dict, Any
from .llm_client import call_llm
import json, re

SYSTEM = "You are a planner for a crisis grid world. Plan first in text, then output STRICT FINAL_JSON per schema."

USER = """High-level instruction:
Draft a short step-by-step plan for the next tick only (brief).
Then produce FINAL_JSON with concrete commands for this tick.

Context:
{context_json}

Schema reminder (STRICT):
{{"commands":[{{"agent_id":"<id>","type":"move","to":[x,y]}},{{"agent_id":"<id>","type":"act","action_name":"pickup_survivor|drop_at_hospital|extinguish_fire|clear_rubble|recharge|resupply"}}]}}
"""

def plan_execute_plan(context: Dict[str, Any], scratchpad: str = "") -> Dict[str, Any]:
    msgs = [{"role":"system","content":SYSTEM},
            {"role":"user","content": USER.format(context_json=context)}]
    if scratchpad:
        msgs.insert(1, {"role":"assistant","content": f"Notes:\n{scratchpad}"})
    out = call_llm(messages=msgs, temperature=0.2, max_tokens=600)
    text = out if isinstance(out, str) else str(out)
    m = re.findall(r"\{[\s\S]*\}\s*$", text)
    candidate = m[-1] if m else "{}"
    try:
        return json.loads(candidate)
    except Exception:
        return {"commands": []}
