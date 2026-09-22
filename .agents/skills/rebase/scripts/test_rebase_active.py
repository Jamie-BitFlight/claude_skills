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
import sys
from pathlib import Path

from rebase_test_support import BOUNDED_RUNNER, SKILL_ROOT, VALIDATOR_PATH, commit_file, initialize_repository, run_git

ACTIVE_ROUTE = SKILL_ROOT / "scripts" / "rebase_active.py"


def run_active_route(repository: Path) -> subprocess.CompletedProcess[str]:
    """Run the active-operation inspector through the bounded process owner."""
    return subprocess.run(
        [str(BOUNDED_RUNNER), "--timeout-seconds", "20", "--", sys.executable, str(ACTIVE_ROUTE)],
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


def test_stopped_apply_backend_routes_as_active(tmp_path: Path) -> None:
    """Treat rebase-apply metadata as an authoritative active operation."""
    repository = tmp_path / "stopped-apply-rebase"
    initialize_repository(repository)
    commit_file(repository, "shared.txt", "base\n", "add shared")
    run_git(repository, "switch", "-c", "feature")
    commit_file(repository, "shared.txt", "feature\n", "feature edit")
    run_git(repository, "switch", "main")
    commit_file(repository, "shared.txt", "target\n", "target edit")
    run_git(repository, "switch", "feature")
    assert run_git(repository, "rebase", "--apply", "main", check=False).returncode != 0

    result = run_active_route(repository)
    observation = json.loads(result.stdout)

    assert result.returncode == 0
    assert observation["route"] == "active"
    assert observation["rebase_merge_present"] is False
    assert observation["rebase_apply_present"] is True
    run_git(repository, "rebase", "--abort")


def test_completed_rebase_with_stale_rebase_head_routes_to_no_active_terminal(tmp_path: Path) -> None:
    """Ignore a retained REBASE_HEAD after the rebase metadata is removed."""
    repository = tmp_path / "completed-rebase"
    initialize_repository(repository)
    commit_file(repository, "shared.txt", "base\n", "add shared")
    run_git(repository, "switch", "-c", "feature")
    commit_file(repository, "shared.txt", "feature\n", "feature edit")
    run_git(repository, "switch", "main")
    commit_file(repository, "shared.txt", "target\n", "target edit")
    run_git(repository, "switch", "feature")
    assert run_git(repository, "rebase", "main", check=False).returncode != 0

    (repository / "shared.txt").write_text("target\nfeature\n", encoding="utf-8")
    run_git(repository, "add", "shared.txt")
    run_git(repository, "-c", "core.editor=true", "rebase", "--continue")
    assert run_git(repository, "rev-parse", "--verify", "--quiet", "REBASE_HEAD").returncode == 0

    result = run_active_route(repository)
    observation = json.loads(result.stdout)

    assert result.returncode == 0
    assert observation["route"] == "NO_ACTIVE_REBASE"
    assert observation["current_branch"] == "feature"
    assert observation["head_detached"] is False
    assert observation["rebase_merge_present"] is False
    assert observation["rebase_apply_present"] is False
    assert observation["rebase_head_present"] is True
    assert observation["status"] == "## feature\n"

    states_result = subprocess.run(
        [str(BOUNDED_RUNNER), "--timeout-seconds", "20", "--", sys.executable, str(VALIDATOR_PATH), "states"],
        cwd=repository,
        check=False,
        capture_output=True,
        text=True,
    )
    states = json.loads(states_result.stdout)
    no_active = next(state for state in states if state["name"] == observation["route"])

    assert states_result.returncode == 0
    assert "no rebase metadata" in no_active["evidence"]
    assert "REBASE_HEAD observation, present or absent" in no_active["evidence"]
    assert "absent REBASE_HEAD" not in no_active["evidence"]


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
