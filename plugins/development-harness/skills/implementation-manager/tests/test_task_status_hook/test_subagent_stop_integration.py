"""Integration tests for handle_subagent_stop with GitHub sync.

Tests the full SubagentStop execution path:
  local YAML write → delete context file → sync_completion_to_github

Two variants:
1. GitHub sync succeeds — verify local YAML status is 'complete', context file
   is deleted, and update_task_status was called with the correct arguments.
2. GitHub sync fails — verify local YAML status is still 'complete' (local write
   succeeded before GitHub failure), update_task_status was called, and the
   function returns without raising.

Scope: Integration tests — real task_status_hook functions are called end-to-end.
       Only GitHub I/O is mocked (sys.modules injection).

Strategy: Use tmp_path for all temporary files. Inject mock backlog_core.github
          via sys.modules so the conditional import resolves the mock. Assert
          YAML file content after handle_subagent_stop returns.

Why: The full path test ensures the wiring between local write, context file
     cleanup, and GitHub sync is correct. Unit tests verify each component;
     integration tests verify they compose correctly.
"""

from __future__ import annotations

import json
import sys
import types
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from pathlib import Path

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_TASK_YAML_IN_PROGRESS_WITH_GITHUB = """\
---
feature: test-feature
task: T1
title: Integration Test Task
status: in-progress
agent: general-purpose
priority: 2
complexity: low
dependencies: []
github_issue: 481
---
"""


def _write_task_file(tmp_path: Path, content: str = _TASK_YAML_IN_PROGRESS_WITH_GITHUB) -> Path:
    """Write a task YAML file to tmp_path.

    Args:
        tmp_path: Directory to write the file in.
        content: YAML content to write.

    Returns:
        Path to the created task file.
    """
    task_file = tmp_path / "tasks-1-test-feature.md"
    task_file.write_text(content, encoding="utf-8")
    return task_file


def _write_context_file(
    tmp_path: Path, session_id: str, task_file: Path, task_id: str = "T1", parent_issue_number: int | None = 480
) -> Path:
    """Write an active-task context JSON file.

    Args:
        tmp_path: Root directory to write the context file under .claude/context/.
        session_id: Session identifier used in filename.
        task_file: Path to the task file.
        task_id: Task identifier.
        parent_issue_number: Optional parent story issue number.

    Returns:
        Path to the written context file.
    """
    context_dir = tmp_path / ".claude" / "context"
    context_dir.mkdir(parents=True, exist_ok=True)
    data: dict[str, Any] = {"task_file_path": str(task_file), "task_id": task_id}
    if parent_issue_number is not None:
        data["parent_issue_number"] = parent_issue_number
    context_file = context_dir / f"active-task-{session_id}.json"
    context_file.write_text(json.dumps(data), encoding="utf-8")
    return context_file


def _build_hook_input(tmp_path: Path, session_id: str, task_file: Path) -> dict[str, Any]:
    """Build a SubagentStop hook input dict.

    Args:
        tmp_path: Root working directory (used as cwd).
        session_id: Session identifier.
        task_file: Path used in the prompt.

    Returns:
        Hook input dictionary with SubagentStop event.
    """
    return {
        "hook_event_name": "SubagentStop",
        "session_id": session_id,
        "cwd": str(tmp_path),
        "prompt": f"/start-task {task_file} --task T1",
    }


def _make_mock_backlog_core_github(
    mock_repo: MagicMock, update_task_status_mock: MagicMock
) -> tuple[types.ModuleType, types.ModuleType]:
    """Build fake backlog_core and backlog_core.github modules.

    Args:
        mock_repo: Mock repository object returned by get_github.
        update_task_status_mock: Mock for the update_task_status function.

    Returns:
        Tuple of (backlog_core module, backlog_core.github module).
    """
    mock_bc = types.ModuleType("backlog_core")
    mock_bc_github = types.ModuleType("backlog_core.github")
    vars(mock_bc_github).update({
        "get_github": MagicMock(return_value=mock_repo),
        "update_task_status": update_task_status_mock,
    })
    return mock_bc, mock_bc_github


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------


