"""Tests for github_project_setup.py — milestone/issue workflow automation.

Each test class maps to one CLI command (one step in the workflow):

  Step 1  labels         — create/update label taxonomy
  Step 2  milestone list — list milestones
  Step 3  milestone create — create a new milestone
  Step 4  issue create   — create an issue with labels and optional milestone
  Step 5  milestone start — bulk-transition status:needs-grooming → status:in-progress
  Step 6  issue list     — list issues (post-start verification)

Tests: every happy-path and key error-path for each command
How:   Typer CliRunner + unittest.mock to mock PyGithub calls (no network)
Why:   Prove each workflow step executes correctly and exits with the right code
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

# ---------------------------------------------------------------------------
# Load github_project_setup as a module (filename contains underscores so
# a plain import works, but we use importlib for clarity and path safety).
# ---------------------------------------------------------------------------
_SCRIPT = Path(__file__).parent.parent / "scripts" / "github_project_setup.py"
_spec = importlib.util.spec_from_file_location("github_project_setup", _SCRIPT)
assert _spec is not None, f"Cannot find spec for {_SCRIPT}"
assert _spec.loader is not None, f"Cannot find loader for {_SCRIPT}"
_gps = importlib.util.module_from_spec(_spec)
sys.modules["github_project_setup"] = _gps
_spec.loader.exec_module(_gps)

app = _gps.app

runner = CliRunner()


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_label(name: str) -> MagicMock:
    lbl = MagicMock()
    lbl.name = name
    return lbl


def _make_issue(number: int, title: str, labels: list[str]) -> MagicMock:
    issue = MagicMock()
    issue.number = number
    issue.title = title
    issue.labels = [_make_label(n) for n in labels]
    return issue


def _make_milestone(
    number: int,
    title: str,
    state: str = "open",
    open_issues: int = 2,
    closed_issues: int = 1,
    due_on: object = None,
    html_url: str = "https://github.com/owner/repo/milestone/1",
) -> MagicMock:
    m = MagicMock()
    m.number = number
    m.title = title
    m.state = state
    m.open_issues = open_issues
    m.closed_issues = closed_issues
    m.due_on = due_on
    m.html_url = html_url
    return m


# ---------------------------------------------------------------------------
# Step 1 — labels command
# ---------------------------------------------------------------------------


class TestLabelsCommand:
    """Step 1: create/update the label taxonomy."""

    def test_creates_missing_labels(self) -> None:
        """Labels that don't exist are created; output confirms creation."""
        mock_repo = MagicMock()
        mock_repo.get_labels.return_value = []  # no existing labels

        with (
            patch.dict("os.environ", {"GITHUB_TOKEN": "test-token"}),
            patch("github_project_setup.get_repo", return_value=mock_repo),
            patch("github_project_setup.Github"),
        ):
            result = runner.invoke(app, ["labels", "--repo", "owner/repo"])

        assert result.exit_code == 0, result.output
        assert mock_repo.create_label.called
        assert "created" in result.output

    def test_skips_existing_labels_without_force(self) -> None:
        """Existing labels are skipped when --force is not passed."""
        existing = _make_label("priority:p0")
        mock_repo = MagicMock()
        mock_repo.get_labels.return_value = [existing]

        with (
            patch.dict("os.environ", {"GITHUB_TOKEN": "test-token"}),
            patch("github_project_setup.get_repo", return_value=mock_repo),
            patch("github_project_setup.Github"),
        ):
            result = runner.invoke(app, ["labels", "--repo", "owner/repo"])

        assert result.exit_code == 0, result.output
        assert "exists" in result.output

    def test_force_updates_existing_labels(self) -> None:
        """--force flag causes existing labels to be updated."""
        existing_label = _make_label("priority:p0")
        mock_repo = MagicMock()
        mock_repo.get_labels.return_value = [existing_label]

        with (
            patch.dict("os.environ", {"GITHUB_TOKEN": "test-token"}),
            patch("github_project_setup.get_repo", return_value=mock_repo),
            patch("github_project_setup.Github"),
        ):
            result = runner.invoke(app, ["labels", "--repo", "owner/repo", "--force"])

        assert result.exit_code == 0, result.output
        assert existing_label.edit.called
        assert "updated" in result.output

    def test_missing_token_exits_nonzero(self) -> None:
        """Missing GITHUB_TOKEN exits with code 1."""
        env = {k: v for k, v in __import__("os").environ.items() if k != "GITHUB_TOKEN"}
        with patch.dict("os.environ", env, clear=True):
            result = runner.invoke(app, ["labels"])

        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# Step 2 — milestone list
