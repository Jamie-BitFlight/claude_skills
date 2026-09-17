"""Per-operation CLI/MCP parity tests (T-P5-PARITY).

Proves the same logical operation through both transports produces equivalent
results.  The structural parity (both delegate to ``dh_core.operations``) is
already proven by ``test_server_operation_boundary.py``; these tests verify the
runtime pattern works end-to-end against a shared SQLite provider.

Covered operations:
- Backlog list (CLI adds item, both list it)
- Query filter (both filter by the same key and get the same results)

Plan CRUD parity tests use an explicit ``plan_dir``.
"""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest

_plugin_root = Path(__file__).resolve().parent.parent
if str(_plugin_root) not in sys.path:
    sys.path.insert(0, str(_plugin_root))

from backlog_core.backend_protocol import reset_config as _reset_bp_config, set_config as _set_bp_config
from backlog_core.backend_types import BacklogConfig as _BPBacklogConfig
from backlog_core.backends.memory_backend import InMemoryBackend
from backlog_core.backends.sqlite_backend import SQLiteBackend
from backlog_core.models import BacklogItem
from backlog_core.server import mcp as _backlog_mcp
from fastmcp.exceptions import ToolError
from sam_schema import artifacts, dispatch
from sam_schema.cli import app
from sam_schema.core.backends.local_context_backend import LocalContextBackend
from sam_schema.core.backends.memory_context_backend import InMemoryContextBackend
from sam_schema.core.context_config import ContextConfig, reset_context_config, set_context_config
from sam_schema.server import mcp as _sam_mcp
from typer.testing import CliRunner

from tests.helpers import call_mcp_tool, run_cli_subprocess

_runner = CliRunner()


def _run_cli(args: list[str], env: dict[str, str]) -> dict[str, Any]:
    """Run the supported direct CLI script and return compact stdout JSON.

    Real subprocess spawn (``uv run cli.py ...``) — reserved for the handful of
    tests that specifically need a fresh interpreter (env-var backend
    selection, PEP 723 dependency resolution). Everything else uses
    ``_invoke_cli`` below, which runs in-process via ``typer.testing.CliRunner``.
    """
    import json

    result = run_cli_subprocess(["uv", "run", str(_plugin_root / "sam_schema" / "cli.py"), *args], timeout=30, env=env)
    if result.returncode != 0:
        raise RuntimeError(f"CLI exited {result.returncode}: {result.stderr}")
    assert result.stdout.endswith("\n")
    assert result.stdout.count("\n") == 1
    assert '": "' not in result.stdout
    assert '", "' not in result.stdout
    return json.loads(result.stdout)


def _invoke_cli(args: list[str]) -> dict[str, Any]:
    """Invoke the CLI in-process via ``CliRunner`` and return compact stdout JSON.

    Shares the current process's ``BacklogConfig``/``ContextConfig`` singletons
    (set by the ``dh_env`` fixture) with the MCP calls in the same test, rather
    than opening the SQLite file independently in a fresh interpreter. Same
    compact-JSON stdout contract as ``_run_cli``.
    """
    result = _runner.invoke(app, args)
    if result.exit_code != 0:
        raise RuntimeError(f"CLI exited {result.exit_code}: {result.stderr}")
    assert result.stdout.endswith("\n")
    assert result.stdout.count("\n") == 1
    assert '": "' not in result.stdout
    assert '", "' not in result.stdout
    return json.loads(result.stdout)


@pytest.fixture
def dh_env(tmp_path: Path, request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch):
    """Provide an isolated SQLite backlog provider shared by both transports.

    The CLI selects SQLite through ``BACKLOG_BACKEND``. The in-process MCP
    server receives the same SQLite file directly, because process-local
    provider singletons cannot otherwise be shared with the CLI subprocess.
    """
    import dh_paths

    dh_state = str(tmp_path / "dh_state")
    env = os.environ.copy()
    env.update({"DH_STATE_HOME": dh_state, "BACKLOG_BACKEND": "sqlite", "GITHUB_TOKEN": "", "GH_TOKEN": ""})
    monkeypatch.setenv("GITHUB_TOKEN", "")
    monkeypatch.setenv("GH_TOKEN", "")

    saved_dh_home = os.environ.get("DH_STATE_HOME")
    os.environ["DH_STATE_HOME"] = dh_state
    db_path = dh_paths.state_root() / "backlog.sqlite3"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    _set_bp_config(_BPBacklogConfig(backend=SQLiteBackend(str(db_path))))
    set_context_config(ContextConfig(backend=InMemoryContextBackend()))
    if request.node.name.startswith("test_active_task_"):
        set_context_config(ContextConfig(backend=LocalContextBackend()))

    yield env

    if saved_dh_home is not None:
        os.environ["DH_STATE_HOME"] = saved_dh_home
    else:
        os.environ.pop("DH_STATE_HOME", None)
    reset_context_config()
    _reset_bp_config()


@pytest.mark.integration
async def test_memory_provider_is_process_local(dh_env: dict[str, str]) -> None:
    """A memory-backed CLI item is absent from the fresh MCP provider."""
    memory_env = {**dh_env, "BACKLOG_BACKEND": "memory"}

    cli_result = _run_cli(
        ["backlog", "add", "--title", "Memory Only", "--description", "test", "--priority", "P1"], env=memory_env
    )
    _set_bp_config(_BPBacklogConfig(backend=InMemoryBackend()))
    mcp_list = await call_mcp_tool(_backlog_mcp, "backlog_list", {})

    assert cli_result["title"] == "Memory Only"
    assert "Memory Only" not in {item["title"] for item in mcp_list.get("items", [])}


def test_sqlite_round_trip_restores_section_from_priority(tmp_path: Path) -> None:
    backend = SQLiteBackend(str(tmp_path / "backlog.sqlite3"))
    backend.put_work_item(BacklogItem(title="Round Trip", priority="P1", reference="p1-round-trip"))

    assert backend.get_work_item("p1-round-trip").section == "P1"


# ---------------------------------------------------------------------------
# Backlog list parity
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_backlog_list_parity(dh_env: dict[str, str]) -> None:
    """A backlog item added via CLI is visible through both list transports."""
    _run_cli(["backlog", "add", "--title", "Parity Item", "--description", "test", "--priority", "P1"], env=dh_env)

    cli_list = _run_cli(["backlog", "list"], env=dh_env)
    mcp_list = await call_mcp_tool(_backlog_mcp, "backlog_list", {})

    cli_titles = {item["title"] for item in cli_list.get("items", [])}
    mcp_titles = {item["title"] for item in mcp_list.get("items", [])}
    assert "Parity Item" in cli_titles
    assert "Parity Item" in mcp_titles


# ---------------------------------------------------------------------------
# Query filter parity
# ---------------------------------------------------------------------------


async def test_query_filter_parity(dh_env: dict[str, str]) -> None:
    """The --filter key=value CLI option and filter_by_key MCP param produce the same results."""
    _invoke_cli(["backlog", "add", "--title", "Filter Item", "--description", "test", "--priority", "P1"])

    cli_filtered = _invoke_cli(["backlog", "list", "--filter", "section=P1"])
    mcp_filtered = await call_mcp_tool(_backlog_mcp, "backlog_list", {"filter_by_key": {"section": "P1"}})

    cli_titles = {item["title"] for item in cli_filtered.get("items", [])}
    mcp_titles = {item["title"] for item in mcp_filtered.get("items", [])}
    assert "Filter Item" in cli_titles
    assert "Filter Item" in mcp_titles


async def test_query_filter_absent_key_returns_empty(dh_env: dict[str, str]) -> None:
    """Filtering by a key no item carries returns empty, not an error."""
    _invoke_cli(["backlog", "add", "--title", "No Match Item", "--description", "test", "--priority", "P1"])

    cli_filtered = _invoke_cli(["backlog", "list", "--filter", "nonexistent_key=xyz"])
    mcp_filtered = await call_mcp_tool(_backlog_mcp, "backlog_list", {"filter_by_key": {"nonexistent_key": "xyz"}})

    assert cli_filtered.get("count", 0) == 0
    assert len(mcp_filtered.get("items", [])) == 0


# ---------------------------------------------------------------------------
# Backlog CRUD parity (add, view, update, close, resolve, groom)
# ---------------------------------------------------------------------------


async def test_backlog_add_parity(dh_env: dict[str, str]) -> None:
    """Backlog add via CLI and MCP both create items with equivalent metadata."""
    cli_result = _invoke_cli([
        "backlog",
        "add",
        "--title",
        "Parity CLI Add",
        "--description",
        "cli test",
        "--priority",
        "P1",
    ])
    mcp_result = await call_mcp_tool(
        _backlog_mcp,
        "backlog_add",
        {"title": "Parity MCP Add", "priority": "P1", "description": "mcp test", "force": True},
    )

    assert cli_result["title"] == "Parity CLI Add"
    assert cli_result["priority"] == "P1"
    assert mcp_result["title"] == "Parity MCP Add"
    assert mcp_result["priority"] == "P1"

    # Both items visible via list
    cli_list = _invoke_cli(["backlog", "list"])
    titles = {item["title"] for item in cli_list.get("items", [])}
    assert "Parity CLI Add" in titles
    assert "Parity MCP Add" in titles


async def test_backlog_view_parity(dh_env: dict[str, str]) -> None:
    """Backlog item viewed through CLI and MCP returns the same identity fields."""
    _invoke_cli(["backlog", "add", "--title", "Parity View Item", "--description", "view test", "--priority", "P1"])

    cli_view = _invoke_cli(["backlog", "view", "--selector", "Parity View Item"])
    mcp_view = await call_mcp_tool(
        _backlog_mcp, "backlog_view", {"selector": "Parity View Item", "summary": False, "include_content": True}
    )

    assert cli_view.get("title") == "Parity View Item"
    assert mcp_view.get("title") == "Parity View Item"
    assert cli_view.get("priority") == mcp_view.get("priority")


async def test_backlog_update_parity(dh_env: dict[str, str]) -> None:
    """Backlog update through CLI and MCP both change the title correctly."""
    _invoke_cli(["backlog", "add", "--title", "Parity Update CLI", "--description", "update test", "--priority", "P1"])
    _invoke_cli([
        "backlog",
        "add",
        "--title",
        "Parity Update MCP",
        "--description",
        "update test",
        "--priority",
        "P1",
        "--force",
    ])

    # CLI update
    cli_update = _invoke_cli(["backlog", "update", "--selector", "Parity Update CLI", "--title", "CLI Updated Title"])
    assert "CLI Updated Title" in str(cli_update)

    # MCP update
    mcp_update = await call_mcp_tool(
        _backlog_mcp, "backlog_update", {"selector": "Parity Update MCP", "title": "MCP Updated Title"}
    )
    assert "MCP Updated Title" in str(mcp_update)

    # Verify via list
    cli_list = _invoke_cli(["backlog", "list"])
    titles = {item["title"] for item in cli_list.get("items", [])}
    assert "CLI Updated Title" in titles
    assert "MCP Updated Title" in titles


