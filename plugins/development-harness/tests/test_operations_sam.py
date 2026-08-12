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

from typing import TYPE_CHECKING, cast

import pytest
from backlog_core.backend_protocol import BacklogConfig, reset_config, set_config
from backlog_core.backends.memory_backend import InMemoryBackend
from backlog_core.models import ContentUnavailableError, GitHubUnavailableError, Output
from backlog_core.operations import create_sam_task, get_ready_sam_tasks, get_sam_tasks, update_sam_task_status
from sam_schema.core.backends.content import ContentTaskProvider
from sam_schema.core.models import Task, TaskStatus

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


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
    def test_get_sam_tasks_reads_native_plan_content_without_github_or_context_cache(
        self, mocker: MockerFixture
    ) -> None:
        provider = InMemoryBackend()
        task_provider = ContentTaskProvider(provider)
        task_provider.create_plan(
            "my-feature",
            "Do the work",
            [
                Task(
                    id="T1",
                    title="Implement thing",
                    status=TaskStatus.NOT_STARTED,
                    agent="some-agent",
                    priority=2,
                    skills=["python"],
                    github_issue=101,
                )
            ],
            issue=480,
        )
        set_config(BacklogConfig(backend=provider))
        mocker.patch("backlog_core.operations.try_get_github", side_effect=AssertionError("GitHub bypass"))

        try:
            result = get_sam_tasks(parent_issue_number=480)
        finally:
            reset_config()

        assert result["count"] == 1
        assert result["parent_issue_number"] == 480
        assert result["stale"] is False
        assert result["unavailable"] is False
        assert result["tasks"] == [
            {
                "task_id": "T1",
                "feature": "my-feature",
                "status": "not-started",
                "agent": "some-agent",
                "priority": 2,
                "skills": ["python"],
                "dependencies": [],
                "issue_number": 101,
                "issue_url": "",
                "title": "Implement thing",
            }
        ]

    def test_get_sam_tasks_accepts_opaque_parent_reference(self) -> None:
        provider = InMemoryBackend()
        task_provider = ContentTaskProvider(provider)
        plan = task_provider.create_plan(
            "opaque-feature", "Do the work", [Task(id="T1", title="Task", status=TaskStatus.NOT_STARTED)]
        )
        task_provider.set_owner(plan["plan_id"], "bd-a1b2")
        set_config(BacklogConfig(backend=provider))

        try:
            result = get_sam_tasks(parent_issue_number="bd-a1b2")
        finally:
            reset_config()

        assert result["count"] == 1
        assert result["parent_issue_number"] == "bd-a1b2"

    def test_get_sam_tasks_surfaces_provider_staleness(self, mocker: MockerFixture) -> None:
        provider = InMemoryBackend()
        task_provider = ContentTaskProvider(provider)
        task_provider.create_plan(
            "stale-feature", "Do the work", [Task(id="T1", title="Task", status=TaskStatus.NOT_STARTED)], issue=480
        )
        original_list_content = provider.list_content
        mocker.patch.object(
            provider,
            "list_content",
            side_effect=lambda query: [
                record.model_copy(update={"stale": True}) for record in original_list_content(query)
            ],
        )
        set_config(BacklogConfig(backend=provider))

        try:
            result = get_sam_tasks(parent_issue_number=480)
        finally:
            reset_config()

        assert result["stale"] is True
        assert result["unavailable"] is False
        assert result["count"] == 1
        assert result["warnings"]

    def test_get_sam_tasks_returns_explicit_unavailable_result(self, mocker: MockerFixture) -> None:
        provider = InMemoryBackend()
        mocker.patch.object(provider, "list_content", side_effect=ContentUnavailableError("offline cache miss"))
        set_config(BacklogConfig(backend=provider))

        try:
            result = get_sam_tasks(parent_issue_number=480)
        finally:
            reset_config()

        assert result["tasks"] == []
        assert result["count"] == 0
        assert result["stale"] is False
        assert result["unavailable"] is True
        assert result["errors"] == ["offline cache miss"]


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

    def test_get_ready_sam_tasks_dep_resolution(self, mocker: MockerFixture) -> None:
        """get_ready_sam_tasks excludes T2 while T1 is not-started, includes T2 when T1 is complete.

        Tests: get_ready_sam_tasks dependency gate logic.
        How: First call: T1 not-started, T2 depends on T1 — assert T2 absent.
             Second call: T1 complete, T2 depends on T1 — assert T2 present.
        Why: Verifies the inline readiness logic correctly resolves feature-scoped
             dependencies, mirroring implementation_manager.py get_ready_tasks().
        """
        tasks = [
            {"task_id": "T1", "feature": "dep-feature", "status": "not-started", "dependencies": []},
            {"task_id": "T2", "feature": "dep-feature", "status": "not-started", "dependencies": ["T1"]},
        ]
        get_tasks = mocker.patch("backlog_core.operations.get_sam_tasks", return_value={"tasks": tasks})

        # Act: T1 not-started — T2 should be blocked
        result_blocked = get_ready_sam_tasks(parent_issue_number=480)
        ready_tasks_blocked = cast("list[dict[str, object]]", result_blocked["ready_tasks"])
        ready_ids = [str(t["id"]) for t in ready_tasks_blocked]

        # Assert: T1 is ready (no deps), T2 is blocked (T1 not complete)
        assert "T1" in ready_ids, "T1 should be ready (no dependencies)"
        assert "T2" not in ready_ids, "T2 should be blocked while T1 is not-started"

        get_tasks.return_value = {"tasks": [{**tasks[0], "status": "complete"}, tasks[1]]}

        # Act: T1 complete — T2 should now be ready
        result_unblocked = get_ready_sam_tasks(parent_issue_number=480)
        ready_tasks_unblocked = cast("list[dict[str, object]]", result_unblocked["ready_tasks"])
        ready_ids_after = [str(t["id"]) for t in ready_tasks_unblocked]

        # Assert: T2 is now ready
        assert "T2" in ready_ids_after, "T2 should be ready when T1 is complete"
        assert "T1" not in ready_ids_after, "T1 is complete — not returned as ready"

    def test_get_ready_sam_tasks_cross_feature_dep(self, mocker: MockerFixture) -> None:
        """get_ready_sam_tasks treats cross-feature #N deps as always-satisfied.

        Tests: get_ready_sam_tasks cross-feature dependency handling.
        How: Create a task with dependencies: ["#479"] — a cross-feature GitHub issue ref.
             Assert the task appears in ready_tasks despite #479 having no known local status.
        Why: Cross-feature dependencies reference GitHub issues outside this feature's scope.
             They cannot be resolved by scanning local tasks, so they are treated as satisfied
             to avoid permanently blocking tasks that depend on external work.
        """
        mocker.patch(
            "backlog_core.operations.get_sam_tasks",
            return_value={
                "tasks": [
                    {
                        "task_id": "T3",
                        "feature": "cross-feature",
                        "status": "not-started",
                        "dependencies": ["#479"],
                        "issue_number": 301,
                    }
                ]
            },
        )

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
