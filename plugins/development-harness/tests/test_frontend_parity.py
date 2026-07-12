"""Parity tests: every operation must produce identical output through CLI and MCP paths.

Each test calls the same operation through both frontends and asserts
identical structured output. This is the primary validation gate for
the unified backend extraction.

Strategy:
  - CLI path: subprocess `uv run sam <cmd> --format json`
  - MCP path: call the MCP tool function directly (imported from server module)
  - Both paths should delegate to the same dh_core.operations function.
  - Once delegation is in place, parity is structural — both call the same
    function with the same arguments. These tests verify that delegation
    produces matching output.

Tests are added incrementally as operations are extracted to dh_core.operations.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator

# Ensure plugin root is on sys.path so dh_core resolves.
_plugin_root = Path(__file__).resolve().parent.parent
if str(_plugin_root) not in sys.path:
    sys.path.insert(0, str(_plugin_root))


def run_cli(args: list[str], *, timeout: int = 30, env: dict[str, str] | None = None) -> dict[str, Any]:
    """Run `uv run sam <args> --format json` and return parsed JSON output.

    Args:
        args: CLI arguments after `sam` (e.g. ["list", "--limit", "1"]).
        timeout: Maximum seconds to wait for the subprocess.
        env: Optional environment variable overrides merged onto os.environ.

    Returns:
        Parsed JSON dict from stdout.

    Raises:
        subprocess.TimeoutExpired: If the CLI does not finish in time.
        json.JSONDecodeError: If stdout is not valid JSON.
        RuntimeError: If the CLI exits with a non-zero code.
    """
    import os

    run_env = os.environ.copy()
    if env:
        run_env.update(env)
    result = subprocess.run(
        ["uv", "run", "sam", *args, "--format", "json"],
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
def dh_state_home(tmp_path: Path) -> Iterator[Path]:
    """Provide an isolated DH_STATE_HOME so the CLI finds a valid plan dir.

    The CLI derives the project slug from the git root, not cwd. We run
    the subprocess from _plugin_root (which is inside the git repo), so
    the slug will be based on the git root path. We create the plan dir
    under the git-root-derived slug so the CLI finds it.
    """
    import os

    import dh_paths

    state_home = tmp_path / "dh_state"
    # Use dh_paths to derive the actual slug the CLI will compute
    project_root = dh_paths.infer_project_root()
    slug = dh_paths.compute_slug(project_root)
    plan_dir = state_home / "projects" / slug / "plan"
    plan_dir.mkdir(parents=True, exist_ok=True)
    os.environ["DH_STATE_HOME"] = str(state_home)
    yield state_home
    os.environ.pop("DH_STATE_HOME", None)


class TestParityInfrastructure:
    """Verify the test harness itself works before adding operation tests."""

    def test_cli_list_returns_json(self, dh_state_home: Path) -> None:
        """The CLI `list` command must return valid JSON with an 'items' key."""
        result = run_cli(["list", "--limit", "1"])
        assert "items" in result
        assert isinstance(result["items"], list)

    def test_dh_core_operations_importable(self) -> None:
        """The unified operations layer must be importable."""
        import dh_core.operations

        assert dh_core.operations is not None

    def test_dh_core_protocols_importable(self) -> None:
        """The backend protocol module must be importable."""
        import dh_core.protocols

        assert dh_core.protocols is not None
