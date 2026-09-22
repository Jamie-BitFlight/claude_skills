#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pytest",
# ]
# [tool.ty.environment]
# root = ["."]
# ///
"""Behavioral checks for active-rebase entry routing."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from rebase_test_support import BOUNDED_RUNNER, SKILL_ROOT, commit_file, initialize_repository, run_git

ACTIVE_ROUTE = SKILL_ROOT / "scripts" / "rebase_active.py"


def run_active_route(repository: Path) -> subprocess.CompletedProcess[str]:
    """Run the active-operation inspector through the bounded process owner."""
    return subprocess.run(
        [str(BOUNDED_RUNNER), "--timeout-seconds", "20", "--", "uv", "run", "--script", str(ACTIVE_ROUTE)],
        cwd=repository,
        check=False,
        capture_output=True,
        text=True,
    )


def test_stopped_rebase_with_detached_head_routes_as_active(tmp_path: Path) -> None:
    """Treat detached HEAD as expected evidence inside a real stopped rebase."""
    repository = tmp_path / "stopped-rebase"
    initialize_repository(repository)
    commit_file(repository, "shared.txt", "base\n", "add shared")
    run_git(repository, "switch", "-c", "feature")
    commit_file(repository, "shared.txt", "feature\n", "feature edit")
    run_git(repository, "switch", "main")
    commit_file(repository, "shared.txt", "target\n", "target edit")
    run_git(repository, "switch", "feature")
    assert run_git(repository, "rebase", "main", check=False).returncode != 0

    result = run_active_route(repository)
    observation = json.loads(result.stdout)

    assert result.returncode == 0
    assert observation["route"] == "active"
    assert observation["current_branch"] is None
    assert observation["head_detached"] is True
    assert observation["rebase_merge_present"] is True
    assert observation["rebase_head_present"] is True
    run_git(repository, "rebase", "--abort")


def test_repository_without_rebase_routes_to_no_active_terminal(tmp_path: Path) -> None:
    """Return the existing no-active terminal from a clean attached repository."""
    repository = tmp_path / "no-active-rebase"
    initialize_repository(repository)

    result = run_active_route(repository)
    observation = json.loads(result.stdout)

    assert result.returncode == 0
    assert observation["route"] == "NO_ACTIVE_REBASE"
    assert observation["current_branch"] == "main"
    assert observation["head_detached"] is False
    assert observation["rebase_merge_present"] is False
    assert observation["rebase_apply_present"] is False
    assert observation["rebase_head_present"] is False
