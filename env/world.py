\
from mesa import Model
from mesa.space import MultiGrid
from mesa.time import SimultaneousActivation
from mesa.datacollection import DataCollector
import random
from collections import deque
from .agents import DroneAgent, MedicAgent, TruckAgent, Survivor
from env.agents import Survivor, MedicAgent

from .dynamics import spread_fires, trigger_aftershocks

CELL_ROAD = "road"
CELL_BUILDING = "building"
CELL_RUBBLE = "rubble"
CELL_FIRE = "fire"
CELL_HOSPITAL = "hospital"
CELL_DEPOT = "depot"
CELL_EMPTY = "empty"

class CrisisModel(Model):
    """
    Mesa model containing the world grid, agents, and per-tick dynamics.
    Reasoning/planning is orchestrated by main.py; this model exposes helpers
    to summarize state and to apply per-tick plans.
    """
    def __init__(self, width, height, rng_seed=42, config=None, render=False):
        super().__init__()
        self.random = random.Random(rng_seed)
        self.width = width
        self.height = height
        self.grid = MultiGrid(width, height, torus=False)
        self.schedule = SimultaneousActivation(self)
        self.render = render
        self.running = True
        self.total_survivors = None  # will compute first step
    
        # Params
        self.p_fire_spread = 0.15
        self.p_aftershock = 0.02
        self.hospital_service_rate = 2  # patients per tick per hospital
        self.hospital_queues = {}  # {(x,y): [survivor_ids...]}
        # Timing / rescue-time tracking
        self.time = 0                      # simulation ticks since start
        self._rescue_times = []            # list of tick-times when survivors get admitted
        self.avg_rescue_time = 0.0         # rolling average (in ticks)

        # Metrics (some are placeholders for extension)
        self.rescued = 0
        self.deaths = 0
        self.fires_extinguished = 0
        self.roads_cleared = 0
        self.energy_used = 0
        self.tool_calls = 0
        self.invalid_json = 0
        self.replans = 0
        self.hospital_overflow_events = 0

        # Map
        self.cell_types = [[CELL_EMPTY for _ in range(width)] for _ in range(height)]
        self._init_from_config(config or {})

        # Agents
        self._spawn_initial_agents()
        self._place_survivors(config.get("survivors", 10))
        # Cache how many survivors were spawned at start (fallback to None if types differ)
        try:
            self.total_survivors = sum(1 for a in self.schedule.agents if isinstance(a, Survivor))
        except Exception:
            self.total_survivors = None  # we'll infer on the first step if needed

        # DataCollector
        self.datacollector = DataCollector(model_reporters={
            "rescued": "rescued",
            "deaths": "deaths",
            "fires_extinguished": "fires_extinguished",
            "roads_cleared": "roads_cleared",
            "energy_used": "energy_used",
            "tool_calls": "tool_calls",
            "invalid_json": "invalid_json",
            "replans": "replans",
            "hospital_overflow_events": "hospital_overflow_events",
        })

        # Plan from planner applied each tick
        self.pending_commands = []  # list of {"agent_id": str, "type": "move|act", ...}

    def _init_from_config(self, cfg):
        W, H = self.width, self.height
        # Default: everything road except explicit types
        for y in range(H):
            for x in range(W):
                self.cell_types[y][x] = CELL_ROAD

        def set_cell(x, y, val):
            if 0 <= x < W and 0 <= y < H:
                self.cell_types[y][x] = val

        depot = cfg.get("depot", [1,1])
        set_cell(depot[0], depot[1], CELL_DEPOT)
        self.depot = tuple(depot)

        for h in cfg.get("hospitals", []):
            set_cell(h[0], h[1], CELL_HOSPITAL)
            self.hospital_queues[tuple(h)] = []

        for r in cfg.get("rubble", []):
            set_cell(r[0], r[1], CELL_RUBBLE)

        for f in cfg.get("initial_fires", []):
            set_cell(f[0], f[1], CELL_FIRE)

        for b in cfg.get("buildings", []):
            if isinstance(b, list) and len(b) == 2 and all(isinstance(v, int) for v in b):
                set_cell(b[0], b[1], CELL_BUILDING)

    def _spawn_initial_agents(self):
        # 1 drone, 2 medics, 1 truck to start (tweak as desired)
        d = DroneAgent(self.next_id(), self, battery_max=80)
        m1 = MedicAgent(self.next_id(), self)
        m2 = MedicAgent(self.next_id(), self)
        t = TruckAgent(self.next_id(), self, mode="water", water_max=30, tools_max=10)

        for a in (d, m1, m2, t):
            self.schedule.add(a)
            self.grid.place_agent(a, self.depot)

    def _place_survivors(self, n):
        placed = 0
        attempts = 0
        while placed < n and attempts < n*50:
            x = self.random.randrange(self.width)
            y = self.random.randrange(self.height)
            ct = self.cell_types[y][x]
            if ct in (CELL_BUILDING, CELL_RUBBLE, CELL_ROAD, CELL_EMPTY):
                s = Survivor(self.next_id(), self, life_deadline=self.random.randint(120, 260))
                self.schedule.add(s)
                self.grid.place_agent(s, (x, y))
                placed += 1
            attempts += 1

    # ----------------- Per-tick orchestration -----------------
    def set_plan(self, commands):
        """Accept list of per-agent command dicts generated by planner."""
        self.pending_commands = commands or []
    def step(self):
        """Apply pending plan, update dynamics, and collect metrics."""
        # --- Apply planner commands to agents for this tick ---

        # --- AUTO-PLAN in GUI mode ---
        if getattr(self, "render", False):
            try:
                from reasoning.react import mock_react_with_tools
            except Exception:
                mock_react_with_tools = None

            if mock_react_with_tools is not None:
                # export a context dict like the one used in headless runs
                ctx = self.export_state() if hasattr(self, "export_state") else {
                    "grid": {"w": self.width, "h": self.height},
                    "depot": list(self.depot),
                    "agents": [
                        {
                            "id": str(a.unique_id),
                            "kind": getattr(a, "kind", "unknown"),
                            "pos": list(a.pos),
                            "battery": getattr(a, "battery", None),
                            "water": getattr(a, "water", None),
                            "tools": getattr(a, "tools", None),
                            "carrying": getattr(a, "carrying", False),
                        }
                        for a in self.schedule.agents
                    ],
                    "hospitals": [{"pos": list(k)} for k in self.hospital_queues.keys()],
                    "fires": [
                        [x, y] for y in range(self.height) for x in range(self.width)
                        if self.cell_type(x, y) == "fire" or self.cell_type(x, y) == CELL_FIRE
                    ],
                    "rubble": [
                        [x, y] for y in range(self.height) for x in range(self.width)
                        if self.cell_type(x, y) == "rubble" or self.cell_type(x, y) == CELL_RUBBLE
                    ],
                    "survivors": [
                        {"id": str(a.unique_id), "pos": list(a.pos), "deadline": getattr(a, "deadline", 999)}
                        for a in self.schedule.agents if a.__class__.__name__ == "Survivor"
                    ],
                }
                plan = mock_react_with_tools(ctx)
                self.pending_commands = plan.get("commands", [])
        # --- end auto-plan block ---

        # existing code that maps self.pending_commands to each agent, then:
        # self.schedule.step()
        # spread_fires / trigger_aftershocks / hospital queues / removals / datacollector

        self.time += 1
        cmd_map = {}
        for cmd in self.pending_commands:
            aid = cmd.get("agent_id")
            if aid is not None:
                cmd_map[aid] = cmd
        for agent in self.schedule.agents:
            if hasattr(agent, "set_command"):
                acmd = cmd_map.get(str(agent.unique_id))
                agent.set_command(acmd)

        # --- Run one scheduler cycle (SimultaneousActivation: step() then advance()) ---
        self.schedule.step()

        # --- World dynamics (fires, aftershocks) ---
        fe = spread_fires(self)
        self.fires_extinguished += fe.get("extinguished", 0)
        ac = trigger_aftershocks(self)
        self.roads_cleared += ac.get("roads_cleared", 0)

        # --- Hospital service (queues -> rescued) ---
        self._process_hospital_queues()

        # === DEFERRED REMOVALS ===
        # Remove survivors that were picked up (flagged) or died this tick.
        to_remove = []
        for a in list(self.schedule.agents):
            if isinstance(a, Survivor):
                if getattr(a, "_dead", False):
                    self.deaths += 1
                    to_remove.append(a)
                elif getattr(a, "_picked", False):
                    to_remove.append(a)
        for a in to_remove:
            try:
                self.grid.remove_agent(a)
            except Exception:
                pass
            try:
                self.schedule.remove(a)
            except Exception:
                pass
        # === end deferred removals ===

        # --- Metrics collection ---
        self.datacollector.collect(self)

        # --- Clear the applied plan for next tick ---
        self.pending_commands = []
        # --- Stop conditions ---
        # a) stop if no survivors remain (rescued + deaths = total)
        total_spawned = getattr(self, "total_survivors", None)
        # compute total once
        if self.total_survivors is None:
            self.total_survivors = (
                sum(1 for a in self.schedule.agents if a.__class__.__name__ == "Survivor")
                + sum(len(q) for q in self.hospital_queues.values())
                + sum(1 for a in self.schedule.agents if a.__class__.__name__ == "MedicAgent" and getattr(a, "carrying", False))
                + self.rescued + self.deaths
            )

        # stop when all survivors resolved
        # if self.rescued + self.deaths >= self.total_survivors:
            # self.running = False

        # or stop at a cap to mirror CLI ticks
        # MAX_TICKS = 300
        # if self.time >= MAX_TICKS:
            # self.running = False


    def _process_hospital_queues(self):
        """
        Each tick, every hospital serves up to `hospital_service_rate` survivors (FIFO).
        Records time-to-admission in ticks and updates avg_rescue_time.
        """
        rate = int(self.hospital_service_rate) if self.hospital_service_rate is not None else 0
        for hpos, q in self.hospital_queues.items():
            served = 0
            while q and served < rate:
                _sid = q.pop(0)  # FIFO list
                self.rescued += 1
                # record this admission time (ticks since start)
                self._rescue_times.append(self.time)
                # update rolling average
                self.avg_rescue_time = (
                    sum(self._rescue_times) / float(len(self._rescue_times))
                )
                served += 1
            if len(q) > 10:
                self.hospital_overflow_events += 1



    def summarize_state(self):
        agents = []
        for a in self.schedule.agents:
            if hasattr(a, "kind"):
                agents.append({
                    "id": str(a.unique_id),
                    "kind": a.kind,
                    "pos": list(a.pos) if hasattr(a, "pos") else None,
                    "battery": getattr(a, "battery", None),
                    "water": getattr(a, "water", None),
                    "tools": getattr(a, "tools", None),
                    "carrying": getattr(a, "carrying", False),
                })
        hospitals = [{"pos": list(pos), "queue_len": len(q)} for pos, q in self.hospital_queues.items()]
        fires, rubble, survivors = [], [], []
        for y in range(self.height):
            for x in range(self.width):
                ct = self.cell_types[y][x]
                if ct == CELL_FIRE: fires.append([x,y])
                if ct == CELL_RUBBLE: rubble.append([x,y])
        for a in self.schedule.agents:
            if isinstance(a, Survivor):
                survivors.append({"id": str(a.unique_id), "pos": list(a.pos), "deadline": a.life_deadline})

        return {
            "grid": {"w": self.width, "h": self.height},
            "depot": list(self.depot),
            "agents": agents,
            "hospitals": hospitals,
            "fires": fires,
            "rubble": rubble,
            "survivors": survivors
        }

    def hospital_queue_state(self):
        return {
            "queues": [{"hospital": list(k), "len": len(v)} for k,v in self.hospital_queues.items()],
            "service_rate": self.hospital_service_rate
        }

    # def add_to_hospital_queue(self, pos, survivor_id):
    #     if tuple(pos) in self.hospital_queues:
    #         self.hospital_queues[tuple(pos)].append(survivor_id)

    def cell_type(self, x, y):
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.cell_types[y][x]
        return None
    def add_to_hospital_queue(self, pos, survivor_id: str):
        """
        Enqueue a survivor at the hospital located at `pos` (x,y).
        If the exact pos is not a hospital key, fallback to the nearest hospital.
        """
        key = tuple(pos)
        if key not in self.hospital_queues:
            # fallback to nearest hospital by Manhattan distance
            if not self.hospital_queues:
                return
            px, py = key
            nearest = min(
                self.hospital_queues.keys(),
                key=lambda hp: abs(hp[0] - px) + abs(hp[1] - py)
            )
            key = nearest
        self.hospital_queues[key].append(str(survivor_id))


    def _process_hospital_queues(self):
        """
        Each tick, every hospital serves up to `hospital_service_rate` survivors (FIFO).
        Increments self.rescued and optionally tracks overflow.
        """
        rate = int(self.hospital_service_rate) if self.hospital_service_rate is not None else 0
        for hpos, q in self.hospital_queues.items():
            served = 0
            while q and served < rate:
                _sid = q.pop(0)  # FIFO list
                self.rescued += 1
                served += 1
            if len(q) > 10:
                self.hospital_overflow_events += 1


        def is_blocked(self, x, y):
            return self.cell_type(x,y) in (CELL_FIRE, CELL_RUBBLE, CELL_BUILDING)

import yaml, os

def load_map_config(path: str):
    """
    Load a YAML map config and return it as a Python dict.
    """
    with open(path, "r") as f:
        return yaml.safe_load(f)

