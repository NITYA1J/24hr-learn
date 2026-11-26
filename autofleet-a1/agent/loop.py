"""The tool-calling loop (Block 6), model-agnostic.

  question -> model picks tool(s) -> Python runs them -> results go back -> model answers
  (repeat up to `max_calls` tool calls, then force a final answer)

A backend is any object with  .complete(system, messages, tools, allow_tools) -> (text, [tool_uses])
where each tool_use is {"id", "name", "input"}. Messages use Anthropic's block format.
Returns {"answer", "tool_calls": [{name, args, result}]}, exactly what eval/score.py reads.
"""
from __future__ import annotations
import json
from agent.registry import call_tool, tool_specs

SYSTEM = (
    "You are the AutoFleet fleet-service analyst. State ONLY numbers returned by tools; never estimate or recall "
    "numbers. If the data cannot answer the question (revenue, pricing, competitors, forecasts: anything outside "
    "fleet readiness and service operations), say you cannot answer it and do not guess. For root-cause or "
    "'what should we do' questions, call search_playbooks and answer in four parts: **Finding**, **Evidence** "
    "(tool numbers only), **Recommended actions**, **Source playbook**. Dates are ISO strings; sites are A-E; regions R1/R2."
)


def run_agent(question: str, llm, max_calls: int = 4, system: str = SYSTEM, verbose: bool = False) -> dict:
    tools, messages, calls = tool_specs(), [{"role": "user", "content": question}], []
    while True:
        allow = len(calls) < max_calls
        text, uses = llm.complete(system, messages, tools, allow)
        if not uses or not allow:
            return {"answer": text, "tool_calls": calls}
        blocks = ([{"type": "text", "text": text}] if text else []) + \
                 [{"type": "tool_use", "id": u["id"], "name": u["name"], "input": u["input"]} for u in uses]
        messages.append({"role": "assistant", "content": blocks})
        results = []
        for u in uses[: max_calls - len(calls)] if len(uses) > max_calls - len(calls) else uses:
            res = call_tool(u["name"], u["input"])
            calls.append({"name": u["name"], "args": u["input"], "result": res})
            if verbose:
                print(f"  -> {u['name']}({json.dumps(u['input'])})")
            results.append({"type": "tool_result", "tool_use_id": u["id"], "content": json.dumps(res),
                            **({"is_error": True} if "error" in res else {})})
        # every tool_use needs a result block, even ones skipped by the call cap
        done = {r["tool_use_id"] for r in results}
        results += [{"type": "tool_result", "tool_use_id": u["id"], "content": json.dumps({"error": "call limit reached"}),
                     "is_error": True} for u in uses if u["id"] not in done]
        messages.append({"role": "user", "content": results})


class ClaudeBackend:
    """Claude via the Anthropic API (needs `pip install anthropic` and ANTHROPIC_API_KEY)."""
    def __init__(self, model: str = "claude-sonnet-5-5", api_key: str | None = None, max_tokens: int = 1500, client=None):
        if client is None:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
        self.client, self.model, self.max_tokens = client, model, max_tokens

    def complete(self, system, messages, tools, allow_tools=True):
        kw = dict(model=self.model, max_tokens=self.max_tokens, system=system, messages=messages, tools=tools)
        if not allow_tools:
            kw["tool_choice"] = {"type": "none"}
        resp = self.client.messages.create(**kw)
        text = "".join(b.text for b in resp.content if b.type == "text")
        uses = [{"id": b.id, "name": b.name, "input": dict(b.input)} for b in resp.content if b.type == "tool_use"]
        return text, uses


class ScriptedBackend:
    """Offline stand-in for an LLM so the notebook and tests run with no API key or network.
    It looks up the question in eval/questions.jsonl, calls the expected tools, then quotes the tool numbers.
    NOT intelligent: it exists to test the loop, the tools and the scorer."""
    def __init__(self, questions: list[dict]):
        self.by_q = {q["question"]: q for q in questions}

    def complete(self, system, messages, tools, allow_tools=True):
        q = self.by_q.get(messages[0]["content"])
        if q is None or q["type"] == "out_of_scope":
            return "I can't answer that: the data only covers fleet readiness and service operations.", []
        plan = [{"name": q["expected_tool"], "input": q["tool_args"]}, *({"name": e["name"], "input": e["args"]} for e in q["extra_calls"]),
                *({"name": t, "input": {"query": q["question"]} if t == "search_playbooks" else {}} for t in q["also_tools"])]
        done = sum(1 for m in messages if m["role"] == "user" and isinstance(m["content"], list) for _ in m["content"])
        if allow_tools and done < len(plan):
            p = plan[done]
            return "", [{"id": f"toolu_{done}", "name": p["name"], "input": p["input"]}]
        return "Findings: " + "; ".join(f"{k} = {v}" for k, v in q["expected_values"].items()) + ". " + " ".join(q["expected_text"]), []


class OpenAICompatBackend:
    """Any model behind an OpenAI-compatible chat API with tool calling: Kimi (Moonshot API), Qwen / Llama / Kimi
    served locally by Ollama or vLLM, Together, Groq, OpenRouter, etc.  Needs `pip install openai`.
      base_url examples: Ollama  http://localhost:11434/v1   |  vLLM  http://localhost:8000/v1
      (check your provider's docs for its exact base_url and model name)"""
    def __init__(self, model: str, base_url: str | None = None, api_key: str | None = None, max_tokens: int = 1500, client=None):
        if client is None:
            import openai
            client = openai.OpenAI(base_url=base_url, api_key=api_key or "not-needed")
        self.client, self.model, self.max_tokens = client, model, max_tokens

    @staticmethod
    def _convert(system, messages):
        """Anthropic-style blocks -> OpenAI chat messages."""
        out = [{"role": "system", "content": system}]
        for m in messages:
            c = m["content"]
            if isinstance(c, str):
                out.append({"role": m["role"], "content": c})
            elif m["role"] == "assistant":
                text = "".join(b["text"] for b in c if b["type"] == "text")
                calls = [{"id": b["id"], "type": "function", "function": {"name": b["name"], "arguments": json.dumps(b["input"])}}
                         for b in c if b["type"] == "tool_use"]
                out.append({"role": "assistant", "content": text or None, **({"tool_calls": calls} if calls else {})})
            else:
                out += [{"role": "tool", "tool_call_id": b["tool_use_id"], "content": b["content"]} for b in c]
        return out

    def complete(self, system, messages, tools, allow_tools=True):
        oa_tools = [{"type": "function", "function": {"name": t["name"], "description": t["description"],
                                                       "parameters": t["input_schema"]}} for t in tools]
        kw = dict(model=self.model, max_tokens=self.max_tokens, messages=self._convert(system, messages), tools=oa_tools)
        if not allow_tools:
            kw["tool_choice"] = "none"
        msg = self.client.chat.completions.create(**kw).choices[0].message
        uses = []
        for tc in (msg.tool_calls or []):
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}  # small models sometimes emit broken JSON; the tool will return a helpful error
            uses.append({"id": tc.id, "name": tc.function.name, "input": args})
        return msg.content or "", uses
