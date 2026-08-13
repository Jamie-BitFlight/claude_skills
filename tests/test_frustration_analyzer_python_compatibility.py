"""Regression checks for the frustration-analyzer interpreter contract."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).parents[1]
PLUGIN = ROOT / "plugins" / "frustration-analyzer"


def test_frustration_analyzer_server_imports_on_current_interpreter() -> None:
    """The MCP server module must import cleanly under the running interpreter.

    Replaces a prior version of this test that asserted the PEP 723
    ``requires-python`` bound equaled a literal string -- a tautology that
    proved only that the string was edited, not that the server actually
    works on the interpreters it claims to support. Reuses the existing
    ``_server`` loader from the plugin's own test suite (importable here
    via the shared ``pythonpath`` entry in the root ``pyproject.toml``)
    instead of duplicating its importlib boilerplate.
    """
    import _server

    assert _server.extract_user_messages is not None


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


def test_codex_mcp_launcher_defers_interpreter_selection_to_pep_723() -> None:
    """Codex must use the script's tested interpreter contract, not a forced minor."""
    config = json.loads((PLUGIN / ".mcp.json").read_text(encoding="utf-8"))
    server = config["mcpServers"]["frustration-analyzer"]

    assert server["args"] == ["run", "--script", "mcp/server.py"]
    assert server["env"] == {"UV_NO_BUILD": "1"}


def test_codex_manifest_uses_canonical_mcp_config() -> None:
    manifest = json.loads((PLUGIN / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))

    assert manifest["mcpServers"] == "./.mcp.json"