# ---------------------------------------------------------------------------


class TestMilestoneList:
    """Step 2: list milestones (read-only verification step)."""

    def test_lists_milestones(self) -> None:
        """Open and closed milestones are printed with number, state, title."""
        m1 = _make_milestone(1, "v1.0 — Skills Foundation", open_issues=5)
        m2 = _make_milestone(2, "v1.1 — Quality Gates", state="closed")
        mock_repo = MagicMock()
        mock_repo.get_milestones.return_value = [m1, m2]

        with (
            patch.dict("os.environ", {"GITHUB_TOKEN": "tok"}),
            patch("github_project_setup.get_repo", return_value=mock_repo),
            patch("github_project_setup.Github"),
        ):
            result = runner.invoke(app, ["milestone", "list"])

        assert result.exit_code == 0, result.output
        assert "#  1" in result.output
        assert "v1.0" in result.output
        assert "#  2" in result.output

    def test_empty_repo_prints_no_milestones(self) -> None:
        """Empty milestone list prints a 'No milestones.' message."""
        mock_repo = MagicMock()
        mock_repo.get_milestones.return_value = []

        with (
            patch.dict("os.environ", {"GITHUB_TOKEN": "tok"}),
            patch("github_project_setup.get_repo", return_value=mock_repo),
            patch("github_project_setup.Github"),
        ):
            result = runner.invoke(app, ["milestone", "list"])

        assert result.exit_code == 0
        assert "No milestones" in result.output


# ---------------------------------------------------------------------------
# Step 3 — milestone create
# ---------------------------------------------------------------------------


class TestMilestoneCreate:
    """Step 3: create a new milestone."""

    def test_creates_milestone_title_only(self) -> None:
        """Milestone is created with title only (no due date, no description)."""
        new_ms = _make_milestone(3, "test-milestone")
        mock_repo = MagicMock()
        mock_repo.create_milestone.return_value = new_ms

        with (
            patch.dict("os.environ", {"GITHUB_TOKEN": "tok"}),
            patch("github_project_setup.get_repo", return_value=mock_repo),
            patch("github_project_setup.Github"),
        ):
            result = runner.invoke(app, ["milestone", "create", "--title", "test-milestone"])

        assert result.exit_code == 0, result.output
        mock_repo.create_milestone.assert_called_once_with(title="test-milestone")
        assert "Created milestone #3" in result.output

    def test_creates_milestone_with_due_date(self) -> None:
        """Due date is parsed and passed as datetime to create_milestone."""
        new_ms = _make_milestone(4, "sprint")
        mock_repo = MagicMock()
        mock_repo.create_milestone.return_value = new_ms

        with (
            patch.dict("os.environ", {"GITHUB_TOKEN": "tok"}),
            patch("github_project_setup.get_repo", return_value=mock_repo),
            patch("github_project_setup.Github"),
        ):
            result = runner.invoke(app, ["milestone", "create", "--title", "sprint", "--due", "2026-03-31"])

        assert result.exit_code == 0, result.output
        call_kwargs = mock_repo.create_milestone.call_args[1]
        assert "due_on" in call_kwargs
        assert call_kwargs["due_on"].year == 2026

    def test_creates_milestone_with_description(self) -> None:
        """Description is included when provided."""
        new_ms = _make_milestone(5, "release")
        mock_repo = MagicMock()
        mock_repo.create_milestone.return_value = new_ms

        with (
            patch.dict("os.environ", {"GITHUB_TOKEN": "tok"}),
            patch("github_project_setup.get_repo", return_value=mock_repo),
            patch("github_project_setup.Github"),
        ):
            result = runner.invoke(
                app, ["milestone", "create", "--title", "release", "--description", "Release milestone"]
            )

        assert result.exit_code == 0, result.output
        call_kwargs = mock_repo.create_milestone.call_args[1]
        assert call_kwargs.get("description") == "Release milestone"


# ---------------------------------------------------------------------------
# Step 4 — issue create
# ---------------------------------------------------------------------------


