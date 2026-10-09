"""Contract for plugin ``run_pytests.py`` runners.

Behavior is exercised on a copy of the summarizer runner in a bare plugin; the
configuration each runner hands to pytest is checked for every runner.
"""

from __future__ import annotations

import ast
import importlib.util
import os
import shlex
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parents[1]
RUNNER = REPO_ROOT / "plugins" / "summarizer" / "run_pytests.py"
RUNNERS = sorted((REPO_ROOT / "plugins").glob("*/run_pytests.py"))
LANE_MARKERS = """
import pytest

def pytest_configure(config):
    for name in ("e2e", "integration", "cross_backend", "research_vault"):
        config.addinivalue_line("markers", f"{name}: lane marker")
"""


def root_fast_marker() -> str:
    """Return the ``-m`` expression the root pytest configuration applies by default."""
    addopts = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))["tool"]["pytest"][
        "ini_options"
    ]["addopts"]
    return addopts[addopts.index("-m") + 1]


@pytest.fixture
def plugin(tmp_path: Path) -> Path:
    """Copy the runner into a bare plugin with one declared test and one stray test."""
    root = tmp_path / "plugin"
    (root / "tests").mkdir(parents=True)
    (root / "stray").mkdir()
    shutil.copy(RUNNER, root / "run_pytests.py")
    (root / "tests" / "test_declared.py").write_text("def test_declared() -> None:\n    pass\n")
    (root / "stray" / "test_stray.py").write_text("def test_stray() -> None:\n    pass\n")
    return root


