"""Unit tests for dh_migrate CLI tool.

dh_migrate is invoked exclusively by AI agents via subprocess, so every
command emits a single compact JSON object on stdout — these tests parse
that JSON and assert on structured fields, not human-formatted text.

Tests cover:
- verify command: detects old layout, new layout, partial migration
- migrate --dry-run: shows plan without modifying files
- migrate: moves directories, creates .dh/.gitkeep, removes empty old dirs
- _detect_layout: correct flags for old/new/both/neither
- _old_dirs: correct path construction
- _artifact_manifest_instructions: structured follow-up instructions (no external calls)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Bootstrap: add the harness package to sys.path so dh_paths and dh_migrate
# can be imported in the test environment.
# ---------------------------------------------------------------------------
_HARNESS_DIR = Path(__file__).resolve().parents[1]
if str(_HARNESS_DIR) not in sys.path:
    sys.path.insert(0, str(_HARNESS_DIR))

from typing import TYPE_CHECKING

import dh_paths
from scripts.dh_migrate import (
    _OLD_TO_NEW,
    _artifact_manifest_instructions,
    _detect_layout,
    _merge_dir,
    _old_dirs,
    _remove_empty_old_dirs,
    app,
)
from typer.testing import CliRunner

if TYPE_CHECKING:
    from collections.abc import Generator

runner = CliRunner()

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[Path, None, None]:
    """Create an isolated fake project root with DH_STATE_HOME overridden.

    Returns:
        Absolute path to the fake project root (git root mock).
    """
    project_root = tmp_path / "my-project"
    project_root.mkdir()
    state_home = tmp_path / "dh-state"
    state_home.mkdir()
    monkeypatch.setenv("DH_STATE_HOME", str(state_home))
    # Patch git_project_root to return our fake project root
    with patch.object(dh_paths, "git_project_root", return_value=project_root):
        # Also clear the root cache so it doesn't interfere
        dh_paths._root_cache.clear()
        yield project_root


@pytest.fixture
def old_layout(fake_project: Path) -> Path:
    """Create the old layout directories inside the fake project root.

    Returns:
        The fake project root path.
    """
    (fake_project / ".claude" / "backlog").mkdir(parents=True)
    (fake_project / ".claude" / "backlog" / "item.md").write_text("# item")
    (fake_project / ".claude" / "context").mkdir(parents=True)
    (fake_project / ".claude" / "reports").mkdir(parents=True)
    (fake_project / "plan").mkdir(parents=True)
    (fake_project / "plan" / "P001-test.yaml").write_text("slug: test")
    return fake_project


@pytest.fixture
def new_layout(fake_project: Path) -> Path:
    """Create the new layout directories under state_home.

    Returns:
        The fake project root path.
    """
    backlog = dh_paths.backlog_dir(fake_project)
    backlog.mkdir(parents=True)
    (backlog / "item.md").write_text("# item")
    return fake_project


# ---------------------------------------------------------------------------
# _detect_layout
# ---------------------------------------------------------------------------


def test_detect_layout_old_only_returns_old_present(old_layout: Path) -> None:
    # Arrange: old dirs present, new absent (fixture creates old only)
    # Act
    result = _detect_layout(old_layout)
    # Assert
    assert result["old_present"] is True
    assert result["new_present"] is False


def test_detect_layout_new_only_returns_new_present(new_layout: Path) -> None:
    # Arrange: new dirs present, old absent
    # Act
    result = _detect_layout(new_layout)
    # Assert
    assert result["old_present"] is False
    assert result["new_present"] is True


def test_detect_layout_neither_returns_both_false(fake_project: Path) -> None:
    # Arrange: clean project with no dirs
    # Act
    result = _detect_layout(fake_project)
    # Assert
    assert result["old_present"] is False
    assert result["new_present"] is False


def test_detect_layout_both_present_returns_both_true(old_layout: Path, new_layout: Path) -> None:
    # Arrange: old_layout and new_layout fixtures both applied to fake_project
    # Act (both fixtures share same fake_project root)
    result = _detect_layout(old_layout)
    # Assert
    assert result["old_present"] is True
    assert result["new_present"] is True


# ---------------------------------------------------------------------------
# _old_dirs
# ---------------------------------------------------------------------------


def test_old_dirs_returns_correct_paths(fake_project: Path) -> None:
    # Arrange
    result = _old_dirs(fake_project)
    # Assert: all keys from _OLD_TO_NEW are present and paths are absolute
    assert set(result.keys()) == set(_OLD_TO_NEW.keys())
    for key, path in result.items():
        assert path == fake_project / key
        assert path.is_absolute()


def test_old_dirs_paths_are_under_project_root(fake_project: Path) -> None:
    # Arrange / Act
    result = _old_dirs(fake_project)
    # Assert: all paths are children of the project root
    for path in result.values():
        assert str(path).startswith(str(fake_project))


# ---------------------------------------------------------------------------
# verify command
# ---------------------------------------------------------------------------


def test_verify_old_layout_exits_1_and_reports_present(old_layout: Path) -> None:
    # Arrange: old layout in place
    with patch.object(dh_paths, "git_project_root", return_value=old_layout):
        # Act
        result = runner.invoke(app, ["verify"])
    # Assert
    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["status"] in {"action_required", "partial_migration"}
    assert any(entry["present"] for entry in payload["old_layout"])


def test_verify_new_layout_exits_0(new_layout: Path) -> None:
    # Arrange: new layout in place
    with patch.object(dh_paths, "git_project_root", return_value=new_layout):
        # Act
        result = runner.invoke(app, ["verify"])
    # Assert
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["status"] == "migrated"
    assert payload["new_layout"]["present"] is True


def test_verify_no_layout_exits_0_status_migrated(fake_project: Path) -> None:
    # Arrange: neither old nor new layout
    with patch.object(dh_paths, "git_project_root", return_value=fake_project):
        # Act
        result = runner.invoke(app, ["verify"])
    # Assert: old_present is False so the command reports "migrated" and exits 0,
    # regardless of whether new_present is also False (fresh/clean project).
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["status"] == "migrated"


def test_verify_shows_project_slug(old_layout: Path) -> None:
    # Arrange
    with patch.object(dh_paths, "git_project_root", return_value=old_layout):
        # Act
        result = runner.invoke(app, ["verify"])
    # Assert: project_slug field is present and non-empty
    payload = json.loads(result.output)
    assert payload["project_slug"]


# ---------------------------------------------------------------------------
# migrate --dry-run command
# ---------------------------------------------------------------------------


def test_migrate_dry_run_exits_0_and_shows_plan(old_layout: Path) -> None:
    # Arrange
    with patch.object(dh_paths, "git_project_root", return_value=old_layout):
        # Act
        result = runner.invoke(app, ["migrate", "--dry-run"])
    # Assert
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["status"] == "dry_run"
    assert payload["moves"]


def test_migrate_dry_run_does_not_move_files(old_layout: Path) -> None:
    # Arrange: confirm old backlog file exists before dry-run
    old_backlog = old_layout / ".claude" / "backlog" / "item.md"
    assert old_backlog.exists()

    with patch.object(dh_paths, "git_project_root", return_value=old_layout):
        # Act
        runner.invoke(app, ["migrate", "--dry-run"])

    # Assert: source file still exists after dry-run
    assert old_backlog.exists()
    # New backlog dir should NOT exist
    assert not dh_paths.backlog_dir(old_layout).exists()


def test_migrate_dry_run_shows_source_and_destination(old_layout: Path) -> None:
    # Arrange
    with patch.object(dh_paths, "git_project_root", return_value=old_layout):
        # Act
        result = runner.invoke(app, ["migrate", "--dry-run"])
    # Assert: each planned move has source/destination fields
    payload = json.loads(result.output)
    assert payload["status"] == "dry_run"
    for move in payload["moves"]:
        assert move["source"]
        assert move["destination"]


# ---------------------------------------------------------------------------
# migrate (real move) command
# ---------------------------------------------------------------------------


def test_migrate_moves_backlog_to_new_location(old_layout: Path) -> None:
    # Arrange
    old_backlog_file = old_layout / ".claude" / "backlog" / "item.md"
    assert old_backlog_file.exists()

    with patch.object(dh_paths, "git_project_root", return_value=old_layout):
        # Act
        result = runner.invoke(app, ["migrate"])

    # Assert
    assert result.exit_code == 0
    new_backlog_file = dh_paths.backlog_dir(old_layout) / "item.md"
    assert new_backlog_file.exists()
    assert new_backlog_file.read_text() == "# item"


def test_migrate_moves_plan_to_new_location(old_layout: Path) -> None:
    # Arrange
    old_plan_file = old_layout / "plan" / "P001-test.yaml"
    assert old_plan_file.exists()

    with patch.object(dh_paths, "git_project_root", return_value=old_layout):
        # Act
        result = runner.invoke(app, ["migrate"])

    # Assert
    assert result.exit_code == 0
    new_plan_file = dh_paths.plan_dir(old_layout) / "P001-test.yaml"
    assert new_plan_file.exists()
    assert new_plan_file.read_text() == "slug: test"


def test_migrate_creates_dh_gitkeep(old_layout: Path) -> None:
    # Arrange
    gitkeep = old_layout / ".dh" / ".gitkeep"
    assert not gitkeep.exists()

    with patch.object(dh_paths, "git_project_root", return_value=old_layout):
        # Act
        result = runner.invoke(app, ["migrate"])

    # Assert
    assert result.exit_code == 0
    assert gitkeep.exists()
    payload = json.loads(result.output)
    assert payload["status"] == "success"
    assert payload["gitkeep_created"] is True


def test_migrate_removes_empty_old_dirs(old_layout: Path) -> None:
    # Arrange: old dirs have content that will be moved. When the destination
    # does not pre-exist, shutil.move() relocates the whole source directory —
    # by the time _remove_empty_old_dirs runs, it no longer exists at all
    # (neither empty nor non-empty), so it is not one of the paths that
    # function reports as removed. _merge_dir's own return value is covered
    # directly by test_merge_dir_returns_merged_items_and_removes_source below.
    with patch.object(dh_paths, "git_project_root", return_value=old_layout):
        # Act
        result = runner.invoke(app, ["migrate"])

    # Assert: old dirs no longer exist after migration
    assert result.exit_code == 0
    old_backlog = old_layout / ".claude" / "backlog"
    old_plan = old_layout / "plan"
    assert not old_backlog.exists()
    assert not old_plan.exists()


def test_migrate_no_old_dirs_exits_0_with_nothing_to_migrate(fake_project: Path) -> None:
    # Arrange: no old layout dirs at all
    with patch.object(dh_paths, "git_project_root", return_value=fake_project):
        # Act
        result = runner.invoke(app, ["migrate"])
    # Assert: exits 0, reports nothing to migrate
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["status"] == "nothing_to_migrate"
    assert payload["moves"] == []


def test_migrate_idempotent_gitkeep_already_present(old_layout: Path) -> None:
    # Arrange: pre-create the .dh/.gitkeep
    dh_dir = old_layout / ".dh"
    dh_dir.mkdir(parents=True)
    (dh_dir / ".gitkeep").touch()

    with patch.object(dh_paths, "git_project_root", return_value=old_layout):
        # Act
        result = runner.invoke(app, ["migrate"])

    # Assert: exits 0, does not error on existing .gitkeep
    assert result.exit_code == 0
    assert (dh_dir / ".gitkeep").exists()
    payload = json.loads(result.output)
    assert payload["gitkeep_created"] is False


# ---------------------------------------------------------------------------
# _merge_dir
# ---------------------------------------------------------------------------


def test_merge_dir_returns_merged_items_and_removes_source(tmp_path: Path) -> None:
    # Arrange: src has two items, dest already exists (the merge case)
    src = tmp_path / "src"
    dest = tmp_path / "dest"
    src.mkdir()
    dest.mkdir()
    (src / "a.md").write_text("a")
    (src / "b.md").write_text("b")

    # Act
    merged = _merge_dir(src, dest)

    # Assert: both item names reported, files copied, source removed
    assert set(merged) == {"a.md", "b.md"}
    assert (dest / "a.md").read_text() == "a"
    assert (dest / "b.md").read_text() == "b"
    assert not src.exists()


# ---------------------------------------------------------------------------
# _remove_empty_old_dirs
# ---------------------------------------------------------------------------


def test_remove_empty_old_dirs_reports_removed_and_skipped(fake_project: Path) -> None:
    # Arrange: .claude/backlog is empty (removable), .claude/context has content (skipped)
    empty_dir = fake_project / ".claude" / "backlog"
    non_empty_dir = fake_project / ".claude" / "context"
    empty_dir.mkdir(parents=True)
    non_empty_dir.mkdir(parents=True)
    (non_empty_dir / "leftover.md").write_text("still here")

    # Act
    removed, skipped = _remove_empty_old_dirs(fake_project)

    # Assert
    assert str(empty_dir) in removed
    assert not empty_dir.exists()
    assert str(non_empty_dir) in skipped
    assert non_empty_dir.exists()


# ---------------------------------------------------------------------------
# _artifact_manifest_instructions
# ---------------------------------------------------------------------------


def test_artifact_manifest_instructions_returns_dict_without_raising(fake_project: Path) -> None:
    # Act — should not raise, should return a populated dict
    result = _artifact_manifest_instructions(fake_project)

    # Assert
    assert isinstance(result, dict)
    assert result


def test_artifact_manifest_instructions_mentions_artifact_register(fake_project: Path) -> None:
    # Act
    result = _artifact_manifest_instructions(fake_project)
    steps = result["steps"]

    assert isinstance(steps, list)
    assert any("content=<artifact body>" in str(step) for step in steps)


def test_artifact_manifest_instructions_shows_old_prefixes(fake_project: Path) -> None:
    # Act
    result = _artifact_manifest_instructions(fake_project)
    old_prefixes = result["old_prefixes"]

    # Assert: old prefixes are present in structured form
    assert isinstance(old_prefixes, list)
    assert "plan/" in old_prefixes
    assert ".claude/backlog/" in old_prefixes