class TestIssueCreate:
    """Step 4: create an issue with labels and optional milestone."""

    def test_creates_issue_with_all_labels(self) -> None:
        """Issue created with priority, type, and status:needs-grooming labels."""
        new_issue = _make_issue(42, "feat: add skill", [])
        new_issue.html_url = "https://github.com/owner/repo/issues/42"
        mock_repo = MagicMock()
        mock_repo.create_issue.return_value = new_issue
        mock_repo.get_label.side_effect = _make_label

        with (
            patch.dict("os.environ", {"GITHUB_TOKEN": "tok"}),
            patch("github_project_setup.get_repo", return_value=mock_repo),
            patch("github_project_setup.Github"),
        ):
            result = runner.invoke(
                app,
                [
                    "issue",
                    "create",
                    "--title",
                    "feat: add skill",
                    "--priority-label",
                    "priority:p1",
                    "--type-label",
                    "type:feature",
                ],
            )

        assert result.exit_code == 0, result.output
        assert "Created issue #42" in result.output
        # Verify labels passed to create_issue include all three
        call_kwargs = mock_repo.create_issue.call_args[1]
        label_names = [lbl.name for lbl in call_kwargs["labels"]]
        assert "status:needs-grooming" in label_names
        assert "priority:p1" in label_names
        assert "type:feature" in label_names

    def test_creates_issue_with_milestone(self) -> None:
        """Issue is assigned to milestone when --milestone is provided."""
        new_issue = _make_issue(43, "fix: bug", [])
        new_issue.html_url = "https://github.com/owner/repo/issues/43"
        milestone_obj = _make_milestone(1, "v1.0")
        mock_repo = MagicMock()
        mock_repo.create_issue.return_value = new_issue
        mock_repo.get_label.side_effect = _make_label
        mock_repo.get_milestone.return_value = milestone_obj

        with (
            patch.dict("os.environ", {"GITHUB_TOKEN": "tok"}),
            patch("github_project_setup.get_repo", return_value=mock_repo),
            patch("github_project_setup.Github"),
        ):
            result = runner.invoke(app, ["issue", "create", "--title", "fix: bug", "--milestone", "1"])

        assert result.exit_code == 0, result.output
        call_kwargs = mock_repo.create_issue.call_args[1]
        assert call_kwargs["milestone"] is milestone_obj

    def test_missing_title_exits_nonzero(self) -> None:
        """Missing --title exits with code 1."""
        with (
            patch.dict("os.environ", {"GITHUB_TOKEN": "tok"}),
            patch("github_project_setup.Github"),
            patch("github_project_setup.get_repo", return_value=MagicMock()),
        ):
            result = runner.invoke(app, ["issue", "create"])

        assert result.exit_code == 1

    def test_unknown_label_is_skipped_not_fatal(self) -> None:
        """Unknown label prints a warning but issue is still created."""
        from github import GithubException

        new_issue = _make_issue(44, "test", [])
        new_issue.html_url = "https://github.com/owner/repo/issues/44"
        mock_repo = MagicMock()
        mock_repo.create_issue.return_value = new_issue
        mock_repo.get_label.side_effect = GithubException(404, "not found")

        with (
            patch.dict("os.environ", {"GITHUB_TOKEN": "tok"}),
            patch("github_project_setup.get_repo", return_value=mock_repo),
            patch("github_project_setup.Github"),
        ):
            result = runner.invoke(
                app, ["issue", "create", "--title", "test", "--priority-label", "priority:p99-nonexistent"]
            )

        assert result.exit_code == 0, result.output
        assert "Created issue" in result.output


# ---------------------------------------------------------------------------
# Step 5 — milestone start (the new command)
# ---------------------------------------------------------------------------


