"""Unit tests for the four SAM task functions added to backlog_core/operations.py.

Covers:
- create_sam_task: success, GitHub unavailable, sub-issue link failure
- get_sam_tasks: online fetch, offline with cache, offline no cache, cache write
- update_sam_task_status: success (updated=True), no-change (updated=False)
- get_ready_sam_tasks: dependency resolution, cross-feature dep treated as satisfied

All GitHub calls are mocked at the operations.py import boundary using pytest-mock.
Cache I/O is isolated with monkeypatch on Path.home() to avoid writing to the real
~/.claude/context/ directory.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING, cast

import dh_paths
import pytest
from backlog_core.models import GitHubUnavailableError, Output
from backlog_core.operations import create_sam_task, get_ready_sam_tasks, get_sam_tasks, update_sam_task_status

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_sub_issue(
    *,
    number: int = 100,
    title: str = "Test task",
    html_url: str = "https://github.com/org/repo/issues/100",
    body: str = "",
) -> dict:
    """Return a dict mimicking a GraphQL IssueNode with number, title, body, etc."""
    return {
        "id": f"I_{number}",
        "number": number,
        "title": title,
        "state": "OPEN",
        "body": body,
        "createdAt": "",
        "updatedAt": "",
        "labels": [],
        "milestone": None,
        "assignees": [],
    }


def _make_sam_task_body(
    task_id: str = "T1",
    feature: str = "my-feature",
    status: str = "not-started",
    agent: str = "context-gathering",
    priority: int = 1,
    skills: list[str] | None = None,
    dependencies: list[str] | None = None,
) -> str:
    """Build a minimal issue body with a sam:task YAML block."""
    skills_yaml = ", ".join(f'"{s}"' for s in (skills or []))
    deps_yaml = ", ".join(f'"{d}"' for d in (dependencies or []))
    return (
        "## What\n\nDo the thing.\n\n"
        f"<!-- sam:task\n"
        f"task_id: {task_id}\n"
        f"feature: {feature}\n"
        f"task_type: implement\n"
        f"status: {status}\n"
        f"agent: {agent}\n"
        f"priority: {priority}\n"
        f"skills: [{skills_yaml}]\n"
        f"dependencies: [{deps_yaml}]\n"
        "-->\n"
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect DH_STATE_HOME to tmp_path so cache files are isolated.

    Tests: Cache I/O isolation.
    How: Sets DH_STATE_HOME env var so dh_paths.context_dir() resolves under tmp_path.
    Why: Prevents tests from writing to or reading from the real ~/.dh/projects/.
    """
    dh_home = tmp_path / "dh"
    dh_home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("DH_STATE_HOME", str(dh_home))
    return dh_home


# ---------------------------------------------------------------------------
# create_sam_task tests
# ---------------------------------------------------------------------------


