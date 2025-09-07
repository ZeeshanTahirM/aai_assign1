import json
from reasoning.react import react_plan
def make_plan(context, strategy="react_reflexion", scratchpad=""):
    kind, payload = react_plan(context, scratchpad=scratchpad)
    if kind == "final":
        try:
            return json.loads(payload)
        except Exception:
            return {"commands": []}
    else:
        # For full LLM ReAct you'd call tools based on 'action' here and loop;
        # this starter keeps it simple.
        return {"commands": []}