async def test_backlog_close_parity(dh_env: dict[str, str]) -> None:
    """Backlog close through CLI and MCP both close items correctly."""
    _invoke_cli(["backlog", "add", "--title", "Parity Close CLI", "--description", "close test", "--priority", "P1"])
    _invoke_cli([
        "backlog",
        "add",
        "--title",
        "Parity Close MCP",
        "--description",
        "close test",
        "--priority",
        "P1",
        "--force",
    ])

    # CLI close
    cli_close = _invoke_cli(["backlog", "close", "--selector", "Parity Close CLI", "--reason", "duplicate"])
    assert cli_close.get("title") == "Parity Close CLI"
    assert cli_close.get("closed") is True

    # MCP close
    mcp_close = await call_mcp_tool(
        _backlog_mcp, "backlog_close", {"selector": "Parity Close MCP", "reason": "duplicate"}
    )
    assert mcp_close.get("title") == "Parity Close MCP"
    assert mcp_close.get("closed") is True


async def test_backlog_resolve_parity(dh_env: dict[str, str]) -> None:
    """CLI backlog resolve and MCP backlog_close both complete items."""
    _invoke_cli([
        "backlog",
        "add",
        "--title",
        "Parity Resolve CLI",
        "--description",
        "resolve test",
        "--priority",
        "P1",
    ])
    _invoke_cli([
        "backlog",
        "add",
        "--title",
        "Parity Close MCP2",
        "--description",
        "close test",
        "--priority",
        "P1",
        "--force",
    ])

    # CLI resolve
    cli_resolve = _invoke_cli(["backlog", "resolve", "--selector", "Parity Resolve CLI", "--summary", "Done"])
    assert cli_resolve.get("title") == "Parity Resolve CLI"
    assert cli_resolve.get("resolved") is True

    # MCP close
    mcp_close = await call_mcp_tool(
        _backlog_mcp, "backlog_close", {"selector": "Parity Close MCP2", "reason": "duplicate"}
    )
    assert mcp_close.get("title") == "Parity Close MCP2"
    assert mcp_close.get("closed") is True


async def test_backlog_groom_parity(dh_env: dict[str, str]) -> None:
    """Both transports generate identical groomed content for the same section."""
    _invoke_cli(["backlog", "add", "--title", "Parity Groom CLI", "--description", "groom test", "--priority", "P1"])
    _invoke_cli([
        "backlog",
        "add",
        "--title",
        "Parity Groom MCP",
        "--description",
        "groom test",
        "--priority",
        "P1",
        "--force",
    ])

    GROOM_CONTENT = "## Analysis\n\nThis item needs investigation."

    # CLI groom
    cli_groom = _invoke_cli([
        "backlog",
        "groom",
        "--selector",
        "Parity Groom CLI",
        "--section",
        "Analysis",
        "--content",
        GROOM_CONTENT,
    ])
    assert cli_groom.get("title") == "Parity Groom CLI"

    # MCP groom
    mcp_groom = await call_mcp_tool(
        _backlog_mcp, "backlog_groom", {"selector": "Parity Groom MCP", "section": "Analysis", "content": GROOM_CONTENT}
    )
    assert mcp_groom.get("title") == "Parity Groom MCP"

    # Verify both items have groomed content via view
    cli_view = _invoke_cli(["backlog", "view", "--selector", "Parity Groom CLI", "--section", "Analysis"])
    mcp_view = await call_mcp_tool(
        _backlog_mcp, "backlog_view", {"selector": "Parity Groom MCP", "summary": False, "section": "Analysis"}
    )

    assert "needs investigation" in str(cli_view)
    assert "needs investigation" in str(mcp_view)


# ---------------------------------------------------------------------------
# Plan CRUD parity (Phase 5 E2E)
# ---------------------------------------------------------------------------


async def test_plan_create_read_parity(dh_env: dict[str, str], tmp_path: Path) -> None:
    """Plan created via CLI is readable via MCP and vice-versa."""
    plan_dir = str(tmp_path / "plan")
    Path(plan_dir).mkdir(parents=True, exist_ok=True)

    # CLI creates, MCP reads
    cli_result = _invoke_cli(["plan", "create", "--slug", "cli-plan", "--goal", "CLI goal", "--plan-dir", plan_dir])
    plan_id = cli_result["plan_id"]
    mcp_result = await call_mcp_tool(
        _sam_mcp, "sam_plan", {"config": {"action": "read"}, "plan": plan_id, "plan_dir": plan_dir}
    )
    assert mcp_result["plan"]["feature"] == "cli-plan"
    assert mcp_result["plan"]["goal"] == "CLI goal"

    # MCP creates, CLI reads
    mcp_create = await call_mcp_tool(
        _sam_mcp,
        "sam_plan",
        {"config": {"action": "create", "slug": "mcp-plan", "goal": "MCP goal"}, "plan_dir": plan_dir},
    )
    mcp_plan_id = mcp_create["plan_id"]
    cli_read = _invoke_cli(["plan", "read", "--address", mcp_plan_id, "--plan-dir", plan_dir])
    assert cli_read["plan"]["feature"] == "mcp-plan"
    assert cli_read["plan"]["goal"] == "MCP goal"


async def test_plan_status_parity(dh_env: dict[str, str], tmp_path: Path) -> None:
    """Plan status is the same dict through both transports."""
    plan_dir = str(tmp_path / "plan")
    Path(plan_dir).mkdir(parents=True, exist_ok=True)

    cli_result = _invoke_cli([
        "plan",
        "create",
        "--slug",
        "status-plan",
        "--goal",
        "Status goal",
        "--plan-dir",
        plan_dir,
    ])
    plan_id = cli_result["plan_id"]

    cli_status = _invoke_cli(["plan", "status", "--plan-address", plan_id, "--plan-dir", plan_dir])
    mcp_status = await call_mcp_tool(
        _sam_mcp, "sam_plan", {"config": {"action": "status"}, "plan": plan_id, "plan_dir": plan_dir}
    )
    assert cli_status["feature"] == mcp_status["feature"]
    assert cli_status["total_tasks"] == mcp_status["total_tasks"]


async def test_plan_list_parity(dh_env: dict[str, str], tmp_path: Path) -> None:
    """Plan list returns the same plans through both transports."""
    plan_dir = str(tmp_path / "plan")
    Path(plan_dir).mkdir(parents=True, exist_ok=True)

    for slug in ["list-a", "list-b"]:
        _invoke_cli(["plan", "create", "--slug", slug, "--goal", f"Goal {slug}", "--plan-dir", plan_dir])

    cli_list = _invoke_cli(["plan", "list", "--plan-dir", plan_dir])
    mcp_list = await call_mcp_tool(_sam_mcp, "sam_plan", {"config": {"action": "list"}, "plan_dir": plan_dir})
    cli_ids = {item.get("plan_id", item.get("plan_ref")) for item in cli_list.get("items", [])}
    mcp_ids = {item.get("plan_id", item.get("plan_ref")) for item in mcp_list.get("items", [])}
    assert cli_ids == mcp_ids
    assert len(cli_ids) == 2


# ---------------------------------------------------------------------------
# Plan operation parity (ready, update, append_task, finalize)
# ---------------------------------------------------------------------------


async def test_plan_ready_parity(dh_env: dict[str, str], tmp_path: Path) -> None:
    """Ready-for-dispatch tasks are identical through CLI and MCP transports."""

    plan_dir = str(tmp_path / "plan")
    Path(plan_dir).mkdir(parents=True, exist_ok=True)

    cli_create = _invoke_cli([
        "plan",
        "create",
        "--slug",
        "ready-parity",
        "--goal",
        "Ready parity goal",
        "--plan-dir",
        plan_dir,
    ])
    plan_id = cli_create["plan_id"]
    _invoke_cli(["plan", "append-task", "--plan-address", plan_id, *_task_args(_TASK_DEF), "--plan-dir", plan_dir])
    _invoke_cli(["plan", "finalize", "--plan-address", plan_id, "--plan-dir", plan_dir])

    cli_ready = _invoke_cli(["plan", "ready", "--plan-address", plan_id, "--plan-dir", plan_dir])
    mcp_ready = await call_mcp_tool(
        _sam_mcp, "sam_plan", {"config": {"action": "ready"}, "plan": plan_id, "plan_dir": plan_dir}
    )
    assert cli_ready["feature"] == mcp_ready["feature"]
    assert cli_ready["count"] == mcp_ready["count"] == 1


async def test_plan_update_parity(dh_env: dict[str, str], tmp_path: Path) -> None:
    """Plan update through CLI and MCP produces equivalent field changes."""

    plan_dir = str(tmp_path / "plan")
    Path(plan_dir).mkdir(parents=True, exist_ok=True)

    plan_a = plan_b = None
    for slug in ["update-a", "update-b"]:
        result = _invoke_cli(["plan", "create", "--slug", slug, "--goal", "Update goal", "--plan-dir", plan_dir])
        pid = result["plan_id"]
        _invoke_cli(["plan", "append-task", "--plan-address", pid, *_task_args(_TASK_DEF), "--plan-dir", plan_dir])
        _invoke_cli(["plan", "finalize", "--plan-address", pid, "--plan-dir", plan_dir])
        if slug == "update-a":
            plan_a = pid
        else:
            plan_b = pid
    assert plan_a
    assert plan_b

    # CLI update plan_a
    cli_update = _invoke_cli([
        "plan",
        "update",
        "--plan-address",
        plan_a,
        "--plan-dir",
        plan_dir,
        "--feature",
        "update-a",
        "--version",
        "1.0",
        "--description",
        "",
        "--state",
        "ready",
        "--autonomy",
        "full_auto",
        "--goal",
        "CLI Updated",
    ])
    assert cli_update["updated"] is True

    # MCP update plan_b
    mcp_update = await call_mcp_tool(
        _sam_mcp,
        "sam_plan",
        {
            "config": {"action": "update", "set_fields_json": {"goal": "MCP Updated"}},
            "plan": plan_b,
            "plan_dir": plan_dir,
        },
    )
    assert mcp_update["updated"] is True

    # Read both through CLI to verify
    cli_read_a = _invoke_cli(["plan", "read", "--address", plan_a, "--plan-dir", plan_dir])
    cli_read_b = _invoke_cli(["plan", "read", "--address", plan_b, "--plan-dir", plan_dir])
    assert cli_read_a["plan"]["goal"] == "CLI Updated"
    assert cli_read_b["plan"]["goal"] == "MCP Updated"


