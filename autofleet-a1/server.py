"""AutoFleet A1 as an MCP server.

Exposes the Block 3 KPI functions + playbook retrieval as MCP *tools*, the schema/KPI
definitions as an MCP *resource*, and the central question as an MCP *prompt*.
Claude (Claude Code / Claude Desktop) is the "LLM tool-calling loop" of Block 6: it reads the
tool descriptions (our docstrings), picks tools, receives results, and writes the answer.

Run directly (stdio):  python server.py
"""
from pathlib import Path
from mcp.server.mcpserver import MCPServer
from tools.kpis import TOOLS
from tools.playbooks import search_playbooks

ROOT = Path(__file__).parent
mcp = MCPServer(
    "autofleet-a1",
    instructions=(
        "You are the AutoFleet fleet-service analyst. State ONLY numbers returned by tools; never estimate or "
        "recall numbers. If the data cannot answer the question (e.g. revenue, pricing, anything outside "
        "fleet readiness / service operations), say so and do not guess. For root-cause questions, answer in four parts: "
        "Finding, Evidence (tool numbers), Recommended actions, Source playbook (via search_playbooks)."
    ),
)

for fn in [*TOOLS, search_playbooks]:
    mcp.add_tool(fn)  # name + description + JSON schema come from the function itself


@mcp.resource("autofleet://schema")
def schema() -> str:
    """Table schema and KPI definitions for the AutoFleet dataset."""
    return (ROOT / "SCHEMA.md").read_text()


@mcp.prompt()
def diagnose_readiness() -> str:
    """The central A1 question, with the four-part answer format."""
    return (
        "What is preventing our robotaxi fleet from achieving target operational readiness, and what actions "
        "would improve it?\n\nPlan: (1) fleet_readiness to size the gap and find sites below target; "
        "(2) top_bottlenecks for the biggest causes; (3) readiness_trend, backlog_aging and technician_productivity "
        "to locate sites/regions with structural problems; (4) service_cycle_time / downtime_by_category to drill into "
        "anomalies; (5) search_playbooks for each finding.\n\nAnswer as: **Finding**, **Evidence** (only numbers "
        "from tools), **Recommended actions**, **Source playbook**."
    )


if __name__ == "__main__":
    mcp.run()
