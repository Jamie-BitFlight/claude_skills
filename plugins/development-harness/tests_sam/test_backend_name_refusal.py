"""An unrecognised backend name must not be a bare ``ValueError``.

``create_task_backend`` and ``create_context_backend`` resolve their name from an env
var, then ``.dh/config.yaml``, then the beads marker, and refused an unknown one with a
plain ``ValueError`` -- the unconverted siblings of the refusal 5c804ad6a fixed in
``backlog_core.backend_protocol``. Nothing on the SAM path catches ``ValueError``, and
``server_backend`` built the context backend at import time, so ``CONTEXTBACKEND=bogus``
made ``import sam_schema.server_backend`` fail outright: the server did not start, which
is worse than a failed call.

The refusal is now ``SamError``, sam_schema's own base error, and ``server_backend``
builds the context backend on first use -- converting the refusal into the ``ToolError``
the MCP layer reports to the caller, the same way ``cli_active_task`` turns it into a
clean CLI error.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastmcp.exceptions import ToolError
from sam_schema.core.action_models import GetActiveTaskConfig
from sam_schema.core.context_config import create_context_backend, reset_context_config
from sam_schema.core.exceptions import SamError
from sam_schema.core.task_config import create_task_backend
from sam_schema.server_active_task import sam_active_task_impl

_PLUGIN_DIR = Path(__file__).resolve().parents[1]


def test_unknown_context_backend_name_refuses_as_a_sam_error() -> None:
    """``create_context_backend`` refuses an unknown name with sam_schema's own error."""
    with pytest.raises(SamError, match="Unknown backend"):
        create_context_backend("bogus")


def test_unknown_task_backend_name_refuses_as_a_sam_error() -> None:
    """``create_task_backend`` refuses an unknown name the same way."""
    with pytest.raises(SamError, match="Unknown backend"):
        create_task_backend("bogus")


def test_server_backend_imports_with_an_unknown_context_backend_name() -> None:
    """A misconfigured backend must fail the call that needs it, not the server's import."""
    result = subprocess.run(
        [sys.executable, "-c", "import sam_schema.server_backend"],
        cwd=_PLUGIN_DIR,
        env={**os.environ, "CONTEXTBACKEND": "bogus"},
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def test_context_backend_refusal_reaches_the_tool_as_a_tool_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """``sam_active_task`` resolves its backend here, and ``ToolError`` is what it reports."""
    from sam_schema import server_backend

    monkeypatch.setenv("CONTEXTBACKEND", "bogus")
    reset_context_config()
    try:
        with pytest.raises(ToolError, match="Unknown backend"):
            server_backend.get_context_backend()
    finally:
        reset_context_config()


def test_github_context_backend_reaches_the_tool_as_a_tool_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """The unavailable GitHub backend refuses through ``ToolError``.

    ``create_context_backend`` refuses it with ``NotImplementedError``, not ``SamError``, and the
    name appears in the "Valid options" list the sibling refusal prints -- so a user who follows
    that message reaches this one. It has to report as the same ``ToolError``.

    The assertion names what must not leak rather than the wording. The message reaches a
    consumer of this plugin, who cannot open its tracker or read its source, so a rewrite may
    change the words but may not put an internal name back.
    """
    monkeypatch.setenv("CONTEXTBACKEND", "github")
    reset_context_config()
    try:
        with pytest.raises(ToolError, match="not available") as caught:
            sam_active_task_impl(GetActiveTaskConfig(), "sess-1")
    finally:
        reset_context_config()

    reported = str(caught.value)
    for leaked in ("#", ".py", "dh_config", "NotImplementedError", "factory"):
        assert leaked not in reported, f"message names something behind the surface: {leaked!r}"