async def test_plan_append_task_parity(dh_env: dict[str, str], tmp_path: Path) -> None:
    """Task appended via CLI and MCP produces equivalent results."""

    plan_dir = str(tmp_path / "plan")
    Path(plan_dir).mkdir(parents=True, exist_ok=True)

    plan_a = plan_b = None
    for slug in ["append-a", "append-b"]:
        result = _invoke_cli(["plan", "create", "--slug", slug, "--goal", "Append goal", "--plan-dir", plan_dir])
        if slug == "append-a":
            plan_a = result["plan_id"]
        else:
            plan_b = result["plan_id"]
    assert plan_a
    assert plan_b

    # CLI append to plan_a
    cli_append = _invoke_cli([
        "plan",
        "append-task",
        "--plan-address",
        plan_a,
        *_task_args(_TASK_DEF),
        "--plan-dir",
        plan_dir,
    ])
    assert cli_append["appended"] is True
    assert cli_append["task_id"] == "T01"

    # MCP append to plan_b
    mcp_append = await call_mcp_tool(
        _sam_mcp,
        "sam_plan",
        {"config": {"action": "append_task", "task": _TASK_DEF}, "plan": plan_b, "plan_dir": plan_dir},
    )
    assert mcp_append["appended"] is True
    assert mcp_append["task_id"] == "T01"

    # Finalize both and read to verify
    _invoke_cli(["plan", "finalize", "--plan-address", plan_a, "--plan-dir", plan_dir])
    _invoke_cli(["plan", "finalize", "--plan-address", plan_b, "--plan-dir", plan_dir])

    cli_read_a = _invoke_cli(["plan", "read", "--address", plan_a, "--plan-dir", plan_dir])
    cli_read_b = _invoke_cli(["plan", "read", "--address", plan_b, "--plan-dir", plan_dir])
    assert len(cli_read_a["plan"]["tasks"]) == len(cli_read_b["plan"]["tasks"]) == 1


async def test_plan_finalize_parity(dh_env: dict[str, str], tmp_path: Path) -> None:
    """Plan finalize through CLI and MCP produces equivalent results."""

    plan_dir = str(tmp_path / "plan")
    Path(plan_dir).mkdir(parents=True, exist_ok=True)

    plan_a = plan_b = None
    for slug in ["finalize-a", "finalize-b"]:
        result = _invoke_cli(["plan", "create", "--slug", slug, "--goal", "Finalize goal", "--plan-dir", plan_dir])
        pid = result["plan_id"]
        _invoke_cli(["plan", "append-task", "--plan-address", pid, *_task_args(_TASK_DEF), "--plan-dir", plan_dir])
        if slug == "finalize-a":
            plan_a = pid
        else:
            plan_b = pid
    assert plan_a
    assert plan_b

    # CLI finalize plan_a
    cli_finalize = _invoke_cli(["plan", "finalize", "--plan-address", plan_a, "--plan-dir", plan_dir])
    assert cli_finalize["finalized"] is True
    assert cli_finalize["state"] == "ready"

    # MCP finalize plan_b
    mcp_finalize = await call_mcp_tool(
        _sam_mcp, "sam_plan", {"config": {"action": "finalize"}, "plan": plan_b, "plan_dir": plan_dir}
    )
    assert mcp_finalize["finalized"] is True
    assert mcp_finalize["state"] == "ready"

    # Read both to verify state
    cli_read_a = _invoke_cli(["plan", "read", "--address", plan_a, "--plan-dir", plan_dir])
    cli_read_b = _invoke_cli(["plan", "read", "--address", plan_b, "--plan-dir", plan_dir])
    assert cli_read_a["plan"]["state"] == cli_read_b["plan"]["state"] == "ready"


# ---------------------------------------------------------------------------
# Task CRUD parity
# ---------------------------------------------------------------------------

_TASK_DEF = {
    "id": "T01",
    "title": "Parity Task",
    "status": "not-started",
    "agent": "test-agent",
    "dependencies": [],
    "priority": 1,
    "complexity": "low",
}


def _task_args(task: dict[str, Any]) -> list[str]:
    args = ["--task-id", task["id"], "--task-title", task["title"]]
    for key, option in (
        ("status", "--task-status"),
        ("agent", "--task-agent"),
        ("priority", "--task-priority"),
        ("complexity", "--task-complexity"),
    ):
        if task.get(key) is not None:
            args.extend([option, str(task[key])])
    for dependency in task.get("dependencies", []):
        args.extend(["--task-dependency", dependency])
    return args


async def test_task_read_parity(dh_env: dict[str, str], tmp_path: Path) -> None:
    """Task read through CLI and MCP returns the same task data."""

    plan_dir = str(tmp_path / "plan")
    Path(plan_dir).mkdir(parents=True, exist_ok=True)

    cli_create = _invoke_cli(["plan", "create", "--slug", "read-task", "--goal", "Read goal", "--plan-dir", plan_dir])
    plan_id = cli_create["plan_id"]
    _invoke_cli(["plan", "append-task", "--plan-address", plan_id, *_task_args(_TASK_DEF), "--plan-dir", plan_dir])
    _invoke_cli(["plan", "finalize", "--plan-address", plan_id, "--plan-dir", plan_dir])

    cli_read = _invoke_cli(["plan", "read", "--address", f"{plan_id}/T01", "--plan-dir", plan_dir])
    mcp_read = await call_mcp_tool(
        _sam_mcp, "sam_task", {"plan": plan_id, "task": "T01", "config": {"action": "read"}, "plan_dir": plan_dir}
    )
    assert cli_read["task"]["id"] == mcp_read["task"]["id"] == "T01"
    assert cli_read["task"]["title"] == mcp_read["task"]["title"] == "Parity Task"
    assert cli_read["task"]["status"] == mcp_read["task"]["status"]


async def test_task_claim_parity(dh_env: dict[str, str], tmp_path: Path) -> None:
    """Claim via CLI and MCP both produce claimed=true with a started timestamp."""

    plan_dir = str(tmp_path / "plan")
    Path(plan_dir).mkdir(parents=True, exist_ok=True)

    cli_create = _invoke_cli(["plan", "create", "--slug", "claim-task", "--goal", "Claim goal", "--plan-dir", plan_dir])
    plan_id = cli_create["plan_id"]
    _invoke_cli(["plan", "append-task", "--plan-address", plan_id, *_task_args(_TASK_DEF), "--plan-dir", plan_dir])
    _invoke_cli(["plan", "finalize", "--plan-address", plan_id, "--plan-dir", plan_dir])

    cli_claim = _invoke_cli(["plan", "claim", "--address", f"{plan_id}/T01", "--plan-dir", plan_dir])
    assert cli_claim["claimed"] is True
    assert cli_claim["task_id"] == "T01"
    assert cli_claim.get("started") is not None

    # Reset task to not-started for MCP claim (same backend, need fresh task).
    TASK_DEF2 = dict(_TASK_DEF, id="T02")
    _invoke_cli(["plan", "append-task", "--plan-address", plan_id, *_task_args(TASK_DEF2), "--plan-dir", plan_dir])
    _invoke_cli(["plan", "finalize", "--plan-address", plan_id, "--plan-dir", plan_dir])

    mcp_claim = await call_mcp_tool(
        _sam_mcp, "sam_task", {"plan": plan_id, "task": "T02", "config": {"action": "claim"}, "plan_dir": plan_dir}
    )
    assert mcp_claim["claimed"] is True
    assert mcp_claim["task_id"] == "T02"
    assert mcp_claim.get("started") is not None


async def test_task_state_parity(dh_env: dict[str, str], tmp_path: Path) -> None:
    """Task status changed via CLI and MCP is visible through both reads."""
    plan_dir = str(tmp_path / "plan")
    Path(plan_dir).mkdir(parents=True, exist_ok=True)

    cli_create = _invoke_cli(["plan", "create", "--slug", "state-task", "--goal", "State goal", "--plan-dir", plan_dir])
    plan_id = cli_create["plan_id"]
    _invoke_cli(["plan", "append-task", "--plan-address", plan_id, *_task_args(_TASK_DEF), "--plan-dir", plan_dir])
    _invoke_cli(["plan", "finalize", "--plan-address", plan_id, "--plan-dir", plan_dir])

    state_result = _invoke_cli([
        "plan",
        "state",
        "--address",
        f"{plan_id}/T01",
        "--new-status",
        "complete",
        "--plan-dir",
        plan_dir,
    ])
    assert state_result["status"] == "complete"

    cli_read = _invoke_cli(["plan", "read", "--address", f"{plan_id}/T01", "--plan-dir", plan_dir])
    mcp_read = await call_mcp_tool(
        _sam_mcp, "sam_task", {"plan": plan_id, "task": "T01", "config": {"action": "read"}, "plan_dir": plan_dir}
    )
    assert cli_read["task"]["status"] == "complete"
    assert mcp_read["task"]["status"] == "complete"


async def test_task_update_parity(dh_env: dict[str, str], tmp_path: Path) -> None:
    """Task field updated via CLI --set is visible through both read transports."""

    plan_dir = str(tmp_path / "plan")
    Path(plan_dir).mkdir(parents=True, exist_ok=True)

    cli_create = _invoke_cli([
        "plan",
        "create",
        "--slug",
        "update-task",
        "--goal",
        "Update goal",
        "--plan-dir",
        plan_dir,
    ])
    plan_id = cli_create["plan_id"]
    _invoke_cli(["plan", "append-task", "--plan-address", plan_id, *_task_args(_TASK_DEF), "--plan-dir", plan_dir])
    _invoke_cli(["plan", "finalize", "--plan-address", plan_id, "--plan-dir", plan_dir])

    # CLI update --set
    _invoke_cli([
        "plan",
        "update",
        "--plan-address",
        plan_id,
        "--task-id",
        "T01",
        "--plan-dir",
        plan_dir,
        "--title",
        "Parity Task",
        "--task-status",
        "not-started",
        "--agent",
        "test-agent",
        "--priority",
        "5",
        "--complexity",
        "low",
    ])

    cli_read = _invoke_cli(["plan", "read", "--address", f"{plan_id}/T01", "--plan-dir", plan_dir])
    mcp_read = await call_mcp_tool(
        _sam_mcp, "sam_task", {"plan": plan_id, "task": "T01", "config": {"action": "read"}, "plan_dir": plan_dir}
    )
    assert cli_read["task"]["priority"] == 5
    assert mcp_read["task"]["priority"] == 5