class TestMilestoneStart:
    """Step 5: bulk-transition status:needs-grooming → status:in-progress."""

    def _setup_repo(
        self, issues: list[MagicMock] | None = None, milestone_state: str = "open"
    ) -> tuple[MagicMock, MagicMock]:
        """Return (mock_repo, milestone) with issues attached."""
        if issues is None:
            issues = [
                _make_issue(10, "First issue", ["priority:p1", "status:needs-grooming"]),
                _make_issue(11, "Second issue", ["priority:p2", "status:needs-grooming"]),
            ]
        milestone = _make_milestone(1, "v1.0", state=milestone_state, open_issues=len(issues))
        mock_repo = MagicMock()
        mock_repo.get_milestone.return_value = milestone
        mock_repo.get_issues.return_value = issues
        mock_repo.get_label.return_value = _make_label("status:in-progress")
        return mock_repo, milestone

    # --- happy path ---

    def test_transitions_needs_grooming_to_in_progress(self) -> None:
        """Each issue has status:needs-grooming removed and status:in-progress added."""
        mock_repo, _ = self._setup_repo()

        with (
            patch.dict("os.environ", {"GITHUB_TOKEN": "tok"}),
            patch("github_project_setup.get_repo", return_value=mock_repo),
            patch("github_project_setup.Github"),
        ):
            result = runner.invoke(app, ["milestone", "start", "--number", "1"])

        assert result.exit_code == 0, result.output
        # Both issues should have been edited
        for iss in mock_repo.get_issues.return_value:
            iss.edit.assert_called_once()
            call_kwargs = iss.edit.call_args[1]
            assert "status:in-progress" in call_kwargs["labels"]
            assert "status:needs-grooming" not in call_kwargs["labels"]

    def test_skips_already_in_progress_issues(self) -> None:
        """Issues already labeled status:in-progress are skipped, not double-edited."""
        issues = [_make_issue(20, "already done", ["priority:p1", "status:in-progress"])]
        mock_repo, _ = self._setup_repo(issues=issues)

        with (
            patch.dict("os.environ", {"GITHUB_TOKEN": "tok"}),
            patch("github_project_setup.get_repo", return_value=mock_repo),
            patch("github_project_setup.Github"),
        ):
            result = runner.invoke(app, ["milestone", "start", "--number", "1"])

        assert result.exit_code == 0, result.output
        # edit must NOT have been called
        issues[0].edit.assert_not_called()
        assert "skipped" in result.output

    def test_creates_in_progress_label_when_missing(self) -> None:
        """status:in-progress label is created if it doesn't exist in the repo."""
        from github import GithubException

        issues = [_make_issue(30, "work", ["status:needs-grooming"])]
        new_label = _make_label("status:in-progress")
        mock_repo, _ = self._setup_repo(issues=issues)
        mock_repo.get_label.side_effect = GithubException(404, "not found")
        mock_repo.create_label.return_value = new_label

        with (
            patch.dict("os.environ", {"GITHUB_TOKEN": "tok"}),
            patch("github_project_setup.get_repo", return_value=mock_repo),
            patch("github_project_setup.Github"),
        ):
            result = runner.invoke(app, ["milestone", "start", "--number", "1"])

        assert result.exit_code == 0, result.output
        mock_repo.create_label.assert_called_once()

    def test_summary_counts_reported(self) -> None:
        """Final summary line shows transitioned/skipped/failed counts."""
        issues = [
            _make_issue(40, "pending", ["status:needs-grooming"]),
            _make_issue(41, "already", ["status:in-progress"]),
        ]
        mock_repo, _ = self._setup_repo(issues=issues)

        with (
            patch.dict("os.environ", {"GITHUB_TOKEN": "tok"}),
            patch("github_project_setup.get_repo", return_value=mock_repo),
            patch("github_project_setup.Github"),
        ):
            result = runner.invoke(app, ["milestone", "start", "--number", "1"])

        assert result.exit_code == 0, result.output
        assert "1 transitioned" in result.output
        assert "1 already in-progress" in result.output
        assert "0 failed" in result.output

    # --- error paths ---

    def test_closed_milestone_exits_nonzero(self) -> None:
        """Closed milestone exits with code 1 and explains the error."""
        mock_repo, _ = self._setup_repo(milestone_state="closed")

        with (
            patch.dict("os.environ", {"GITHUB_TOKEN": "tok"}),
            patch("github_project_setup.get_repo", return_value=mock_repo),
            patch("github_project_setup.Github"),
        ):
            result = runner.invoke(app, ["milestone", "start", "--number", "1"])

        assert result.exit_code == 1
        assert "already closed" in result.stderr

    def test_empty_milestone_exits_zero_with_warning(self) -> None:
        """Milestone with zero open issues exits 0 and prints a warning."""
        milestone = _make_milestone(1, "empty", open_issues=0)
        mock_repo = MagicMock()
        mock_repo.get_milestone.return_value = milestone

        with (
            patch.dict("os.environ", {"GITHUB_TOKEN": "tok"}),
            patch("github_project_setup.get_repo", return_value=mock_repo),
            patch("github_project_setup.Github"),
        ):
            result = runner.invoke(app, ["milestone", "start", "--number", "1"])

        assert result.exit_code == 0
        assert "no open issues" in result.output.lower()

    def test_milestone_not_found_lists_open_milestones(self) -> None:
        """Non-existent milestone prints open milestones and exits 1."""
        from github import GithubException

        open_ms = _make_milestone(2, "v2.0")
        mock_repo = MagicMock()
        mock_repo.get_milestone.side_effect = GithubException(404, "not found")
        mock_repo.get_milestones.return_value = [open_ms]

        with (
            patch.dict("os.environ", {"GITHUB_TOKEN": "tok"}),
            patch("github_project_setup.get_repo", return_value=mock_repo),
            patch("github_project_setup.Github"),
        ):
            result = runner.invoke(app, ["milestone", "start", "--number", "999"])

        assert result.exit_code == 1
        assert "v2.0" in result.stderr

    def test_per_issue_failure_continues_and_exits_nonzero(self) -> None:
        """Failure on one issue is logged; remaining issues are attempted; exit code 1."""
        from github import GithubException

        good_issue = _make_issue(50, "good", ["status:needs-grooming"])
        bad_issue = _make_issue(51, "bad", ["status:needs-grooming"])
        bad_issue.edit.side_effect = GithubException(403, "forbidden")
        issues = [good_issue, bad_issue]
        mock_repo, _ = self._setup_repo(issues=issues)

        with (
            patch.dict("os.environ", {"GITHUB_TOKEN": "tok"}),
            patch("github_project_setup.get_repo", return_value=mock_repo),
            patch("github_project_setup.Github"),
        ):
            result = runner.invoke(app, ["milestone", "start", "--number", "1"])

        assert result.exit_code == 1
        good_issue.edit.assert_called_once()  # good issue was still processed
        assert "FAILED" in result.stderr

    def test_preserves_non_status_labels(self) -> None:
        """priority:p1 label is preserved; only status:needs-grooming is removed."""
        issues = [_make_issue(60, "preserve labels", ["priority:p1", "type:feature", "status:needs-grooming"])]
        mock_repo, _ = self._setup_repo(issues=issues)

        with (
            patch.dict("os.environ", {"GITHUB_TOKEN": "tok"}),
            patch("github_project_setup.get_repo", return_value=mock_repo),
            patch("github_project_setup.Github"),
        ):
            result = runner.invoke(app, ["milestone", "start", "--number", "1"])

        assert result.exit_code == 0, result.output
        call_kwargs = issues[0].edit.call_args[1]
        assert "priority:p1" in call_kwargs["labels"]
        assert "type:feature" in call_kwargs["labels"]
        assert "status:needs-grooming" not in call_kwargs["labels"]
        assert "status:in-progress" in call_kwargs["labels"]


