"""Parity tests: every operation must produce identical output through CLI and MCP paths.

Each test calls the same operation through both frontends and asserts
identical structured output. This is the primary validation gate for
the unified backend extraction.

Strategy:
  - CLI path: subprocess ``uv run <cli.py> <group> <command>`` (compact JSON stdout)
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
import sys
from pathlib import Path
from typing import Any

import pytest

# Ensure plugin root is on sys.path so dh_core resolves.
_plugin_root = Path(__file__).resolve().parent.parent
if str(_plugin_root) not in sys.path:
    sys.path.insert(0, str(_plugin_root))

from tests.helpers import run_cli_subprocess

_CLI_PATH = _plugin_root / "sam_schema" / "cli.py"
_WRAPPER_PATH = _plugin_root / "scripts" / "run_sam_cli.py"
_REPO_ROOT = _plugin_root.parent.parent  # claude_skills repo root (for DH_PROJECT_ROOT in subprocess tests)


def _get_project_slug() -> str:
    """Derive the project slug the CLI will compute from the git root."""
    import dh_paths

    project_root = dh_paths.infer_project_root()
    return dh_paths.compute_slug(project_root)


def run_cli(args: list[str], *, timeout: int = 180, env: dict[str, str] | None = None) -> dict[str, Any]:
    """Run ``uv run <cli.py> <args>`` and return parsed JSON output.

    Args:
        args: CLI arguments after the script path (e.g. ``["plan", "list", "--limit", "1"]``).
        timeout: Maximum seconds to wait for the subprocess.
        env: Optional environment variable overrides merged onto os.environ.

    Returns:
        Parsed JSON dict from stdout.

    Raises:
        subprocess.TimeoutExpired: If the CLI does not finish in time.
        json.JSONDecodeError: If stdout is not valid JSON.
        RuntimeError: If the CLI exits with a non-zero code.
    """
    # Sanitize before applying caller overrides: these tests assert returncode/JSON shape only
    # and never depend on the live github backend, so a real network round trip here is a
    # correctness bug (results depend on whether GITHUB_TOKEN happens to be exported), not just
    # slower (measured ~28x: ~70-85s live vs ~2.5s sqlite). run_cli_subprocess's own
    # sanitize_env default would also catch this; setting it here too keeps the behavior visible
    # at the call site, matching the dh_env fixture pattern in test_frontend_parity_ops.py.
    run_env = os.environ.copy()
    run_env.update({"BACKLOG_BACKEND": "sqlite", "GITHUB_TOKEN": "", "GH_TOKEN": ""})
    if env:
        run_env.update(env)
    result = run_cli_subprocess(["uv", "run", str(_CLI_PATH), *args], timeout=timeout, env=run_env)
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


@pytest.mark.integration
class TestCLIForeignCWD:
    """Regression: the plugin folder is never the CWD in real use."""

    @pytest.mark.parametrize(("extra_env", "label"), [({}, "clean"), ({"PYTHONPATH": "/tmp"}, "contaminated")])
    def test_cli_runs_from_a_foreign_cwd(self, tmp_path: Path, extra_env: dict[str, str], label: str) -> None:
        state_home = tmp_path / label / "dh_state"
        plan_dir = state_home / "projects" / _get_project_slug() / "plan"
        plan_dir.mkdir(parents=True, exist_ok=True)
        # BACKLOG_BACKEND/GITHUB_TOKEN/GH_TOKEN sanitized: this test verifies foreign-CWD and
        # contaminated-PYTHONPATH behavior, not backend selection -- a live github round trip
        # here is unrelated to what it asserts and was making the run 28x slower.
        result = run_cli_subprocess(
            ["uv", "run", str(_CLI_PATH), "plan", "list", "--limit", "1"],
            timeout=180,
            cwd=tmp_path,
            env={
                **os.environ,
                **extra_env,
                "DH_STATE_HOME": str(state_home),
                "DH_PROJECT_ROOT": str(_REPO_ROOT),
                "BACKLOG_BACKEND": "sqlite",
                "GITHUB_TOKEN": "",
                "GH_TOKEN": "",
            },
        )
        assert result.returncode == 0, f"label={label} {result.stderr[:500]}"
        json.loads(result.stdout)

    @pytest.mark.parametrize("package", ["pydantic", "typer"])
    def test_cli_ignores_an_importable_foreign_dependency_on_pythonpath(self, tmp_path: Path, package: str) -> None:
        """A foreign copy of a declared dependency that imports cleanly does not reach the CLI.

        The existing contaminated case puts ``/tmp`` on ``PYTHONPATH``, which holds no dependency,
        so it cannot see a foreign package that imports but has the wrong version.
        """
        foreign = tmp_path / "foreign" / package
        foreign.mkdir(parents=True)
        (foreign / "__init__.py").write_text('VERSION = "1.10.26"\n', encoding="utf-8")
        state_home = tmp_path / "dh_state"
        (state_home / "projects" / _get_project_slug() / "plan").mkdir(parents=True)
        result = run_cli_subprocess(
            ["uv", "run", str(_CLI_PATH), "plan", "list", "--limit", "1"],
            timeout=180,
            cwd=tmp_path,
            env={
                **os.environ,
                "PYTHONPATH": str(foreign.parent),
                "DH_STATE_HOME": str(state_home),
                "DH_PROJECT_ROOT": str(_REPO_ROOT),
                "BACKLOG_BACKEND": "sqlite",
                "GITHUB_TOKEN": "",
                "GH_TOKEN": "",
            },
        )
        assert result.returncode == 0, f"package={package} {result.stderr[:500]}"
        json.loads(result.stdout)

    def test_wrapper_script_ignores_an_importable_foreign_dependency_on_pythonpath(self, tmp_path: Path) -> None:
        """``scripts/run_sam_cli.py`` survives a foreign dependency on ``PYTHONPATH``.

        The wrapper, not ``cli.py``, is what ships: the implementation-manager
        ``task_status_hook`` names and invokes it. ``cli.py``'s own guard cannot cover this
        path -- the wrapper *imports* that module rather than running it, so the guard is
        gated off, and ``sam_schema/__init__`` reaches pydantic before ``cli.py``'s module
        body ever runs. The wrapper's own copy of the guard is the only thing that fires
        here, so it needs its own test.
        """
        foreign = tmp_path / "foreign" / "pydantic"
        foreign.mkdir(parents=True)
        # Imports cleanly but lacks what the real pydantic exports: ``sam_schema/core/models.py``
        # imports ``AliasChoices``, so an unguarded run fails outright rather than silently
        # running against the wrong version.
        (foreign / "__init__.py").write_text('VERSION = "1.10.26"\n', encoding="utf-8")
        # Drop the guard's own sentinel before forwarding the environment, for the reason spelled
        # out in ``test_importing_cli_module_does_not_hijack_a_foreign_pythonpath_host`` below:
        # inheriting ``DH_CLI_PYTHONPATH_CLEARED`` makes the child skip the guard, so this test
        # would report green on the very defect it exists to catch. Keep in sync with
        # ``_RELOADED`` in ``scripts/run_sam_cli.py``.
        child_env = {k: v for k, v in os.environ.items() if k != "DH_CLI_PYTHONPATH_CLEARED"}
        child_env["PYTHONPATH"] = str(foreign.parent)
        result = run_cli_subprocess(
            ["uv", "run", "--script", str(_WRAPPER_PATH), "plan", "--help"], timeout=180, cwd=tmp_path, env=child_env
        )
        assert result.returncode == 0, f"stdout={result.stdout[-2000:]} stderr={result.stderr[-2000:]}"
        assert "Usage" in result.stdout, f"stdout={result.stdout[-2000:]} stderr={result.stderr[-2000:]}"

    def test_importing_cli_module_does_not_hijack_a_foreign_pythonpath_host(self, tmp_path: Path) -> None:
        """Importing ``sam_schema.cli`` in-process must never re-exec the host process.

        The importers that drive it in-process are the ones ``git grep -nE "^from
        sam_schema.cli import" -- plugins/development-harness`` lists, anchored at line start
        so the pattern cannot match prose quoting it, such as this docstring. Read that list
        with two adjustments: every entry but one is a ``CliRunner`` test module, the
        exception being the PEP 723 wrapper ``scripts/run_sam_cli.py``; and this module is
        absent from it yet drives the import too, via ``import sam_schema.cli`` in the probe
        it writes below.
        If the ``PYTHONPATH`` guard fires at import time
        rather than only on direct script execution, importing the module while a
        *foreign* ``PYTHONPATH`` is set (common in developer/CI shells) calls
        ``os.execve`` using the *importing* process's own ``sys.argv`` -- pytest's, not
        the CLI's -- silently replacing the whole pytest run instead of merely importing
        a module. Reproduced via a nested ``uv run pytest`` so the outer test observes
        exactly what a real in-process importer sees: either a clean pass, or the outer
        process's collection getting hijacked.
        """
        probe = tmp_path / "test_import_guard_probe.py"
        probe.write_text(
            f"""