async def test_task_set_fields_parity(dh_env: dict[str, str], tmp_path: Path) -> None:
    """CLI ``--set`` and MCP ``set_fields_json`` are mutually consistent across reads."""

    plan_dir = str(tmp_path / "plan")
    Path(plan_dir).mkdir(parents=True, exist_ok=True)

    cli_create = _invoke_cli([
        "plan",
        "create",
        "--slug",
        "set-fields-parity",
        "--goal",
        "Set-fields goal",
        "--plan-dir",
        plan_dir,
    ])
    plan_id = cli_create["plan_id"]
    _invoke_cli(["plan", "append-task", "--plan-address", plan_id, *_task_args(_TASK_DEF), "--plan-dir", plan_dir])
    _invoke_cli(["plan", "finalize", "--plan-address", plan_id, "--plan-dir", plan_dir])

    # CLI write --set
    _invoke_cli([
        "plan",
        "update",
        "--plan-address",
        plan_id,
        "--task-id",
        "T01",
        "--plan-dir",
        plan_dir,
        "--title",
        "Parity Task",
        "--task-status",
        "not-started",
        "--agent",
        "test-agent",
        "--priority",
        "5",
        "--complexity",
        "low",
    ])
    cli_read = _invoke_cli(["plan", "read", "--address", f"{plan_id}/T01", "--plan-dir", plan_dir])
    mcp_read = await call_mcp_tool(
        _sam_mcp, "sam_task", {"plan": plan_id, "task": "T01", "config": {"action": "read"}, "plan_dir": plan_dir}
    )
    assert cli_read["task"]["priority"] == 5
    assert mcp_read["task"]["priority"] == 5

    # MCP write set_fields_json on a second task
    TASK_DEF2 = dict(_TASK_DEF, id="T02")
    _invoke_cli(["plan", "append-task", "--plan-address", plan_id, *_task_args(TASK_DEF2), "--plan-dir", plan_dir])
    _invoke_cli(["plan", "finalize", "--plan-address", plan_id, "--plan-dir", plan_dir])

    await call_mcp_tool(
        _sam_mcp,
        "sam_task",
        {
            "plan": plan_id,
            "task": "T02",
            "config": {"action": "update", "set_fields_json": {"priority": 3}},
            "plan_dir": plan_dir,
        },
    )
    cli_read2 = _invoke_cli(["plan", "read", "--address", f"{plan_id}/T02", "--plan-dir", plan_dir])
    mcp_read2 = await call_mcp_tool(
        _sam_mcp, "sam_task", {"plan": plan_id, "task": "T02", "config": {"action": "read"}, "plan_dir": plan_dir}
    )
    assert cli_read2["task"]["priority"] == 3
    assert mcp_read2["task"]["priority"] == 3


async def test_task_append_section_parity(dh_env: dict[str, str], tmp_path: Path) -> None:
    """CLI ``--append-section`` and MCP ``append_section`` are mutually consistent across reads."""

    plan_dir = str(tmp_path / "plan")
    Path(plan_dir).mkdir(parents=True, exist_ok=True)

    cli_create = _invoke_cli([
        "plan",
        "create",
        "--slug",
        "append-section-parity",
        "--goal",
        "Section goal",
        "--plan-dir",
        plan_dir,
    ])
    plan_id = cli_create["plan_id"]
    _invoke_cli(["plan", "append-task", "--plan-address", plan_id, *_task_args(_TASK_DEF), "--plan-dir", plan_dir])
    _invoke_cli(["plan", "finalize", "--plan-address", plan_id, "--plan-dir", plan_dir])

    # CLI write --append-section
    _invoke_cli([
        "plan",
        "update",
        "--plan-address",
        plan_id,
        "--task-id",
        "T01",
        "--plan-dir",
        plan_dir,
        "--title",
        "Parity Task",
        "--task-status",
        "not-started",
        "--agent",
        "test-agent",
        "--priority",
        "1",
        "--complexity",
        "low",
        "--append-section",
        "Notes",
        "--section-content",
        "CLI appended note.",
    ])
    cli_read = _invoke_cli(["plan", "read", "--address", f"{plan_id}/T01", "--plan-dir", plan_dir])
    mcp_read = await call_mcp_tool(
        _sam_mcp, "sam_task", {"plan": plan_id, "task": "T01", "config": {"action": "read"}, "plan_dir": plan_dir}
    )
    cli_notes = cli_read["task"].get("context-notes", "")
    mcp_notes = mcp_read["task"].get("context-notes", "")
    assert "Notes" in cli_notes
    assert "CLI appended note." in cli_notes
    assert "Notes" in mcp_notes
    assert "CLI appended note." in mcp_notes

    # MCP write append_section on a second task
    TASK_DEF2 = dict(_TASK_DEF, id="T02")
    _invoke_cli(["plan", "append-task", "--plan-address", plan_id, *_task_args(TASK_DEF2), "--plan-dir", plan_dir])
    _invoke_cli(["plan", "finalize", "--plan-address", plan_id, "--plan-dir", plan_dir])

    await call_mcp_tool(
        _sam_mcp,
        "sam_task",
        {
            "plan": plan_id,
            "task": "T02",
            "config": {"action": "update", "append_section": "Decisions", "section_content": "MCP appended decision."},
            "plan_dir": plan_dir,
        },
    )
    cli_read2 = _invoke_cli(["plan", "read", "--address", f"{plan_id}/T02", "--plan-dir", plan_dir])
    mcp_read2 = await call_mcp_tool(
        _sam_mcp, "sam_task", {"plan": plan_id, "task": "T02", "config": {"action": "read"}, "plan_dir": plan_dir}
    )
    cli_notes2 = cli_read2["task"].get("context-notes", "")
    mcp_notes2 = mcp_read2["task"].get("context-notes", "")
    assert "Decisions" in cli_notes2
    assert "MCP appended decision." in cli_notes2
    assert "Decisions" in mcp_notes2
    assert "MCP appended decision." in mcp_notes2


# ---------------------------------------------------------------------------
# Ledger routing parity (T-P2-LEDGER-ROUTING)
#
# ``sam_plan``/``sam_task`` resolve a ``ContentTaskProvider`` unconditionally
# (``server.py`` ``_get_backend``), with no check of ``dh_core.ledger.holds``.
# The CLI's ``store_for``/``ledger_holds`` chain (``sam_plan.py``) routes a
# plan the ledger holds -- e.g. after ``plan import`` -- to the ledger
# instead. Every test below sets up a plan the ledger holds and shows the MCP
# result diverges from (or cannot reach) the CLI's ledger-backed result.
# ---------------------------------------------------------------------------