class TestSubagentStopFullPathWithGithubSync:
    """Integration tests for the full SubagentStop path including GitHub sync.

    Scope: Verifies end-to-end behaviour of handle_subagent_stop when a task
    completes — local YAML write, context file cleanup, and GitHub sync.

    Why: Unit tests verify each component in isolation. These integration tests
    verify the components are wired together correctly and that GitHub failure
    does not corrupt the local task state.
    """

    def test_subagent_stop_full_path_with_github_sync(self, tmp_path: Path) -> None:
        """Full success path: local write completes, GitHub issue updated.

        Tests: handle_subagent_stop end-to-end with GitHub sync succeeding.
        How:
          1. Create temp task YAML with status in-progress and github_issue: 481.
          2. Create temp context file with parent_issue_number: 480.
          3. Build SubagentStop hook input with /start-task prompt.
          4. Inject mock get_github and update_task_status (returns True).
          5. Call handle_subagent_stop.
        Assert:
          - Local YAML status field is 'complete'.
          - Local YAML completed field is set (not empty).
          - Context file is deleted.
          - update_task_status called once with (mock_repo, 481, 'complete').

        Why: This is the primary happy-path scenario. Every assertion verifies
             a distinct invariant that must hold for correct task tracking.
        """
        # Arrange
        import task_status_hook as hook

        session_id = "integration-success-session"
        task_file = _write_task_file(tmp_path)
        context_file = _write_context_file(tmp_path, session_id, task_file)
        hook_input = _build_hook_input(tmp_path, session_id, task_file)

        mock_repo = MagicMock()
        mock_update = MagicMock(return_value=True)
        mock_bc, mock_bc_github = _make_mock_backlog_core_github(mock_repo, mock_update)

        mock_hook_path = MagicMock()
        mock_hook_path.exists.return_value = True
        with (
            pytest.MonkeyPatch.context() as mp,
            patch.object(hook, "_resolve_context_file_from_transcript", return_value=context_file),
        ):
            mp.setitem(sys.modules, "backlog_core", mock_bc)
            mp.setitem(sys.modules, "backlog_core.github", mock_bc_github)
            mp.setattr(hook, "_BACKLOG_CORE_HOOK", mock_hook_path)

            # Act
            hook.handle_subagent_stop(hook_input)

        # Assert: local YAML is marked complete
        updated_content = task_file.read_text(encoding="utf-8")
        assert "status: complete" in updated_content

        # Assert: completed timestamp was written
        assert "completed:" in updated_content

        # Assert: context file was deleted
        assert not context_file.exists()

        # Assert: GitHub update was called with the correct arguments
        mock_update.assert_called_once_with(mock_repo, 481, "complete")

    def test_subagent_stop_full_path_github_failure(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """GitHub failure does not corrupt local task state.

        Tests: handle_subagent_stop when update_task_status raises an exception.
        How:
          1. Same setup as success variant.
          2. update_task_status raises RuntimeError.
          3. Call handle_subagent_stop.
        Assert:
          - Local YAML status is still 'complete' (local write already succeeded).
          - update_task_status was called (attempt was made).
          - handle_subagent_stop returns without raising.
          - Warning appears in stderr.

        Why: GitHub sync is best-effort. The golden rule is: if the local write
             succeeded, the hook must exit 0 regardless of what GitHub does.
        """
        # Arrange
        import task_status_hook as hook

        session_id = "integration-failure-session"
        task_file = _write_task_file(tmp_path)
        context_file = _write_context_file(tmp_path, session_id, task_file)
        hook_input = _build_hook_input(tmp_path, session_id, task_file)

        mock_repo = MagicMock()
        mock_update = MagicMock(side_effect=RuntimeError("GitHub API unreachable"))
        mock_bc, mock_bc_github = _make_mock_backlog_core_github(mock_repo, mock_update)

        mock_hook_path = MagicMock()
        mock_hook_path.exists.return_value = True
        with (
            pytest.MonkeyPatch.context() as mp,
            patch.object(hook, "_resolve_context_file_from_transcript", return_value=context_file),
        ):
            mp.setitem(sys.modules, "backlog_core", mock_bc)
            mp.setitem(sys.modules, "backlog_core.github", mock_bc_github)
            mp.setattr(hook, "_BACKLOG_CORE_HOOK", mock_hook_path)

            # Act — must not raise
            result = hook.handle_subagent_stop(hook_input)

        # Assert: local YAML still shows complete
        updated_content = task_file.read_text(encoding="utf-8")
        assert "status: complete" in updated_content

        # Assert: GitHub update was attempted
        mock_update.assert_called_once()

        # Assert: function returned None (did not raise)
        assert result is None

        # Assert: warning was written to stderr
        stderr = capsys.readouterr().err
        assert "GitHub" in stderr
