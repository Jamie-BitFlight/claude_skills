"""Per-operation CLI/MCP parity tests (T-P5-PARITY).

Proves the same logical operation through both transports produces equivalent
results.  The structural parity (both delegate to ``dh_core.operations``) is
already proven by ``test_server_operation_boundary.py``; these tests verify the
runtime pattern works end-to-end against a shared state directory.

Covered operations:
- Backlog list (CLI adds item, both list it)
- Query filter (both filter by the same key and get the same results)

Plan CRUD parity tests use explicit plan_dir to bypass the config singleton
and issue=None to skip Gist write-through. The network guard in conftest.py
forces GistTaskLayer to fall back to local cache for read/status/list.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import pytest

_plugin_root = Path(__file__).resolve().parent.parent
if str(_plugin_root) not in sys.path:
    sys.path.insert(0, str(_plugin_root))

import backlog_core.models as _bc_models
from backlog_core.backend_protocol import reset_config as _reset_bp_config, set_config as _set_bp_config
from backlog_core.backend_types import BacklogConfig as _BPBacklogConfig
from backlog_core.backends.memory_backend import InMemoryBackend
from backlog_core.models import BacklogConfig as _ModelsBacklogConfig
from backlog_core.server import mcp as _backlog_mcp
from sam_schema.core.backends.local_context_backend import LocalContextBackend
from sam_schema.core.context_config import ContextConfig, get_context_config, reset_context_config, set_context_config
from sam_schema.server import mcp as _sam_mcp

from tests.helpers import call_mcp_tool


def _run_cli(args: list[str], env: dict[str, str]) -> dict[str, Any]:
    """Run ``uv run sam <args> --format json`` and return parsed JSON.

    Args:
        args: CLI arguments after ``sam``.
        env: Environment variable overrides.

    Returns:
        Parsed JSON dict from stdout.

    Raises:
        RuntimeError: If the CLI exits with a non-zero code.
    """
    import json
    import subprocess

    result = subprocess.run(
        ["uv", "run", "sam", *args, "--format", "json"],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(_plugin_root),
        env=env,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"CLI exited {result.returncode}: {result.stderr[:500]}")
    return json.loads(result.stdout)


@pytest.fixture
def dh_env(tmp_path: Path):
    """Provide an isolated DH_STATE_HOME with memory backends for both transports.

    The CLI subprocess reads BACKLOG_BACKEND/TASKBACKEND/CONTEXTBACKEND env vars.
    The in-process MCP calls read the respective singletons, so we patch them to
    appropriate backends explicitly.  Both transports share the same state
    directory so file-based operations see the same state.
    """
    import dh_paths

    real_root = dh_paths.infer_project_root()
    bd = dh_paths.backlog_dir(project_root=real_root)
    bd.mkdir(parents=True, exist_ok=True)

    # In-process: force the backlog backend to InMemoryBackend so MCP calls
    # don't auto-init a GitHubBackend and hit the network.
    _set_bp_config(_BPBacklogConfig(backend=InMemoryBackend()))
    existing = _bc_models._config
    saved_bc_config = existing
    _bc_models._config = _ModelsBacklogConfig(
        repo_root=real_root, backlog_dir=bd, default_repo=existing.default_repo if existing is not None else ""
    )

    dh_state = str(tmp_path / "dh_state")
    env = os.environ.copy()
    env.update({
        "DH_STATE_HOME": dh_state,
        "BACKLOG_BACKEND": "memory",
        "TASKBACKEND": "memory",
        "CONTEXTBACKEND": "local",
        "GITHUB_TOKEN": "",
        "GH_TOKEN": "",
    })

    # In-process: point dh_paths and context config at the test state home so
    # MCP calls share the same file-based context store as the CLI subprocess.
    saved_dh_home = os.environ.get("DH_STATE_HOME")
    os.environ["DH_STATE_HOME"] = dh_state
    saved_ctx_config = None
    try:
        saved_ctx_config = get_context_config()
    except RuntimeError:
        pass
    set_context_config(ContextConfig(backend=LocalContextBackend()))

    yield env

    # Teardown: reset singletons so downstream tests get fresh config
    reset_context_config()
    if saved_ctx_config is not None:
        set_context_config(saved_ctx_config)
    if saved_dh_home is not None:
        os.environ["DH_STATE_HOME"] = saved_dh_home
    else:
        os.environ.pop("DH_STATE_HOME", None)
    _reset_bp_config()
    _bc_models._config = saved_bc_config


# ---------------------------------------------------------------------------
# Backlog list parity
# ---------------------------------------------------------------------------


async def test_backlog_list_parity(dh_env: dict[str, str]) -> None:
    """A backlog item added via CLI is visible through both list transports."""
    _run_cli(
        ["backlog-add", "Parity Item", "--description", "test", "--priority", "P1", "--format", "json"], env=dh_env
    )

    cli_list = _run_cli(["backlog-list", "--format", "json"], env=dh_env)
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
    _run_cli(
        ["backlog-add", "Filter Item", "--description", "test", "--priority", "P1", "--format", "json"], env=dh_env
    )

    cli_filtered = _run_cli(["backlog-list", "--filter", "section=P1", "--format", "json"], env=dh_env)
    mcp_filtered = await call_mcp_tool(_backlog_mcp, "backlog_list", {"filter_by_key": {"section": "P1"}})

    cli_titles = {item["title"] for item in cli_filtered.get("items", [])}
    mcp_titles = {item["title"] for item in mcp_filtered.get("items", [])}
    assert "Filter Item" in cli_titles
    assert "Filter Item" in mcp_titles


async def test_query_filter_absent_key_returns_empty(dh_env: dict[str, str]) -> None:
    """Filtering by a key no item carries returns empty, not an error."""
    _run_cli(
        ["backlog-add", "No Match Item", "--description", "test", "--priority", "P1", "--format", "json"], env=dh_env
    )

    cli_filtered = _run_cli(["backlog-list", "--filter", "nonexistent_key=xyz", "--format", "json"], env=dh_env)
    mcp_filtered = await call_mcp_tool(_backlog_mcp, "backlog_list", {"filter_by_key": {"nonexistent_key": "xyz"}})

    assert cli_filtered.get("count", 0) == 0
    assert len(mcp_filtered.get("items", [])) == 0


# ---------------------------------------------------------------------------
# Backlog CRUD parity (add, view, update, close, resolve, groom)
# ---------------------------------------------------------------------------


def _setup_gate_token(dh_state_home: str, session_id: str = "test-session", token: str = "abc123") -> str:
    """Create a gate token file and return the full token string for MCP backlog_add."""
    gate_dir = Path(dh_state_home) / "sessions" / session_id
    gate_dir.mkdir(parents=True, exist_ok=True)
    full_token = f"{session_id}:{token}"
    (gate_dir / ".gate-token").write_text(full_token)
    return full_token


async def test_backlog_add_parity(dh_env: dict[str, str]) -> None:
    """Backlog add via CLI and MCP both create items with equivalent metadata."""
    gate_token = _setup_gate_token(dh_env["DH_STATE_HOME"])

    cli_result = _run_cli(
        ["backlog-add", "Parity CLI Add", "--description", "cli test", "--priority", "P1"], env=dh_env
    )
    mcp_result = await call_mcp_tool(
        _backlog_mcp, "backlog_add",
        {"title": "Parity MCP Add", "priority": "P1", "description": "mcp test", "gate_token": gate_token, "force": True},
    )

    assert cli_result["title"] == "Parity CLI Add"
    assert cli_result["priority"] == "P1"
    assert mcp_result["title"] == "Parity MCP Add"
    assert mcp_result["priority"] == "P1"

    # Both items visible via list
    cli_list = _run_cli(["backlog-list"], env=dh_env)
    titles = {item["title"] for item in cli_list.get("items", [])}
    assert "Parity CLI Add" in titles
    assert "Parity MCP Add" in titles


async def test_backlog_view_parity(dh_env: dict[str, str]) -> None:
    """Backlog item viewed through CLI and MCP returns the same identity fields."""
    _run_cli(
        ["backlog-add", "Parity View Item", "--description", "view test", "--priority", "P1"], env=dh_env
    )

    cli_view = _run_cli(["backlog-view", "Parity View Item"], env=dh_env)
    mcp_view = await call_mcp_tool(
        _backlog_mcp, "backlog_view",
        {"selector": "Parity View Item", "summary": False, "include_content": True},
    )

    assert cli_view.get("title") == "Parity View Item"
    assert mcp_view.get("title") == "Parity View Item"
    assert cli_view.get("priority") == mcp_view.get("priority")


async def test_backlog_update_parity(dh_env: dict[str, str]) -> None:
    """Backlog update through CLI and MCP both change the title correctly."""
    _run_cli(
        ["backlog-add", "Parity Update CLI", "--description", "update test", "--priority", "P1"], env=dh_env
    )
    _run_cli(
        ["backlog-add", "Parity Update MCP", "--description", "update test", "--priority", "P1", "--force"], env=dh_env
    )

    # CLI update
    cli_update = _run_cli(
        ["backlog-update", "Parity Update CLI", "--title", "CLI Updated Title"], env=dh_env
    )
    assert "CLI Updated Title" in str(cli_update)

    # MCP update
    mcp_update = await call_mcp_tool(
        _backlog_mcp, "backlog_update",
        {"selector": "Parity Update MCP", "title": "MCP Updated Title"},
    )
    assert "MCP Updated Title" in str(mcp_update)

    # Verify via list
    cli_list = _run_cli(["backlog-list"], env=dh_env)
    titles = {item["title"] for item in cli_list.get("items", [])}
    assert "CLI Updated Title" in titles
    assert "MCP Updated Title" in titles


async def test_backlog_close_parity(dh_env: dict[str, str]) -> None:
    """Backlog close through CLI and MCP both close items correctly."""
    _run_cli(
        ["backlog-add", "Parity Close CLI", "--description", "close test", "--priority", "P1"], env=dh_env
    )
    _run_cli(
        ["backlog-add", "Parity Close MCP", "--description", "close test", "--priority", "P1", "--force"], env=dh_env
    )

    # CLI close
    cli_close = _run_cli(
        ["backlog-close", "Parity Close CLI", "--reason", "duplicate"], env=dh_env
    )
    assert cli_close.get("title") == "Parity Close CLI"
    assert cli_close.get("closed") is True

    # MCP close
    mcp_close = await call_mcp_tool(
        _backlog_mcp, "backlog_close",
        {"selector": "Parity Close MCP", "reason": "duplicate"},
    )
    assert mcp_close.get("title") == "Parity Close MCP"
    assert mcp_close.get("closed") is True


async def test_backlog_resolve_parity(dh_env: dict[str, str]) -> None:
    """CLI backlog resolve and MCP backlog_close both complete items."""
    _run_cli(
        ["backlog-add", "Parity Resolve CLI", "--description", "resolve test", "--priority", "P1"], env=dh_env
    )
    _run_cli(
        ["backlog-add", "Parity Close MCP2", "--description", "close test", "--priority", "P1", "--force"], env=dh_env
    )

    # CLI resolve
    cli_resolve = _run_cli(
        ["backlog-resolve", "Parity Resolve CLI", "--summary", "Done"], env=dh_env
    )
    assert cli_resolve.get("title") == "Parity Resolve CLI"
    assert cli_resolve.get("resolved") is True

    # MCP close
    mcp_close = await call_mcp_tool(
        _backlog_mcp, "backlog_close",
        {"selector": "Parity Close MCP2", "reason": "duplicate"},
    )
    assert mcp_close.get("title") == "Parity Close MCP2"
    assert mcp_close.get("closed") is True


async def test_backlog_groom_parity(dh_env: dict[str, str]) -> None:
    """Both transports generate identical groomed content for the same section."""
    _run_cli(
        ["backlog-add", "Parity Groom CLI", "--description", "groom test", "--priority", "P1"], env=dh_env
    )
    _run_cli(
        ["backlog-add", "Parity Groom MCP", "--description", "groom test", "--priority", "P1", "--force"], env=dh_env
    )

    GROOM_CONTENT = "## Analysis\n\nThis item needs investigation."

    # CLI groom
    cli_groom = _run_cli(
        ["backlog-groom", "Parity Groom CLI", "--section", "Analysis", "--content", GROOM_CONTENT], env=dh_env
    )
    assert cli_groom.get("title") == "Parity Groom CLI"

    # MCP groom
    mcp_groom = await call_mcp_tool(
        _backlog_mcp, "backlog_groom",
        {"selector": "Parity Groom MCP", "section": "Analysis", "content": GROOM_CONTENT},
    )
    assert mcp_groom.get("title") == "Parity Groom MCP"

    # Verify both items have groomed content via view
    cli_view = _run_cli(["backlog-view", "Parity Groom CLI", "--section", "Analysis"], env=dh_env)
    mcp_view = await call_mcp_tool(
        _backlog_mcp, "backlog_view",
        {"selector": "Parity Groom MCP", "summary": False, "section": "Analysis"},
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
    cli_result = _run_cli(
        ["create", "cli-plan", "--goal", "CLI goal", "--plan-dir", plan_dir, "--format", "json"], env=dh_env
    )
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
    cli_read = _run_cli(["read", mcp_plan_id, "--plan-dir", plan_dir, "--format", "json"], env=dh_env)
    assert cli_read["plan"]["feature"] == "mcp-plan"
    assert cli_read["plan"]["goal"] == "MCP goal"


async def test_plan_status_parity(dh_env: dict[str, str], tmp_path: Path) -> None:
    """Plan status is the same dict through both transports."""
    plan_dir = str(tmp_path / "plan")
    Path(plan_dir).mkdir(parents=True, exist_ok=True)

    cli_result = _run_cli(
        ["create", "status-plan", "--goal", "Status goal", "--plan-dir", plan_dir, "--format", "json"], env=dh_env
    )
    plan_id = cli_result["plan_id"]

    cli_status = _run_cli(["status", plan_id, "--plan-dir", plan_dir, "--format", "json"], env=dh_env)
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
        _run_cli(["create", slug, "--goal", f"Goal {slug}", "--plan-dir", plan_dir, "--format", "json"], env=dh_env)

    cli_list = _run_cli(["list", "--plan-dir", plan_dir, "--format", "json"], env=dh_env)
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
    import json

    plan_dir = str(tmp_path / "plan")
    Path(plan_dir).mkdir(parents=True, exist_ok=True)

    cli_create = _run_cli(
        ["create", "ready-parity", "--goal", "Ready parity goal", "--plan-dir", plan_dir, "--format", "json"],
        env=dh_env,
    )
    plan_id = cli_create["plan_id"]
    _run_cli(
        ["append-task", plan_id, "--plan-dir", plan_dir, "--task-json", json.dumps(_TASK_DEF), "--format", "json"],
        env=dh_env,
    )
    _run_cli(["finalize", plan_id, "--plan-dir", plan_dir, "--format", "json"], env=dh_env)

    cli_ready = _run_cli(["ready", plan_id, "--plan-dir", plan_dir, "--format", "json"], env=dh_env)
    mcp_ready = await call_mcp_tool(
        _sam_mcp, "sam_plan", {"config": {"action": "ready"}, "plan": plan_id, "plan_dir": plan_dir}
    )
    assert cli_ready["feature"] == mcp_ready["feature"]
    assert cli_ready["count"] == mcp_ready["count"] == 1


async def test_plan_update_parity(dh_env: dict[str, str], tmp_path: Path) -> None:
    """Plan update through CLI and MCP produces equivalent field changes."""
    import json

    plan_dir = str(tmp_path / "plan")
    Path(plan_dir).mkdir(parents=True, exist_ok=True)

    plan_a = plan_b = None
    for slug in ["update-a", "update-b"]:
        result = _run_cli(
            ["create", slug, "--goal", "Update goal", "--plan-dir", plan_dir, "--format", "json"], env=dh_env
        )
        pid = result["plan_id"]
        _run_cli(
            ["append-task", pid, "--plan-dir", plan_dir, "--task-json", json.dumps(_TASK_DEF), "--format", "json"],
            env=dh_env,
        )
        _run_cli(["finalize", pid, "--plan-dir", plan_dir, "--format", "json"], env=dh_env)
        if slug == "update-a":
            plan_a = pid
        else:
            plan_b = pid
    assert plan_a and plan_b

    # CLI update plan_a
    cli_update = _run_cli(
        ["update", plan_a, "--plan-dir", plan_dir, "--set", "goal=CLI Updated", "--format", "json"], env=dh_env
    )
    assert cli_update["updated"] is True

    # MCP update plan_b
    mcp_update = await call_mcp_tool(
        _sam_mcp, "sam_plan",
        {"config": {"action": "update", "set_fields_json": {"goal": "MCP Updated"}}, "plan": plan_b, "plan_dir": plan_dir},
    )
    assert mcp_update["updated"] is True

    # Read both through CLI to verify
    cli_read_a = _run_cli(["read", plan_a, "--plan-dir", plan_dir, "--format", "json"], env=dh_env)
    cli_read_b = _run_cli(["read", plan_b, "--plan-dir", plan_dir, "--format", "json"], env=dh_env)
    assert cli_read_a["plan"]["goal"] == "CLI Updated"
    assert cli_read_b["plan"]["goal"] == "MCP Updated"


async def test_plan_append_task_parity(dh_env: dict[str, str], tmp_path: Path) -> None:
    """Task appended via CLI and MCP produces equivalent results."""
    import json

    plan_dir = str(tmp_path / "plan")
    Path(plan_dir).mkdir(parents=True, exist_ok=True)

    plan_a = plan_b = None
    for slug in ["append-a", "append-b"]:
        result = _run_cli(
            ["create", slug, "--goal", "Append goal", "--plan-dir", plan_dir, "--format", "json"], env=dh_env
        )
        if slug == "append-a":
            plan_a = result["plan_id"]
        else:
            plan_b = result["plan_id"]
    assert plan_a and plan_b

    # CLI append to plan_a
    cli_append = _run_cli(
        ["append-task", plan_a, "--plan-dir", plan_dir, "--task-json", json.dumps(_TASK_DEF), "--format", "json"],
        env=dh_env,
    )
    assert cli_append["appended"] is True
    assert cli_append["task_id"] == "T01"

    # MCP append to plan_b
    mcp_append = await call_mcp_tool(
        _sam_mcp, "sam_plan",
        {"config": {"action": "append_task", "task": _TASK_DEF}, "plan": plan_b, "plan_dir": plan_dir},
    )
    assert mcp_append["appended"] is True
    assert mcp_append["task_id"] == "T01"

    # Finalize both and read to verify
    _run_cli(["finalize", plan_a, "--plan-dir", plan_dir, "--format", "json"], env=dh_env)
    _run_cli(["finalize", plan_b, "--plan-dir", plan_dir, "--format", "json"], env=dh_env)

    cli_read_a = _run_cli(["read", plan_a, "--plan-dir", plan_dir, "--format", "json"], env=dh_env)
    cli_read_b = _run_cli(["read", plan_b, "--plan-dir", plan_dir, "--format", "json"], env=dh_env)
    assert len(cli_read_a["plan"]["tasks"]) == len(cli_read_b["plan"]["tasks"]) == 1


async def test_plan_finalize_parity(dh_env: dict[str, str], tmp_path: Path) -> None:
    """Plan finalize through CLI and MCP produces equivalent results."""
    import json

    plan_dir = str(tmp_path / "plan")
    Path(plan_dir).mkdir(parents=True, exist_ok=True)

    plan_a = plan_b = None
    for slug in ["finalize-a", "finalize-b"]:
        result = _run_cli(
            ["create", slug, "--goal", "Finalize goal", "--plan-dir", plan_dir, "--format", "json"], env=dh_env
        )
        pid = result["plan_id"]
        _run_cli(
            ["append-task", pid, "--plan-dir", plan_dir, "--task-json", json.dumps(_TASK_DEF), "--format", "json"],
            env=dh_env,
        )
        if slug == "finalize-a":
            plan_a = pid
        else:
            plan_b = pid
    assert plan_a and plan_b

    # CLI finalize plan_a
    cli_finalize = _run_cli(
        ["finalize", plan_a, "--plan-dir", plan_dir, "--format", "json"], env=dh_env
    )
    assert cli_finalize["finalized"] is True
    assert cli_finalize["state"] == "ready"

    # MCP finalize plan_b
    mcp_finalize = await call_mcp_tool(
        _sam_mcp, "sam_plan",
        {"config": {"action": "finalize"}, "plan": plan_b, "plan_dir": plan_dir},
    )
    assert mcp_finalize["finalized"] is True
    assert mcp_finalize["state"] == "ready"

    # Read both to verify state
    cli_read_a = _run_cli(["read", plan_a, "--plan-dir", plan_dir, "--format", "json"], env=dh_env)
    cli_read_b = _run_cli(["read", plan_b, "--plan-dir", plan_dir, "--format", "json"], env=dh_env)
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


async def test_task_read_parity(dh_env: dict[str, str], tmp_path: Path) -> None:
    """Task read through CLI and MCP returns the same task data."""
    import json

    plan_dir = str(tmp_path / "plan")
    Path(plan_dir).mkdir(parents=True, exist_ok=True)

    cli_create = _run_cli(
        ["create", "read-task", "--goal", "Read goal", "--plan-dir", plan_dir, "--format", "json"], env=dh_env
    )
    plan_id = cli_create["plan_id"]
    _run_cli(
        ["append-task", plan_id, "--plan-dir", plan_dir, "--task-json", json.dumps(_TASK_DEF), "--format", "json"],
        env=dh_env,
    )
    _run_cli(["finalize", plan_id, "--plan-dir", plan_dir, "--format", "json"], env=dh_env)

    cli_read = _run_cli(["read", f"{plan_id}/T01", "--plan-dir", plan_dir, "--format", "json"], env=dh_env)
    mcp_read = await call_mcp_tool(
        _sam_mcp, "sam_task", {"plan": plan_id, "task": "T01", "config": {"action": "read"}, "plan_dir": plan_dir}
    )
    assert cli_read["task"]["id"] == mcp_read["task"]["id"] == "T01"
    assert cli_read["task"]["title"] == mcp_read["task"]["title"] == "Parity Task"
    assert cli_read["task"]["status"] == mcp_read["task"]["status"]


async def test_task_claim_parity(dh_env: dict[str, str], tmp_path: Path) -> None:
    """Claim via CLI and MCP both produce claimed=true with a started timestamp."""
    import json

    plan_dir = str(tmp_path / "plan")
    Path(plan_dir).mkdir(parents=True, exist_ok=True)

    cli_create = _run_cli(
        ["create", "claim-task", "--goal", "Claim goal", "--plan-dir", plan_dir, "--format", "json"], env=dh_env
    )
    plan_id = cli_create["plan_id"]
    _run_cli(
        ["append-task", plan_id, "--plan-dir", plan_dir, "--task-json", json.dumps(_TASK_DEF), "--format", "json"],
        env=dh_env,
    )
    _run_cli(["finalize", plan_id, "--plan-dir", plan_dir, "--format", "json"], env=dh_env)

    cli_claim = _run_cli(["claim", f"{plan_id}/T01", "--plan-dir", plan_dir, "--format", "json"], env=dh_env)
    assert cli_claim["claimed"] is True
    assert cli_claim["task_id"] == "T01"
    assert cli_claim.get("started") is not None

    # Reset task to not-started for MCP claim (same backend, need fresh task).
    TASK_DEF2 = dict(_TASK_DEF, id="T02")
    _run_cli(
        ["append-task", plan_id, "--plan-dir", plan_dir, "--task-json", json.dumps(TASK_DEF2), "--format", "json"],
        env=dh_env,
    )
    _run_cli(["finalize", plan_id, "--plan-dir", plan_dir, "--format", "json"], env=dh_env)

    mcp_claim = await call_mcp_tool(
        _sam_mcp, "sam_task", {"plan": plan_id, "task": "T02", "config": {"action": "claim"}, "plan_dir": plan_dir}
    )
    assert mcp_claim["claimed"] is True
    assert mcp_claim["task_id"] == "T02"
    assert mcp_claim.get("started") is not None


async def test_task_state_parity(dh_env: dict[str, str], tmp_path: Path) -> None:
    """Task status changed via CLI and MCP is visible through both reads."""
    import json
    import subprocess

    plan_dir = str(tmp_path / "plan")
    Path(plan_dir).mkdir(parents=True, exist_ok=True)

    cli_create = _run_cli(
        ["create", "state-task", "--goal", "State goal", "--plan-dir", plan_dir, "--format", "json"], env=dh_env
    )
    plan_id = cli_create["plan_id"]
    _run_cli(
        ["append-task", plan_id, "--plan-dir", plan_dir, "--task-json", json.dumps(_TASK_DEF), "--format", "json"],
        env=dh_env,
    )
    _run_cli(["finalize", plan_id, "--plan-dir", plan_dir, "--format", "json"], env=dh_env)

    # CLI state command (no --format json — just prints status line).
    result = subprocess.run(
        ["uv", "run", "sam", "state", f"{plan_id}/T01", "complete", "--plan-dir", plan_dir],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(_plugin_root),
        env=dh_env,
        check=False,
    )
    assert result.returncode == 0, f"CLI state failed: {result.stderr[:500]}"

    cli_read = _run_cli(["read", f"{plan_id}/T01", "--plan-dir", plan_dir, "--format", "json"], env=dh_env)
    mcp_read = await call_mcp_tool(
        _sam_mcp, "sam_task", {"plan": plan_id, "task": "T01", "config": {"action": "read"}, "plan_dir": plan_dir}
    )
    assert cli_read["task"]["status"] == "complete"
    assert mcp_read["task"]["status"] == "complete"


async def test_task_update_parity(dh_env: dict[str, str], tmp_path: Path) -> None:
    """Task field updated via CLI --set is visible through both read transports."""
    import json

    plan_dir = str(tmp_path / "plan")
    Path(plan_dir).mkdir(parents=True, exist_ok=True)

    cli_create = _run_cli(
        ["create", "update-task", "--goal", "Update goal", "--plan-dir", plan_dir, "--format", "json"], env=dh_env
    )
    plan_id = cli_create["plan_id"]
    _run_cli(
        ["append-task", plan_id, "--plan-dir", plan_dir, "--task-json", json.dumps(_TASK_DEF), "--format", "json"],
        env=dh_env,
    )
    _run_cli(["finalize", plan_id, "--plan-dir", plan_dir, "--format", "json"], env=dh_env)

    # CLI update --set
    _run_cli(
        ["update", f"{plan_id}/T01", "--plan-dir", plan_dir, "--set", "priority=5", "--format", "json"], env=dh_env
    )

    cli_read = _run_cli(["read", f"{plan_id}/T01", "--plan-dir", plan_dir, "--format", "json"], env=dh_env)
    mcp_read = await call_mcp_tool(
        _sam_mcp, "sam_task", {"plan": plan_id, "task": "T01", "config": {"action": "read"}, "plan_dir": plan_dir}
    )
    assert cli_read["task"]["priority"] == 5
    assert mcp_read["task"]["priority"] == 5


# ---------------------------------------------------------------------------
# Active-task parity
# ---------------------------------------------------------------------------


async def test_active_task_get_parity(dh_env: dict[str, str]) -> None:
    """CLI ``active-task get`` and MCP ``sam_active_task(action='get')`` return the same result."""
    # Both report None when nothing is set
    cli_get = _run_cli(["active-task", "get", "--format", "json"], env=dh_env)
    mcp_get = await call_mcp_tool(_sam_mcp, "sam_active_task", {"config": {"action": "get"}})
    assert cli_get["active_task"] is None
    assert mcp_get["active_task"] is None

    # Set via CLI and both read it back
    _run_cli(["active-task", "set", "P1/T3", "--format", "json"], env=dh_env)
    cli_get2 = _run_cli(["active-task", "get", "--format", "json"], env=dh_env)
    mcp_get2 = await call_mcp_tool(_sam_mcp, "sam_active_task", {"config": {"action": "get"}})
    assert cli_get2["active_task"]["plan"] == mcp_get2["active_task"]["plan"]
    assert cli_get2["active_task"]["task"] == mcp_get2["active_task"]["task"]


async def test_active_task_set_parity(dh_env: dict[str, str]) -> None:
    """CLI set → MCP get and MCP set → CLI get produce identical active task context."""
    # CLI sets, MCP reads
    cli_set = _run_cli(["active-task", "set", "P5/T7", "--format", "json"], env=dh_env)
    mcp_get = await call_mcp_tool(_sam_mcp, "sam_active_task", {"config": {"action": "get"}})
    assert mcp_get["active_task"]["plan"] == cli_set["active_task"]["plan"]
    assert mcp_get["active_task"]["task"] == cli_set["active_task"]["task"]

    # MCP sets, CLI reads
    mcp_set = await call_mcp_tool(
        _sam_mcp, "sam_active_task", {"config": {"action": "set", "plan": "P9", "task": "T2"}}
    )
    cli_get = _run_cli(["active-task", "get", "--format", "json"], env=dh_env)
    assert cli_get["active_task"]["plan"] == mcp_set["active_task"]["plan"]
    assert cli_get["active_task"]["task"] == mcp_set["active_task"]["task"]


async def test_active_task_update_parity(dh_env: dict[str, str], tmp_path: Path) -> None:
    """CLI active-task update and MCP sam_active_task update produce equivalent results."""
    import json

    plan_dir = str(tmp_path / "plan")
    Path(plan_dir).mkdir(parents=True, exist_ok=True)

    cli_create = _run_cli(
        ["create", "at-update", "--goal", "AT update goal", "--plan-dir", plan_dir, "--format", "json"], env=dh_env
    )
    plan_id = cli_create["plan_id"]
    _run_cli(
        ["append-task", plan_id, "--plan-dir", plan_dir, "--task-json", json.dumps(_TASK_DEF), "--format", "json"],
        env=dh_env,
    )
    _run_cli(["finalize", plan_id, "--plan-dir", plan_dir, "--format", "json"], env=dh_env)

    # Set active task via MCP (preserves 'T01' prefix that plan file uses)
    await call_mcp_tool(
        _sam_mcp, "sam_active_task",
        {"config": {"action": "set", "plan": plan_id, "task": "T01", "plan_dir": plan_dir}},
    )

    # CLI update
    cli_update = _run_cli(
        ["active-task", "update", "--set-fields-json", json.dumps({"priority": 8}), "--format", "json"], env=dh_env
    )
    assert cli_update["updated"] is True

    # MCP read verifies the update
    mcp_read = await call_mcp_tool(
        _sam_mcp, "sam_task", {"plan": plan_id, "task": "T01", "config": {"action": "read"}, "plan_dir": plan_dir}
    )
    assert mcp_read["task"]["priority"] == 8

    # Reset priority for reverse direction
    _run_cli(
        ["update", f"{plan_id}/T01", "--plan-dir", plan_dir, "--set", "priority=1", "--format", "json"], env=dh_env
    )

    # MCP update
    mcp_update = await call_mcp_tool(
        _sam_mcp, "sam_active_task",
        {"config": {"action": "update", "set_fields_json": {"priority": 9}}},
    )
    assert mcp_update["updated"] is True

    # CLI read verifies
    cli_read = _run_cli(["read", f"{plan_id}/T01", "--plan-dir", plan_dir, "--format", "json"], env=dh_env)
    assert cli_read["task"]["priority"] == 9


async def test_active_task_clear_parity(dh_env: dict[str, str]) -> None:
    """CLI clear → MCP get returns null, and MCP clear → CLI get returns null."""
    # Set via CLI
    _run_cli(["active-task", "set", "P3/T5", "--format", "json"], env=dh_env)

    # CLI clear
    cli_clear = _run_cli(["active-task", "clear", "--format", "json"], env=dh_env)
    assert cli_clear["cleared"] is True

    # MCP get returns null
    mcp_get = await call_mcp_tool(_sam_mcp, "sam_active_task", {"config": {"action": "get"}})
    assert mcp_get["active_task"] is None

    # MCP set, MCP clear, CLI get returns null
    await call_mcp_tool(_sam_mcp, "sam_active_task", {"config": {"action": "set", "plan": "P8", "task": "T4"}})
    mcp_clear = await call_mcp_tool(_sam_mcp, "sam_active_task", {"config": {"action": "clear"}})
    assert mcp_clear["cleared"] is True

    cli_get = _run_cli(["active-task", "get", "--format", "json"], env=dh_env)
    assert cli_get["active_task"] is None