class TestCreateSamTask:
    """Unit tests for create_sam_task().

    Tests the intermediary layer that constructs a SamTask, calls get_github(),
    and delegates to github.create_task_issue(). All GitHub I/O is mocked.
    """

    def test_create_sam_task_success(self, mocker: MockerFixture) -> None:
        """create_sam_task returns issue_number, title, url when create_task_issue succeeds.

        Tests: create_sam_task happy path.
        How: Mock get_github and create_task_issue; verify return dict shape.
        Why: Verifies the operations layer correctly wraps the github layer and
             returns the expected response shape for the MCP tool caller.
        """
        # Arrange
        mock_repo = mocker.MagicMock()
        mock_issue = {
            "id": "I_42",
            "number": 42,
            "title": "[my-feature/T1] implement: Do the thing",
            "state": "OPEN",
            "body": "",
            "createdAt": "",
            "updatedAt": "",
            "labels": [],
            "milestone": None,
            "assignees": [],
        }

        mocker.patch("backlog_core.operations.get_github", return_value=mock_repo)
        mocker.patch("backlog_core.operations.create_task_issue", return_value=mock_issue)

        # Act
        result = create_sam_task(
            parent_issue_number=480,
            task_id="T1",
            feature="my-feature",
            task_type="implement",
            agent="context-gathering",
            priority=1,
            skills=["python3-development"],
            dependencies=[],
            description="Do the thing",
        )

        # Assert
        assert result["issue_number"] == 42
        assert result["title"] == "[my-feature/T1] implement: Do the thing"
        assert result["url"] == ""  # IssueNode has no url field; implementation returns ""
        assert "messages" in result
        assert "warnings" in result

    def test_create_sam_task_forwards_repo(self, mocker: MockerFixture) -> None:
        """create_sam_task passes the explicit repository to GitHub lookup."""
        mock_repo = mocker.Mock()
        get_github = mocker.patch("backlog_core.operations.get_github", return_value=mock_repo)
        mocker.patch("backlog_core.operations.create_task_issue", return_value={"number": 42, "title": "T1"})

        create_sam_task(
            parent_issue_number=480,
            task_id="T1",
            feature="my-feature",
            task_type="implement",
            agent="agent",
            priority=1,
            skills=[],
            dependencies=[],
            description="Do the thing",
            repo="acme/project",
        )

        get_github.assert_called_once_with("acme/project")

    def test_create_sam_task_positional_output_keeps_default_repo(self, mocker: MockerFixture) -> None:
        """The legacy positional output argument remains output, not repo."""
        mock_repo = mocker.Mock()
        get_github = mocker.patch("backlog_core.operations.get_github", return_value=mock_repo)
        create_issue = mocker.patch(
            "backlog_core.operations.create_task_issue", return_value={"number": 42, "title": "T1"}
        )
        output = Output()

        create_sam_task(480, "T1", "my-feature", "implement", "agent", 1, [], [], "Do the thing", None, None, output)

        get_github.assert_called_once_with("")
        create_issue.assert_called_once()
        assert create_issue.call_args.kwargs["output"] is output

    def test_create_sam_task_github_unavailable(self, mocker: MockerFixture) -> None:
        """create_sam_task raises GitHubUnavailableError when get_github fails.

        Tests: create_sam_task error propagation.
        How: Mock get_github to raise GitHubUnavailableError; assert it propagates.
        Why: write operations must fail-fast when GitHub token is absent —
             callers (MCP server) catch BacklogError and return an error dict.
        """
        # Arrange
        mocker.patch("backlog_core.operations.get_github", side_effect=GitHubUnavailableError("No token"))

        # Act / Assert
        with pytest.raises(GitHubUnavailableError, match="No token"):
            create_sam_task(
                parent_issue_number=480,
                task_id="T1",
                feature="my-feature",
                task_type="implement",
                agent="context-gathering",
                priority=1,
                skills=[],
                dependencies=[],
                description="Do the thing",
            )

    def test_create_sam_task_link_failure(self, mocker: MockerFixture) -> None:
        """create_sam_task returns zeroed dict when create_task_issue returns None.

        Tests: create_sam_task sub-issue link partial failure path.
        How: Mock create_task_issue to return None (issue created but not linked).
        Why: Ensures the function handles partial failure gracefully without raising,
             so the MCP caller receives a deterministic response rather than an exception.
        """
        # Arrange
        mock_repo = mocker.MagicMock()
        mocker.patch("backlog_core.operations.get_github", return_value=mock_repo)
        mocker.patch("backlog_core.operations.create_task_issue", return_value=None)

        # Act
        result = create_sam_task(
            parent_issue_number=480,
            task_id="T1",
            feature="my-feature",
            task_type="implement",
            agent="context-gathering",
            priority=1,
            skills=[],
            dependencies=[],
            description="Do the thing",
        )

        # Assert
        assert result["issue_number"] == 0
        assert result["title"] == ""
        assert result["url"] == ""


# ---------------------------------------------------------------------------
# get_sam_tasks tests
# ---------------------------------------------------------------------------


