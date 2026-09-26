"""Behavioral contract for plugin ``run_pytests.py`` runners, exercised on the summarizer runner."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

RUNNER = Path(__file__).parents[1] / "plugins" / "summarizer" / "run_pytests.py"


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


def collected(plugin: Path, *args: str) -> list[str]:
    """Run the copied runner from an unrelated cwd and return the collected node IDs."""
    result = subprocess.run(
        [sys.executable, str(plugin / "run_pytests.py"), "--collect-only", "-q", "-p", "no:cacheprovider", *args],
        cwd=plugin.parent,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return [line for line in result.stdout.splitlines() if "::" in line]


def test_option_only_invocation_collects_only_declared_roots(plugin: Path) -> None:
    """Options such as ``-m`` must not replace the declared roots with the whole plugin."""
    assert collected(plugin, "-m", "not integration") == ["tests/test_declared.py::test_declared"]


def test_explicit_path_overrides_declared_roots(plugin: Path) -> None:
    assert collected(plugin, "stray") == ["stray/test_stray.py::test_stray"]
