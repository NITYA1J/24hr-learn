"""Block 4: the scorer.

Input: a results .jsonl, one line per question:
  {"id": "q01", "tool_calls": [{"name": "...", "args": {...}, "result": {...}}], "answer": "text"}
Metrics (the four from the plan):
  tool_choice   expected tool (and any also_tools) was called; out-of-scope: no data tool needed
  numeric       every expected value appears in the answer within tolerance
  refusal       out-of-scope answered with a decline; in-scope NOT declined
  hallucination any number in the answer that is not in a tool result (or in the question)
Usage: python eval/score.py results.jsonl
"""
import json, re, sys
from pathlib import Path

QS = {q["id"]: q for q in map(json.loads, (Path(__file__).parent / "questions.jsonl").read_text().splitlines())}
DECLINE = re.compile(r"can(?:no|')t (?:answer|help)|cannot|can't|don't have|do not have|not available|out of scope|outside|unable|no data", re.I)
NUM = re.compile(r"(?<![\w.])-?\d+(?:,\d{3})*(?:\.\d+)?")
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def nums(text: str) -> list[float]:
    return [float(m.replace(",", "")) for m in NUM.findall(DATE.sub(" ", text))]


def flatten(x) -> list[float]:
    if isinstance(x, bool): return []
    if isinstance(x, (int, float)): return [float(x)]
    if isinstance(x, dict): return [n for v in x.values() for n in flatten(v)]
    if isinstance(x, list): return [n for v in x for n in flatten(v)]
    if isinstance(x, str): return nums(x)
    return []


def close(a: float, b: float, tol: float = 0.02) -> bool:
    return abs(a - b) <= max(tol * abs(b), 0.06)


def score_one(q: dict, r: dict) -> dict:
    ans, calls = r.get("answer", ""), r.get("tool_calls", [])
    called = {c["name"] for c in calls}
    declined = bool(DECLINE.search(ans))
    out = {"id": q["id"], "type": q["type"]}
    if q["type"] == "out_of_scope":
        out.update(tool_ok=True, numeric_ok=True, refusal_ok=declined)
    else:
        out["tool_ok"] = q["expected_tool"] in called and all(t in called for t in q["also_tools"])
        a = nums(ans)
        out["numeric_ok"] = all(any(close(x, v, q["tolerance"]) for x in a) for v in q["expected_values"].values()) \
            and all(t.lower().replace("_", " ") in ans.lower().replace("_", " ") for t in q["expected_text"])
        out["refusal_ok"] = not declined
    allowed = [n for c in calls for n in flatten(c.get("result"))] + nums(q["question"])
    bad = [x for x in nums(ans) if not any(close(x, y, 0.001) for y in allowed)]
    out["hallucinated"] = bool(bad)
    out["bad_numbers"] = bad
    return out


def main(path: str) -> None:
    res = {json.loads(l)["id"]: json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()}
    rows = [score_one(q, res.get(i, {})) for i, q in QS.items()]
    types = ["lookup", "ranking", "root_cause", "trend", "out_of_scope"]
    print(f"{'type':<13}{'n':>3}{'tool':>8}{'numeric':>9}{'refusal':>9}{'halluc':>8}")
    def line(label, rs):
        n = len(rs); f = lambda k: f"{sum(r[k] for r in rs) / n:.0%}"
        print(f"{label:<13}{n:>3}{f('tool_ok'):>8}{f('numeric_ok'):>9}{f('refusal_ok'):>9}{sum(r['hallucinated'] for r in rs) / n:>8.0%}")
    for t in types: line(t, [r for r in rows if r["type"] == t])
    line("ALL", rows)
    for r in rows:
        if r["bad_numbers"]: print(f"  hallucinated numbers in {r['id']}: {r['bad_numbers']}")


if __name__ == "__main__":
    main(sys.argv[1])