class TestGetSamTasks:
    """Unit tests for get_sam_tasks().

    Tests online fetch (via mocked get_task_issues), offline cache fallback,
    and cache write behaviour. All GitHub I/O and Path.home() are isolated.
    """

    def test_get_sam_tasks_online(self, mocker: MockerFixture, isolated_home: Path) -> None:
        """get_sam_tasks returns tasks dict when GitHub is available.

        Tests: get_sam_tasks happy path with GitHub available.
        How: Mock try_get_github and get_task_issues; verify return dict shape and task fields.
        Why: Verifies the function correctly fetches sub-issues and maps them to task dicts.
        """
        # Arrange
        mock_repo = mocker.MagicMock()
        body = _make_sam_task_body(task_id="T1", feature="my-feature", status="not-started")
        mock_si = _make_mock_sub_issue(number=101, title="[my-feature/T1] implement: thing", body=body)

        mocker.patch("backlog_core.operations.try_get_github", return_value=mock_repo)
        mocker.patch("backlog_core.operations.get_task_issues", return_value=[mock_si])

        # Act
        result = get_sam_tasks(parent_issue_number=480, refresh_cache=False)

        # Assert
        assert result["count"] == 1
        assert result["parent_issue_number"] == 480
        tasks = result["tasks"]
        assert isinstance(tasks, list)
        assert len(tasks) == 1
        assert tasks[0]["issue_number"] == 101
        assert tasks[0]["task_id"] == "T1"
        assert tasks[0]["feature"] == "my-feature"

    def test_get_sam_tasks_offline_with_cache(self, mocker: MockerFixture, tmp_path: Path, isolated_home: Path) -> None:
        """get_sam_tasks returns cached tasks when GitHub is unavailable but cache exists.

        Tests: get_sam_tasks offline fallback path.
        How: Mock try_get_github to return None; pre-write cache file in tmp_path;
             assert cached tasks are returned.
        Why: Ensures agents can query task status even when GitHub is unreachable,
             using the last-known-good cache as the data source.
        """
        # Arrange: create cache file in the isolated DH context directory
        cache_dir = dh_paths.context_dir()
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_data = {
            "feature_slug": "my-feature",
            "parent_issue_number": 480,
            "synced_at": "2026-03-06T12:00:00+00:00",
            "tasks": [
                {
                    "issue_number": 101,
                    "task_id": "T1",
                    "feature": "my-feature",
                    "status": "not-started",
                    "agent": "context-gathering",
                    "priority": 1,
                    "skills": ["python3-development"],
                    "dependencies": [],
                }
            ],
            "count": 1,
        }
        cache_file = cache_dir / "sam-tasks-my-feature.json"
        cache_file.write_text(json.dumps(cache_data), encoding="utf-8")

        mocker.patch("backlog_core.operations.try_get_github", return_value=None)

        # Act
        result = get_sam_tasks(parent_issue_number=480)

        # Assert
        assert result["count"] == 1
        assert result["parent_issue_number"] == 480
        tasks = result["tasks"]
        assert isinstance(tasks, list)
        assert len(tasks) == 1
        assert tasks[0]["task_id"] == "T1"
        # Verify a warning was emitted about GitHub unavailability
        warnings = result.get("warnings", [])
        assert isinstance(warnings, list)
        assert any("WARNING" in w for w in warnings)

    def test_get_sam_tasks_offline_no_cache(self, mocker: MockerFixture, isolated_home: Path) -> None:
        """get_sam_tasks returns empty tasks when GitHub is unavailable and no cache exists.

        Tests: get_sam_tasks double-offline path.
        How: Mock try_get_github to return None; no cache file in tmp_path.
        Why: Ensures the function degrades gracefully returning an empty list with a warning,
             rather than raising an exception that would halt the orchestrator.
        """
        # Arrange
        mocker.patch("backlog_core.operations.try_get_github", return_value=None)

        # Act
        result = get_sam_tasks(parent_issue_number=480)

        # Assert
        assert result["tasks"] == []
        assert result["count"] == 0
        assert result["parent_issue_number"] == 480
        warnings = result.get("warnings", [])
        assert isinstance(warnings, list)
        assert any("WARNING" in w for w in warnings)

    def test_get_sam_tasks_writes_cache(self, mocker: MockerFixture, isolated_home: Path) -> None:
        """get_sam_tasks writes the cache file after a successful GitHub fetch.

        Tests: get_sam_tasks cache write path.
        How: Mock GitHub functions; run with refresh_cache=True; assert cache file exists
             with valid JSON and correct parent_issue_number.
        Why: The cache file is the offline fallback. Verifying it is written ensures that
             subsequent offline requests return correct data.
        """
        # Arrange
        mock_repo = mocker.MagicMock()
        body = _make_sam_task_body(task_id="T1", feature="cache-feature", status="not-started")
        mock_si = _make_mock_sub_issue(number=202, title="[cache-feature/T1] task", body=body)

        mocker.patch("backlog_core.operations.try_get_github", return_value=mock_repo)
        mocker.patch("backlog_core.operations.get_task_issues", return_value=[mock_si])

        # Act
        result = get_sam_tasks(parent_issue_number=555, refresh_cache=True)

        # Assert: cache file was written to the isolated DH context directory
        cache_dir = dh_paths.context_dir()
        cache_file = cache_dir / "sam-tasks-cache-feature.json"
        assert cache_file.exists(), "Cache file was not written"
        cached = json.loads(cache_file.read_text(encoding="utf-8"))
        assert cached["parent_issue_number"] == 555
        assert cached["feature_slug"] == "cache-feature"
        assert datetime.fromisoformat(cached["synced_at"]).tzinfo is not None
        assert cached["count"] == 1
        assert len(cached["tasks"]) == 1
        # Result should also have the correct data
        assert result["count"] == 1


