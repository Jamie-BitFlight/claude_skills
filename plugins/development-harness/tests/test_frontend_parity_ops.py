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

    The CLI subprocess reads BACKLOG_BACKEND/TASKBACKEND env vars.  The
    in-process MCP calls read the backlog_core singleton, so we patch it to
    an InMemoryBackend explicitly.  Both transports share the same backlog
    directory (derived from the real git root) so file-based operations
    (add_item, list_items) see the same state.
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

    env = os.environ.copy()
    env.update({
        "DH_STATE_HOME": str(tmp_path / "dh_state"),
        "BACKLOG_BACKEND": "memory",
        "TASKBACKEND": "memory",
        "GITHUB_TOKEN": "",
        "GH_TOKEN": "",
    })
    yield env
    # Teardown: reset the singleton so downstream tests get a fresh config
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
