# Learning guide: what you built and why

## 1. What MCP is, in one paragraph
Model Context Protocol is a standard way for an AI app (the *client*: Claude Code, Claude Desktop) to
discover and call capabilities in a separate process (the *server*: `server.py`). The server advertises
three kinds of things: **tools** (functions the model may call), **resources** (read-only context, e.g. the schema),
and **prompts** (reusable task templates). Transport here is stdio: the client launches `python server.py` and
exchanges JSON-RPC messages over stdin/stdout. That is why **you must never `print()` in server code**: stdout is the protocol.

## 2. How the pieces map to your original plan
| Plan | In this repo |
|---|---|
| Block 6 "loop: model picks tool, Python runs it, result goes back, up to 4 calls" | Claude (the MCP client) *is* that loop. You wrote only the tool side. |
| "Define tool schemas from docstrings" | `mcp.add_tool(fn)` reads the type hints (JSON schema) and docstring (description). |
| System prompt "state only numbers returned by tools" | `instructions=` in `MCPServer(...)` + the `diagnose_readiness` prompt. |
| Hallucination flag | `eval/score.py`: any number in the answer not found in a tool result. |

## 3. Concepts worth being able to explain in a demo
- **Planted ground truth.** Because you generated the data, you know the right answer, so "does the agent find sensor calibration at 35%?" is measurable, not a vibe.
- **Docstrings are prompts.** Compare `top_bottlenecks`'s docstring to a vague one; tool selection quality depends on it. Try breaking it and re-running the eval.
- **Eval before agent.** The oracle stub (100%) and sloppy stub (23% tool choice, 100% hallucination flag) prove the *scorer* is trustworthy before any model is scored.
- **Readiness points lost** (downtime hours / vehicle-hours x 100) is the common currency that lets you rank unlike causes.
- **Metric choice matters.** Backlog snapshots on one day were too noisy (3-7 open orders per site), so `backlog_aging` also returns a daily-averaged mean age. Look at `mean_age_days` vs `mean_age_days_avg_daily` for Site C.
- **Tuned synthetic data is a caveat.** The generator's parameters were grid-searched on seed 42 until the planted effects landed near their targets (see the comments at the top of `generate.py`). Say so if asked.

## 4. Hands-on exercises (in order; each ~30-60 min)
1. **Talk to it.** Connect the server (README), ask the central question, then ask "why is Site C below target?". Check each number against `truth.json`. Which tools did Claude call, in what order?
2. **Record a baseline.** Ask Claude the 30 questions in `eval/questions.jsonl`, saving `{id, tool_calls, answer}` per line, then `python eval/score.py results.jsonl`. (Writing a small runner with the Anthropic SDK's tool-use loop is a great exercise: it is the loop that MCP hid from you.)
3. **Break a docstring** on `service_cycle_time`, re-run, and see which question types drop.
4. **Block 8: messy data.** Add a `--messy` flag to `generate.py` (3% duplicate work orders, 2% missing `closed_at`, inconsistent category spellings), write `tools/clean.py`, and add a `data_quality_report` tool. Compare clean vs messy scores.
5. **Block 7 upgrade.** Replace TF-IDF in `tools/playbooks.py` with `sentence-transformers` + FAISS; keep `search_playbooks` unchanged and check retrieval still passes.
6. **Block 9: `simulate(site, add_technicians, parts_delay_days)`.** Capacity model: night-shift throughput = technicians x WOs/tech-shift; queue wait scales with load. Add 3 eval questions.
7. **Block 10.** Gradio chat + KPI panel, architecture diagram, 3-minute demo script.

## 5. Gotchas hit while building
- `mcp` 2.x renamed `FastMCP` to `MCPServer` (`from mcp.server.mcpserver import MCPServer`). Tutorials online mostly show the v1 API.
- Sample noise: with ~30 brake orders in a window, medians swing a lot. Plant effects strongly and test with ranges, not exact values.
- The scorer initially flagged the oracle for "hallucinating" numbers that came from a second tool call it hadn't made. That was the scorer being right about the *question* (it needs two calls), which is why questions carry `extra_calls`.