# ---------------------------------------------------------------------------
# Step 6 — issue list (verification step after start)
# ---------------------------------------------------------------------------


class TestIssueList:
    """Step 6: list issues to verify status labels after milestone start."""

    def test_lists_open_issues_with_labels_and_milestone(self) -> None:
        """Issue list shows number, title, labels, and milestone."""
        issue = _make_issue(70, "do work", ["priority:p1", "status:in-progress"])
        issue.milestone = _make_milestone(1, "v1.0")
        mock_repo = MagicMock()
        mock_repo.get_issues.return_value = [issue]

        with (
            patch.dict("os.environ", {"GITHUB_TOKEN": "tok"}),
            patch("github_project_setup.get_repo", return_value=mock_repo),
            patch("github_project_setup.Github"),
        ):
            result = runner.invoke(app, ["issue", "list", "--state", "open"])

        assert result.exit_code == 0, result.output
        assert "#  70" in result.output
        assert "status:in-progress" in result.output
        assert "v1.0" in result.output

    def test_empty_issue_list_prints_message(self) -> None:
        """No matching issues prints 'No issues found.'"""
        mock_repo = MagicMock()
        mock_repo.get_issues.return_value = []

        with (
            patch.dict("os.environ", {"GITHUB_TOKEN": "tok"}),
            patch("github_project_setup.get_repo", return_value=mock_repo),
            patch("github_project_setup.Github"),
        ):
            result = runner.invoke(app, ["issue", "list"])

        assert result.exit_code == 0
        assert "No issues found" in result.output

    def test_priority_filter_passes_label_to_api(self) -> None:
        """--priority p1 filters issues by the priority:p1 label."""
        p1_label = _make_label("priority:p1")
        issue = _make_issue(80, "p1 work", ["priority:p1"])
        issue.milestone = None
        mock_repo = MagicMock()
        mock_repo.get_label.return_value = p1_label
        mock_repo.get_issues.return_value = [issue]

        with (
            patch.dict("os.environ", {"GITHUB_TOKEN": "tok"}),
            patch("github_project_setup.get_repo", return_value=mock_repo),
            patch("github_project_setup.Github"),
        ):
            result = runner.invoke(app, ["issue", "list", "--priority", "p1"])

        assert result.exit_code == 0, result.output
        mock_repo.get_label.assert_called_with("priority:p1")
        call_kwargs = mock_repo.get_issues.call_args[1]
        assert "labels" in call_kwargs


# ---------------------------------------------------------------------------
# issue set-milestone (T01)
# ---------------------------------------------------------------------------