import sys

sys.path.insert(0, {str(_plugin_root)!r})


def test_importing_cli_module_is_safe() -> None:
    import sam_schema.cli

    assert sam_schema.cli.app is not None
""",
            encoding="utf-8",
        )
        # Drop the guard's own sentinel before forwarding the environment. Inheriting
        # ``DH_CLI_PYTHONPATH_CLEARED`` -- which the outer process carries whenever it was
        # itself re-exec'd by an unfixed guard, or whenever a developer exports it -- makes
        # the child skip the guard entirely, so this test would pass on the very defect it
        # guards. Keep this in sync with ``_RELOADED`` in ``sam_schema/cli.py``.
        child_env = {k: v for k, v in os.environ.items() if k != "DH_CLI_PYTHONPATH_CLEARED"}
        child_env["PYTHONPATH"] = "/tmp"
        result = run_cli_subprocess(
            ["uv", "run", "pytest", str(probe), "-q", "-p", "no:randomly", "--no-cov"],
            timeout=180,
            cwd=_plugin_root,
            env=child_env,
        )
        assert result.returncode == 0, f"stdout={result.stdout[-2000:]} stderr={result.stderr[-2000:]}"
        assert "1 passed" in result.stdout, f"stdout={result.stdout[-2000:]} stderr={result.stderr[-2000:]}"
