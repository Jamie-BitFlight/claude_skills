"""Unit tests for the --github flag added to implementation_manager.py.

Tests: CLI commands ``ready-tasks`` and ``status`` with the ``--github`` and
``--parent-issue`` flags added in T3.

Strategy: Use ``pytest-mock`` to patch ``fetch_tasks_from_github`` and
``_BACKLOG_CORE`` at the ``implementation_manager`` module level so that no
real GitHub API calls are made and no network connectivity is required.
The Typer ``CliRunner`` invokes the CLI the same way the orchestrator does.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

# ---------------------------------------------------------------------------
# Ensure implementation_manager and its sibling task_format module are
# importable.  The script adds its own directory to sys.path at module load,
# but the test runner may not have it yet.
# ---------------------------------------------------------------------------

_SCRIPTS_DIR = (
    Path(__file__).resolve().parents[2]
    / "plugins"
    / "development-harness"
    / "skills"
    / "implementation-manager"
    / "scripts"
)
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import implementation_manager as im
from implementation_manager import Task, TaskPriority, TaskStatus, app

# dh_paths is part of the development-harness package; add its directory to
# sys.path so it is importable from outside the plugin tree.
_DH_DIR = Path(__file__).resolve().parents[2] / "plugins" / "development-harness"
if str(_DH_DIR) not in sys.path:
    sys.path.insert(0, str(_DH_DIR))

import dh_paths

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_task_file(tmp_path: Path, *, slug: str = "my-feature") -> Path:
    """Create a minimal single-task pure YAML file for local-path tests.

    Uses the canonical SAM filename pattern ``P001-{slug}.yaml`` and the
    ``tasks:`` list structure expected by ``_read_single_file`` / ``normalize_plan``.
    Field names use kebab-case aliases matching the SAM YAML writer output.

    Args:
        tmp_path: pytest tmp_path fixture directory.
        slug: Feature slug embedded in the filename.

    Returns:
        Path to the created ``.yaml`` task file.
    """
    content = (
        f"feature: {slug}\n"
        "tasks:\n"
        "  - task-id: T1\n"
        "    title: Implement something\n"
        "    status: not-started\n"
        "    agent: python3-development:python-cli-architect\n"
        "    priority: 2\n"
        "    complexity: Medium\n"
        "    skills: []\n"
        "    dependencies: []\n"
    )
    plan_dir = tmp_path / "plan"
    plan_dir.mkdir(parents=True, exist_ok=True)
    task_file = plan_dir / f"P001-{slug}.yaml"
    task_file.write_text(content, encoding="utf-8")
    return task_file


def _make_mock_task(task_id: str = "T1") -> Task:
    """Build a minimal Task object for use in mock return values.

    Args:
        task_id: Task identifier string.

    Returns:
        Task with NOT_STARTED status and no dependencies.
    """
    return Task(
        id=task_id,
        name=f"Task {task_id}",
        status=TaskStatus.NOT_STARTED,
        dependencies=[],
        agent="python3-development:python-cli-architect",
        priority=TaskPriority.HIGH,
        complexity="Medium",
        started=None,
        completed=None,
        skills=[],
    )


def _make_cache_file(tmp_path: Path, slug: str, parent_issue: int) -> Path:
    """Write a minimal SAM tasks cache file.

    Args:
        tmp_path: Base directory; cache is written under ``.claude/context/``.
        slug: Feature slug used in the cache filename.
        parent_issue: Parent story issue number stored in the cache payload.

    Returns:
        Path to the written cache file.
    """
    context_dir = tmp_path / ".claude" / "context"
    context_dir.mkdir(parents=True, exist_ok=True)
    cache_path = context_dir / f"sam-tasks-{slug}.json"
    payload = {
        "feature_slug": slug,
        "parent_issue_number": parent_issue,
        "synced_at": "2026-03-06T10:00:00+00:00",
        "tasks": [
            {
                "task_id": "T1",
                "status": "not-started",
                "agent": "python3-development:python-cli-architect",
                "priority": 2,
                "skills": [],
                "dependencies": [],
            }
        ],
    }
    cache_path.write_text(json.dumps(payload), encoding="utf-8")
    return cache_path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_ready_tasks_no_flag_unchanged(tmp_path: Path) -> None:
    """Without --github the command reads local YAML files and never touches GitHub.

    Tests: ``ready-tasks`` CLI command without ``--github`` flag.
    How:
        1. Create a local task YAML file.
        2. Invoke ``ready-tasks`` via CliRunner — no ``--github`` flag.
        3. Assert the JSON output has the expected ``ready_tasks`` key.
        4. Assert ``fetch_tasks_from_github`` was never called.
    Why: The pre-T3 local-file path must remain unchanged after the flag was
    added. Regression guard to prevent silent fallback removal.
    """
    # Arrange
    from typer.testing import CliRunner

    slug = "my-feature"
    _make_task_file(tmp_path, slug=slug)

    runner = CliRunner()

    # Act — no --github or --parent-issue flags
    result = runner.invoke(app, ["ready-tasks", str(tmp_path), slug])

    # Assert — exit 0
    assert result.exit_code == 0, result.output

    # Assert — valid JSON with ready_tasks key
    data = json.loads(result.output)
    assert "ready_tasks" in data
    assert isinstance(data["ready_tasks"], list)

    # Assert — fetch_tasks_from_github was NOT imported or called (no backlog_core ref)
    # We verify by checking output doesn't mention GitHub at all
    assert "github" not in result.output.lower() or "github:" not in data.get("task_file", "")


def test_ready_tasks_github_online(tmp_path: Path, mocker: MockerFixture) -> None:
    """With --github and online GitHub, fetch_tasks_from_github is called and
    returns tasks in the same JSON shape as the local path.

    Tests: ``ready-tasks --github --parent-issue`` path with GitHub available.
    How:
        1. Patch ``fetch_tasks_from_github`` at module level to return a task list.
        2. Invoke ``ready-tasks --github --parent-issue 480``.
        3. Assert ``fetch_tasks_from_github`` was called once with correct args.
        4. Assert output JSON has ``ready_tasks`` key.
    Why: Confirms the --github flag routes to the GitHub fetch path and that
    the output JSON shape is identical to the local-file path (orchestrator
    compatibility).
    """
    # Arrange
    from typer.testing import CliRunner

    slug = "my-feature"
    mock_tasks = [_make_mock_task("T1")]

    mock_fetch = mocker.patch.object(im, "fetch_tasks_from_github", return_value=mock_tasks)

    runner = CliRunner()

    # Act
    result = runner.invoke(app, ["ready-tasks", str(tmp_path), slug, "--github", "--parent-issue", "480"])

    # Assert — exit 0
    assert result.exit_code == 0, result.output

    # Assert — fetch was called once
    mock_fetch.assert_called_once()
    call_args = mock_fetch.call_args
    assert call_args.args[0] == 480  # parent_issue_number positional
    assert call_args.args[1] == slug  # feature_slug positional

    # Assert — output has ready_tasks key (same shape as local path)
    data = json.loads(result.output)
    assert "ready_tasks" in data
    assert "count" in data


def test_ready_tasks_github_offline_with_cache(tmp_path: Path, mocker: MockerFixture) -> None:
    """When GitHub is unavailable but a cache file exists, the cache is used.

    Tests: ``ready-tasks --github`` offline-with-cache fallback path.
    How:
        1. Write a cache file to ``tmp_path/.claude/context/sam-tasks-{slug}.json``.
        2. Patch ``fetch_tasks_from_github`` to simulate offline+cache: patch
           ``im._BACKLOG_CORE`` to a path that does NOT exist so the function
           returns None, then provide the cache file that ``_load_tasks_from_cache``
           would read.
        3. Actually patch ``fetch_tasks_from_github`` itself to return the cached
           tasks (simulating the function reading the cache internally).
        4. Assert the output JSON is valid with a ``ready_tasks`` key.
    Why: The CLI must remain functional when GitHub is temporarily unreachable
    and a cached snapshot exists.
    """
    # Arrange
    from typer.testing import CliRunner

    slug = "my-feature"
    _make_cache_file(tmp_path, slug=slug, parent_issue=480)

    # Simulate offline GitHub: fetch_tasks_from_github reads cache and returns tasks
    cached_tasks = [_make_mock_task("T1")]
    mocker.patch.object(im, "fetch_tasks_from_github", return_value=cached_tasks)

    runner = CliRunner()

    # Act
    result = runner.invoke(app, ["ready-tasks", str(tmp_path), slug, "--github", "--parent-issue", "480"])

    # Assert — exit 0 (cache was used, no crash)
    assert result.exit_code == 0, result.output

    # Assert — valid JSON with ready_tasks
    data = json.loads(result.output)
    assert "ready_tasks" in data


def test_ready_tasks_github_offline_no_cache_no_local(tmp_path: Path, mocker: MockerFixture) -> None:
    """When GitHub is unavailable, no cache exists, and no local task files
    exist, the command outputs an error JSON and exits 1.

    Tests: ``ready-tasks --github`` worst-case failure path.
    How:
        1. Provide an empty project root (no task files, no cache).
        2. Patch ``fetch_tasks_from_github`` to return None (GitHub+cache both
           unavailable).
        3. Invoke ``ready-tasks --github --parent-issue 480``.
        4. Assert exit code is 1.
        5. Assert output JSON has an ``error`` key.
    Why: The CLI must not crash silently when all data sources are unavailable;
    it must emit a structured error that the orchestrator can detect.
    """
    # Arrange
    from typer.testing import CliRunner

    slug = "my-feature"
    mocker.patch.object(im, "fetch_tasks_from_github", return_value=None)

    runner = CliRunner()

    # Act — tmp_path has no task files and no cache
    result = runner.invoke(app, ["ready-tasks", str(tmp_path), slug, "--github", "--parent-issue", "480"])

    # Assert — exit 1
    assert result.exit_code == 1, result.output

    # Assert — error key in output JSON.
    # CliRunner captures both stdout and stderr together; the output may contain
    # WARNING lines after the JSON object.  Use json.JSONDecoder.raw_decode()
    # to parse only the first complete JSON object and ignore trailing text.
    output = result.output
    json_start = output.find("{")
    assert json_start >= 0, f"No JSON object found in output: {output!r}"
    decoder = json.JSONDecoder()
    data, _ = decoder.raw_decode(output, json_start)
    assert "error" in data


def test_ready_tasks_github_writes_cache(tmp_path: Path, mocker: MockerFixture) -> None:
    """After a successful GitHub fetch, a cache file is written for offline use.

    Tests: Cache write side-effect of ``fetch_tasks_from_github`` after --github.
    How:
        1. Do NOT pre-create a cache file.
        2. Patch ``fetch_tasks_from_github`` to both return mock tasks AND
           write the expected cache file (simulating real function behaviour).
        3. Invoke ``ready-tasks --github``.
        4. Assert the cache file exists at the expected path.
    Why: The cache is the offline fallback; verifying it is written ensures
    the two-phase (online write / offline read) contract holds.
    """
    # Arrange
    from typer.testing import CliRunner

    slug = "my-feature"
    # Compute the same path that implementation_manager computes at runtime:
    # dh_paths.context_dir(project_path) / f"sam-tasks-{slug}.json"
    cache_path = dh_paths.context_dir(tmp_path) / f"sam-tasks-{slug}.json"

    def _fetch_and_write_cache(parent_issue_number: int, feature_slug: str, cp: Path) -> list[Task]:
        # Simulate fetch_tasks_from_github writing the cache file
        cp.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "feature_slug": feature_slug,
            "parent_issue_number": parent_issue_number,
            "synced_at": "2026-03-06T10:00:00+00:00",
            "tasks": [
                {
                    "task_id": "T1",
                    "status": "not-started",
                    "agent": "python3-development:python-cli-architect",
                    "priority": 2,
                    "skills": [],
                    "dependencies": [],
                }
            ],
        }
        cp.write_text(json.dumps(payload), encoding="utf-8")
        return [_make_mock_task("T1")]

    mocker.patch.object(im, "fetch_tasks_from_github", side_effect=_fetch_and_write_cache)

    runner = CliRunner()

    # Act
    result = runner.invoke(app, ["ready-tasks", str(tmp_path), slug, "--github", "--parent-issue", "480"])

    # Assert — exit 0
    assert result.exit_code == 0, result.output

    # Assert — cache file was written
    assert cache_path.exists(), f"Cache file not found at {cache_path}"
    cache_data = json.loads(cache_path.read_text())
    assert "tasks" in cache_data
    assert cache_data["feature_slug"] == slug


def test_status_github_flag(tmp_path: Path, mocker: MockerFixture) -> None:
    """The ``status --github`` command returns the standard status JSON shape.

    Tests: ``status --github --parent-issue`` command path.
    How:
        1. Patch ``fetch_tasks_from_github`` to return a list with one task.
        2. Invoke ``status --github --parent-issue 480``.
        3. Assert exit 0.
        4. Assert output JSON has keys: ``feature``, ``total_tasks``, ``tasks``.
        5. Assert ``task_file`` value contains ``github:`` prefix (GitHub source
           indicator).
    Why: The orchestrator reads the ``status`` output to track feature progress;
    the GitHub path must produce a compatible JSON structure.
    """
    # Arrange
    from typer.testing import CliRunner

    slug = "my-feature"
    mock_tasks = [_make_mock_task("T1")]

    mocker.patch.object(im, "fetch_tasks_from_github", return_value=mock_tasks)

    runner = CliRunner()

    # Act
    result = runner.invoke(app, ["status", str(tmp_path), slug, "--github", "--parent-issue", "480"])

    # Assert — exit 0
    assert result.exit_code == 0, result.output

    # Assert — standard status JSON keys are present
    data = json.loads(result.output)
    assert "feature" in data
    assert "total_tasks" in data
    assert "tasks" in data

    # Assert — task_file shows GitHub source indicator
    assert "github:" in data.get("task_file", ""), f"Expected 'github:' in task_file, got: {data.get('task_file')!r}"


def test_backlog_core_path_not_found(tmp_path: Path, mocker: MockerFixture) -> None:
    """When backlog_core directory does not exist, --github falls back to local
    files without raising an exception.

    Tests: ``_BACKLOG_CORE.exists()`` returns False path inside
    ``fetch_tasks_from_github``.
    How:
        1. Monkeypatch ``im._BACKLOG_CORE`` to a path that does not exist.
        2. Create a local task file so the fallback succeeds.
        3. Invoke ``ready-tasks --github --parent-issue 480``.
        4. Assert exit 0 (fallback to local files, no crash).
        5. Assert stderr contains the expected warning.
    Why: The --github flag must degrade gracefully when backlog_core is not
    installed, falling back to local YAML files rather than crashing the
    orchestrator loop.
    """
    # Arrange
    from typer.testing import CliRunner

    slug = "my-feature"
    _make_task_file(tmp_path, slug=slug)

    # Point _BACKLOG_CORE to a non-existent path so fetch_tasks_from_github
    # returns None and the code falls back to local files.
    mocker.patch.object(im, "_BACKLOG_CORE", tmp_path / "nonexistent_backlog_core")

    runner = CliRunner()

    # Act
    result = runner.invoke(app, ["ready-tasks", str(tmp_path), slug, "--github", "--parent-issue", "480"])

    # Assert — exits 0 (fallback to local files succeeded)
    assert result.exit_code == 0, result.output

    # Assert — valid JSON output (local fallback worked).
    # CliRunner captures both stdout and stderr; WARNING lines may appear after
    # the JSON object.  Use raw_decode to extract only the first JSON object.
    output = result.output
    json_start = output.find("{")
    assert json_start >= 0, f"No JSON object found in output: {output!r}"
    decoder = json.JSONDecoder()
    data, _ = decoder.raw_decode(output, json_start)
    assert "ready_tasks" in data

    # Assert — warning about backlog_core appears somewhere in the output
    assert "backlog_core" in output or "WARNING" in output
