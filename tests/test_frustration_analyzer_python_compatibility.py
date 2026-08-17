"""Regression checks for the frustration-analyzer interpreter contract."""

from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).parents[1]
PLUGIN = ROOT / "plugins" / "frustration-analyzer"


def read_pep_723_metadata(script: Path) -> dict[str, object]:
    """Parse the inline PEP 723 block without importing the MCP server."""
    lines = script.read_text(encoding="utf-8").splitlines()
    start = lines.index("# /// script") + 1
    end = lines.index("# ///", start)
    metadata = "\n".join(line.removeprefix("# ") for line in lines[start:end])
    return tomllib.loads(metadata)


def test_frustration_analyzer_declares_python_312_through_314_support() -> None:
    """The server metadata includes every interpreter the plugin supports."""
    metadata = read_pep_723_metadata(PLUGIN / "mcp" / "server.py")

    assert metadata["requires-python"] == ">=3.11,<3.15"