class TestIssueSetMilestone:
    """issue set-milestone: assign an issue to a milestone by number."""

    def test_set_milestone_success(self) -> None:
        """Issue is assigned to milestone; confirmation is printed."""
        issue_obj = _make_issue(100, "some issue", [])
        milestone_obj = _make_milestone(5, "Sprint 5")
        mock_repo = MagicMock()
        mock_repo.get_issue.return_value = issue_obj
        mock_repo.get_milestone.return_value = milestone_obj

        with (
            patch.dict("os.environ", {"GITHUB_TOKEN": "tok"}),
            patch("github_project_setup.get_repo", return_value=mock_repo),
            patch("github_project_setup.Github"),
        ):
            result = runner.invoke(app, ["issue", "set-milestone", "--issue", "100", "--milestone", "5"])

        assert result.exit_code == 0, result.output
        issue_obj.edit.assert_called_once_with(milestone=milestone_obj)
        assert "Issue #100 assigned to milestone #5" in result.output
        assert "Sprint 5" in result.output

    def test_set_milestone_issue_not_found_exits_1(self) -> None:
        """Non-existent issue exits with code 1."""
        from github import GithubException

        mock_repo = MagicMock()
        mock_repo.get_issue.side_effect = GithubException(404, "not found")

        with (
            patch.dict("os.environ", {"GITHUB_TOKEN": "tok"}),
            patch("github_project_setup.get_repo", return_value=mock_repo),
            patch("github_project_setup.Github"),
        ):
            result = runner.invoke(app, ["issue", "set-milestone", "--issue", "999", "--milestone", "1"])

        assert result.exit_code == 1
        assert "not found" in result.stderr.lower() or "ERROR" in result.stderr

    def test_set_milestone_milestone_not_found_exits_1(self) -> None:
        """Non-existent milestone exits with code 1."""
        from github import GithubException

        issue_obj = _make_issue(100, "some issue", [])
        mock_repo = MagicMock()
        mock_repo.get_issue.return_value = issue_obj
        mock_repo.get_milestone.side_effect = GithubException(404, "not found")

        with (
            patch.dict("os.environ", {"GITHUB_TOKEN": "tok"}),
            patch("github_project_setup.get_repo", return_value=mock_repo),
            patch("github_project_setup.Github"),
        ):
            result = runner.invoke(app, ["issue", "set-milestone", "--issue", "100", "--milestone", "999"])

        assert result.exit_code == 1
        assert "ERROR" in result.stderr


# ---------------------------------------------------------------------------
# issue remove-milestone (T02)
# ---------------------------------------------------------------------------


class TestIssueRemoveMilestone:
    """issue remove-milestone: remove milestone assignment from an issue."""

    def test_remove_milestone_success(self) -> None:
        """Issue with a milestone has it cleared; confirmation is printed."""
        from github import GithubObject

        issue_obj = _make_issue(101, "issue with milestone", [])
        issue_obj.milestone = _make_milestone(3, "old sprint")
        mock_repo = MagicMock()
        mock_repo.get_issue.return_value = issue_obj

        with (
            patch.dict("os.environ", {"GITHUB_TOKEN": "tok"}),
            patch("github_project_setup.get_repo", return_value=mock_repo),
            patch("github_project_setup.Github"),
        ):
            result = runner.invoke(app, ["issue", "remove-milestone", "--issue", "101"])

        assert result.exit_code == 0, result.output
        issue_obj.edit.assert_called_once_with(milestone=GithubObject.NotSet)
        assert "Issue #101 milestone removed" in result.output

    def test_remove_milestone_no_milestone_exits_0_with_warning(self) -> None:
        """Issue with no milestone prints warning and exits 0 (idempotent)."""
        issue_obj = _make_issue(102, "issue without milestone", [])
        issue_obj.milestone = None
        mock_repo = MagicMock()
        mock_repo.get_issue.return_value = issue_obj

        with (
            patch.dict("os.environ", {"GITHUB_TOKEN": "tok"}),
            patch("github_project_setup.get_repo", return_value=mock_repo),
            patch("github_project_setup.Github"),
        ):
            result = runner.invoke(app, ["issue", "remove-milestone", "--issue", "102"])

        assert result.exit_code == 0
        issue_obj.edit.assert_not_called()
        assert "WARNING" in result.output
        assert "no milestone" in result.output.lower()

    def test_remove_milestone_issue_not_found_exits_1(self) -> None:
        """Non-existent issue exits with code 1."""
        from github import GithubException

        mock_repo = MagicMock()
        mock_repo.get_issue.side_effect = GithubException(404, "not found")

        with (
            patch.dict("os.environ", {"GITHUB_TOKEN": "tok"}),
            patch("github_project_setup.get_repo", return_value=mock_repo),
            patch("github_project_setup.Github"),
        ):
            result = runner.invoke(app, ["issue", "remove-milestone", "--issue", "999"])

        assert result.exit_code == 1
        assert "ERROR" in result.stderr


