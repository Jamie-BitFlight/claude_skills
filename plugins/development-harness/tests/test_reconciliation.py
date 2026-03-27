"""Tests for reconciliation functions added by T2.

Tests: _has_active_work, _reconcile_item, _reconcile_open_item,
       _reconcile_closed_item, _reconcile_batch, _filter_closed_items,
       and ReconcileResult dataclass in backlog_core.operations.
How: Mock GitHub API objects, plan files, and context files. Use tmp_path
     for file-based isolation.
Why: The reconciliation layer detects local/GitHub state divergence and
     auto-corrects DAG-valid transitions, flags invalid ones, and protects
     work-in-progress items from premature closure.

NOTE: ReconcileResult, _reconcile_open_item, _has_active_work, _reconcile_item,
      _reconcile_batch, and _reconcile_closed_item are planned but not yet
      implemented in backlog_core. Tests for those symbols are skipped until
      the backlog-state-reconciliation feature is implemented.
      Tracking: plan/tasks-1-backlog-state-reconciliation.md
"""

from __future__ import annotations

import importlib
import json
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pytest

if TYPE_CHECKING:
    from pathlib import Path


def _backlog_ops() -> Any:
    """Return backlog_core.operations as Any so ty does not flag unimplemented symbols."""
    return importlib.import_module("backlog_core.operations")


# The reconciliation symbols (ReconcileResult, _reconcile_open_item, etc.) live
# in backlog_core.operations once implemented. The old scripts/backlog.py path
# never existed in this repository.
_RECONCILIATION_NOT_IMPLEMENTED = pytest.mark.skip(
    reason=(
        "ReconcileResult and reconciliation helpers are not yet implemented in "
        "backlog_core.operations. See plan/tasks-1-backlog-state-reconciliation.md"
    )
)


@_RECONCILIATION_NOT_IMPLEMENTED
class TestReconcileResultDataclass:
    """Verify ReconcileResult dataclass has all required fields and is constructible."""

    def test_reconcile_result_has_all_fields(self) -> None:
        """ReconcileResult stores issue_number, action, old_status, new_status, and warning."""
        ReconcileResult = _backlog_ops().ReconcileResult

        result = ReconcileResult(
            issue_number=42, action="no_change", old_status="groomed", new_status="groomed", warning=""
        )
        assert result.issue_number == 42
        assert result.action == "no_change"
        assert result.old_status == "groomed"
        assert result.new_status == "groomed"
        assert result.warning == ""

    def test_reconcile_result_with_warning(self) -> None:
        """ReconcileResult can hold a non-empty warning string."""
        ReconcileResult = _backlog_ops().ReconcileResult

        result = ReconcileResult(
            issue_number=10,
            action="flagged_divergence",
            old_status="groomed",
            new_status="groomed",
            warning="#10 divergence: local='groomed', GitHub='in-progress'",
        )
        assert result.warning != ""
        assert "#10" in result.warning


