"""Parity tests: every operation must produce identical output through CLI and MCP paths.

Each test calls the same operation through both frontends and asserts
identical structured output. This is the primary validation gate for
the unified backend extraction.

Strategy:
  - CLI path: subprocess `uv run sam <group> <command>` (JSON is the default)
  - MCP path: call the internal server function directly with a test backend
  - Both paths should delegate to the same dh_core.operations function.
  - Once delegation is in place, parity is structural — both call the same
    function with the same arguments. These tests verify that delegation
    produces matching output.

Tests are added incrementally as operations are extracted to dh_core.operations.

See also ``tests/test_cli_active_task.py`` for the ``active-task`` command
group (T-P5-ACTIVE-TASK): it covers CLI/MCP shared-context-store parity plus
CLI-only concerns (backend selection via CONTEXTBACKEND, clean error on a bad
backend name). T-P5-PARITY will fold per-operation parity into this file.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

# Ensure plugin root is on sys.path so dh_core resolves.
_plugin_root = Path(__file__).resolve().parent.parent
if str(_plugin_root) not in sys.path:
    sys.path.insert(0, str(_plugin_root))


def _get_project_slug() -> str:
    """Derive the project slug the CLI will compute from the git root."""
    import dh_paths

    project_root = dh_paths.infer_project_root()
    return dh_paths.compute_slug(project_root)


def run_cli(args: list[str], *, timeout: int = 30, env: dict[str, str] | None = None) -> dict[str, Any]:
    """Run `uv run sam <args>` and return parsed JSON output.

    Args:
        args: CLI arguments after `sam` (e.g. ["plan", "list", "--limit", "1"]).
        timeout: Maximum seconds to wait for the subprocess.
        env: Optional environment variable overrides merged onto os.environ.

    Returns:
        Parsed JSON dict from stdout.

    Raises:
        subprocess.TimeoutExpired: If the CLI does not finish in time.
        json.JSONDecodeError: If stdout is not valid JSON.
        RuntimeError: If the CLI exits with a non-zero code.
    """
    run_env = os.environ.copy()
    if env:
        run_env.update(env)
    result = subprocess.run(
        ["uv", "run", "sam", *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=_plugin_root,
        env=run_env,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"CLI exited {result.returncode}: {result.stderr[:500]}")
    return json.loads(result.stdout)


@pytest.fixture
def dh_state_home(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    """Provide an isolated DH_STATE_HOME for the CLI subprocess.

    Returns a tuple of (state_home_path, env_overrides) so tests can pass
    the env dict to run_cli() explicitly instead of mutating os.environ.

    The CLI derives the project slug from the git root, not cwd. We create
    the plan dir under the git-root-derived slug so the CLI finds it.
    """
    state_home = tmp_path / "dh_state"
    slug = _get_project_slug()
    plan_dir = state_home / "projects" / slug / "plan"
    plan_dir.mkdir(parents=True, exist_ok=True)
    env = {"DH_STATE_HOME": str(state_home)}
    return state_home, env


class TestParityInfrastructure:
    """Verify the test harness itself works before adding operation tests."""

    def test_cli_plan_list_returns_json(self, dh_state_home: tuple[Path, dict[str, str]]) -> None:
        """The grouped plan-list CLI command returns an envelope with items."""
        _, env = dh_state_home
        result = run_cli(["plan", "list", "--limit", "1"], env=env)
        # list_plans returns an envelope {"items": [...], "count": N, "total": N}.
        assert isinstance(result, dict)
        assert "items" in result

    def test_dh_core_operations_importable(self) -> None:
        """The unified operations layer must be importable."""
        import dh_core.operations

        assert dh_core.operations is not None

    def test_dh_core_protocols_importable(self) -> None:
        """The backend protocol module must be importable."""
        import dh_core.protocols

        assert dh_core.protocols is not None

    def test_dh_core_protocols_re_exports_task_backend(self) -> None:
        """dh_core.protocols must re-export TaskBackend for Phase 1 typing."""
        from dh_core.protocols import TaskBackend

        assert TaskBackend is not None