# ---------------------------------------------------------------------------
# issue close (T03)
# ---------------------------------------------------------------------------


class TestIssueClose:
    """issue close: close an issue with an optional comment."""

    def test_close_issue_success_no_comment(self) -> None:
        """Open issue is closed; no comment is created; confirmation printed."""
        issue_obj = _make_issue(200, "open issue", [])
        issue_obj.state = "open"
        mock_repo = MagicMock()
        mock_repo.get_issue.return_value = issue_obj

        with (
            patch.dict("os.environ", {"GITHUB_TOKEN": "tok"}),
            patch("github_project_setup.get_repo", return_value=mock_repo),
            patch("github_project_setup.Github"),
        ):
            result = runner.invoke(app, ["issue", "close", "--number", "200"])

        assert result.exit_code == 0, result.output
        issue_obj.create_comment.assert_not_called()
        issue_obj.edit.assert_called_once_with(state="closed")
        assert "Issue #200 closed" in result.output

    def test_close_issue_success_with_comment(self) -> None:
        """Comment is created BEFORE issue is closed (order verified)."""
        issue_obj = _make_issue(201, "open issue", [])
        issue_obj.state = "open"
        call_order: list[str] = []
        issue_obj.create_comment.side_effect = lambda *_: call_order.append("comment")
        issue_obj.edit.side_effect = lambda **_: call_order.append("close")
        mock_repo = MagicMock()
        mock_repo.get_issue.return_value = issue_obj

        with (
            patch.dict("os.environ", {"GITHUB_TOKEN": "tok"}),
            patch("github_project_setup.get_repo", return_value=mock_repo),
            patch("github_project_setup.Github"),
        ):
            result = runner.invoke(app, ["issue", "close", "--number", "201", "--comment", "Closing: done"])

        assert result.exit_code == 0, result.output
        issue_obj.create_comment.assert_called_once_with("Closing: done")
        assert call_order == ["comment", "close"], f"Expected comment before close, got: {call_order}"
        assert "Issue #201 closed" in result.output

    def test_close_issue_not_found_exits_1(self) -> None:
        """Non-existent issue exits with code 1."""
        from github import GithubException

        mock_repo = MagicMock()
        mock_repo.get_issue.side_effect = GithubException(404, "not found")

        with (
            patch.dict("os.environ", {"GITHUB_TOKEN": "tok"}),
            patch("github_project_setup.get_repo", return_value=mock_repo),
            patch("github_project_setup.Github"),
        ):
            result = runner.invoke(app, ["issue", "close", "--number", "999"])

        assert result.exit_code == 1
        assert "ERROR" in result.stderr

    def test_close_already_closed_exits_0_with_warning(self) -> None:
        """Already-closed issue prints warning and exits 0 (idempotent)."""
        issue_obj = _make_issue(202, "closed issue", [])
        issue_obj.state = "closed"
        mock_repo = MagicMock()
        mock_repo.get_issue.return_value = issue_obj

        with (
            patch.dict("os.environ", {"GITHUB_TOKEN": "tok"}),
            patch("github_project_setup.get_repo", return_value=mock_repo),
            patch("github_project_setup.Github"),
        ):
            result = runner.invoke(app, ["issue", "close", "--number", "202"])

        assert result.exit_code == 0
        issue_obj.edit.assert_not_called()
        assert "WARNING" in result.output
        assert "already closed" in result.output.lower()

    def test_close_comment_fails_does_not_close_issue(self) -> None:
        """If comment creation fails, issue is NOT closed and exit code is 1."""
        from github import GithubException

        issue_obj = _make_issue(203, "open issue", [])
        issue_obj.state = "open"
        issue_obj.create_comment.side_effect = GithubException(500, "server error")
        mock_repo = MagicMock()
        mock_repo.get_issue.return_value = issue_obj

        with (
            patch.dict("os.environ", {"GITHUB_TOKEN": "tok"}),
            patch("github_project_setup.get_repo", return_value=mock_repo),
            patch("github_project_setup.Github"),
        ):
            result = runner.invoke(app, ["issue", "close", "--number", "203", "--comment", "will fail"])

        assert result.exit_code == 1
        issue_obj.create_comment.assert_called_once()
        issue_obj.edit.assert_not_called()  # issue must NOT be closed
        assert "ERROR" in result.stderr


