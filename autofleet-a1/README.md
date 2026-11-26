# AutoFleet A1: Fleet Service Intelligence (as an MCP server)

Answers *"What is preventing our robotaxi fleet from achieving target operational readiness, and what
actions would improve it?"* with evidence and a recommendation. Synthetic data with planted root causes,
a pandas KPI tool library, playbook retrieval, an eval harness, and an **MCP server** so Claude is the
tool-calling agent.

```
data/generate.py ──► data/*.csv + truth.json (answer key)
tools/kpis.py ──────► 7 KPI functions   ┐
tools/playbooks.py ─► playbook search   ├─► server.py (MCP) ◄── Claude Code / Claude Desktop
SCHEMA.md ──────────► MCP resource      ┘
eval/ ──► 30 questions + scorer + stub agents      tests/ ──► truth recovery + MCP-over-stdio
```

## Quick start
```bash
pip install -r requirements.txt
python data/generate.py          # deterministic (seed 42); rewrites data/ and truth.json
python -m pytest -q              # 17 tests: all 5 planted truths recovered, server works over stdio
python eval/build_questions.py   # regenerate the 30 eval questions from the tools
python eval/stub_agents.py oracle > /tmp/r.jsonl && python eval/score.py /tmp/r.jsonl
```

## Run it as a notebook (Jupyter or Colab)
Open `notebooks/autofleet_a1_agent.ipynb`. It runs the whole pipeline: data, KPI tools, the tool-calling agent
(`agent/loop.py`), the 30-question eval, a side-by-side model comparison, and an MCP client. The brain is pluggable:

| Backend | How to select it (environment variables) |
|---|---|
| **Gemini** (Google AI Studio key, via its OpenAI-compatible endpoint) | `GEMINI_API_KEY` (or paste it when prompted). The notebook lists your key's models and asks you to pick one |
| **Kimi (Moonshot AI)** | `MOONSHOT_API_KEY` (or paste it when prompted). The notebook lists the models your key can use and asks you to pick one. China accounts: `AUTOFLEET_BASE_URL=https://api.moonshot.cn/v1` |
| Other open models: Qwen, Llama (Ollama, vLLM, any OpenAI-compatible API with tool calling) | `AUTOFLEET_BASE_URL`, `AUTOFLEET_MODEL`, optional `AUTOFLEET_API_KEY` |
| Claude (optional) | `AUTOFLEET_MODE=claude` + `ANTHROPIC_API_KEY` |
| Offline scripted (tests the loop, tools and scorer; not a model score) | `AUTOFLEET_MODE=scripted`, or nothing set |
```bash
pip install -r requirements.txt jupyter
jupyter notebook notebooks/autofleet_a1_agent.ipynb
```
On Colab, upload or open the notebook; the first cell clones the repo and installs dependencies. To use the agent from
your own code: `from agent.loop import run_agent, ClaudeBackend`.

## Use it from Claude
**Claude Code** (from this folder; `.mcp.json` is picked up automatically, or add it explicitly):
```bash
claude mcp add autofleet-a1 -- python3 /absolute/path/to/autofleet-a1/server.py
```
Then ask: *"Use the diagnose_readiness prompt"* or the central question directly.

**Claude Desktop** (`claude_desktop_config.json`):
```json
{ "mcpServers": { "autofleet-a1": { "command": "python3", "args": ["/absolute/path/to/autofleet-a1/server.py"] } } }
```

Exposed over MCP: 8 **tools** (`fleet_readiness`, `downtime_by_category`, `service_cycle_time`, `backlog_aging`,
`technician_productivity`, `top_bottlenecks`, `readiness_trend`, `search_playbooks`), 1 **resource**
(`autofleet://schema`), 1 **prompt** (`diagnose_readiness`).

## Planted truths (measured values in `data/truth.json`)
| # | Truth | Where a tool shows it |
|---|---|---|
| 1 | sensor_calibration = 35% of downtime hours (~2.9 readiness pts) | `top_bottlenecks` |
| 2 | Site C night-shift shortage (2 night techs vs 5), backlog ~1.95x older | `backlog_aging`, `technician_productivity` |
| 3 | Site B brake-pad shortage weeks 5-6, brake cycle time +64% | `service_cycle_time`, `parts_availability.csv` |
| 4 | Region 2 readiness falls ~1.57 pts/week | `readiness_trend` |
| 5 | Site A healthy (control, above target) | `fleet_readiness` |

Dataset: 4,583 work orders, 300 vehicles, 5 sites, 8 weeks (plan said ~4,000; close enough, the extra comes from Region 2's rising intake).

## Status vs the 48h plan
| Block | Status |
|---|---|
| 1 Setup/schema | done (`SCHEMA.md`) |
| 2 Generator | done |
| 3 KPI tools + tests | done |
| 4 Eval set + scorer | done (validated with stub agents; no LLM score yet) |
| 5 Checkpoint | done |
| 6 LLM tool-calling loop | done two ways: **MCP** (`server.py`, Claude Desktop/Code is the loop) and **notebook** (`agent/loop.py` + Anthropic API). The Claude and OpenAI-compatible (Kimi/Qwen/etc.) paths are tested with fake clients only; no live baseline score recorded yet |
| 7 Playbook RAG | done, TF-IDF (embedding + FAISS swap is an exercise) |
| 8 Messy data / model comparison | model comparison tooling done (`eval/compare.py`, notebook section 7); messy data not started |
| 9 What-if `simulate` | not started |
| 10 UI / diagram / demo | notebook host done; Gradio UI, diagram, demo script not started |
