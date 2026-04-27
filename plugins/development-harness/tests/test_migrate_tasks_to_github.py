"""Tests for migrate_tasks_to_github.py migration script.

Covers: dry-run safety, idempotency, YAML field writes, task type inference,
partial failure resilience, and cache file output.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Import the script under test.
# The script adds its own sys.path entries at import time; we replicate
# the module-level import here.
# ---------------------------------------------------------------------------

_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "plugins" / "python3-development" / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from migrate_tasks_to_github import _write_cache, _write_github_issue_field, infer_task_type, parse_task_file

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_task_file(tmp_path: Path, *, github_issue: int | None = None) -> Path:
    """Write a single-task YAML frontmatter file.

    Args:
        tmp_path: Pytest tmp_path fixture directory.
        github_issue: Optional existing github_issue field value.

    Returns:
        Path to the created task file.
    """
    issue_line = f"github_issue: {github_issue}\n" if github_issue is not None else ""
    content = (
        "---\n"
        "task_id: T1\n"
        "title: Implement the feature\n"
        "status: not-started\n"
        "agent: python3-development:python-cli-architect\n"
        "priority: 2\n"
        "complexity: Medium\n"
        "skills:\n"
        "  - python3-development\n"
        "dependencies: []\n"
        f"{issue_line}"
        "---\n\n"
        "## Context\n\nSome task body.\n"
    )
    task_file = tmp_path / "tasks-001-my-feature.md"
    task_file.write_text(content)
    return task_file


def _make_two_task_file(tmp_path: Path) -> Path:
    """Write a multi-task file with two tasks (T1 and T2).

    Args:
        tmp_path: Pytest tmp_path fixture directory.

    Returns:
        Path to the created multi-task file.
    """
    content = (
        "---\n"
        "feature: my-feature\n"
        "parent_issue: 480\n"
        "---\n\n"
        "## Feature\n\nTwo tasks.\n\n"
        "---\n"
        "task_id: T1\n"
        "title: Implement the widget\n"
        "status: not-started\n"
        "agent: python3-development:python-cli-architect\n"
        "priority: 2\n"
        "complexity: Medium\n"
        "skills: []\n"
        "dependencies: []\n"
        "---\n\n"
        "## Context\n\nFirst task.\n\n"
        "---\n"
        "task_id: T2\n"
        "title: Review the implementation\n"
        "status: not-started\n"
        "agent: python3-development:python-cli-architect\n"
        "priority: 2\n"
        "complexity: Medium\n"
        "skills: []\n"
        "dependencies:\n"
        "  - T1\n"
        "---\n\n"
        "## Context\n\nSecond task.\n"
    )
    task_file = tmp_path / "tasks-001-my-feature.md"
    task_file.write_text(content)
    return task_file


def _make_mock_issue(number: int) -> dict[str, object]:
    """Create a minimal IssueNode dict with the given issue number.

    The production code accesses the return value of create_task_issue via
    subscript (issue["number"]), matching the IssueNode TypedDict interface.
    Returning a plain dict ensures JSON serialisation in _write_cache succeeds.

    Args:
        number: Issue number to assign.

    Returns:
        Dict with "number" key matching the IssueNode TypedDict interface.
    """
    return {"number": number, "title": "", "state": "OPEN", "body": "", "id": "", "createdAt": ""}


# ---------------------------------------------------------------------------
# Test: dry-run produces no writes and no API calls
# ---------------------------------------------------------------------------


def test_dry_run_no_writes(tmp_path: Path) -> None:
    """Dry-run flag must produce zero file writes and zero API calls."""
    # Arrange
    task_file = _make_task_file(tmp_path)
    original_mtime = task_file.stat().st_mtime

    from typer.testing import CliRunner

    from migrate_tasks_to_github import app

    runner = CliRunner()

    with patch("migrate_tasks_to_github.create_task_issue") as mock_create:
        # Act
        result = runner.invoke(app, ["--task-file", str(task_file), "--parent-issue", "480", "--dry-run"])

    # Assert: exit 0
    assert result.exit_code == 0, result.output

    # Assert: no GitHub API calls
    mock_create.assert_not_called()

    # Assert: task file not modified
    assert task_file.stat().st_mtime == original_mtime

    # Assert: no cache file written
    cache_file = tmp_path / ".claude" / "context" / "sam-tasks-my-feature.json"
    assert not cache_file.exists()

    # Assert: "Would create:" line in output
    assert "Would create:" in result.output


# ---------------------------------------------------------------------------
# Test: tasks with existing github_issue field are skipped
# ---------------------------------------------------------------------------


def test_skips_already_migrated(tmp_path: Path) -> None:
    """Tasks with github_issue field must be skipped without API calls."""
    # Arrange
    task_file = _make_task_file(tmp_path, github_issue=100)

    from typer.testing import CliRunner

    from migrate_tasks_to_github import app

    runner = CliRunner()

    with (
        patch("migrate_tasks_to_github._BACKLOG_CORE", Path(tmp_path) / "fake_backlog_core"),
        patch("migrate_tasks_to_github.get_github") as mock_gh,
        patch("migrate_tasks_to_github.create_task_issue") as mock_create,
    ):
        # Provide a mock repo so the live-mode path doesn't fail on import.
        mock_gh.return_value = MagicMock()

        # Act: invoke with --dry-run; the task should still be skipped
        result = runner.invoke(app, ["--task-file", str(task_file), "--parent-issue", "480", "--dry-run"])

    # Assert
    assert result.exit_code == 0, result.output
    mock_create.assert_not_called()
    assert "Skipping T1" in result.output
    assert "github_issue: 100" in result.output or "100" in result.output


# ---------------------------------------------------------------------------
# Test: github_issue field is written on success
# ---------------------------------------------------------------------------


def test_writes_github_issue_field(tmp_path: Path) -> None:
    """After successful issue creation, github_issue: 481 is written to YAML."""
    # Arrange
    task_file = _make_task_file(tmp_path)
    assert "github_issue" not in task_file.read_text()

    tasks = parse_task_file(task_file)
    assert len(tasks) == 1

    # Act
    _write_github_issue_field(tasks[0], 481)

    # Assert
    updated = task_file.read_text()
    assert "github_issue: 481" in updated

    # Ensure other fields are preserved.
    assert "task_id: T1" in updated or "task: T1" in updated
    assert "Implement the feature" in updated


# ---------------------------------------------------------------------------
# Test: infer_task_type heuristics
# ---------------------------------------------------------------------------

_TYPE_CASES: list[tuple[str, str]] = [
    ("Research the options for X", "research"),
    ("Investigate performance regression", "research"),
    ("Explore new approach for Y", "research"),
    ("Implement the migration script", "implement"),
    ("Add support for --dry-run flag", "implement"),
    ("Build the cache writer", "implement"),
    ("Create the task record class", "implement"),
    ("Review the implementation", "review"),
    ("Audit the test coverage", "review"),
    ("Check for edge cases", "review"),
    ("Fix the broken YAML parser", "fix"),
    ("Repair incorrect status handling", "fix"),
    ("Correct the path calculation", "fix"),
    ("Update skill documentation", "docs"),
    ("Write doc comments for module", "docs"),
    ("Unknown title with no keywords", "implement"),  # default
]


@pytest.mark.parametrize(("title", "expected"), _TYPE_CASES)
def test_task_type_inference(title: str, expected: str) -> None:
    """Each heuristic keyword maps to the correct task_type."""
    # Act
    result = infer_task_type(title)

    # Assert
    assert result == expected, f"infer_task_type({title!r}) = {result!r}, want {expected!r}"


# ---------------------------------------------------------------------------
# Test: partial failure continues to next task
# ---------------------------------------------------------------------------


def test_partial_failure_continues(tmp_path: Path) -> None:
    """If the first create_task_issue call fails, the second task is still processed."""
    # Arrange
    task_file = _make_two_task_file(tmp_path)
    tasks = parse_task_file(task_file)
    assert len(tasks) == 2

    from typer.testing import CliRunner

    from migrate_tasks_to_github import app

    runner = CliRunner()

    success_issue = _make_mock_issue(482)

    def _side_effect(repo, parent, sam_task, **kwargs):
        if sam_task.task_id == "T1":
            msg = "GitHub API error"
            raise RuntimeError(msg)
        return success_issue

    fake_bc = tmp_path / "bc"
    fake_bc.mkdir()

    with (
        patch("migrate_tasks_to_github._BACKLOG_CORE", fake_bc),
        patch("migrate_tasks_to_github.SamTask") as mock_sam_cls,
        patch("migrate_tasks_to_github.get_github") as mock_gh,
        patch("migrate_tasks_to_github.create_task_issue", side_effect=_side_effect),
    ):
        mock_gh.return_value = MagicMock()
        mock_sam_cls.side_effect = lambda **kw: MagicMock(task_id=kw["task_id"])

        result = runner.invoke(app, ["--task-file", str(task_file), "--parent-issue", "480"])

    assert result.exit_code == 0, result.output

    # The second task's github_issue field should be written (issue 482).
    updated_content = task_file.read_text()
    assert "github_issue: 482" in updated_content


# ---------------------------------------------------------------------------
# Test: cache file is written after successful migration
# ---------------------------------------------------------------------------


def test_writes_cache_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """After live migration, sam-tasks-{slug}.json cache is written."""
    # Arrange
    task_file = _make_task_file(tmp_path)
    tasks = parse_task_file(task_file)
    assert len(tasks) == 1

    # Act: call _write_cache directly (bypasses GitHub API).
    # Pass tmp_path as project_root so dh_paths.context_dir() does not attempt
    # git auto-detection (which fails in a tmp directory with no git repo).
    task_rec = tasks[0]
    cache_path = _write_cache("my-feature", 480, [(task_rec, 481)], project_root=tmp_path)

    # Assert: file exists.
    assert cache_path.exists()

    # Assert: valid JSON with "tasks" key.
    data = json.loads(cache_path.read_text())
    assert "tasks" in data
    assert isinstance(data["tasks"], list)
    assert len(data["tasks"]) == 1
    assert data["tasks"][0]["issue_number"] == 481
    assert data["tasks"][0]["task_id"] == "T1"
    assert data["feature_slug"] == "my-feature"
    assert data["parent_issue_number"] == 480
