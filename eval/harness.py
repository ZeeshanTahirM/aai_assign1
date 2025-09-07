\
import argparse, os, json, csv
from pathlib import Path
from tqdm import trange
from ..main import run_episode

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n_seeds", type=int, default=5)
    ap.add_argument("--maps", nargs="+", default=["configs/map_small.yaml"])
    ap.add_argument("--conditions", nargs="+", default=["react_reflexion_mock"])
    ap.add_argument("--ticks", type=int, default=200)
    args = ap.parse_args()

    os.makedirs("results", exist_ok=True)
    os.makedirs("logs", exist_ok=True)

    fieldnames = ["seed","provider","strategy","map","rescued","deaths","avg_rescue_time","fires_extinguished",
                  "roads_cleared","energy_used","tool_calls","invalid_json","replans","hospital_overflow_events","crisis_score"]

    for mappath in args.maps:
        mapname = Path(mappath).stem
        out_csv = f"results/{mapname}_results.csv"
        with open(out_csv, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for cond in args.conditions:
                if "gemini" in cond:
                    provider = "gemini"
                elif "groq" in cond:
                    provider = "groq"
                else:
                    provider = "mock"
                if "react_reflexion" in cond:
                    strategy = "react_reflexion"
                else:
                    strategy = "react"

                for s in trange(args.n_seeds, desc=f"{mapname}-{cond}"):
                    seed = 1000 + s
                    log_path = f"logs/seed_{seed}_{mapname}_{cond}.txt"
                    metrics = run_episode(mappath, seed=seed, ticks=args.ticks, provider=provider, strategy=strategy, log_path=log_path, render=False)
                    row = {
                        "seed": seed,
                        "provider": provider,
                        "strategy": strategy,
                        "map": mapname,
                        "rescued": metrics.get("rescued",0),
                        "deaths": metrics.get("deaths",0),
                        "avg_rescue_time": metrics.get("avg_rescue_time",0.0),
                        "fires_extinguished": metrics.get("fires_extinguished",0),
                        "roads_cleared": metrics.get("roads_cleared",0),
                        "energy_used": metrics.get("energy_used",0),
                        "tool_calls": metrics.get("tool_calls",0),
                        "invalid_json": metrics.get("invalid_json",0),
                        "replans": metrics.get("replans",0),
                        "hospital_overflow_events": metrics.get("hospital_overflow_events",0),
                    }
                    row["crisis_score"] = 3*row["rescued"] - 2*row["deaths"] + 1*row["fires_extinguished"] + 0.5*row["roads_cleared"] - 0.1*row["energy_used"] - 0.05*row["hospital_overflow_events"]
                    writer.writerow(row)

    print("Done. CSVs saved in results/.")

if __name__ == "__main__":
    main()
