"""Regression test: MCP servers disable FastMCP's Rich logging/tracebacks.

Why: FastMCP attaches a ``RichHandler(rich_tracebacks=True)`` to its logger.
``rich/logging.py`` lazily imports ``rich.traceback`` *inside* ``emit()`` — only
when an exception is logged. A broken ``rich`` install then turns any dh tool
exception into ``No module named 'rich.traceback'``, masking the real error.
``dh_mcp_preinit`` sets ``FASTMCP_ENABLE_RICH_LOGGING`` /
``FASTMCP_ENABLE_RICH_TRACEBACKS`` to ``"false"`` before either MCP server
imports ``fastmcp``, so FastMCP falls back to a plain ``StreamHandler`` and no
lazy ``rich.traceback`` import ever runs.

"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
_PREINIT = _SCRIPTS_DIR / "dh_mcp_preinit.py"


@pytest.mark.unit
def test_preinit_disables_fastmcp_rich_by_default() -> None:
    """Importing dh_mcp_preinit sets both FASTMCP_ENABLE_RICH_* vars to false."""
    code = (
        "import os, sys; "
        f"sys.path.insert(0, {str(_SCRIPTS_DIR)!r}); "
        "import dh_mcp_preinit; "
        "print(os.environ.get('FASTMCP_ENABLE_RICH_LOGGING')); "
        "print(os.environ.get('FASTMCP_ENABLE_RICH_TRACEBACKS'))"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True, env={}, cwd=str(_SCRIPTS_DIR)
    )
    logging_val, tracebacks_val = result.stdout.splitlines()
    assert logging_val == "false"
    assert tracebacks_val == "false"


@pytest.mark.unit
def test_preinit_does_not_override_explicit_env() -> None:
    """setdefault semantics: an operator-set value survives the import."""
    code = (
        "import os, sys; "
        f"sys.path.insert(0, {str(_SCRIPTS_DIR)!r}); "
        "import dh_mcp_preinit; "
        "print(os.environ['FASTMCP_ENABLE_RICH_LOGGING'])"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=True,
        env={"FASTMCP_ENABLE_RICH_LOGGING": "true"},
        cwd=str(_SCRIPTS_DIR),
    )
    assert result.stdout.strip() == "true"
