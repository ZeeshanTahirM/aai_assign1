# reasoning/react.py
import json

def react_plan(context, scratchpad: str = ""):
    """
    Entry point used by planner.make_plan(...):
      returns ("final", <json string of {"commands": [...]}>)
    """
    plan_dict = mock_react_with_tools(context)
    return ("final", json.dumps(plan_dict))


# -------------------- Mock ReAct w/ simple tool reasoning --------------------

def mock_react_with_tools(context: dict) -> dict:
    """
    A self-contained, model-free ReAct-style planner.

    - Medics:
        * If carrying and on a hospital tile -> drop_at_hospital
        * If carrying and not on hospital -> move toward nearest hospital
        * If not carrying:
            - if co-located with a survivor -> pickup_survivor
            - else move toward nearest survivor
    - Truck:
        * If on a fire tile -> extinguish
        * Else move toward nearest fire
    - Drone: idle (extend as you like)

    NOTE: Uses simple greedy Manhattan step (no obstacles). The environment
    validates acts (e.g., hospital check) so it's safe if we over-approximate.
    """
    commands = []

    agents = context.get("agents", [])
    fires = [tuple(p) for p in context.get("fires", [])]
    survivors = [tuple(s["pos"]) for s in context.get("survivors", [])]
    hospital_positions = [tuple(h["pos"]) for h in context.get("hospitals", [])]
    hospital_set = set(hospital_positions)
    survivor_set = set(survivors)
    fire_set = set(fires)

    for a in agents:
        aid = a["id"]
        kind = a.get("kind")
        pos = tuple(a.get("pos", (0, 0)))

        if kind == "truck":
            # If standing on fire -> extinguish
            if pos in fire_set:
                commands.append({"agent_id": aid, "type": "act", "action_name": "extinguish"})
                continue
            # Else go to nearest fire
            tgt = _nearest_from(pos, fires)
            if tgt:
                nxt = _greedy_step(pos, tgt)
                commands.append({"agent_id": aid, "type": "move", "to": list(nxt)})

        elif kind == "medic":
            carrying = bool(a.get("carrying", False))
            if carrying:
                # If on hospital -> drop
                if pos in hospital_set:
                    commands.append({"agent_id": aid, "type": "act", "action_name": "drop_at_hospital"})
                else:
                    hpos = _nearest_from(pos, hospital_positions)
                    if hpos:
                        nxt = _greedy_step(pos, hpos)
                        commands.append({"agent_id": aid, "type": "move", "to": list(nxt)})
            else:
                # If co-located with survivor -> pickup
                if pos in survivor_set:
                    commands.append({"agent_id": aid, "type": "act", "action_name": "pickup_survivor"})
                else:
                    s_pos = _nearest_from(pos, survivors)
                    if s_pos:
                        nxt = _greedy_step(pos, s_pos)
                        commands.append({"agent_id": aid, "type": "move", "to": list(nxt)})

        elif kind == "drone":
            # Idle (or patrol if you want to extend)
            pass

    return {"commands": commands}


# -------------------- Helpers --------------------

def _manhattan(a, b) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def _nearest_from(pos, points):
    if not points:
        return None
    return min(points, key=lambda p: _manhattan(pos, p))

def _greedy_step(src, dst):
    """Take one Manhattan step from src -> dst (prefers x, then y)."""
    sx, sy = src
    dx, dy = dst
    if sx < dx: 
        return (sx + 1, sy)
    if sx > dx: 
        return (sx - 1, sy)
    if sy < dy: 
        return (sx, sy + 1)
    if sy > dy: 
        return (sx, sy - 1)
    return src
