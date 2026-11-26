"""Block 8: run the same 30-question eval on several backends and return one comparison table."""
from __future__ import annotations
import json
from pathlib import Path
import pandas as pd
from agent.loop import run_agent
from eval.score import QS, score_one


def evaluate(llm, questions: list[dict] | None = None, out_path: str | None = None) -> pd.DataFrame:
    """Run `llm` on the questions; return one scored row per question (and optionally save raw results as .jsonl)."""
    rows, raw = [], []
    for q in (questions or list(QS.values())):
        r = run_agent(q["question"], llm)
        raw.append({"id": q["id"], **r})
        rows.append(score_one(q, r))
    if out_path:
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_text("\n".join(json.dumps(x) for x in raw) + "\n")
    return pd.DataFrame(rows)


def compare(backends: dict[str, object]) -> pd.DataFrame:
    """backends: {"claude": ClaudeBackend(...), "qwen3-8b": OpenAICompatBackend(...)} -> one row per model, percentages."""
    out = {}
    for name, llm in backends.items():
        d = evaluate(llm, out_path=f"eval/results/{name.replace(':', '_')}.jsonl")
        out[name] = {"tool_choice_%": d.tool_ok.mean() * 100, "numeric_%": d.numeric_ok.mean() * 100,
                     "refusal_%": d.refusal_ok.mean() * 100, "hallucination_%": d.hallucinated.mean() * 100,
                     "questions": len(d)}
    return pd.DataFrame(out).T.round(1)
