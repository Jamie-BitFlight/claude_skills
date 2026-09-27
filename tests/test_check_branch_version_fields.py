"""Branches may not change plugin or marketplace version fields."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Final

ROOT: Final = Path(__file__).resolve().parents[1]
SCRIPT: Final = ROOT / "scripts/check_branch_version_fields.py"
PLUGIN: Final = "plugins/tool/.claude-plugin/plugin.json"
CATALOG: Final = ".claude-plugin/marketplace.json"


def git(repo: Path, *args: str) -> str:
    """Run git in the fixture repository.

    Returns:
        The command's stdout.
    """
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True).stdout


def write(repo: Path, path: str, data: dict[str, object]) -> None:
    """Write one JSON manifest, creating its directory."""
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data))


def commit(repo: Path, message: str) -> None:
    """Commit every change in the fixture repository."""
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", message)


def check(repo: Path) -> subprocess.CompletedProcess[str]:
    """Run the check for the `branch` branch against `main`.

    Returns:
        The completed check process.
    """
    return subprocess.run(
        [str(SCRIPT), "--base", "main", "--head", "branch"], cwd=repo, check=False, capture_output=True, text=True
    )


def fixture(tmp_path: Path) -> Path:
    """Create a repository with one plugin and a catalog, checked out on `branch`.

    Returns:
        The repository root.
    """
    git(tmp_path, "init", "-q", "--initial-branch=main")
    git(tmp_path, "config", "user.name", "Fixture")
    git(tmp_path, "config", "user.email", "fixture@example.invalid")
    write(tmp_path, PLUGIN, {"name": "tool", "version": "1.0.0", "skills": []})
    write(tmp_path, CATALOG, {"name": "f", "metadata": {"version": "1.0.0"}, "plugins": []})
    commit(tmp_path, "init")
    git(tmp_path, "switch", "-qc", "branch")
    return tmp_path


def test_branch_version_change_fails(tmp_path: Path) -> None:
    """A branch that edits a plugin or catalog version is rejected, naming each field."""
    repo = fixture(tmp_path)
    write(repo, PLUGIN, {"name": "tool", "version": "1.0.1", "skills": []})
    write(repo, CATALOG, {"name": "f", "metadata": {"version": "1.0.1"}, "plugins": []})
    commit(repo, "bump on branch")

    result = check(repo)

    assert result.returncode == 1, result.stdout + result.stderr
    assert f"{PLUGIN}: version '1.0.0' -> '1.0.1'" in result.stderr
    assert f"{CATALOG}: metadata.version '1.0.0' -> '1.0.1'" in result.stderr


def test_renamed_manifest_version_change_fails(tmp_path: Path) -> None:
    """Moving a plugin directory does not hide a version edit made in the same branch."""
    repo = fixture(tmp_path)
    manifest = {"name": "tool", "version": "1.0.0", "description": "d", "author": {"name": "a"}, "skills": []}
    (repo / PLUGIN).write_text(json.dumps(manifest, indent=2) + "\n")
    commit(repo, "multi-line manifest, as every real plugin.json is")
    git(repo, "switch", "-q", "main")
    git(repo, "merge", "-q", "--ff-only", "branch")
    git(repo, "switch", "-q", "branch")
    git(repo, "mv", "plugins/tool", "plugins/renamed")
    renamed = "plugins/renamed/.claude-plugin/plugin.json"
    (repo / renamed).write_text(json.dumps({**manifest, "name": "renamed", "version": "9.9.9"}, indent=2) + "\n")
    commit(repo, "rename plugin and bump")

    result = check(repo)

    assert result.returncode == 1, result.stdout + result.stderr
    assert f"{renamed}: version '1.0.0' -> '9.9.9'" in result.stderr


def test_rewritten_move_version_change_fails(tmp_path: Path) -> None:
    """A move rewritten past git's rename threshold (a delete plus an add) is still paired and checked."""
    repo = fixture(tmp_path)
    git(repo, "rm", "-q", PLUGIN)
    moved = "plugins/renamed/.claude-plugin/plugin.json"
    write(repo, moved, {"name": "renamed", "version": "9.9.9", "description": "rewritten", "agents": ["./a.md"]})
    commit(repo, "move and rewrite")
    assert set(git(repo, "diff", "--name-status", "-M", "main", "branch").splitlines()) == {
        f"D\t{PLUGIN}",
        f"A\t{moved}",
    }

    result = check(repo)

    assert result.returncode == 1, result.stdout + result.stderr
    assert f"{moved}: version '1.0.0' -> '9.9.9'" in result.stderr


def test_branch_behind_main_bump_and_new_plugin_pass(tmp_path: Path) -> None:
    """Non-version edits pass, as do new manifests, even when main bumped versions after the fork."""
    repo = fixture(tmp_path)
    write(repo, PLUGIN, {"name": "tool", "version": "1.0.0", "skills": ["./skills/a"]})
    write(repo, "plugins/fresh/.claude-plugin/plugin.json", {"name": "fresh", "version": "0.1.0"})
    commit(repo, "content change and new plugin")
    git(repo, "switch", "-q", "main")
    write(repo, PLUGIN, {"name": "tool", "version": "1.0.5", "skills": []})
    commit(repo, "chore(plugins): assign plugin versions")

    result = check(repo)

    assert result.returncode == 0, result.stdout + result.stderr
