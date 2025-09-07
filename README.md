# CrisisSim (Agentic AI Assignment Starter, Pure Python)

Mesa-based ABM + minimal agentic planner (ReAct + Reflexion skeleton).  
Runs in **mock** mode (no API keys) or with **Groq/Gemini** if you supply keys.

## Quickstart
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# MOCK run (no API keys)
python main.py --map configs/map_small.yaml --provider mock --strategy react_reflexion --seed 42 --ticks 150

# GUI
python server.py     # open http://127.0.0.1:8521

# Batch evaluation
python eval/harness.py --n_seeds 5 --maps configs/map_small.yaml configs/map_hard.yaml --conditions react_reflexion_mock

# Plots
python eval/plots.py --input results --out results/plots
```

## Real LLMs (optional)
```bash
# Groq
export LLM_PROVIDER=groq
export GROQ_API_KEY=YOUR_KEY

# Gemini
export LLM_PROVIDER=gemini
export GEMINI_API_KEY=YOUR_KEY
```

**Structure**
```
crisis-sim/
  env/           # Mesa world, agents, dynamics, sensors
  tools/         # routing (A*), resources, hospital
  reasoning/     # llm_client, react (mock+LLM), reflexion, planner
  configs/       # YAML maps
  eval/          # harness (CSV), plots
  logs/, results/, prompts/
```
