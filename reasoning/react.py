# reasoning/react.py
from typing import Dict, Any
from .llm_client import call_llm

SYSTEM_PROMPT = """You are a disaster-response planner operating a grid simulation.
Decide only via LLM reasoning (no rules). Output STRICT JSON matching:
{"commands":[
  {"agent_id":"<id>","type":"move","to":[x,y]},
  {"agent_id":"<id>","type":"act","action_name":"pickup_survivor|drop_at_hospital|extinguish_fire|clear_rubble|recharge|resupply"}
]}
Do NOT include any extra keys or text outside JSON for your final answer.
"""

USER_TEMPLATE = """Context (JSON, truncated):
{context_json}

Allowed actions & schema:
- move -> to: [x,y]
- act  -> action_name in {allowed}

Constraints:
- Prefer rescuing nearby survivors; keep agents safe; respect obstacles & capacities.
- Use recharge/resupply if low battery/resources (if provided in state).
Return ONLY FINAL_JSON for the final message."""

def react_plan(context: Dict[str, Any], scratchpad: str = "") -> Dict[str, Any]:
    allowed = ["pickup_survivor","drop_at_hospital","extinguish_fire","clear_rubble","recharge","resupply"]
    user = USER_TEMPLATE.format(context_json=context, allowed=allowed)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]
    if scratchpad:
        messages.insert(1, {"role": "assistant", "content": f"Notes:\n{scratchpad}"})

    # Call provider (Groq/Gemini/etc.) via your llm_client.py
    raw = call_llm(messages=messages, temperature=0.2, max_tokens=500)

    # Expect model to include a JSON block. If the provider wraps it, try to extract.
    import json, re
    text = raw if isinstance(raw, str) else str(raw)
    # Try strict extraction: the largest {...} block at the end
    m = re.findall(r"\{[\s\S]*\}\s*$", text)
    candidate = m[-1] if m else "{}"
    try:
        return json.loads(candidate)
    except Exception:
        return {"commands": []}
