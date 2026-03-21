"""Unit tests for task_status_hook.py GitHub sync functionality.

Test suite for ``get_parent_issue_number`` and ``sync_completion_to_github``
added in T4, plus a guard test that ``handle_activity_update`` does not
call any GitHub code.

Scope: Unit tests — all GitHub I/O is mocked via sys.modules injection.

Strategy:
- Inject mock ``backlog_core.github`` into ``sys.modules`` before each test
  that exercises the GitHub path. The conditional import in
  ``sync_completion_to_github`` reads from ``sys.modules`` at call-time.
- Use ``tmp_path`` for all temporary files.
- Each test is fully independent; no shared mutable state.

Why: ``sync_completion_to_github`` wraps its entire body in try/except and
must never raise. Tests confirm both the happy path (GitHub updated) and
failure paths (unavailable, exception) behave correctly without propagating
errors to the caller.
"""

from __future__ import annotations

import json
import sys
import types
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

# ---------------------------------------------------------------------------
# Minimal YAML task fixtures
# ---------------------------------------------------------------------------

_TASK_YAML_WITH_GITHUB_ISSUE = """\
---
feature: test-feature
task: T1
title: Test Task
status: in-progress
agent: general-purpose
priority: 2
complexity: low
dependencies: []
github_issue: 481
---
"""

_TASK_YAML_WITHOUT_GITHUB_ISSUE = """\
---
feature: test-feature
task: T1
title: Test Task
status: in-progress
agent: general-purpose
priority: 2
complexity: low
dependencies: []
---
"""