# ---------------------------------------------------------------------------
# update_sam_task_status tests
# ---------------------------------------------------------------------------


class TestUpdateSamTaskStatus:
    """Unit tests for update_sam_task_status().

    Tests the success (status changed) and no-change (status already matches) paths.
    """

    def test_update_sam_task_status_success(self, mocker: MockerFixture) -> None:
        """update_sam_task_status returns updated=True when the status was changed.

        Tests: update_sam_task_status happy path.
        How: Mock get_github and update_task_status returning True.
        Why: Verifies the operations layer maps the bool return value to the correct
             response dict shape for the MCP tool caller.
        """
        # Arrange
        mock_repo = mocker.MagicMock()
        mocker.patch("backlog_core.operations.get_github", return_value=mock_repo)
        mocker.patch("backlog_core.operations.update_task_status", return_value=True)

        # Act
        result = update_sam_task_status(issue_number=101, new_status="complete")

        # Assert
        assert result["updated"] is True
        assert result["issue_number"] == 101
        assert result["new_status"] == "complete"

    def test_update_sam_task_status_forwards_repo(self, mocker: MockerFixture) -> None:
        """update_sam_task_status passes the explicit repository to GitHub lookup."""
        mock_repo = mocker.Mock()
        get_github = mocker.patch("backlog_core.operations.get_github", return_value=mock_repo)
        mocker.patch("backlog_core.operations.update_task_status", return_value=True)

        update_sam_task_status(issue_number=101, new_status="complete", repo="acme/project")

        get_github.assert_called_once_with("acme/project")

    def test_update_sam_task_status_positional_output_keeps_default_repo(self, mocker: MockerFixture) -> None:
        """The legacy positional output argument remains output, not repo."""
        mock_repo = mocker.Mock()
        get_github = mocker.patch("backlog_core.operations.get_github", return_value=mock_repo)
        update_status = mocker.patch("backlog_core.operations.update_task_status", return_value=True)
        output = Output()

        update_sam_task_status(101, "complete", output)

        get_github.assert_called_once_with("")
        update_status.assert_called_once()
        assert update_status.call_args.kwargs["output"] is output

    def test_update_sam_task_status_no_change(self, mocker: MockerFixture) -> None:
        """update_sam_task_status returns updated=False without error when status unchanged.

        Tests: update_sam_task_status no-op path.
        How: Mock update_task_status returning False (status already matches).
        Why: The no-op case must not raise and must clearly communicate that no
             GitHub write occurred — callers may rely on this to avoid redundant syncs.
        """
        # Arrange
        mock_repo = mocker.MagicMock()
        mocker.patch("backlog_core.operations.get_github", return_value=mock_repo)
        mocker.patch("backlog_core.operations.update_task_status", return_value=False)

        # Act
        result = update_sam_task_status(issue_number=101, new_status="complete")

        # Assert
        assert result["updated"] is False
        assert result["issue_number"] == 101
        assert result["new_status"] == "complete"


# ---------------------------------------------------------------------------
# get_ready_sam_tasks tests
# ---------------------------------------------------------------------------


