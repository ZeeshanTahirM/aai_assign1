import argparse, os, json, yaml
from pathlib import Path
from env.world import CrisisModel
from reasoning.planner import make_plan
from utils.jsonl_logger import write_tick_conversation  # added for per-tick JSONL

def load_config(path):
    with open(path, "r") as f:
        return yaml.safe_load(f) or {}

def run_episode(map_path, seed=42, ticks=200, provider="mock", strategy="react_reflexion", log_path=None, render=False):
    os.environ["LLM_PROVIDER"] = provider
    cfg = load_config(map_path)
    W = cfg.get("width", 20)
    H = cfg.get("height", 20)

    model = CrisisModel(W, H, rng_seed=seed, config=cfg, render=render)

    if log_path is None:
        log_path = f"logs/seed_{seed}_{Path(map_path).stem}_{provider}_{strategy}.txt"
    os.makedirs(Path(log_path).parent, exist_ok=True)
    logf = open(log_path, "w", buffering=1, encoding="utf-8")

    transcript = []

    # ---- run_id for JSONL logs (added) ----
    run_id = f"{Path(map_path).stem}_{provider}_{strategy}_seed{seed}"

    for t in range(ticks):
        state = model.summarize_state()
        plan = make_plan(state, strategy=strategy, scratchpad="\n".join(transcript[-10:]))
        cmds = plan.get("commands", [])
        model.set_plan(cmds)

        # ---- Sprint-1 per-tick JSONL logging (added) ----
        # Build conversation payloads and write logs/strategy=<name>/run=<id>/tickNNN.jsonl
        try:
            conv_lines = [
                {"role": "system", "content": f"strategy={strategy}"},
                {"role": "user", "content": json.dumps(state, ensure_ascii=False)[:4000]},
                {"role": "assistant", "content": "FINAL_JSON: " + json.dumps(plan, ensure_ascii=False)},
            ]
            write_tick_conversation(
                base_dir="logs",
                strategy=strategy,
                run_id=run_id,
                tick=t,
                conversation_lines=conv_lines
            )
        except Exception:
            # non-fatal: keep the sim running even if logging fails
            pass

        # Track invalid_json count if planner returned empty/malformed commands (added)
        try:
            model.invalid_json = getattr(model, "invalid_json", 0) + (0 if (isinstance(plan, dict) and plan.get("commands")) else 1)
        except Exception:
            pass
        # -----------------------------------------------

        logf.write(f"=== t={t} ===\n")
        logf.write(json.dumps({"context": state, "plan": plan})[:2000] + "\n")
        transcript.append(f"t={t}: plan={plan}")

        model.step()

    logf.close()

    hist = model.datacollector.get_model_vars_dataframe()
    rescued = int(hist["rescued"].max() if len(hist) else 0)
    deaths = int(hist["deaths"].max() if len(hist) else 0)
    fires_ext = int(hist["fires_extinguished"].max() if len(hist) else 0)
    roads_cleared = int(hist["roads_cleared"].max() if len(hist) else 0)

    metrics = {
        "rescued": model.rescued,
        "deaths": model.deaths,
        "avg_rescue_time": model.avg_rescue_time,
        "fires_extinguished": model.fires_extinguished,
        "roads_cleared": model.roads_cleared,
        "energy_used": model.energy_used,
        "tool_calls": model.tool_calls,
        "invalid_json": model.invalid_json,
        "replans": model.replans,
        "hospital_overflow_events": model.hospital_overflow_events,
    }
    return metrics
# --- context discovery helper -----------------------------------------------
def build_state(model):
    """
    Try to reuse an existing context/export function from the project.
    Falls back to a minimal dict if none is found.
    """
    candidates = [
        ("crisis.context",        ["export_context", "build_context", "get_context", "to_dict"]),
        ("crisis.utils.context",  ["export_context", "build_context", "get_context", "to_dict"]),
        ("crisis.state",          ["export_context", "build_context", "get_context", "to_dict"]),
        ("crisis.server",         ["export_context", "build_context", "get_context", "serialize", "to_dict"]),
    ]

    # 1) Try known modules/functions
    for mod_name, fn_names in candidates:
        try:
            mod = __import__(mod_name, fromlist=["*"])
        except Exception:
            continue
        for fn in fn_names:
            if hasattr(mod, fn):
                try:
                    return getattr(mod, fn)(model)
                except TypeError:
                    # Some projects expose to_dict() with no args
                    try:
                        return getattr(mod, fn)()
                    except Exception:
                        pass
                except Exception:
                    pass

    # 2) Try a method on the model (if it exists)
    for meth in ("export_context", "to_dict", "as_dict"):
        if hasattr(model, meth) and callable(getattr(model, meth)):
            try:
                return getattr(model, meth)()
            except Exception:
                pass

    # 3) Minimal, safe fallback
    tick = getattr(model, "tick", None)
    if tick is None and hasattr(model, "schedule") and hasattr(model.schedule, "time"):
        tick = model.schedule.time

    agents_list = []
    if hasattr(model, "schedule") and hasattr(model.schedule, "agents"):
        for i, a in enumerate(model.schedule.agents):
            agents_list.append({
                "id": getattr(a, "unique_id", i),
                "type": a.__class__.__name__,
                "pos": getattr(a, "pos", None),
            })

    return {
        "tick": tick,
        "map_name": getattr(model, "map_name", getattr(getattr(model, "map", None), "name", None)),
        "agents": agents_list,
        "resources": getattr(model, "resources", {}),
        "events": getattr(model, "events", []),
        "facts": getattr(model, "facts", {}),
    }
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", type=str, default="configs/map_small.yaml")
    ap.add_argument("--provider", type=str, default="mock", choices=["mock","groq","gemini"])
    ap.add_argument("--strategy", type=str, default="react_reflexion")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--ticks", type=int, default=200)
    ap.add_argument("--render", action="store_true")
    args = ap.parse_args()
    m = run_episode(args.map, seed=args.seed, ticks=args.ticks, provider=args.provider, strategy=args.strategy, render=args.render)
    print(json.dumps(m, indent=2))

if __name__ == "__main__":
    main()
