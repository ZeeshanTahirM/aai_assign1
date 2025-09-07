\
def inventory_state(model, agent_id: str):
    for a in model.schedule.agents:
        if str(a.unique_id) == str(agent_id):
            return {
                "agent_id": str(agent_id),
                "battery": getattr(a, "battery", None),
                "water": getattr(a, "water", None),
                "tools": getattr(a, "tools", None),
                "carrying": getattr(a, "carrying", False)
            }
    return {"status":"error","reason":"agent_not_found"}
