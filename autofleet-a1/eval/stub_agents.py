"""Two stub 'agents' that prove the scorer works before any LLM is involved.
  oracle: calls the expected tool(s), quotes the numbers verbatim -> should score ~100%.
  sloppy: calls the wrong tool and invents numbers -> should score badly and trip the hallucination flag.
Usage: python eval/stub_agents.py oracle|sloppy > results.jsonl
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools import kpis
from tools.playbooks import search_playbooks

FN = {f.__name__: f for f in [*kpis.TOOLS, search_playbooks]}
qs = [json.loads(l) for l in (Path(__file__).parent / "questions.jsonl").read_text().splitlines()]
mode = sys.argv[1]
for q in qs:
    calls, ans = [], ""
    if mode == "oracle":
        if q["type"] == "out_of_scope":
            ans = "I can't answer that: the data only covers fleet readiness and service operations."
        else:
            for name in [q["expected_tool"], *q["also_tools"]]:
                args = q["tool_args"] if name == q["expected_tool"] else ({"query": q["question"]} if name == "search_playbooks" else {})
                calls.append(dict(name=name, args=args, result=FN[name](**args)))
            for e in q.get("extra_calls", []):
                calls.append(dict(name=e["name"], args=e["args"], result=FN[e["name"]](**e["args"])))
            ans = "Findings: " + "; ".join(f"{k} = {v}" for k, v in q["expected_values"].items()) + ". " + " ".join(q["expected_text"])
    else:
        calls = [dict(name="readiness_trend", args={}, result=kpis.readiness_trend())]
        ans = "Readiness is about 77.7 and revenue is 1,250,000." if q["type"] == "out_of_scope" else "It is roughly 88.8, driven by weather."
    print(json.dumps(dict(id=q["id"], tool_calls=calls, answer=ans)))