def _without_nulls(value: Any) -> Any:
    """Drop every ``None``-valued dict key, recursively.

    The CLI prints models with ``exclude_none=True`` (``cli_output.output_json``); FastMCP
    serialises with a plain ``TypeAdapter(Any)`` that keeps explicit nulls. Comparing the two
    raw dicts then fails on transport shape alone, not on which store answered. Stripping both
    sides the same way still catches a wrong store: the content and ledger result shapes share
    no key set, so a mismatch there survives the strip.

    Args:
        value: A parsed JSON value (dict, list, or scalar).

    Returns:
        The same structure with every ``None`` dict value removed.
    """
    if isinstance(value, dict):
        return {k: _without_nulls(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [_without_nulls(v) for v in value]
    return value


def _mint_plan_id_with_a_letter_in_its_hex_suffix(slug: str, goal: str) -> str:
    """Create plans via the CLI until one mints an id whose hex suffix is not all digits.

    ``canonical_plan_id`` lowercases only hex letters, so an all-digit suffix makes
    ``str.upper`` a no-op -- about a 2.3% chance per mint. A case-spelling test built on that id
    would silently degrade into testing the canonical spelling twice.

    Args:
        slug: Distinguishes this mint attempt's plans from a prior attempt's leftovers.
        goal: The plan's goal text.

    Returns:
        A plan id whose 8-hex-digit suffix contains at least one letter.
    """
    for attempt in range(50):
        plan_id = _invoke_cli(["plan", "create", "--slug", f"{slug}-{attempt}", "--goal", goal])["plan_id"]
        if not plan_id[1:].isdigit():
            return plan_id
    pytest.fail("could not mint a plan id with a letter in its hex suffix after 50 tries")


async def test_sam_plan_status_matches_the_cli_on_an_imported_plan(dh_env: dict[str, str]) -> None:
    """MCP ``sam_plan`` ``status`` must read the ledger once the plan is imported and dispatched.

    ``server.py`` always resolves a ``ContentTaskProvider`` and never checks whether the ledger
    holds the plan, so after ``plan import`` and ``plan dispatch`` this call still answers from
    the untouched content record while the CLI answers from the ledger row ``dispatch`` moved to
    ``in-progress``.
    """
    cli_create = _invoke_cli(["plan", "create", "--slug", "status-parity", "--goal", "Status goal"])
    plan_id = cli_create["plan_id"]
    _invoke_cli(["plan", "append-task", "--plan-address", plan_id, *_task_args(_TASK_DEF)])
    _invoke_cli(["plan", "finalize", "--plan-address", plan_id])
    _invoke_cli(["plan", "import", "--from", "content", "--plan-address", plan_id])
    _invoke_cli(["plan", "dispatch", "--address", f"{plan_id}/T01"])

    cli_status = _invoke_cli(["plan", "status", "--plan-address", plan_id])
    mcp_status = await call_mcp_tool(_sam_mcp, "sam_plan", {"config": {"action": "status"}, "plan": plan_id})

    assert cli_status["tasks"][0]["status"] == "in-progress"  # non-vacuity: CLI actually read the ledger
    assert _without_nulls(mcp_status) == _without_nulls(cli_status)


async def test_sam_plan_append_task_lands_in_the_ledger_on_an_imported_plan(dh_env: dict[str, str]) -> None:
    """MCP ``sam_plan`` ``append_task`` must write the ledger, not a content record import left behind.

    The plan starts drafting on the content store, is imported still drafting (no tasks), and MCP
    appends the only task. The CLI's ledger-backed ``status`` must then list it, agent and priority
    fields included -- today it lists nothing, because the append landed in the content record
    instead and the ledger's task list stays empty.
    """
    cli_create = _invoke_cli(["plan", "create", "--slug", "append-task-parity", "--goal", "Append goal"])
    plan_id = cli_create["plan_id"]
    _invoke_cli(["plan", "import", "--from", "content", "--plan-address", plan_id])

    await call_mcp_tool(
        _sam_mcp,
        "sam_plan",
        {
            "config": {
                "action": "append_task",
                "task": {"id": "T01", "title": "Ledger Task", "agent": "task-worker", "priority": 3},
            },
            "plan": plan_id,
        },
    )

    cli_status = _invoke_cli(["plan", "status", "--plan-address", plan_id])
    task_ids = [row["id"] for row in cli_status["tasks"]]
    assert task_ids == ["T01"]
    assert cli_status["tasks"][0]["agent"] == "task-worker"
    assert cli_status["tasks"][0]["priority"] == 3


async def test_sam_task_state_moves_the_ledger_row_on_an_imported_plan(dh_env: dict[str, str]) -> None:
    """MCP ``sam_task`` ``state`` must move the ledger row to the new status, with a reason recorded.

    The task is left not-started (no ``dispatch``), so it passes the ledger's acceptance, lease and
    report checks on the way to ``skipped`` -- the refusal paths those checks guard are a separate
    concern (see the refusal-parity test below), not a routing one. This call succeeds and moves the
    ledger row, exactly like the CLI's ledger-backed ``state`` command does.
    """
    cli_create = _invoke_cli(["plan", "create", "--slug", "state-parity", "--goal", "State goal"])
    plan_id = cli_create["plan_id"]
    _invoke_cli(["plan", "append-task", "--plan-address", plan_id, *_task_args(_TASK_DEF)])
    _invoke_cli(["plan", "finalize", "--plan-address", plan_id])
    _invoke_cli(["plan", "import", "--from", "content", "--plan-address", plan_id])

    await call_mcp_tool(
        _sam_mcp,
        "sam_task",
        {"plan": plan_id, "task": "T01", "config": {"action": "state", "status": "skipped", "reason": "user"}},
    )

    cli_status = _invoke_cli(["plan", "status", "--plan-address", plan_id])
    assert cli_status["tasks"][0]["status"] == "skipped"


async def test_sam_plan_ready_matches_the_cli_on_an_imported_plan(dh_env: dict[str, str]) -> None:
    """MCP ``sam_plan`` ``ready`` must read the ledger's dependency-resolved queue after import.

    ``T01`` is dispatched before the reads, so the ledger and content copies disagree: the ledger no
    longer lists it as ready, while the untouched content record still would. Without the dispatch,
    both stores agree and only the envelope shape (``items``/``count`` versus ``feature``/
    ``ready_tasks``) would tell them apart -- too weak a signal for a routing regression that reads a
    stale ledger-shaped projection.
    """
    cli_create = _invoke_cli(["plan", "create", "--slug", "ready-ledger-parity", "--goal", "Ready goal"])
    plan_id = cli_create["plan_id"]
    _invoke_cli(["plan", "append-task", "--plan-address", plan_id, *_task_args(_TASK_DEF)])
    _invoke_cli(["plan", "finalize", "--plan-address", plan_id])
    _invoke_cli(["plan", "import", "--from", "content", "--plan-address", plan_id])
    _invoke_cli(["plan", "dispatch", "--address", f"{plan_id}/T01"])

    cli_ready = _invoke_cli(["plan", "ready", "--plan-address", plan_id])
    mcp_ready = await call_mcp_tool(_sam_mcp, "sam_plan", {"config": {"action": "ready"}, "plan": plan_id})

    assert cli_ready["count"] == 0  # non-vacuity: the dispatched task is gone from the ledger's queue
    assert mcp_ready == cli_ready


async def test_sam_plan_read_matches_the_cli_on_an_imported_plan(dh_env: dict[str, str]) -> None:
    """MCP ``sam_plan`` ``read`` must return the ledger projection, not the pre-import content copy."""
    cli_create = _invoke_cli(["plan", "create", "--slug", "read-ledger-parity", "--goal", "Read goal"])
    plan_id = cli_create["plan_id"]
    _invoke_cli(["plan", "append-task", "--plan-address", plan_id, *_task_args(_TASK_DEF)])
    _invoke_cli(["plan", "finalize", "--plan-address", plan_id])
    _invoke_cli(["plan", "import", "--from", "content", "--plan-address", plan_id])
    _invoke_cli(["plan", "update", "--plan-address", plan_id, "--set", "goal=Ledger-only goal"])

    cli_read = _invoke_cli(["plan", "read", "--address", plan_id])
    mcp_read = await call_mcp_tool(_sam_mcp, "sam_plan", {"config": {"action": "read"}, "plan": plan_id})

    assert cli_read["source_format"] == "ledger"  # non-vacuity: the CLI actually read the ledger
    assert cli_read["plan"]["goal"] == "Ledger-only goal"
    assert _without_nulls(mcp_read) == _without_nulls(cli_read)


async def test_sam_plan_update_lands_in_the_ledger_on_an_imported_plan(dh_env: dict[str, str]) -> None:
    """MCP ``sam_plan`` ``update`` must write the ledger's context field once the plan is imported."""
    cli_create = _invoke_cli(["plan", "create", "--slug", "update-ledger-parity", "--goal", "Update goal"])
    plan_id = cli_create["plan_id"]
    _invoke_cli(["plan", "append-task", "--plan-address", plan_id, *_task_args(_TASK_DEF)])
    _invoke_cli(["plan", "finalize", "--plan-address", plan_id])
    _invoke_cli(["plan", "import", "--from", "content", "--plan-address", plan_id])

    await call_mcp_tool(
        _sam_mcp, "sam_plan", {"config": {"action": "update", "context": "MCP-WROTE-THIS"}, "plan": plan_id}
    )

    cli_status = _invoke_cli(["plan", "status", "--plan-address", plan_id])
    assert cli_status["row"]["context"] == "MCP-WROTE-THIS"


async def test_sam_plan_finalize_moves_the_ledger_plan_out_of_drafting(dh_env: dict[str, str]) -> None:
    """MCP ``sam_plan`` ``finalize`` must clear the ledger's drafting state once the plan is imported."""
    cli_create = _invoke_cli(["plan", "create", "--slug", "finalize-ledger-parity", "--goal", "Finalize goal"])
    plan_id = cli_create["plan_id"]
    _invoke_cli(["plan", "append-task", "--plan-address", plan_id, *_task_args(_TASK_DEF)])
    _invoke_cli(["plan", "import", "--from", "content", "--plan-address", plan_id])

    mcp_finalize = await call_mcp_tool(_sam_mcp, "sam_plan", {"config": {"action": "finalize"}, "plan": plan_id})
    assert mcp_finalize.get("noop") is None  # a TransitionResult carries no finalized/state keys to assert on

    cli_status = _invoke_cli(["plan", "status", "--plan-address", plan_id])
    assert cli_status["state"] == "ready"


async def test_sam_task_read_matches_the_cli_on_an_imported_plan(dh_env: dict[str, str]) -> None:
    """MCP ``sam_task`` ``read`` must return the ledger's task row once the plan is imported and dispatched."""
    cli_create = _invoke_cli(["plan", "create", "--slug", "task-read-ledger-parity", "--goal", "Task read goal"])
    plan_id = cli_create["plan_id"]
    _invoke_cli(["plan", "append-task", "--plan-address", plan_id, *_task_args(_TASK_DEF)])
    _invoke_cli(["plan", "finalize", "--plan-address", plan_id])
    _invoke_cli(["plan", "import", "--from", "content", "--plan-address", plan_id])
    _invoke_cli(["plan", "dispatch", "--address", f"{plan_id}/T01"])

    cli_read = _invoke_cli(["plan", "read", "--address", f"{plan_id}/T01"])
    mcp_read = await call_mcp_tool(_sam_mcp, "sam_task", {"plan": plan_id, "task": "T01", "config": {"action": "read"}})

    assert cli_read["row"]["status"] == "in-progress"  # non-vacuity: the CLI actually read the ledger
    assert _without_nulls(mcp_read) == _without_nulls(cli_read)


async def test_sam_task_update_lands_in_the_ledger_on_an_imported_plan(dh_env: dict[str, str]) -> None:
    """MCP ``sam_task`` ``update`` must patch the ledger task row and its ``attempt``-scoped section."""
    cli_create = _invoke_cli(["plan", "create", "--slug", "task-update-ledger-parity", "--goal", "Task update goal"])
    plan_id = cli_create["plan_id"]
    _invoke_cli(["plan", "append-task", "--plan-address", plan_id, *_task_args(_TASK_DEF)])
    _invoke_cli(["plan", "finalize", "--plan-address", plan_id])
    _invoke_cli(["plan", "import", "--from", "content", "--plan-address", plan_id])
    _invoke_cli(["plan", "dispatch", "--address", f"{plan_id}/T01"])

    await call_mcp_tool(
        _sam_mcp,
        "sam_task",
        {"plan": plan_id, "task": "T01", "config": {"action": "update", "set_fields_json": {"priority": 5}}},
    )

    cli_status = _invoke_cli(["plan", "status", "--plan-address", plan_id])
    assert cli_status["tasks"][0]["priority"] == 5

    # The runner's actual write shape: an attempt-scoped section append, not a bare field patch.
    await call_mcp_tool(
        _sam_mcp,
        "sam_task",
        {
            "plan": plan_id,
            "task": "T01",
            "config": {
                "action": "update",
                "attempt": 1,
                "append_section": "Completion Report",
                "section_content": "Done.",
            },
        },
    )

    cli_attempt_read = _invoke_cli(["plan", "read", "--address", f"{plan_id}/T01", "--attempt", "1"])
    section_names = {section["name"] for section in cli_attempt_read["sections"]}
    assert "Completion Report" in section_names


_CASE_SPELLINGS = pytest.mark.parametrize(
    "spell", [str.upper, lambda plan_id: "p" + plan_id[1:]], ids=["upper hex", "lower p"]
)


@_CASE_SPELLINGS
async def test_sam_plan_status_matches_the_cli_for_a_plan_id_spelled_in_another_case(
    dh_env: dict[str, str], spell: Callable[[str], str]
) -> None:
    """MCP routing must canonicalise a plan id the same way the CLI does before checking the ledger.

    ``canonical_plan_id`` (``addressing.py``) lowercases the hex suffix of a UID-derived plan id.
    The CLI's ``store_for``/``ledger_holds`` chain (``sam_plan.py`` ``raw_plan_of``/``_plan_of``)
    already canonicalises before checking whether the ledger holds the plan. ``server.py`` has no
    equivalent step today, so this call reads the content store regardless of spelling. ``T01`` is
    dispatched before the read so the two stores disagree; on an un-dispatched plan they would agree
    and only the envelope shape would tell a wrong store from a right one.
    """
    plan_id = _mint_plan_id_with_a_letter_in_its_hex_suffix("case-ledger-parity", "Case goal")
    assert spell(plan_id) != plan_id  # non-vacuity: this spelling actually differs from the canonical one
    _invoke_cli(["plan", "append-task", "--plan-address", plan_id, *_task_args(_TASK_DEF)])
    _invoke_cli(["plan", "finalize", "--plan-address", plan_id])
    _invoke_cli(["plan", "import", "--from", "content", "--plan-address", plan_id])
    _invoke_cli(["plan", "dispatch", "--address", f"{plan_id}/T01"])

    cli_status = _invoke_cli(["plan", "status", "--plan-address", spell(plan_id)])
    mcp_status = await call_mcp_tool(_sam_mcp, "sam_plan", {"config": {"action": "status"}, "plan": spell(plan_id)})

    assert _without_nulls(mcp_status) == _without_nulls(cli_status)


@_CASE_SPELLINGS
async def test_sam_task_read_matches_the_cli_for_a_plan_id_spelled_in_another_case(
    dh_env: dict[str, str], spell: Callable[[str], str]
) -> None:
    """A task read must canonicalise the plan id the way ``sam_plan`` does, not just the plan actions.

    ``sam_task`` resolves ``plan`` at its own entry point, separately from ``sam_plan``'s. A fix that
    canonicalises only inside ``sam_plan`` would leave this call reading content.
    """
    plan_id = _mint_plan_id_with_a_letter_in_its_hex_suffix("case-task-read-parity", "Case task goal")
    assert spell(plan_id) != plan_id
    _invoke_cli(["plan", "append-task", "--plan-address", plan_id, *_task_args(_TASK_DEF)])
    _invoke_cli(["plan", "finalize", "--plan-address", plan_id])
    _invoke_cli(["plan", "import", "--from", "content", "--plan-address", plan_id])
    _invoke_cli(["plan", "dispatch", "--address", f"{plan_id}/T01"])

    cli_read = _invoke_cli(["plan", "read", "--address", f"{plan_id}/T01"])
    mcp_read = await call_mcp_tool(
        _sam_mcp, "sam_task", {"plan": spell(plan_id), "task": "T01", "config": {"action": "read"}}
    )

    assert _without_nulls(mcp_read) == _without_nulls(cli_read)


@_CASE_SPELLINGS
async def test_sam_plan_update_lands_in_the_ledger_for_a_plan_id_spelled_in_another_case(
    dh_env: dict[str, str], spell: Callable[[str], str]
) -> None:
    """A write must canonicalise the plan id too, not just land safely because content matches case-insensitively.

    The content resolver matches ids without regard to case, so a write that skips canonicalisation
    would silently succeed against content instead of failing loudly -- the gap only a write case, not
    a read case, can show.
    """
    plan_id = _mint_plan_id_with_a_letter_in_its_hex_suffix("case-write-parity", "Case write goal")
    assert spell(plan_id) != plan_id
    _invoke_cli(["plan", "append-task", "--plan-address", plan_id, *_task_args(_TASK_DEF)])
    _invoke_cli(["plan", "finalize", "--plan-address", plan_id])
    _invoke_cli(["plan", "import", "--from", "content", "--plan-address", plan_id])

    await call_mcp_tool(
        _sam_mcp, "sam_plan", {"config": {"action": "update", "context": "CASE-WROTE-THIS"}, "plan": spell(plan_id)}
    )

    cli_status = _invoke_cli(["plan", "status", "--plan-address", plan_id])
    assert cli_status["row"]["context"] == "CASE-WROTE-THIS"


async def test_sam_task_read_matches_the_cli_on_a_ledger_native_plan(dh_env: dict[str, str]) -> None:
    """A plan created directly on the ledger (``--base-sha``) has no content record at all.

    ``resolve_provider_plan_address`` returns the raw address unchanged when no content plan
    matches it, so ``sam_task`` reaches ``operations.read_task`` against a content backend that was
    never told this plan exists, instead of checking the ledger first the way the CLI's ``store_for``
    does. The CLI reads the task fine; MCP raises ``Plan not found`` instead of matching it.
    """
    cli_create = _invoke_cli([
        "plan",
        "create",
        "--slug",
        "ledger-native-parity",
        "--goal",
        "Native goal",
        "--base-sha",
        "abc123",
    ])
    plan_id = cli_create["plan"]
    _invoke_cli(["plan", "append-task", "--plan-address", plan_id, "--task-id", "T01", "--task-title", "Native Task"])
    _invoke_cli(["plan", "finalize", "--plan-address", plan_id])

    cli_read = _invoke_cli(["plan", "read", "--address", f"{plan_id}/T01"])
    assert cli_read["task"] == "T01"  # non-vacuity: the CLI actually found the ledger-native plan
    assert cli_read["row"]["id"] == "T01"

    mcp_read = await call_mcp_tool(_sam_mcp, "sam_task", {"plan": plan_id, "task": "T01", "config": {"action": "read"}})

    assert _without_nulls(mcp_read) == _without_nulls(cli_read)


async def test_mcp_reads_content_for_a_plan_the_ledger_does_not_hold(dh_env: dict[str, str]) -> None:
    """A plan the ledger does not hold must keep answering from content once a ledger database exists.

    A ``holds`` check that returns true whenever the database file exists, or a server that routes
    every plan once anything is imported, would pass every other test in this module while breaking
    MPR-style plans that stay on content by user choice. Plan A is imported onto the ledger to create
    the database; plan B is built and finalized on content only, and never imported.
    """
    cli_create_a = _invoke_cli(["plan", "create", "--slug", "guard-ledger-a", "--goal", "Ledger A goal"])
    plan_a = cli_create_a["plan_id"]
    _invoke_cli(["plan", "append-task", "--plan-address", plan_a, *_task_args(_TASK_DEF)])
    _invoke_cli(["plan", "finalize", "--plan-address", plan_a])
    _invoke_cli(["plan", "import", "--from", "content", "--plan-address", plan_a])

    cli_create_b = _invoke_cli(["plan", "create", "--slug", "guard-content-b", "--goal", "Content B goal"])
    plan_b = cli_create_b["plan_id"]
    _invoke_cli(["plan", "append-task", "--plan-address", plan_b, *_task_args(_TASK_DEF)])
    _invoke_cli(["plan", "finalize", "--plan-address", plan_b])

    cli_status_b = _invoke_cli(["plan", "status", "--plan-address", plan_b])
    mcp_status_b = await call_mcp_tool(_sam_mcp, "sam_plan", {"config": {"action": "status"}, "plan": plan_b})

    assert "by_status" in mcp_status_b  # non-vacuity: this is the content shape, not the ledger's
    assert _without_nulls(mcp_status_b) == _without_nulls(cli_status_b)


async def test_sam_plan_append_task_refuses_on_an_archived_ledger_plan(dh_env: dict[str, str]) -> None:
    """MCP ``sam_plan`` ``append_task`` must refuse the way ``ledger.append_task``'s ``require_unarchived`` does.

    The CLI's ``archive`` command is ledger-only, so the content record is never told the plan
    archived. MCP therefore appends to content and reports success instead of refusing.
    """
    cli_create = _invoke_cli(["plan", "create", "--slug", "archived-append-parity", "--goal", "Archived goal"])
    plan_id = cli_create["plan_id"]
    _invoke_cli(["plan", "append-task", "--plan-address", plan_id, *_task_args(_TASK_DEF)])
    _invoke_cli(["plan", "finalize", "--plan-address", plan_id])
    _invoke_cli(["plan", "import", "--from", "content", "--plan-address", plan_id])
    _invoke_cli(["plan", "archive", "--plan-address", plan_id, "--reason", "done"])

    with pytest.raises(ToolError):
        await call_mcp_tool(
            _sam_mcp,
            "sam_plan",
            {
                "config": {
                    "action": "append_task",
                    "task": {"id": "T09", "title": "Late Task", "agent": "task-worker"},
                },
                "plan": plan_id,
            },
        )

    cli_status = _invoke_cli(["plan", "status", "--plan-address", plan_id])
    task_ids = {row["id"] for row in cli_status["tasks"]}
    assert "T09" not in task_ids


@pytest.mark.parametrize(
    "action_config",
    [
        pytest.param({"action": "state", "status": "complete"}, id="state without reason"),
        pytest.param(
            {"action": "update", "append_section": "Completion Report", "section_content": "x"},
            id="update section without attempt",
        ),
    ],
)
async def test_sam_task_refuses_on_an_imported_plan_the_way_the_ledger_does(
    dh_env: dict[str, str], action_config: dict[str, Any]
) -> None:
    """MCP must reach the ledger's refusal, not silently write the content record instead.

    Neither case names a field the current MCP schema lacks, so today's failure is not a schema
    error: MCP routes both calls to the untouched content record, which has no reason or attempt
    requirement, and returns a success envelope instead of raising. Green after the fix means MCP
    reached ``ledger.state``'s ``--reason is required`` check or ``ledger.update``'s
    ``attempt-required`` refusal, the same ones the CLI's ledger branch reaches.
    """
    cli_create = _invoke_cli(["plan", "create", "--slug", "refusal-parity", "--goal", "Refusal goal"])
    plan_id = cli_create["plan_id"]
    _invoke_cli(["plan", "append-task", "--plan-address", plan_id, *_task_args(_TASK_DEF)])
    _invoke_cli(["plan", "finalize", "--plan-address", plan_id])
    _invoke_cli(["plan", "import", "--from", "content", "--plan-address", plan_id])
    _invoke_cli(["plan", "dispatch", "--address", f"{plan_id}/T01"])

    with pytest.raises(ToolError):
        await call_mcp_tool(_sam_mcp, "sam_task", {"plan": plan_id, "task": "T01", "config": action_config})

    cli_status = _invoke_cli(["plan", "status", "--plan-address", plan_id])
    assert cli_status["tasks"][0]["status"] == "in-progress"  # the ledger row must stay untouched


async def test_sam_plan_update_refuses_an_unwritable_set_field_like_the_cli_on_an_imported_plan(
    dh_env: dict[str, str],
) -> None:
    """MCP ``sam_plan`` ``update`` must refuse a ``set_fields_json`` name no fields event writes, like the CLI.

    ``archived`` is a stored ``plans`` column only ``archive`` writes. Before the fix, MCP passed
    ``set_fields_json`` straight to ``ledger.update``, which silently dropped the name into the
    result's ``unsettable`` list instead of refusing -- an agent that does not inspect that field
    reads the call as having succeeded. The CLI's ``plan update --set archived=...`` already refuses
    (``sam_plan.py``'s former ``_set_values``); green after the fix means MCP reaches the same
    refusal, now centralised in ``dh_core.ledger.transitions.update``.
    """
    cli_create = _invoke_cli(["plan", "create", "--slug", "update-refusal-parity", "--goal", "Update refusal goal"])
    plan_id = cli_create["plan_id"]
    _invoke_cli(["plan", "append-task", "--plan-address", plan_id, *_task_args(_TASK_DEF)])
    _invoke_cli(["plan", "finalize", "--plan-address", plan_id])
    _invoke_cli(["plan", "import", "--from", "content", "--plan-address", plan_id])

    cli_result = _runner.invoke(app, ["plan", "update", "--plan-address", plan_id, "--set", "archived=2020-01-01"])
    assert cli_result.exit_code != 0  # non-vacuity: the CLI itself refuses this --set name

    with pytest.raises(ToolError):
        await call_mcp_tool(
            _sam_mcp,
            "sam_plan",
            {"config": {"action": "update", "set_fields_json": {"archived": "2020-01-01"}}, "plan": plan_id},
        )

    cli_status = _invoke_cli(["plan", "status", "--plan-address", plan_id])
    assert cli_status["row"]["archived"] is None  # the refused write must not have landed


async def test_sam_task_update_refuses_an_unwritable_set_field_like_the_cli_on_an_imported_plan(
    dh_env: dict[str, str],
) -> None:
    """MCP ``sam_task`` ``update`` must refuse a ``set_fields_json`` name no fields event writes, like the CLI.

    ``status`` moves only through ``dispatch``, ``finish``, ``state``, ``reclaim`` or ``accept`` --
    never ``update``. See the plan-level sibling test above for the same defect (MAJOR-1) on the
    task-level path.
    """
    cli_create = _invoke_cli(["plan", "create", "--slug", "task-update-refusal-parity", "--goal", "Task refusal goal"])
    plan_id = cli_create["plan_id"]
    _invoke_cli(["plan", "append-task", "--plan-address", plan_id, *_task_args(_TASK_DEF)])
    _invoke_cli(["plan", "finalize", "--plan-address", plan_id])
    _invoke_cli(["plan", "import", "--from", "content", "--plan-address", plan_id])

    cli_result = _runner.invoke(
        app, ["plan", "update", "--plan-address", plan_id, "--task-id", "T01", "--set", "status=complete"]
    )
    assert cli_result.exit_code != 0  # non-vacuity: the CLI itself refuses this --set name

    with pytest.raises(ToolError):
        await call_mcp_tool(
            _sam_mcp,
            "sam_task",
            {"plan": plan_id, "task": "T01", "config": {"action": "update", "set_fields_json": {"status": "complete"}}},
        )

    cli_status = _invoke_cli(["plan", "status", "--plan-address", plan_id])
    assert cli_status["tasks"][0]["status"] == "not-started"  # the refused write must not have landed


async def test_sam_plan_append_task_sets_the_conflict_group_on_an_imported_plan(dh_env: dict[str, str]) -> None:
    """MCP ``sam_plan`` ``append_task`` must be able to set ``conflict_group``, like the CLI's ``--conflict-group``.

    Before the fix, ``AppendTaskConfig`` had no ``conflict_group`` field, so MCP could never set it
    even though the CLI's ledger-backed ``append-task`` command always could.
    """
    cli_create = _invoke_cli(["plan", "create", "--slug", "append-task-conflict-group", "--goal", "Conflict goal"])
    plan_id = cli_create["plan_id"]
    _invoke_cli(["plan", "import", "--from", "content", "--plan-address", plan_id])

    await call_mcp_tool(
        _sam_mcp,
        "sam_plan",
        {
            "config": {
                "action": "append_task",
                "task": {"id": "T01", "title": "Exclusive Task", "agent": "task-worker"},
                "conflict_group": "group-a",
            },
            "plan": plan_id,
        },
    )

    cli_status = _invoke_cli(["plan", "status", "--plan-address", plan_id])
    assert cli_status["tasks"][0]["conflict_group"] == "group-a"


async def test_sam_plan_ready_full_false_returns_the_compact_manifest_on_an_imported_plan(
    dh_env: dict[str, str],
) -> None:
    """MCP ``sam_plan`` ``ready`` must honor ``full`` once the ledger holds the plan.

    Before the fix, ``config.full`` never reached ``ledger.ready``, so ``full=False`` and
    ``full=True`` returned identical rows.
    """
    cli_create = _invoke_cli(["plan", "create", "--slug", "ready-full-parity", "--goal", "Ready full goal"])
    plan_id = cli_create["plan_id"]
    _invoke_cli(["plan", "append-task", "--plan-address", plan_id, *_task_args(_TASK_DEF)])
    _invoke_cli(["plan", "finalize", "--plan-address", plan_id])
    _invoke_cli(["plan", "import", "--from", "content", "--plan-address", plan_id])

    mcp_compact = await call_mcp_tool(
        _sam_mcp, "sam_plan", {"config": {"action": "ready", "full": False}, "plan": plan_id}
    )
    mcp_full = await call_mcp_tool(_sam_mcp, "sam_plan", {"config": {"action": "ready", "full": True}, "plan": plan_id})

    assert mcp_compact["count"] == 1
    compact_keys = set(mcp_compact["items"][0])
    assert compact_keys == {"id", "title", "agent", "skills", "dependencies", "status", "priority"}
    assert compact_keys < set(mcp_full["items"][0])


# ---------------------------------------------------------------------------
# Active-task parity
# ---------------------------------------------------------------------------


_AT_SESSION = "parity-test-session"


async def test_active_task_get_parity(dh_env: dict[str, str]) -> None:
    """CLI ``active-task get`` and MCP ``sam_active_task(action='get')`` return the same result."""
    # Both report None when nothing is set
    cli_get = _invoke_cli(["active-task", "get", "--session-id", _AT_SESSION])
    mcp_get = await call_mcp_tool(_sam_mcp, "sam_active_task", {"config": {"action": "get"}, "session_id": _AT_SESSION})
    assert cli_get["active_task"] is None
    assert mcp_get["active_task"] is None

    # Set via CLI and both read it back
    _invoke_cli(["active-task", "set", "--address", "P1/T3", "--session-id", _AT_SESSION])
    cli_get2 = _invoke_cli(["active-task", "get", "--session-id", _AT_SESSION])
    mcp_get2 = await call_mcp_tool(
        _sam_mcp, "sam_active_task", {"config": {"action": "get"}, "session_id": _AT_SESSION}
    )
    assert cli_get2["active_task"]["plan"] == mcp_get2["active_task"]["plan"]
    assert cli_get2["active_task"]["task"] == mcp_get2["active_task"]["task"]


async def test_active_task_set_parity(dh_env: dict[str, str]) -> None:
    """CLI set → MCP get and MCP set → CLI get produce identical active task context."""
    # CLI sets, MCP reads
    cli_set = _invoke_cli(["active-task", "set", "--address", "P5/T7", "--session-id", _AT_SESSION])
    mcp_get = await call_mcp_tool(_sam_mcp, "sam_active_task", {"config": {"action": "get"}, "session_id": _AT_SESSION})
    assert mcp_get["active_task"]["plan"] == cli_set["active_task"]["plan"]
    assert mcp_get["active_task"]["task"] == cli_set["active_task"]["task"]

    # MCP sets, CLI reads
    mcp_set = await call_mcp_tool(
        _sam_mcp,
        "sam_active_task",
        {"config": {"action": "set", "plan": "P9", "task": "T2"}, "session_id": _AT_SESSION},
    )
    cli_get = _invoke_cli(["active-task", "get", "--session-id", _AT_SESSION])
    assert cli_get["active_task"]["plan"] == mcp_set["active_task"]["plan"]
    assert cli_get["active_task"]["task"] == mcp_set["active_task"]["task"]


async def test_active_task_update_parity(dh_env: dict[str, str], tmp_path: Path) -> None:
    """CLI active-task update and MCP sam_active_task update produce equivalent results."""
    plan_dir = str(tmp_path / "plan")
    Path(plan_dir).mkdir(parents=True, exist_ok=True)

    cli_create = _invoke_cli([
        "plan",
        "create",
        "--slug",
        "at-update",
        "--goal",
        "AT update goal",
        "--plan-dir",
        plan_dir,
    ])
    plan_id = cli_create["plan_id"]
    _invoke_cli(["plan", "append-task", "--plan-address", plan_id, *_task_args(_TASK_DEF), "--plan-dir", plan_dir])
    _invoke_cli(["plan", "finalize", "--plan-address", plan_id, "--plan-dir", plan_dir])

    # Set active task via MCP (preserves 'T01' prefix that plan file uses)
    await call_mcp_tool(
        _sam_mcp,
        "sam_active_task",
        {"config": {"action": "set", "plan": plan_id, "task": "T01", "plan_dir": plan_dir}, "session_id": _AT_SESSION},
    )

    # CLI update
    cli_update = _invoke_cli([
        "active-task",
        "update",
        "--set-fields-json",
        '{"priority":5}',
        "--session-id",
        _AT_SESSION,
    ])
    assert cli_update["updated"] is True

    # MCP read verifies the update
    mcp_read = await call_mcp_tool(
        _sam_mcp, "sam_task", {"plan": plan_id, "task": "T01", "config": {"action": "read"}, "plan_dir": plan_dir}
    )
    assert mcp_read["task"]["priority"] == 5

    # Reset priority for reverse direction
    _invoke_cli([
        "plan",
        "update",
        "--plan-address",
        plan_id,
        "--task-id",
        "T01",
        "--plan-dir",
        plan_dir,
        "--priority",
        "1",
    ])

    # MCP update
    mcp_update = await call_mcp_tool(
        _sam_mcp,
        "sam_active_task",
        {"config": {"action": "update", "set_fields_json": {"priority": 4}}, "session_id": _AT_SESSION},
    )
    assert mcp_update["updated"] is True

    # CLI read verifies
    cli_read = _invoke_cli(["plan", "read", "--address", f"{plan_id}/T01", "--plan-dir", plan_dir])
    assert cli_read["task"]["priority"] == 4


async def test_active_task_clear_parity(dh_env: dict[str, str]) -> None:
    """CLI clear → MCP get returns null, and MCP clear → CLI get returns null."""
    # Set via CLI
    _invoke_cli(["active-task", "set", "--address", "P3/T5", "--session-id", _AT_SESSION])

    # CLI clear
    cli_clear = _invoke_cli(["active-task", "clear", "--session-id", _AT_SESSION])
    assert cli_clear["cleared"] is True

    # MCP get returns null
    mcp_get = await call_mcp_tool(_sam_mcp, "sam_active_task", {"config": {"action": "get"}, "session_id": _AT_SESSION})
    assert mcp_get["active_task"] is None

    # MCP set, MCP clear, CLI get returns null
    await call_mcp_tool(
        _sam_mcp,
        "sam_active_task",
        {"config": {"action": "set", "plan": "P8", "task": "T4"}, "session_id": _AT_SESSION},
    )
    mcp_clear = await call_mcp_tool(
        _sam_mcp, "sam_active_task", {"config": {"action": "clear"}, "session_id": _AT_SESSION}
    )
    assert mcp_clear["cleared"] is True

    cli_get = _invoke_cli(["active-task", "get", "--session-id", _AT_SESSION])
    assert cli_get["active_task"] is None


# ---------------------------------------------------------------------------
# Dispatch/artifact CLI forwarding parity (provider-neutral)
# ---------------------------------------------------------------------------


def _assert_compact_result(result: Any, expected: dict[str, Any]) -> None:
    assert result.exit_code == 0, result.stderr
    assert result.stderr == ""
    assert result.stdout.endswith("\n")
    assert result.stdout.count("\n") == 1
    assert ": " not in result.stdout
    assert ", " not in result.stdout
    assert json.loads(result.stdout) == expected


@pytest.mark.parametrize(
    ("command", "operation", "args", "kwargs", "payload"),
    [
        (
            "read",
            "dispatch_read_plan",
            ["--milestone-number", "10"],
            {"milestone_number": 10},
            {"milestone_number": 10},
        ),
        (
            "validate",
            "dispatch_validate_plan",
            ["--milestone-number", "10"],
            {"milestone_number": 10},
            {"milestone_number": 10},
        ),
        (
            "stale-check",
            "dispatch_stale_check",
            ["--milestone-number", "10", "--repo", "owner/name"],
            {"milestone_number": 10, "repo": "owner/name"},
            {"milestone_number": 10, "is_stale": False, "added_issues": [], "removed_issues": []},
        ),
        (
            "conflicts",
            "dispatch_conflicts",
            ["--milestone-number", "10", "--repo", "owner/name"],
            {"milestone_number": 10, "repo": "owner/name"},
            {"milestone_number": 10, "conflict_groups": [], "count": 0},
        ),
        (
            "create-plan",
            "dispatch_create_plan",
            [
                "--milestone-number",
                "10",
                "--milestone-title",
                "Milestone",
                "--integration-branch",
                "main",
                "--wave-item",
                "wave=1;issue=101;title=Feature A;priority=P1",
                "--wave-item",
                "wave=2;issue=102;title=Feature B;priority=P2;depends_on=101",
            ],
            {
                "milestone_number": 10,
                "plan": {
                    "milestone": {"number": 10, "title": "Milestone", "integration_branch": "main"},
                    "conflict_groups": [],
                    "waves": [
                        {
                            "wave": 1,
                            "parallel": True,
                            "items": [
                                {
                                    "title": "Feature A",
                                    "issue": 101,
                                    "priority": "P1",
                                    "conflict_group": None,
                                    "depends_on": [],
                                    "status": "pending",
                                }
                            ],
                        },
                        {
                            "wave": 2,
                            "parallel": True,
                            "items": [
                                {
                                    "title": "Feature B",
                                    "issue": 102,
                                    "priority": "P2",
                                    "conflict_group": None,
                                    "depends_on": [101],
                                    "status": "pending",
                                }
                            ],
                        },
                    ],
                    "quality_gates": {"pre_merge": [], "post_merge": []},
                },
                "overwrite": False,
                "issue": None,
            },
            {"milestone_number": 10, "wave_count": 2},
        ),
        (
            "wave-start",
            "dispatch_wave_start",
            [
                "--milestone-number",
                "10",
                "--wave-number",
                "1",
                "--item",
                "issue=101;title=Feature A",
                "--item",
                "issue=102;title=Feature B",
            ],
            {
                "milestone": 10,
                "wave_num": 1,
                "items": [{"issue": 101, "title": "Feature A"}, {"issue": 102, "title": "Feature B"}],
            },
            {"milestone": 10, "wave_num": 1},
        ),
        (
            "item-status",
            "dispatch_item_status",
            [
                "--milestone-number",
                "10",
                "--issue-number",
                "101",
                "--status",
                "complete",
                "--result",
                "ok",
                "--cost",
                "1.25",
            ],
            {"milestone": 10, "issue": 101, "status": "complete", "result": "ok", "error": "", "cost": 1.25},
            {"milestone": 10, "issue": 101},
        ),
        (
            "wave-status",
            "dispatch_wave_status",
            ["--milestone-number", "10", "--wave-number", "1"],
            {"milestone": 10, "wave_num": 1},
            {"milestone": 10, "wave_num": 1},
        ),
        (
            "spawn",
            "dispatch_spawn",
            [
                "--milestone-number",
                "10",
                "--wave-number",
                "1",
                "--max-concurrent",
                "2",
                "--model",
                "sonnet",
                "--phase",
                "groom",
                "--effort",
                "high",
            ],
            {
                "milestone": 10,
                "wave_num": 1,
                "max_concurrent": 2,
                "model": "sonnet",
                "phase": "groom",
                "effort": "high",
            },
            {"accepted": True},
        ),
    ],
)
def test_dispatch_cli_forwards_named_options(
    monkeypatch: pytest.MonkeyPatch,
    command: str,
    operation: str,
    args: list[str],
    kwargs: dict[str, Any],
    payload: dict[str, Any],
) -> None:
    mock_operation = Mock(return_value=payload)
    monkeypatch.setattr(dispatch.operations, operation, mock_operation)
    result = _runner.invoke(app, ["dispatch", command, *args])
    _assert_compact_result(result, payload)
    mock_operation.assert_called_once_with(**kwargs)


def test_dispatch_create_plan_forwards_issue_option(monkeypatch: pytest.MonkeyPatch) -> None:
    """``--issue`` must reach ``dispatch_create_plan`` so the plan is registered on the item."""
    mock_operation = Mock(return_value={"milestone_number": 10, "wave_count": 1})
    monkeypatch.setattr(dispatch.operations, "dispatch_create_plan", mock_operation)
    result = _runner.invoke(
        app,
        [
            "dispatch",
            "create-plan",
            "--milestone-number",
            "10",
            "--milestone-title",
            "Milestone",
            "--integration-branch",
            "main",
            "--wave-item",
            "wave=1;issue=101;title=Feature A;priority=P1",
            "--issue",
            "55",
        ],
    )
    assert result.exit_code == 0, result.stderr
    assert mock_operation.call_args.kwargs["issue"] == 55


def test_dispatch_create_plan_rejects_undeclared_conflict_group(monkeypatch: pytest.MonkeyPatch) -> None:
    """A ``conflict_group`` referenced by a wave item but never declared via
    ``--conflict-group`` must be rejected before the plan is written — not
    silently persisted with ``is_valid: false``.
    """
    mock_operation = Mock(return_value={"milestone_number": 10, "wave_count": 1, "is_valid": False})
    monkeypatch.setattr(dispatch.operations, "dispatch_create_plan", mock_operation)
    result = _runner.invoke(
        app,
        [
            "dispatch",
            "create-plan",
            "--milestone-number",
            "10",
            "--milestone-title",
            "Milestone",
            "--integration-branch",
            "main",
            "--wave-item",
            "wave=1;issue=101;title=Feature A;priority=P1;conflict_group=9",
        ],
    )
    assert result.exit_code != 0
    assert "conflict_group id(s) [9]" in result.stderr
    mock_operation.assert_not_called()


@pytest.mark.parametrize(
    ("command", "operation", "args", "kwargs", "payload"),
    [
        (
            "register",
            "artifact_register",
            [
                "--item-id",
                "42",
                "--artifact-type",
                "research",
                "--artifact-id",
                "plan/research.md",
                "--status",
                "current",
                "--agent",
                "worker",
                "--content",
                "# Research",
            ],
            {
                "item_id": 42,
                "artifact_type": "research",
                "artifact_id": "plan/research.md",
                "status": "current",
                "agent": "worker",
                "content": "# Research",
            },
            {"registered": True},
        ),
        (
            "list",
            "artifact_list",
            ["--item-id", "42", "--artifact-type", "research"],
            {"item_id": 42, "artifact_type": "research"},
            {"artifacts": [], "count": 0},
        ),
        (
            "get",
            "artifact_get",
            ["--item-id", "42", "--artifact-type", "research", "--artifact-id", "plan/research.md"],
            {"item_id": 42, "artifact_type": "research", "artifact_id": "plan/research.md"},
            {"artifacts": [], "count": 0},
        ),
        (
            "read",
            "artifact_read",
            ["--item-id", "42", "--artifact-type", "research", "--artifact-id", "plan/research.md"],
            {"item_id": 42, "artifact_type": "research", "artifact_id": "plan/research.md"},
            {"artifact_type": "research", "path": "plan/research.md", "content": "# Research", "status": "current"},
        ),
    ],
)
def test_artifact_cli_forwards_named_options(
    monkeypatch: pytest.MonkeyPatch,
    command: str,
    operation: str,
    args: list[str],
    kwargs: dict[str, Any],
    payload: dict[str, Any],
) -> None:
    """A numeric ``--item-id`` is coerced to ``int`` before reaching ``dh_core.operations``.

    GitHub/GitLab artifact providers reject a ``str`` item ID via
    ``backlog_core.artifact_provider._require_int_item_id`` — including a
    numeric one such as ``"42"``. ``sam_schema.cli_inputs.parse_item_id``
    performs the coercion at the CLI boundary so every artifact subcommand
    reaches the provider with the correct type.
    """
    mock_operation = Mock(return_value=payload)
    monkeypatch.setattr(artifacts.operations, operation, mock_operation)
    result = _runner.invoke(app, ["artifact", command, *args])
    _assert_compact_result(result, payload)
    mock_operation.assert_called_once_with(**kwargs)


@pytest.mark.parametrize(
    ("command", "operation", "args", "kwargs", "payload"),
    [
        (
            "register",
            "artifact_register",
            [
                "--item-id",
                "bd-a3f8",
                "--artifact-type",
                "research",
                "--artifact-id",
                "plan/research.md",
                "--content",
                "# Research",
            ],
            {
                "item_id": "bd-a3f8",
                "artifact_type": "research",
                "artifact_id": "plan/research.md",
                "status": "current",
                "agent": "",
                "content": "# Research",
            },
            {"registered": True},
        ),
        (
            "list",
            "artifact_list",
            ["--item-id", "bd-a3f8", "--artifact-type", "research"],
            {"item_id": "bd-a3f8", "artifact_type": "research"},
            {"artifacts": [], "count": 0},
        ),
        (
            "get",
            "artifact_get",
            ["--item-id", "bd-a3f8", "--artifact-type", "research", "--artifact-id", "plan/research.md"],
            {"item_id": "bd-a3f8", "artifact_type": "research", "artifact_id": "plan/research.md"},
            {"artifacts": [], "count": 0},
        ),
        (
            "read",
            "artifact_read",
            ["--item-id", "bd-a3f8", "--artifact-type", "research", "--artifact-id", "plan/research.md"],
            {"item_id": "bd-a3f8", "artifact_type": "research", "artifact_id": "plan/research.md"},
            {"artifact_type": "research", "path": "plan/research.md", "content": "# Research", "status": "current"},
        ),
    ],
)
def test_artifact_cli_preserves_nonnumeric_item_id(
    monkeypatch: pytest.MonkeyPatch,
    command: str,
    operation: str,
    args: list[str],
    kwargs: dict[str, Any],
    payload: dict[str, Any],
) -> None:
    """A non-digit ``--item-id`` (Beads/Linear-style) is forwarded unchanged as ``str``.

    Only digit-only strings are coerced to ``int`` — opaque string identifiers
    used by the Beads and Linear backends must reach ``dh_core.operations``
    exactly as given.
    """
    mock_operation = Mock(return_value=payload)
    monkeypatch.setattr(artifacts.operations, operation, mock_operation)
    result = _runner.invoke(app, ["artifact", command, *args])
    _assert_compact_result(result, payload)
    mock_operation.assert_called_once_with(**kwargs)


def test_artifact_cli_requires_content(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_operation = Mock(return_value={"registered": True})
    monkeypatch.setattr(artifacts.operations, "artifact_register", mock_operation)

    result = _runner.invoke(
        app, ["artifact", "register", "--item-id", "42", "--artifact-type", "research", "--artifact-id", "plan/r.md"]
    )

    assert result.exit_code != 0
    mock_operation.assert_not_called()


def test_artifact_cli_has_no_migrate_command() -> None:
    result = _runner.invoke(app, ["artifact", "migrate"])
    assert result.exit_code != 0
    assert "No such command 'migrate'" in result.stderr


def test_forwarding_diagnostics_are_stderr_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        dispatch.operations,
        "dispatch_wave_status",
        Mock(return_value={"status": "pending", "messages": ["using mocked state"], "warnings": ["demo warning"]}),
    )
    result = _runner.invoke(app, ["dispatch", "wave-status", "--milestone-number", "10", "--wave-number", "1"])
    assert result.exit_code == 0
    assert json.loads(result.stdout) == {
        "status": "pending",
        "messages": ["using mocked state"],
        "warnings": ["demo warning"],
    }
    assert "using mocked state" in result.stderr
    assert "demo warning" in result.stderr
    assert ": " not in result.stdout
    assert ", " not in result.stdout