@_RECONCILIATION_NOT_IMPLEMENTED
@_RECONCILIATION_NOT_IMPLEMENTED
class TestHasActiveWork:
    """Verify _has_active_work detects plan files and context files correctly."""

    def test_no_active_work_when_no_plan_files_exist(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Returns (False, '') when no plan files or context files exist for the item."""
        backlog_mod = _backlog_ops()

        monkeypatch.setattr(backlog_mod, "_REPO_ROOT", tmp_path)
        # Create required directories but no plan files
        (tmp_path / "plan").mkdir(parents=True)
        (tmp_path / ".claude" / "context").mkdir(parents=True)

        item = {"_topic": "nonexistent-topic", "_issue": "#99"}
        has_work, reason = backlog_mod._has_active_work(item)
        assert has_work is False
        assert reason == ""

    def test_active_work_detected_from_plan_file_with_in_progress_legacy(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Returns (True, reason) when a plan file has a task with legacy IN PROGRESS marker."""
        backlog_mod = _backlog_ops()

        monkeypatch.setattr(backlog_mod, "_REPO_ROOT", tmp_path)
        plan_dir = tmp_path / "plan"
        plan_dir.mkdir(parents=True)
        (tmp_path / ".claude" / "context").mkdir(parents=True)

        plan_file = plan_dir / "tasks-1-my-feature.md"
        plan_file.write_text("## Task 1\n**Status**: IN PROGRESS\n", encoding="utf-8")

        item = {"_topic": "my-feature", "_issue": "#10"}
        has_work, reason = backlog_mod._has_active_work(item)
        assert has_work is True
        assert "IN PROGRESS" in reason

    def test_active_work_detected_from_plan_file_with_yaml_in_progress(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Returns (True, reason) when a plan file has a task with YAML status: in-progress."""
        backlog_mod = _backlog_ops()

        monkeypatch.setattr(backlog_mod, "_REPO_ROOT", tmp_path)
        plan_dir = tmp_path / "plan"
        plan_dir.mkdir(parents=True)
        (tmp_path / ".claude" / "context").mkdir(parents=True)

        plan_file = plan_dir / "tasks-2-my-feature.md"
        plan_file.write_text("- id: T1\n  status: in-progress\n", encoding="utf-8")

        item = {"_topic": "my-feature", "_issue": "#10"}
        has_work, reason = backlog_mod._has_active_work(item)
        assert has_work is True
        assert "IN PROGRESS" in reason

    def test_no_active_work_when_plan_file_has_completed_tasks_only(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Returns (False, '') when plan file exists but all tasks are COMPLETE."""
        backlog_mod = _backlog_ops()

        monkeypatch.setattr(backlog_mod, "_REPO_ROOT", tmp_path)
        plan_dir = tmp_path / "plan"
        plan_dir.mkdir(parents=True)
        (tmp_path / ".claude" / "context").mkdir(parents=True)

        plan_file = plan_dir / "tasks-1-my-feature.md"
        plan_file.write_text("## Task 1\n**Status**: COMPLETE\n", encoding="utf-8")

        item = {"_topic": "my-feature", "_issue": "#10"}
        has_work, reason = backlog_mod._has_active_work(item)
        assert has_work is False
        assert reason == ""

    def test_active_work_detected_from_context_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Returns (True, reason) when an active-task context file references the item's issue."""
        backlog_mod = _backlog_ops()

        monkeypatch.setattr(backlog_mod, "_REPO_ROOT", tmp_path)
        (tmp_path / "plan").mkdir(parents=True)
        context_dir = tmp_path / ".claude" / "context"
        context_dir.mkdir(parents=True)

        ctx_file = context_dir / "active-task-abc123.json"
        ctx_file.write_text(json.dumps({"issue_number": 42}), encoding="utf-8")

        item = {"_topic": "some-topic", "_issue": "#42"}
        has_work, reason = backlog_mod._has_active_work(item)
        assert has_work is True
        assert "active task context" in reason
        assert "#42" in reason

    def test_no_active_work_when_context_file_references_different_issue(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Returns (False, '') when context files exist but reference a different issue."""
        backlog_mod = _backlog_ops()

        monkeypatch.setattr(backlog_mod, "_REPO_ROOT", tmp_path)
        (tmp_path / "plan").mkdir(parents=True)
        context_dir = tmp_path / ".claude" / "context"
        context_dir.mkdir(parents=True)

        ctx_file = context_dir / "active-task-abc123.json"
        ctx_file.write_text(json.dumps({"issue_number": 99}), encoding="utf-8")

        item = {"_topic": "some-topic", "_issue": "#42"}
        has_work, reason = backlog_mod._has_active_work(item)
        assert has_work is False
        assert reason == ""

    def test_handles_missing_topic_gracefully(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Returns (False, '') when item has no _topic field — skips plan file check."""
        backlog_mod = _backlog_ops()

        monkeypatch.setattr(backlog_mod, "_REPO_ROOT", tmp_path)
        (tmp_path / "plan").mkdir(parents=True)
        (tmp_path / ".claude" / "context").mkdir(parents=True)

        item = {"_issue": "#10"}
        has_work, _reason = backlog_mod._has_active_work(item)
        assert has_work is False

    def test_handles_non_numeric_issue_gracefully(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Returns (False, '') when item has a non-numeric _issue field."""
        backlog_mod = _backlog_ops()

        monkeypatch.setattr(backlog_mod, "_REPO_ROOT", tmp_path)
        (tmp_path / "plan").mkdir(parents=True)
        (tmp_path / ".claude" / "context").mkdir(parents=True)

        item = {"_topic": "my-topic", "_issue": "not-a-number"}
        has_work, _reason = backlog_mod._has_active_work(item)
        assert has_work is False


@_RECONCILIATION_NOT_IMPLEMENTED
@_RECONCILIATION_NOT_IMPLEMENTED
class TestReconcileOpenItem:
    """Verify _reconcile_open_item handles divergence scenarios for open GitHub issues."""

    def test_no_change_when_statuses_match(self) -> None:
        """Returns no_change when local and GitHub statuses are identical."""
        reconcile_open_item = _backlog_ops()._reconcile_open_item

        result = reconcile_open_item(issue_num=1, local_status="groomed", github_status="groomed", file_path_str=None)
        assert result.action == "no_change"
        assert result.old_status == "groomed"
        assert result.new_status == "groomed"
        assert result.warning == ""

    def test_flagged_divergence_when_github_has_no_status_label(self) -> None:
        """Returns flagged_divergence with stateless void warning when GitHub has no status label."""
        reconcile_open_item = _backlog_ops()._reconcile_open_item

        result = reconcile_open_item(issue_num=5, local_status="groomed", github_status="", file_path_str=None)
        assert result.action == "flagged_divergence"
        assert result.old_status == "groomed"
        assert result.new_status == "groomed"
        assert "stateless void" in result.warning

    def test_auto_corrected_when_dag_valid_divergence(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Returns auto_corrected when divergence is DAG-valid (reachable via state transitions)."""
        backlog_mod = _backlog_ops()

        # find_valid_path returns a path for DAG-valid transitions
        monkeypatch.setattr(backlog_mod, "find_valid_path", lambda f, t: [f, t])
        mock_update = MagicMock()
        monkeypatch.setattr(backlog_mod, "_update_item_metadata", mock_update)

        result = backlog_mod._reconcile_open_item(
            issue_num=3, local_status="needs-grooming", github_status="groomed", file_path_str="/tmp/test.md"
        )
        assert result.action == "auto_corrected"
        assert result.old_status == "needs-grooming"
        assert result.new_status == "groomed"
        assert result.warning == ""

    def test_auto_corrected_persists_via_update_item_metadata(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When auto-correcting, _update_item_metadata is called to persist the change."""
        backlog_mod = _backlog_ops()

        monkeypatch.setattr(backlog_mod, "find_valid_path", lambda f, t: [f, t])
        mock_update = MagicMock()
        monkeypatch.setattr(backlog_mod, "_update_item_metadata", mock_update)

        backlog_mod._reconcile_open_item(
            issue_num=3, local_status="needs-grooming", github_status="groomed", file_path_str="/tmp/test.md"
        )
        mock_update.assert_called_once()
        call_args = mock_update.call_args
        assert call_args[0][1] == {"metadata": {"status": "groomed"}}

    def test_auto_corrected_skips_persistence_when_no_file_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When file_path_str is None, auto-correction returns result but does not persist."""
        backlog_mod = _backlog_ops()

        monkeypatch.setattr(backlog_mod, "find_valid_path", lambda f, t: [f, t])
        mock_update = MagicMock()
        monkeypatch.setattr(backlog_mod, "_update_item_metadata", mock_update)

        result = backlog_mod._reconcile_open_item(
            issue_num=3, local_status="needs-grooming", github_status="groomed", file_path_str=None
        )
        assert result.action == "auto_corrected"
        mock_update.assert_not_called()

    def test_flagged_divergence_when_dag_invalid(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Returns flagged_divergence when no valid DAG path exists between states."""
        backlog_mod = _backlog_ops()

        monkeypatch.setattr(backlog_mod, "find_valid_path", lambda f, t: None)

        result = backlog_mod._reconcile_open_item(
            issue_num=7, local_status="in-progress", github_status="needs-grooming", file_path_str=None
        )
        assert result.action == "flagged_divergence"
        assert result.old_status == "in-progress"
        assert result.new_status == "in-progress"
        assert "invalid transition" in result.warning


@_RECONCILIATION_NOT_IMPLEMENTED
@_RECONCILIATION_NOT_IMPLEMENTED
class TestReconcileClosedItem:
    """Verify _reconcile_closed_item handles closed GitHub issues correctly."""

    def test_wip_protected_when_active_work_exists(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Returns wip_protected when GitHub is closed but active local work exists."""
        backlog_mod = _backlog_ops()

        monkeypatch.setattr(backlog_mod, "_REPO_ROOT", tmp_path)
        plan_dir = tmp_path / "plan"
        plan_dir.mkdir(parents=True)
        (tmp_path / ".claude" / "context").mkdir(parents=True)

        plan_file = plan_dir / "tasks-1-my-feature.md"
        plan_file.write_text("## Task 1\n**Status**: IN PROGRESS\n", encoding="utf-8")

        item = {"_topic": "my-feature", "_issue": "#50"}
        result = backlog_mod._reconcile_closed_item(
            issue_num=50, local_status="in-progress", github_status="closed", file_path_str=None, item=item
        )
        assert result.action == "wip_protected"
        assert result.old_status == "in-progress"
        assert result.new_status == "in-progress"
        assert "active work" in result.warning

    def test_closed_when_no_active_work(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Returns closed and updates to terminal status when no active work exists."""
        backlog_mod = _backlog_ops()

        monkeypatch.setattr(backlog_mod, "_REPO_ROOT", tmp_path)
        (tmp_path / "plan").mkdir(parents=True)
        (tmp_path / ".claude" / "context").mkdir(parents=True)
        mock_update = MagicMock()
        monkeypatch.setattr(backlog_mod, "_update_item_metadata", mock_update)

        item = {"_topic": "done-topic", "_issue": "#60"}
        result = backlog_mod._reconcile_closed_item(
            issue_num=60, local_status="groomed", github_status="closed", file_path_str="/tmp/test.md", item=item
        )
        assert result.action == "closed"
        assert result.new_status == "closed"
        mock_update.assert_called_once()

    def test_closed_uses_terminal_github_status_when_available(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When GitHub has a terminal status label (e.g. 'done'), uses that instead of 'closed'."""
        backlog_mod = _backlog_ops()

        monkeypatch.setattr(backlog_mod, "_REPO_ROOT", tmp_path)
        (tmp_path / "plan").mkdir(parents=True)
        (tmp_path / ".claude" / "context").mkdir(parents=True)
        mock_update = MagicMock()
        monkeypatch.setattr(backlog_mod, "_update_item_metadata", mock_update)

        item = {"_topic": "resolved-topic", "_issue": "#70"}
        result = backlog_mod._reconcile_closed_item(
            issue_num=70, local_status="in-progress", github_status="done", file_path_str="/tmp/test.md", item=item
        )
        assert result.action == "closed"
        assert result.new_status == "done"


@_RECONCILIATION_NOT_IMPLEMENTED
@_RECONCILIATION_NOT_IMPLEMENTED
class TestReconcileItem:
    """Verify _reconcile_item dispatches correctly based on item and GitHub state."""

    def _make_gh_issue(self, *, state: str = "open", labels: list[str] | None = None, number: int = 1) -> MagicMock:
        """Create a mock GitHub issue with the given state and labels."""
        issue = MagicMock()
        issue.state = state
        issue.number = number
        issue.pull_request = None
        mock_labels = []
        for lbl_name in labels or []:
            lbl = MagicMock()
            lbl.name = lbl_name
            mock_labels.append(lbl)
        issue.labels = mock_labels
        return issue

    def test_returns_no_change_when_item_has_no_issue_ref(self) -> None:
        """Items without an _issue field return no_change with issue_number=0."""
        backlog_mod = _backlog_ops()

        item = {"_topic": "orphan"}
        result = backlog_mod._reconcile_item(item, {}, "repo")
        assert result.action == "no_change"
        assert result.issue_number == 0

    def test_returns_no_change_when_issue_not_in_map(self) -> None:
        """Items whose issue number is not in the GitHub map return no_change with warning."""
        backlog_mod = _backlog_ops()

        item = {"_issue": "#999", "_topic": "missing"}
        result = backlog_mod._reconcile_item(item, {}, "repo")
        assert result.action == "no_change"
        assert result.issue_number == 999
        assert "not found" in result.warning

    def test_dispatches_to_open_handler_for_open_issues(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When GitHub issue is open, delegates to _reconcile_open_item."""
        backlog_mod = _backlog_ops()

        gh_issue = self._make_gh_issue(state="open", labels=["status:groomed"], number=10)
        item = {"_issue": "#10", "**Status**": "groomed", "_file_path": None}

        result = backlog_mod._reconcile_item(item, {10: gh_issue}, "repo")
        assert result.action == "no_change"

    def test_dispatches_to_closed_handler_for_closed_issues(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When GitHub issue is closed, delegates to _reconcile_closed_item."""
        backlog_mod = _backlog_ops()

        monkeypatch.setattr(backlog_mod, "_REPO_ROOT", tmp_path)
        (tmp_path / "plan").mkdir(parents=True)
        (tmp_path / ".claude" / "context").mkdir(parents=True)
        mock_update = MagicMock()
        monkeypatch.setattr(backlog_mod, "_update_item_metadata", mock_update)

        gh_issue = self._make_gh_issue(state="closed", labels=["status:done"], number=20)
        item = {"_issue": "#20", "**Status**": "in-progress", "_topic": "closed-topic", "_file_path": "/tmp/t.md"}

        result = backlog_mod._reconcile_item(item, {20: gh_issue}, "repo")
        assert result.action == "closed"
        assert result.new_status == "done"


@_RECONCILIATION_NOT_IMPLEMENTED
class TestReconcileBatch:
    """Verify _reconcile_batch handles GitHub availability and batch processing."""

    def test_returns_warning_when_github_unavailable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When _try_get_github returns None, returns items unchanged with warning."""
        backlog_mod = _backlog_ops()

        monkeypatch.setattr(backlog_mod, "_try_get_github", lambda _repo: None)

        items = [{"_issue": "#1", "**Status**": "groomed"}]
        result_items, warnings = backlog_mod._reconcile_batch(items, "repo")
        assert result_items is items
        assert len(warnings) == 1
        assert "unavailable" in warnings[0].lower()

    def test_returns_warning_on_github_api_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When GitHub API raises GithubException, returns items unchanged with warning."""
        from github import GithubException

        backlog_mod = _backlog_ops()

        mock_repo = MagicMock()
        mock_repo.get_issues.side_effect = GithubException(500, "Server Error", None)
        monkeypatch.setattr(backlog_mod, "_try_get_github", lambda _repo: mock_repo)

        items = [{"_issue": "#1", "**Status**": "groomed"}]
        result_items, warnings = backlog_mod._reconcile_batch(items, "repo")
        assert result_items is items
        assert len(warnings) == 1
        assert "error" in warnings[0].lower()

    def test_auto_corrected_items_updated_in_memory(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When an item is auto-corrected, its in-memory status is updated."""
        backlog_mod = _backlog_ops()

        # Create a mock repo that returns one open issue with status:groomed
        mock_issue = MagicMock()
        mock_issue.number = 1
        mock_issue.state = "open"
        mock_issue.pull_request = None
        lbl = MagicMock()
        lbl.name = "status:groomed"
        mock_issue.labels = [lbl]

        mock_repo = MagicMock()
        mock_repo.get_issues.return_value = [mock_issue]
        monkeypatch.setattr(backlog_mod, "_try_get_github", lambda _repo: mock_repo)
        # find_valid_path returns a valid path so auto-correction triggers
        monkeypatch.setattr(backlog_mod, "find_valid_path", lambda f, t: [f, t])
        monkeypatch.setattr(backlog_mod, "_update_item_metadata", MagicMock())

        items = [{"_issue": "#1", "**Status**": "needs-grooming", "_file_path": "/tmp/t.md"}]
        result_items, warnings = backlog_mod._reconcile_batch(items, "repo")
        assert result_items[0]["**Status**"] == "groomed"
        assert len(warnings) == 0

    def test_divergence_warnings_collected(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Divergence warnings from _reconcile_item are collected in the warnings list."""
        backlog_mod = _backlog_ops()

        # Open issue with no status label triggers flagged_divergence
        mock_issue = MagicMock()
        mock_issue.number = 5
        mock_issue.state = "open"
        mock_issue.pull_request = None
        mock_issue.labels = []

        mock_repo = MagicMock()
        mock_repo.get_issues.return_value = [mock_issue]
        monkeypatch.setattr(backlog_mod, "_try_get_github", lambda _repo: mock_repo)

        items = [{"_issue": "#5", "**Status**": "groomed", "_file_path": None}]
        _result_items, warnings = backlog_mod._reconcile_batch(items, "repo")
        assert len(warnings) == 1
        assert "stateless void" in warnings[0]

    def test_filters_out_pull_requests(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Pull requests are excluded from the GitHub issue map."""
        backlog_mod = _backlog_ops()

        # Create a PR (pull_request is not None) and a real issue
        mock_pr = MagicMock()
        mock_pr.number = 1
        mock_pr.pull_request = MagicMock()  # not None => is a PR

        mock_issue = MagicMock()
        mock_issue.number = 2
        mock_issue.state = "open"
        mock_issue.pull_request = None
        lbl = MagicMock()
        lbl.name = "status:groomed"
        mock_issue.labels = [lbl]

        mock_repo = MagicMock()
        mock_repo.get_issues.return_value = [mock_pr, mock_issue]
        monkeypatch.setattr(backlog_mod, "_try_get_github", lambda _repo: mock_repo)

        # Item #1 (the PR) should not be found in the map
        items = [
            {"_issue": "#1", "**Status**": "groomed", "_file_path": None},
            {"_issue": "#2", "**Status**": "groomed", "_file_path": None},
        ]
        _result_items, warnings = backlog_mod._reconcile_batch(items, "repo")
        # Item #1 should get "not found" warning since PR is filtered out
        pr_warnings = [w for w in warnings if "#1" in w and "not found" in w]
        assert len(pr_warnings) == 1


@_RECONCILIATION_NOT_IMPLEMENTED
class TestFilterClosedItems:
    """Verify _filter_closed_items filters terminal-status items correctly.

    NOTE: backlog_core.operations._filter_closed_items takes BacklogItem objects,
    not plain dicts. These tests exercise the dict-based variant that was planned
    for scripts/backlog.py but never implemented.
    """

    def test_returns_all_items_when_include_closed_true(self) -> None:
        """When include_closed=True, all items are returned unfiltered."""
        filter_closed_items = _backlog_ops()._filter_closed_items

        items = [{"**Status**": "done"}, {"**Status**": "groomed"}, {"**Status**": "closed"}]
        result = filter_closed_items(items, include_closed=True)
        assert len(result) == 3

    def test_excludes_done_resolved_closed_by_default(self) -> None:
        """When include_closed=False, items with done/resolved/closed status are excluded."""
        filter_closed_items = _backlog_ops()._filter_closed_items

        items = [
            {"**Status**": "done"},
            {"**Status**": "resolved"},
            {"**Status**": "closed"},
            {"**Status**": "groomed"},
            {"**Status**": "in-progress"},
        ]
        result = filter_closed_items(items, include_closed=False)
        assert len(result) == 2
        statuses = [it["**Status**"] for it in result]
        assert "groomed" in statuses
        assert "in-progress" in statuses

    def test_handles_items_with_status_key_variant(self) -> None:
        """Items using _status key instead of **Status** are also filtered."""
        filter_closed_items = _backlog_ops()._filter_closed_items

        items = [{"_status": "done"}, {"_status": "groomed"}]
        result = filter_closed_items(items, include_closed=False)
        assert len(result) == 1
        assert result[0]["_status"] == "groomed"

    def test_handles_empty_status(self) -> None:
        """Items with empty or missing status are not filtered out."""
        filter_closed_items = _backlog_ops()._filter_closed_items

        items = [{"**Status**": ""}, {}]
        result = filter_closed_items(items, include_closed=False)
        assert len(result) == 2

    def test_empty_list_returns_empty(self) -> None:
        """Empty input list returns empty output."""
        filter_closed_items = _backlog_ops()._filter_closed_items

        result = filter_closed_items([], include_closed=False)
        assert result == []