class TestGetReadySamTasks:
    """Unit tests for get_ready_sam_tasks().

    Tests dependency resolution logic: tasks blocked by incomplete deps are excluded,
    tasks with all terminal deps are included, and cross-feature #N deps are always satisfied.
    """

    def test_get_ready_sam_tasks_dep_resolution(self, mocker: MockerFixture, isolated_home: Path) -> None:
        """get_ready_sam_tasks excludes T2 while T1 is not-started, includes T2 when T1 is complete.

        Tests: get_ready_sam_tasks dependency gate logic.
        How: First call: T1 not-started, T2 depends on T1 — assert T2 absent.
             Second call: T1 complete, T2 depends on T1 — assert T2 present.
        Why: Verifies the inline readiness logic correctly resolves feature-scoped
             dependencies, mirroring implementation_manager.py get_ready_tasks().
        """
        # Arrange: T1 not-started, T2 depends on T1
        mock_repo = mocker.MagicMock()
        body_t1_not_started = _make_sam_task_body(
            task_id="T1", feature="dep-feature", status="not-started", dependencies=[]
        )
        body_t2 = _make_sam_task_body(task_id="T2", feature="dep-feature", status="not-started", dependencies=["T1"])
        mock_si_t1 = _make_mock_sub_issue(number=201, title="[dep-feature/T1] task1", body=body_t1_not_started)
        mock_si_t2 = _make_mock_sub_issue(number=202, title="[dep-feature/T2] task2", body=body_t2)

        mocker.patch("backlog_core.operations.try_get_github", return_value=mock_repo)
        mock_get_issues = mocker.patch("backlog_core.operations.get_task_issues", return_value=[mock_si_t1, mock_si_t2])

        # Act: T1 not-started — T2 should be blocked
        result_blocked = get_ready_sam_tasks(parent_issue_number=480)
        ready_tasks_blocked = cast("list[dict[str, object]]", result_blocked["ready_tasks"])
        ready_ids = [str(t["id"]) for t in ready_tasks_blocked]

        # Assert: T1 is ready (no deps), T2 is blocked (T1 not complete)
        assert "T1" in ready_ids, "T1 should be ready (no dependencies)"
        assert "T2" not in ready_ids, "T2 should be blocked while T1 is not-started"

        # Arrange: T1 now complete, T2 should unblock
        body_t1_complete = _make_sam_task_body(task_id="T1", feature="dep-feature", status="complete", dependencies=[])
        mock_si_t1_done = _make_mock_sub_issue(number=201, title="[dep-feature/T1] task1", body=body_t1_complete)
        mock_get_issues.return_value = [mock_si_t1_done, mock_si_t2]

        # Act: T1 complete — T2 should now be ready
        result_unblocked = get_ready_sam_tasks(parent_issue_number=480)
        ready_tasks_unblocked = cast("list[dict[str, object]]", result_unblocked["ready_tasks"])
        ready_ids_after = [str(t["id"]) for t in ready_tasks_unblocked]

        # Assert: T2 is now ready
        assert "T2" in ready_ids_after, "T2 should be ready when T1 is complete"
        assert "T1" not in ready_ids_after, "T1 is complete — not returned as ready"

    def test_get_ready_sam_tasks_cross_feature_dep(self, mocker: MockerFixture, isolated_home: Path) -> None:
        """get_ready_sam_tasks treats cross-feature #N deps as always-satisfied.

        Tests: get_ready_sam_tasks cross-feature dependency handling.
        How: Create a task with dependencies: ["#479"] — a cross-feature GitHub issue ref.
             Assert the task appears in ready_tasks despite #479 having no known local status.
        Why: Cross-feature dependencies reference GitHub issues outside this feature's scope.
             They cannot be resolved by scanning local tasks, so they are treated as satisfied
             to avoid permanently blocking tasks that depend on external work.
        """
        # Arrange
        mock_repo = mocker.MagicMock()
        body_cross = _make_sam_task_body(
            task_id="T3", feature="cross-feature", status="not-started", dependencies=["#479"]
        )
        mock_si = _make_mock_sub_issue(number=301, title="[cross-feature/T3] cross-dep task", body=body_cross)

        mocker.patch("backlog_core.operations.try_get_github", return_value=mock_repo)
        mocker.patch("backlog_core.operations.get_task_issues", return_value=[mock_si])

        # Act
        result = get_ready_sam_tasks(parent_issue_number=480)
        ready_tasks = cast("list[dict[str, object]]", result["ready_tasks"])
        ready_ids = [str(t["id"]) for t in ready_tasks]

        # Assert: T3 is ready despite having a cross-feature dep on #479
        assert "T3" in ready_ids, (
            "Task with cross-feature dep #479 should be treated as ready "
            "(external deps are always considered satisfied)"
        )
        assert result["count"] == 1
        # Verify issue_number is propagated to ready task
        ready_t3 = next(t for t in ready_tasks if t["id"] == "T3")
        assert ready_t3["issue_number"] == 301
