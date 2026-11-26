"""Turn the plain Python tool functions into LLM tool specs (name, description, JSON schema).

This is the same idea MCP's add_tool() uses, written out so you can SEE it: the docstring becomes the
description and the type hints become the JSON schema. Works with any LLM API that takes JSON-schema tools.
"""
from __future__ import annotations
import inspect, json
from typing import Any, get_type_hints
from pydantic import TypeAdapter
from tools.kpis import TOOLS
from tools.playbooks import search_playbooks

FUNCS = {f.__name__: f for f in [*TOOLS, search_playbooks]}


def tool_specs() -> list[dict]:
    specs = []
    for name, fn in FUNCS.items():
        hints, props, required = get_type_hints(fn), {}, []
        for p in inspect.signature(fn).parameters.values():
            props[p.name] = TypeAdapter(hints[p.name]).json_schema()
            if p.default is inspect.Parameter.empty:
                required.append(p.name)
        specs.append({"name": name, "description": inspect.getdoc(fn),
                      "input_schema": {"type": "object", "properties": props, "required": required}})
    return specs


def call_tool(name: str, args: dict[str, Any]) -> dict:
    """Run a tool; return its result, or {'error': ...} so the model can recover from bad arguments."""
    if name not in FUNCS:
        return {"error": f"Unknown tool '{name}'. Valid tools: {sorted(FUNCS)}"}
    try:
        return FUNCS[name](**args)
    except Exception as e:  # ValueError for bad site/category, TypeError for bad args
        return {"error": f"{type(e).__name__}: {e}"}


if __name__ == "__main__":
    print(json.dumps(tool_specs()[0], indent=2))