def run_runner(plugin: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run the copied runner's collection from an unrelated cwd."""
    return subprocess.run(
        [sys.executable, str(plugin / "run_pytests.py"), "--collect-only", "-q", "-p", "no:cacheprovider", *args],
        cwd=plugin.parent,
        capture_output=True,
        text=True,
        check=False,
    )


def collected(plugin: Path, *args: str) -> list[str]:
    """Return the node IDs the copied runner collects, requiring a clean exit."""
    result = run_runner(plugin, *args)
    assert result.returncode == 0, result.stdout + result.stderr
    return [line for line in result.stdout.splitlines() if "::" in line]


def test_option_only_invocation_collects_only_declared_roots(plugin: Path) -> None:
    """Options such as ``-m`` must not replace the declared roots with the whole plugin."""
    assert collected(plugin, "-m", "not integration") == ["tests/test_declared.py::test_declared"]


def test_explicit_path_overrides_declared_roots(plugin: Path) -> None:
    assert collected(plugin, "stray") == ["stray/test_stray.py::test_stray"]


def test_bare_invocation_selects_only_the_fast_lane(plugin: Path) -> None:
    """With no ``-m``, lane-marked tests stay out; an explicit ``-m`` replaces the default."""
    (plugin / "conftest.py").write_text(LANE_MARKERS)
    (plugin / "tests" / "test_lanes.py").write_text(
        "import pytest\n\n"
        "@pytest.mark.e2e\ndef test_e2e() -> None:\n    pass\n\n"
        "@pytest.mark.integration\ndef test_integration() -> None:\n    pass\n\n"
        "@pytest.mark.cross_backend\ndef test_cross_backend() -> None:\n    pass\n"
    )
    assert collected(plugin) == ["tests/test_declared.py::test_declared"]
    assert collected(plugin, "-m", "integration") == ["tests/test_lanes.py::test_integration"]


def test_mistyped_marker_fails_collection(plugin: Path) -> None:
    (plugin / "tests" / "test_typo.py").write_text(
        "import pytest\n\n@pytest.mark.intergration\ndef test_typo() -> None:\n    pass\n"
    )
    result = run_runner(plugin)
    assert result.returncode != 0
    assert "'intergration' not found in `markers`" in result.stdout + result.stderr


def test_parent_conftest_is_not_loaded(tmp_path: Path, plugin: Path) -> None:
    (tmp_path / "conftest.py").write_text("raise RuntimeError('parent conftest loaded')\n")
    assert collected(plugin) == ["tests/test_declared.py::test_declared"]


@pytest.mark.parametrize("runner", RUNNERS, ids=lambda path: path.parent.name)
def test_runner_hands_pytest_its_own_isolated_configuration(runner: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Every runner sets the policy root config used to supply, and the root's fast lane."""
    spec = importlib.util.spec_from_file_location(f"runner_{runner.parent.name}", runner)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    captured: list[list[str]] = []
    monkeypatch.setattr(module.pytest, "main", lambda args: captured.append(args) or 0)
    monkeypatch.setattr(os, "chdir", lambda _path: None)
    monkeypatch.setattr(sys, "argv", [str(runner)])
    assert module.main() == 0
    args = captured[0]
    root = runner.parent.resolve()
    collection_root = Path(args[args.index("--rootdir") + 1]).resolve()
    assert args[args.index("-c") + 1] == os.devnull
    assert collection_root.is_relative_to(root)
    assert all((root / path).resolve().is_relative_to(collection_root) for path in module.TEST_PATHS)
    assert args[args.index("--confcutdir") + 1] == str(root)
    assert {"--strict-config", "--strict-markers", "--import-mode=importlib", "--asyncio-mode=auto"} <= set(args)
    assert f"testpaths={shlex.join(module.TEST_PATHS)}" in args
    assert args[args.index("-m") + 1] == root_fast_marker() == module.FAST_MARKER
    assert not any(arg.startswith("python_files") for arg in args)
    assert planner_lanes(runner) == getattr(module, "LANES", {})


def planner_lanes(runner: Path) -> dict[str, str]:
    """Return the lanes the CI planner reads from ``runner`` without importing it."""
    spec = importlib.util.spec_from_file_location("ci_plan_for_runner_contract", REPO_ROOT / ".github/ci/plan.py")
    assert spec is not None
    assert spec.loader is not None
    planner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(planner)
    return planner.runner_lanes(REPO_ROOT, runner.relative_to(REPO_ROOT).as_posix())


def plugin_marker_lines() -> list[tuple[str, str]]:
    """Return every marker line a plugin conftest registers, from ``_MARKERS`` or ``addinivalue_line``."""
    found: list[tuple[str, str]] = []
    for conftest in sorted((REPO_ROOT / "plugins").rglob("conftest.py")):
        for node in ast.walk(ast.parse(conftest.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "_MARKERS" for t in node.targets
            ):
                found.extend((str(conftest.relative_to(REPO_ROOT)), line) for line in ast.literal_eval(node.value))
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "addinivalue_line"
                and len(node.args) == 2
                and isinstance(node.args[0], ast.Constant)
                and node.args[0].value == "markers"
                and isinstance(node.args[1], ast.Constant)
                and isinstance(node.args[1].value, str)
            ):
                found.append((str(conftest.relative_to(REPO_ROOT)), node.args[1].value))
    return found


def test_plugin_marker_registrations_match_the_root_markers() -> None:
    """A marker a plugin registers for its runner carries the root's exact description."""
    root = {
        line.split(":", 1)[0]: line
        for line in tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))["tool"]["pytest"][
            "ini_options"
        ]["markers"]
    }
    registered = plugin_marker_lines()
    assert registered, "no plugin conftest registers a marker, so this check examined nothing"
    drift = [(source, line) for source, line in registered if root.get(line.split(":", 1)[0]) != line]
    assert not drift, f"plugin marker registrations differ from root pyproject markers: {drift}"


@pytest.mark.parametrize("runner", RUNNERS, ids=lambda path: path.parent.name)
def test_runner_lockfile_matches_its_dependencies(runner: Path) -> None:
    """Each runner's committed ``run_pytests.py.lock`` satisfies its PEP 723 block, as CI's --locked run requires."""
    result = subprocess.run(
        ["uv", "lock", "--script", str(runner), "--check"], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, f"{runner.parent.name}: run `uv lock --script {runner}`\n{result.stderr}"