# ---------------------------------------------------------------------------
# Projects V2 status updates
# ---------------------------------------------------------------------------


class TestProjectV2Status:
    """Status selection follows the configured Project V2 field options."""

    def test_discovers_status_options_for_a_user_owner(self) -> None:
        """A user-owned project maps the configured Status options by name."""
        response = {
            "data": {
                "repositoryOwner": {
                    "projectV2": {
                        "id": "PVT_user",
                        "fields": {
                            "nodes": [
                                {
                                    "id": "PVTF_status",
                                    "name": "Status",
                                    "options": [
                                        {"id": "opt_triage", "name": "Triage"},
                                        {"id": "opt_shipped", "name": "Shipped"},
                                    ],
                                }
                            ]
                        },
                    }
                }
            }
        }

        with patch("github_project_setup._gh_graphql", return_value=response) as graphql:
            project_id, field_id, options = _gps._discover_project_fields("octocat", 7)

        query = graphql.call_args.args[0]
        assert 'repositoryOwner(login: "octocat")' in query
        assert "... on ProjectV2Owner" in query
        assert (project_id, field_id) == ("PVT_user", "PVTF_status")
        assert options == {"Triage": "opt_triage", "Shipped": "opt_shipped"}

    def test_discovers_status_options_for_an_organization_owner(self) -> None:
        """An organization-owned project maps the configured Status options by name."""
        response = {
            "data": {
                "repositoryOwner": {
                    "projectV2": {
                        "id": "PVT_org",
                        "fields": {
                            "nodes": [
                                {
                                    "id": "PVTF_status",
                                    "name": "Status",
                                    "options": [{"id": "opt_ready", "name": "Ready for release"}],
                                }
                            ]
                        },
                    }
                }
            }
        }

        with patch("github_project_setup._gh_graphql", return_value=response):
            project_id, field_id, options = _gps._discover_project_fields("octo-org", 9)

        assert (project_id, field_id) == ("PVT_org", "PVTF_status")
        assert options == {"Ready for release": "opt_ready"}

    def test_graphql_errors_fail_closed_when_gh_returns_partial_data(self, capsys: pytest.CaptureFixture[str]) -> None:
        """A gh GraphQL error does not expose its partial data as a successful response."""
        from subprocess import CalledProcessError

        failure = CalledProcessError(
            1,
            ["gh", "api", "graphql"],
            output='{"data":{"repositoryOwner":{"projectV2":{"id":"PVT_1"}}}}',
            stderr="graphql: Could not resolve to a User with the login of 'octo-org'.",
        )

        with (
            patch("github_project_setup._find_gh_cli", return_value="gh"),
            patch("github_project_setup.subprocess.run", side_effect=failure),
            pytest.raises(_gps.typer.Exit),
        ):
            _gps._gh_graphql('{ repositoryOwner(login: "octo-org") { id } }')

        assert "GraphQL query failed" in capsys.readouterr().err

    def test_updates_a_discovered_custom_status_option(self) -> None:
        """A configured custom Status option is selected and applied to the project item."""
        with (
            patch(
                "github_project_setup._discover_project_fields",
                return_value=("PVT_1", "PVTF_1", {"Ready for release": "opt_ready"}),
            ),
            patch("github_project_setup._find_project_item_id", return_value="PVTI_1"),
            patch("github_project_setup._set_project_field") as set_field,
        ):
            updated = _gps._update_project_status("octo-org", 9, "I_1", "Ready for release")

        assert updated is True
        set_field.assert_called_once_with("PVT_1", "PVTI_1", "PVTF_1", "opt_ready")

    def test_rejects_an_unknown_status_before_project_item_mutation(self, capsys: pytest.CaptureFixture[str]) -> None:
        """An unconfigured option reports discovered choices without adding or editing an item."""
        with (
            patch(
                "github_project_setup._discover_project_fields",
                return_value=("PVT_1", "PVTF_1", {"Triage": "opt_triage", "Shipped": "opt_shipped"}),
            ) as discover,
            patch("github_project_setup._find_project_item_id") as find_item,
            patch("github_project_setup._set_project_field") as set_field,
        ):
            updated = _gps._update_project_status("octo-org", 9, "I_1", "Unknown")

        captured = capsys.readouterr()
        assert updated is False
        discover.assert_called_once_with("octo-org", 9)
        find_item.assert_not_called()
        set_field.assert_not_called()
        assert "Available: Triage, Shipped" in captured.err