_TASK_YAML_COMPLETE_STATUS = """\
---
feature: test-feature
task: T1
title: Test Task
status: complete
agent: general-purpose
priority: 2
complexity: low
dependencies: []
---
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_context_file(
    tmp_path: Path, session_id: str, task_file_path: str, task_id: str, parent_issue_number: int | None = None
) -> Path:
    """Write an active-task context JSON file in tmp_path.

    Args:
        tmp_path: pytest tmp_path fixture value.
        session_id: Session identifier used in filename.
        task_file_path: Value for ``task_file_path`` field.
        task_id: Value for ``task_id`` field.
        parent_issue_number: Optional parent issue number to include.

    Returns:
        Path to the created context file.
    """
    context_dir = tmp_path / ".claude" / "context"
    context_dir.mkdir(parents=True, exist_ok=True)
    data: dict[str, object] = {"task_file_path": task_file_path, "task_id": task_id}
    if parent_issue_number is not None:
        data["parent_issue_number"] = parent_issue_number
    context_file = context_dir / f"active-task-{session_id}.json"
    context_file.write_text(json.dumps(data), encoding="utf-8")
    return context_file


def _make_hook_input(
    tmp_path: Path, session_id: str, event_name: str = "SubagentStop", prompt: str = ""
) -> dict[str, object]:
    """Build a minimal hook_input dict for testing.

    Args:
        tmp_path: Root directory used as ``cwd``.
        session_id: Session identifier.
        event_name: Hook event name.
        prompt: Sub-agent prompt (for SubagentStop events).

    Returns:
        Hook input dictionary.
    """
    return {"hook_event_name": event_name, "session_id": session_id, "cwd": str(tmp_path), "prompt": prompt}


# ---------------------------------------------------------------------------
# Test: get_parent_issue_number
# ---------------------------------------------------------------------------


class TestGetParentIssueNumber:
    """Tests for get_parent_issue_number().

    Scope: Reads parent_issue_number from the active-task context file.
    Strategy: Arrange context file variants, call function, assert return value.
    Why: parent_issue_number is the bridge between local task tracking and the
         GitHub sub-issue that must be updated on task completion.
    """

    def test_get_parent_issue_number_from_context(self, tmp_path: Path) -> None:
        """Returns the integer issue number when parent_issue_number is in context file.

        Tests: get_parent_issue_number with a context file containing parent_issue_number.
        How: Create a context file with parent_issue_number=480. Build hook_input
             pointing to tmp_path as cwd. Call get_parent_issue_number. Assert 480.
        Why: This is the primary success path — the orchestrator writes the parent
             issue number so the hook can sync completion to the right GitHub issue.
        """
        # Arrange
        import task_status_hook as hook

        session_id = "test-session-abc"
        _make_context_file(tmp_path, session_id, "plan/tasks.md", "T1", parent_issue_number=480)
        hook_input = _make_hook_input(tmp_path, session_id)

        # Act
        result = hook.get_parent_issue_number(hook_input)

        # Assert
        assert result == 480

    def test_get_parent_issue_number_absent(self, tmp_path: Path) -> None:
        """Returns None when the context file lacks the parent_issue_number field.

        Tests: get_parent_issue_number with a context file that has no parent_issue_number.
        How: Create a context file with only task_file_path and task_id. Call function.
             Assert None is returned.
        Why: parent_issue_number is optional — tasks started before T5 docs update
             will not have it. Function must degrade gracefully.
        """
        # Arrange
        import task_status_hook as hook

        session_id = "test-session-def"
        _make_context_file(tmp_path, session_id, "plan/tasks.md", "T1")
        hook_input = _make_hook_input(tmp_path, session_id)

        # Act
        result = hook.get_parent_issue_number(hook_input)

        # Assert
        assert result is None

    def test_get_parent_issue_number_no_context_file(self, tmp_path: Path) -> None:
        """Returns None when no context file exists for the session.

        Tests: get_parent_issue_number when the context file is absent.
        How: Build hook_input with a valid session_id but no context file written.
             Call function. Assert None.
        Why: The hook must not raise when the context file is missing — it silently
             falls back to no GitHub sync.
        """
        # Arrange
        import task_status_hook as hook

        session_id = "nonexistent-session"
        hook_input = _make_hook_input(tmp_path, session_id)

        # Act
        result = hook.get_parent_issue_number(hook_input)

        # Assert
        assert result is None


# ---------------------------------------------------------------------------
# Test: sync_completion_to_github
# ---------------------------------------------------------------------------


class TestSyncCompletionToGithub:
    """Tests for sync_completion_to_github().

    Scope: Syncs task completion to a GitHub sub-issue. Wraps all GitHub I/O
    in try/except — must never raise regardless of failure mode.

    Strategy: Inject mock ``backlog_core`` and ``backlog_core.github`` modules
    into sys.modules so the conditional import in sync_completion_to_github
    resolves the mock instead of the real module.

    Why: GitHub connectivity is not available in CI. The function must work
    with mocked GitHub calls and must not propagate any exception.
    """

    def test_sync_completion_no_github_issue_field(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """Does nothing when task YAML has no github_issue field.

        Tests: sync_completion_to_github with a task file that lacks github_issue.
        How: Write a task YAML without github_issue. Mock update_task_status.
             Call sync_completion_to_github. Assert update_task_status not called
             and function returns None.
        Why: Most tasks don't have a GitHub issue. Missing field must be a
             silent no-op (warning to stderr, no API call, no exception).
        """
        # Arrange
        import task_status_hook as hook

        task_file = tmp_path / "task.md"
        task_file.write_text(_TASK_YAML_WITHOUT_GITHUB_ISSUE, encoding="utf-8")

        mock_bc = types.ModuleType("backlog_core")
        mock_bc_github = types.ModuleType("backlog_core.github")
        mock_update = MagicMock(return_value=True)
        mock_bc_github.update_task_status = mock_update
        mock_bc_github.get_github = MagicMock()

        with patch.dict(sys.modules, {"backlog_core": mock_bc, "backlog_core.github": mock_bc_github}):
            # Act
            result = hook.sync_completion_to_github(task_file, "T1", 480)

        # Assert
        assert result is None
        mock_update.assert_not_called()
        stderr = capsys.readouterr().err
        assert "skipping GitHub sync" in stderr

    def test_sync_completion_github_success(self, tmp_path: Path) -> None:
        """Calls update_task_status with correct arguments when github_issue is present.

        Tests: sync_completion_to_github happy path — task YAML has github_issue.
        How: Write a task YAML with github_issue: 481. Inject mock get_github and
             update_task_status. Call sync_completion_to_github. Assert
             update_task_status called with (mock_repo, 481, "complete").
        Why: The primary purpose of the function is to sync the correct issue to
             "complete". Arguments must match exactly.
        """
        # Arrange
        import task_status_hook as hook

        task_file = tmp_path / "tasks-1-test-feature.md"
        task_file.write_text(_TASK_YAML_WITH_GITHUB_ISSUE, encoding="utf-8")

        mock_repo = MagicMock()
        mock_bc = types.ModuleType("backlog_core")
        mock_bc_github = types.ModuleType("backlog_core.github")
        mock_get_github = MagicMock(return_value=mock_repo)
        mock_update = MagicMock(return_value=True)
        mock_bc_github.get_github = mock_get_github
        mock_bc_github.update_task_status = mock_update

        mock_hook_path = MagicMock()
        mock_hook_path.exists.return_value = True
        with (
            patch.dict(sys.modules, {"backlog_core": mock_bc, "backlog_core.github": mock_bc_github}),
            patch.object(hook, "_BACKLOG_CORE_HOOK", mock_hook_path),
        ):
            # Act
            result = hook.sync_completion_to_github(task_file, "T1", 480)

        # Assert
        assert result is None
        mock_update.assert_called_once_with(mock_repo, 481, "complete")

    def test_sync_completion_github_exception(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """Returns None and writes warning when update_task_status raises.

        Tests: sync_completion_to_github when update_task_status raises an exception.
        How: Write task YAML with github_issue: 481. Mock update_task_status to
             raise RuntimeError. Call function. Assert None returned and warning
             written to stderr.
        Why: GitHub failures must never break the hook exit code. Local write
             already succeeded — GitHub is best-effort only.
        """
        # Arrange
        import task_status_hook as hook

        task_file = tmp_path / "task.md"
        task_file.write_text(_TASK_YAML_WITH_GITHUB_ISSUE, encoding="utf-8")

        mock_repo = MagicMock()
        mock_bc = types.ModuleType("backlog_core")
        mock_bc_github = types.ModuleType("backlog_core.github")
        mock_get_github = MagicMock(return_value=mock_repo)
        mock_update = MagicMock(side_effect=RuntimeError("GitHub API error"))
        mock_bc_github.get_github = mock_get_github
        mock_bc_github.update_task_status = mock_update

        with patch.dict(sys.modules, {"backlog_core": mock_bc, "backlog_core.github": mock_bc_github}):
            # Act
            result = hook.sync_completion_to_github(task_file, "T1", 480)

        # Assert
        assert result is None
        stderr = capsys.readouterr().err
        assert "update_task_status failed" in stderr or "GitHub sync" in stderr

    def test_sync_completion_get_github_unavailable(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """Returns None when get_github raises (GitHub unavailable).

        Tests: sync_completion_to_github when get_github itself raises.
        How: Write task YAML with github_issue: 481. Mock get_github to raise
             RuntimeError. Call function. Assert None returned (no exception propagated).
        Why: Token missing or network down are common CI scenarios. The hook must
             exit cleanly in both cases.
        """
        # Arrange
        import task_status_hook as hook

        task_file = tmp_path / "task.md"
        task_file.write_text(_TASK_YAML_WITH_GITHUB_ISSUE, encoding="utf-8")

        mock_bc = types.ModuleType("backlog_core")
        mock_bc_github = types.ModuleType("backlog_core.github")
        mock_get_github = MagicMock(side_effect=RuntimeError("No token"))
        mock_update = MagicMock()
        mock_bc_github.get_github = mock_get_github
        mock_bc_github.update_task_status = mock_update

        with patch.dict(sys.modules, {"backlog_core": mock_bc, "backlog_core.github": mock_bc_github}):
            # Act
            result = hook.sync_completion_to_github(task_file, "T1", 480)

        # Assert
        assert result is None
        mock_update.assert_not_called()
        stderr = capsys.readouterr().err
        assert "GitHub" in stderr


# ---------------------------------------------------------------------------
# Test: handle_subagent_stop calls sync_completion_to_github
# ---------------------------------------------------------------------------


class TestHandleSubagentStopCallsSync:
    """Tests that handle_subagent_stop invokes sync_completion_to_github after local write.

    Scope: Integration between handle_subagent_stop and sync_completion_to_github.
    Strategy: Patch sync_completion_to_github at module level and assert it is called.
    Why: The call in handle_subagent_stop is the wiring that connects the two systems.
         A missing call means GitHub never gets updated.
    """

    def test_sync_completion_called_after_local_write(self, tmp_path: Path) -> None:
        """sync_completion_to_github is called after the local YAML write succeeds.

        Tests: handle_subagent_stop calls sync_completion_to_github as its final step.
        How: Create a temp task YAML with status in-progress. Write a context file.
             Patch sync_completion_to_github. Call handle_subagent_stop with a prompt
             containing '/start-task {path} --task T1'. Assert sync was called.
        Why: Without this call the GitHub issue would never be marked complete.
             The call order (local write first) ensures local consistency even if
             GitHub sync fails.
        """
        # Arrange
        import task_status_hook as hook

        task_file = tmp_path / "tasks-1-test-feature.md"
        task_file.write_text(_TASK_YAML_WITH_GITHUB_ISSUE, encoding="utf-8")

        session_id = "sync-test-session"
        _make_context_file(tmp_path, session_id, str(task_file), "T1", parent_issue_number=480)

        hook_input: dict[str, object] = {
            "hook_event_name": "SubagentStop",
            "session_id": session_id,
            "cwd": str(tmp_path),
            "prompt": f"/start-task {task_file} --task T1",
        }

        with patch.object(hook, "sync_completion_to_github") as mock_sync:
            # Act
            hook.handle_subagent_stop(hook_input)

            # Assert
            mock_sync.assert_called_once()
            call_args = mock_sync.call_args
            assert call_args[0][1] == "T1"  # task_id argument


# ---------------------------------------------------------------------------
# Test: handle_activity_update does NOT call GitHub
# ---------------------------------------------------------------------------


class TestActivityUpdateNoGithubCall:
    """Tests that handle_activity_update never calls backlog_core functions.

    Scope: PostToolUse handler must not invoke any GitHub code.
    Strategy: Patch sync_completion_to_github at module level; assert not called.
    Why: handle_activity_update only updates LastActivity. It must not trigger
         any GitHub I/O — that would be incorrect behavior and create unnecessary
         API calls on every Write/Edit/Bash tool use.
    """

    def test_activity_update_no_github_call(self, tmp_path: Path) -> None:
        """handle_activity_update does not call any GitHub or backlog_core functions.

        Tests: handle_activity_update with a valid PostToolUse hook input.
        How: Create a task YAML with status in-progress. Write a context file.
             Patch sync_completion_to_github. Call handle_activity_update.
             Assert sync_completion_to_github was NOT called.
        Why: Updating LastActivity is a local-only operation. GitHub sync must
             only happen on task completion (SubagentStop), not on every tool use.
        """
        # Arrange
        import task_status_hook as hook

        task_file = tmp_path / "tasks-1-test-feature.md"
        task_file.write_text(_TASK_YAML_WITH_GITHUB_ISSUE, encoding="utf-8")

        session_id = "activity-test-session"
        _make_context_file(tmp_path, session_id, str(task_file), "T1")

        hook_input: dict[str, object] = {
            "hook_event_name": "PostToolUse",
            "tool_name": "Write",
            "session_id": session_id,
            "cwd": str(tmp_path),
        }

        with patch.object(hook, "sync_completion_to_github") as mock_sync:
            # Act
            hook.handle_activity_update(hook_input)

            # Assert
            mock_sync.assert_not_called()
