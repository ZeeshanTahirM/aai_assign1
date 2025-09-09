# eval/aggregate.py
import json, os, csv

RAW = "results/raw"
OUTDIR = "results/agg"
os.makedirs(OUTDIR, exist_ok=True)
rows = []
for fn in os.listdir(RAW):
    if not fn.endswith(".json"): continue
    with open(os.path.join(RAW, fn), "r", encoding="utf-8") as f:
        rows.append(json.load(f))

cols = ["run_id","map","strategy","seed","ticks","rescued","deaths",
        "avg_rescue_time","fires_extinguished","roads_cleared","energy_used",
        "tool_calls","invalid_json","replans","hospital_overflow_events"]

with open(os.path.join(OUTDIR, "summary.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader()
    for r in rows:
        w.writerow({c: r.get(c, "") for c in cols})
print(f"Wrote {len(rows)} rows -> results/agg/summary.csv")
