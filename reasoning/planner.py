# reasoning/planner.py
from typing import Dict, Any, List
from .react import react_plan
from .reflexion import reflexion_plan
from .plan_execute import plan_execute_plan  # you'll add this file next

VALID_ACTIONS = {
    "pickup_survivor",
    "drop_at_hospital",
    "extinguish_fire",
    "clear_rubble",
    "recharge",
    "resupply",
}

def _validate_action_json(cmd_json: Dict[str, Any]) -> Dict[str, Any]:
    # Expect: {"commands": [ ... ]}
    if not isinstance(cmd_json, dict) or "commands" not in cmd_json:
        raise ValueError("Planner must return {'commands': [...]}")

    normed: List[Dict[str, Any]] = []
    for c in cmd_json.get("commands", []):
        if not isinstance(c, dict):
            continue
        agent_id = str(c.get("agent_id", "")).strip()
        ctype = c.get("type")
        if ctype == "move":
            to = c.get("to")
            if agent_id and isinstance(to, (list, tuple)) and len(to) == 2:
                normed.append({"agent_id": agent_id, "type": "move", "to": [int(to[0]), int(to[1])]})
        elif ctype == "act":
            action = str(c.get("action_name", "")).strip()
            if agent_id and action in VALID_ACTIONS:
                normed.append({"agent_id": agent_id, "type": "act", "action_name": action})
        # silently drop malformed commands
    return {"commands": normed}

def make_plan(context: Dict[str, Any], strategy: str, scratchpad: str = "") -> Dict[str, Any]:
    strategy = (strategy or "react").lower()
    if strategy == "react":
        out = react_plan(context, scratchpad=scratchpad)
    elif strategy == "reflexion":
        out = reflexion_plan(context, scratchpad=scratchpad)
    elif strategy in ("plan_execute", "plan-and-execute", "planexecute"):
        out = plan_execute_plan(context, scratchpad=scratchpad)
    else:
        # default to react
        out = react_plan(context, scratchpad=scratchpad)

    try:
        return _validate_action_json(out)
    except Exception:
        # single retry hook – caller (main loop) should count invalid_json and trigger one re-prompt if desired
        return {"commands": []}
