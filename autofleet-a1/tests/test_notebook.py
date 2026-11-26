"""Executes the notebook top to bottom with the offline scripted backend (no API key, no network LLM)."""
import os, pytest
from pathlib import Path
nbformat = pytest.importorskip("nbformat"); nbclient = pytest.importorskip("nbclient"); pytest.importorskip("ipykernel")


def test_notebook_runs_offline(monkeypatch):
    monkeypatch.setenv("AUTOFLEET_MODE", "scripted")
    nb_dir = Path(__file__).resolve().parent.parent / "notebooks"
    nb = nbformat.read(nb_dir / "autofleet_a1_agent.ipynb", as_version=4)
    nbclient.NotebookClient(nb, timeout=240, kernel_name="python3", resources={"metadata": {"path": str(nb_dir)}}).execute()
    text = "".join(o.get("text", "") for c in nb.cells if c.cell_type == "code" for o in c.get("outputs", []))
    assert "backend: scripted" in text and "MCP tools:" in text and "ALL" in text
