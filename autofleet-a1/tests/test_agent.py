"""Tests the loop, tool specs and Claude message plumbing offline (a fake Anthropic client, no network)."""
import json
from pathlib import Path
from types import SimpleNamespace as NS
from agent.loop import run_agent, ClaudeBackend, ScriptedBackend
from agent.registry import tool_specs, call_tool

QS = [json.loads(l) for l in (Path(__file__).resolve().parent.parent / "eval" / "questions.jsonl").read_text().splitlines()]


def test_specs_have_descriptions_and_schemas():
    specs = {s["name"]: s for s in tool_specs()}
    assert len(specs) == 8
    assert "site" in specs["fleet_readiness"]["input_schema"]["properties"]
    assert specs["search_playbooks"]["input_schema"]["required"] == ["query"]
    assert all(len(s["description"]) > 40 for s in specs.values())


def test_bad_arguments_return_error_not_crash():
    assert "Valid sites" in call_tool("fleet_readiness", {"site": "Z"})["error"]
    assert "Unknown tool" in call_tool("nope", {})["error"]
    assert "error" in call_tool("fleet_readiness", {"bogus": 1})


def test_scripted_backend_runs_loop_and_scores_100(tmp_path):
    from eval.score import score_one
    rows = []
    for q in QS:
        r = run_agent(q["question"], ScriptedBackend(QS))
        rows.append(score_one(q, r))
    assert all(r["tool_ok"] and r["numeric_ok"] and r["refusal_ok"] and not r["hallucinated"] for r in rows)


class FakeClient:
    """Mimics anthropic.Anthropic().messages.create: first asks for a tool, then answers."""
    def __init__(self): self.calls, self.messages = [], NS(create=self.create)
    def create(self, **kw):
        self.calls.append(kw)
        if len(self.calls) == 1:
            return NS(content=[NS(type="text", text="Let me check."), NS(type="tool_use", id="t1", name="top_bottlenecks", input={"n": 1})])
        assert kw["messages"][-1]["content"][0]["type"] == "tool_result"
        return NS(content=[NS(type="text", text="Sensor calibration costs 2.93 points.")])


def test_claude_backend_message_flow():
    fc = FakeClient()
    out = run_agent("top cause?", ClaudeBackend(client=fc))
    assert out["tool_calls"][0]["name"] == "top_bottlenecks"
    assert out["tool_calls"][0]["result"]["top"][0]["category"] == "sensor_calibration"
    assert out["answer"].startswith("Sensor")
    assert fc.calls[0]["tools"][0]["input_schema"]["type"] == "object"


def test_call_cap_forces_final_answer():
    class Greedy:
        def complete(self, system, messages, tools, allow_tools=True):
            return ("final" if not allow_tools else "", [] if not allow_tools else [{"id": f"x{len(messages)}", "name": "readiness_trend", "input": {}}])
    out = run_agent("q", Greedy(), max_calls=4)
    assert len(out["tool_calls"]) == 4 and out["answer"] == "final"
