# server.py — Mesa 1.2.1 compatible, robust config handling

import os
import yaml
from typing import Dict, Tuple, Iterable
from mesa.visualization.modules import CanvasGrid, ChartModule, TextElement
from mesa.visualization.ModularVisualization import ModularServer
from env.world import CrisisModel
from env.agents import DroneAgent, MedicAgent, TruckAgent, Survivor

MAP_PATH = "configs/map_small.yaml"  # change if needed
SEED = 42
CANVAS_W = 600
CANVAS_H = 600


# ---------------- Portrayal ----------------

def agent_portrayal(agent):
    if agent is None:
        return
    p = {"Layer": 1, "Filled": "true"}

    if isinstance(agent, DroneAgent):
        p.update({
            "Shape": "triangle",
            "Color": "#00bcd4",
            "scale": 0.8,
            "heading_x": 0.0, "heading_y": 1.0
        })
        p["Layer"] = 2

    elif isinstance(agent, MedicAgent):
        color = "#2ecc71" if not getattr(agent, "carrying", False) else "#1e8449"
        p.update({"Shape": "circle", "Color": color, "r": 0.5})
        p["Layer"] = 3

    elif isinstance(agent, TruckAgent):
        p.update({"Shape": "rect", "Color": "#3498db", "w": 0.9, "h": 0.9})
        p["Layer"] = 2

    elif isinstance(agent, Survivor):
        p.update({"Shape": "circle", "Color": "#f1c40f", "r": 0.35})
        p["Layer"] = 1

    else:
        p.update({"Shape": "circle", "Color": "#aaaaaa", "r": 0.3})
        p["Layer"] = 1

    return p


# ---------------- Config helpers ----------------

def load_cfg(path: str) -> Dict:
    if not os.path.exists(path):
        # No YAML — run with an empty config
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _iter_points_from_cfg(cfg: Dict) -> Iterable[Tuple[int, int]]:
    """Yield all (x,y) points referenced in the cfg to infer bounds."""
    depot = cfg.get("depot")
    if isinstance(depot, (list, tuple)) and len(depot) == 2:
        yield (int(depot[0]), int(depot[1]))

    for key in ("hospitals", "rubble", "initial_fires", "buildings"):
        for item in cfg.get(key, []) or []:
            if isinstance(item, (list, tuple)) and len(item) == 2:
                yield (int(item[0]), int(item[1]))

    for s in (cfg.get("survivors_list") or []):
        if isinstance(s, dict) and "pos" in s and isinstance(s["pos"], (list, tuple)) and len(s["pos"]) == 2:
            yield (int(s["pos"][0]), int(s["pos"][1]))
        elif isinstance(s, (list, tuple)) and len(s) == 2:
            yield (int(s[0]), int(s[1]))


def infer_grid_size(cfg: Dict, default: Tuple[int, int] = (20, 20)) -> Tuple[int, int]:
    """Determine (width, height) from cfg, supporting multiple schema variants."""
    grid = cfg.get("grid") or {}
    if isinstance(grid, dict) and "w" in grid and "h" in grid:
        return int(grid["w"]), int(grid["h"])

    if "width" in cfg and "height" in cfg:
        return int(cfg["width"]), int(cfg["height"])

    max_x = max_y = -1
    for (x, y) in _iter_points_from_cfg(cfg):
        if x > max_x: max_x = x
        if y > max_y: max_y = y
    if max_x >= 0 and max_y >= 0:
        return max_x + 1, max_y + 1

    return default


# ---------------- UI panels ----------------

class StatsPanel(TextElement):
    def render(self, model) -> str:
        # survivors still on the map (not picked, not dead)
        on_map = sum(
            1 for a in model.schedule.agents
            if a.__class__.__name__ == "Survivor"
            and not getattr(a, "_picked", False)
            and not getattr(a, "_dead", False)
        )

        # survivors currently being carried by medics
        carrying_now = sum(
            1 for a in model.schedule.agents
            if a.__class__.__name__ == "MedicAgent" and getattr(a, "carrying", False)
        )

        # survivors waiting in hospital queues (not yet admitted)
        queued = sum(len(q) for q in getattr(model, "hospital_queues", {}).values())

        total = getattr(model, "total_survivors", None)
        if total is None:
            total = on_map + carrying_now + queued + model.rescued + model.deaths

        return (
            f"Step: {getattr(model, 'time', 0)}  |  "
            f"Rescued (admitted): {model.rescued}  |  "
            f"In medic arms: {carrying_now}  |  "
            f"In hospital queue: {queued}  |  "
            f"On map: {on_map}  |  "
            f"Deaths: {model.deaths}  |  "
            f"Fires extinguished: {model.fires_extinguished}  |  "
            
        )

# f"Total survivors: {total}"
class LegendPanel(TextElement):
    def render(self, model) -> str:
        return (
            '<div style="font-family: sans-serif; line-height: 1.4; margin:6px 0;">'
            '<strong>Legend</strong> — '
            '<span style="display:inline-block;width:12px;height:12px;background:#3498db;margin:0 6px 0 12px;"></span>'
            'Fire Truck (blue square) '
            '<span style="display:inline-block;width:12px;height:12px;background:#2ecc71;border-radius:50%;margin:0 6px 0 12px;"></span>'
            'Medic / Ambulance (green circle, darker when carrying) '
            # '<span style="display:inline-block;width:0;height:0;border-left:7px solid transparent;border-right:7px solid transparent;border-bottom:12px solid #00bcd4;display:inline-block;margin:0 6px 0 12px;vertical-align:middle;"></span>'
            # 'Drone (cyan triangle) '
            '<span style="display:inline-block;width:12px;height:12px;background:#f1c40f;border-radius:50%;margin:0 6px 0 12px;"></span>'
            'Survivor (yellow circle)'
            '</div>'
        )


# ---------------- Launch ----------------

def launch(port: int = 8521):
    cfg = load_cfg(MAP_PATH)
    width, height = infer_grid_size(cfg, default=(20, 20))

    grid = CanvasGrid(agent_portrayal, width, height, CANVAS_W, CANVAS_H)
    charts = ChartModule(
        [
            {"Label": "rescued", "Color": "Black"},
            {"Label": "deaths", "Color": "Red"},
            {"Label": "fires_extinguished", "Color": "Blue"},
        ],
        data_collector_name="datacollector",
    )

    legend = LegendPanel()
    stats = StatsPanel()

    server = ModularServer(
        CrisisModel,
        [legend, stats, grid, charts],  # order = top-to-bottom in UI
        "CrisisSim",
        {"width": width, "height": height, "rng_seed": SEED, "config": cfg, "render": True},
    )
    server.port = port
    print(f"Starting web UI at http://127.0.0.1:{port}  (Ctrl+C to stop)")
    server.launch()


if __name__ == "__main__":
    launch(port=8522)  # different port to avoid conflicts
