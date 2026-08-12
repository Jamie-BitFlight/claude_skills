"""Active-task CLI/MCP parity checks (T-P5-ACTIVE-TASK).

Verifies the CLI ``active-task`` command group reaches the same session-scoped
context store as the ``sam_active_task`` MCP tool, and that the CLI's
``--parent-issue`` accepts both forms the underlying model allows (int GitHub
issue number, beads-ID string).
"""

from __future__ import annotations

import json

import pytest
from sam_schema.cli import app
from sam_schema.core.context_config import (
    ContextConfig,
    create_context_backend,
    reset_context_config,
    set_context_config,
)
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture(autouse=True)
def _isolated_state(tmp_path, monkeypatch):
    """Point DH state at a temp dir and reset the context singleton per test."""
    monkeypatch.setenv("DH_STATE_HOME", str(tmp_path))
    reset_context_config()
    yield
    reset_context_config()


def _run(*args: str):
    result = runner.invoke(app, ["active-task", *args])
    assert result.exit_code == 0, result.stderr
    assert result.stderr == ""
    payload = result.stdout.strip()
    assert payload
    assert '": "' not in payload
    assert '", "' not in payload
    return json.loads(payload)


def _assert_rejected(*args: str, message: str) -> None:
    result = runner.invoke(app, ["active-task", *args])
    assert result.exit_code != 0
    assert result.stdout == ""
    assert message in result.stderr


def test_get_returns_null_when_unset() -> None:
    """A fresh session has no active task."""
    assert _run("get") == {"active_task": None}


def test_set_get_clear_round_trip() -> None:
    """set stores the address; get reads it back; clear removes it."""
    stored = _run("set", "--address", "P1/T3")["active_task"]
    assert stored["plan"] == "1"
    assert stored["task"] == "T3"

    assert _run("get")["active_task"]["plan"] == "1"

    assert _run("clear") == {"cleared": True}
    assert _run("get") == {"active_task": None}


def test_parent_issue_accepts_integer() -> None:
    """A digit-only --parent-issue is coerced to int, matching the MCP tool.

    Regression guard: typer passes every option as str, but ActiveTaskContext
    rejects a non-beads-pattern string. Without coercion `--parent-issue 42`
    raises a pydantic ValidationError.
    """
    stored = _run("set", "--address", "P1/T3", "--parent-issue", "42")["active_task"]
    assert stored["parent_issue_number"] == 42


def test_parent_issue_accepts_beads_id() -> None:
    """A beads nanoid passes through as a string."""
    stored = _run("set", "--address", "P2/T1", "--parent-issue", "bd-a3f8")["active_task"]
    assert stored["parent_issue_number"] == "bd-a3f8"


def test_cli_and_mcp_share_the_same_context_store() -> None:
    """The CLI write is visible through the same backend the MCP tool uses.

    Both frontends resolve a ContextBackend and call dh_core.operations; this
    asserts they land on the same durable store rather than parallel state.
    """
    from dh_core import operations

    _run("set", "--address", "P7/T2")

    set_context_config(ContextConfig(backend=create_context_backend()))
    mcp_view = operations.get_active_task(create_context_backend(), "_default")

    assert mcp_view.active_task is not None
    assert mcp_view.active_task.plan == "7"
    assert mcp_view.active_task.task == "T2"


def test_backend_is_selectable_not_hardcoded_local(monkeypatch) -> None:
    """CONTEXTBACKEND selects the backend; the CLI is not pinned to 'local'.

    Regression guard: _context_backend() must call create_context_backend()
    with no argument so the env var / .dh/config.yaml chain applies, the
    same way the MCP server resolves it.
    """
    from sam_schema.core.backends.memory_context_backend import InMemoryContextBackend

    monkeypatch.setenv("CONTEXTBACKEND", "memory")
    reset_context_config()

    from sam_schema.cli_active_task import _context_backend

    assert isinstance(_context_backend(), InMemoryContextBackend)


def test_parser_rejects_positional_address_removed_format_and_unknown_option() -> None:
    """Data values and removed flags must use the current named-only contract."""
    _assert_rejected("set", "P1/T3", message="--address")
    _assert_rejected("get", "--format", "json", message="--format")
    _assert_rejected("get", "--unknown", message="--unknown")


@pytest.mark.parametrize(("backend_name", "expected"), [("nope", "Unknown backend"), ("github", "implemented in T02")])
def test_bad_backend_reports_clean_error(monkeypatch, backend_name: str, expected: str) -> None:
    """A misconfigured CONTEXTBACKEND exits cleanly, not with a raw traceback."""
    monkeypatch.setenv("CONTEXTBACKEND", backend_name)
    reset_context_config()

    result = runner.invoke(app, ["active-task", "get"])

    assert result.exit_code != 0
    assert result.stdout == ""
    assert expected in result.stderr
    assert "Traceback" not in result.stderr
