"""Spawns the real server over stdio and talks to it like Claude would."""
import asyncio, json, sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters, stdio_client

ROOT = Path(__file__).resolve().parent.parent


async def _session_run(fn):
    params = StdioServerParameters(command=sys.executable, args=["server.py"], cwd=str(ROOT))
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            return await fn(s)


def test_tools_listed_with_descriptions():
    async def go(s):
        return (await s.list_tools()).tools
    tools = {t.name: t for t in asyncio.run(_session_run(go))}
    assert {"fleet_readiness", "top_bottlenecks", "backlog_aging", "readiness_trend", "search_playbooks"} <= set(tools)
    assert all(t.description and len(t.description) > 40 for t in tools.values())


def test_call_tool_returns_planted_truth():
    async def go(s):
        return await s.call_tool("top_bottlenecks", {"n": 1})
    res = asyncio.run(_session_run(go))
    payload = json.loads(res.content[0].text)
    assert payload["top"][0]["category"] == "sensor_calibration"
