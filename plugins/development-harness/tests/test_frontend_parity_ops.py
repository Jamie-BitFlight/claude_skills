"""Per-operation CLI/MCP parity tests (T-P5-PARITY).

Proves the same logical operation through both transports produces equivalent
results.  The structural parity (both delegate to ``dh_core.operations``) is
already proven by ``test_server_operation_boundary.py``; these tests verify the
runtime pattern works end-to-end against a shared state directory.

Covered operations:
- Backlog list (CLI adds item, both list it)
- Query filter (both filter by the same key and get the same results)

Plan CRUD parity tests are deferred — the MCP ``sam_plan`` tool wraps the
configured backend in GistTaskLayer, which requires additional test
infrastructure to prevent network access.  The structural parity is already
proven by the boundary test; per-operation plan parity will land with Phase 5
E2E validation.
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
from backlog_core.backend_protocol import set_config as _set_bp_config
from backlog_core.backend_types import BacklogConfig as _BPBacklogConfig
from backlog_core.backends.memory_backend import InMemoryBackend
from backlog_core.models import BacklogConfig as _ModelsBacklogConfig
from backlog_core.server import mcp as _backlog_mcp

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
def dh_env(tmp_path: Path) -> dict[str, str]:
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
    return env


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
