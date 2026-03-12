"""Tests for backlog_core/github.py.

Covers: create_issue_for_item, batch_fetch_statuses, check_open_prs_for_issue,
issue_to_local_fields, view_enrich_from_github, try_get_github.

All PyGithub boundary objects are mocked — no live API calls.
"""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Any

import pytest
from backlog_core.github import (
    batch_fetch_statuses,
    check_open_prs_for_issue,
    create_issue_for_item,
    get_github,
    issue_to_local_fields,
    try_get_github,
    view_enrich_from_github,
)
from backlog_core.models import BacklogItem, Output, ViewItemResult

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_label(mocker: MockerFixture, name: str) -> Any:
    """Return a mock PyGithub Label with ``.name`` set."""
    lbl = mocker.Mock()
    lbl.name = name
    return lbl


def _make_mock_issue(
    mocker: MockerFixture,
    *,
    number: int = 1,
    title: str = "feat: Test issue",
    body: str = "Test body",
    state: str = "open",
    label_names: list[str] | None = None,
    milestone_title: str | None = None,
    updated_at: datetime.datetime | None = None,
    pull_request: object = None,
) -> Any:
    """Create a mock PyGithub Issue with configurable attributes.

    Args:
        mocker: pytest-mock fixture for creating mocks.
        number: GitHub issue number.
        title: Issue title string.
        body: Issue body string.
        state: Issue state ("open" or "closed").
        label_names: Label name strings to attach.
        milestone_title: Milestone title or None for no milestone.
        updated_at: Updated-at datetime or None.
        pull_request: Set to a Mock to simulate a PR; None for plain issues.

    Returns:
        Mock object mimicking a PyGithub Issue.
    """
    issue = mocker.Mock()
    issue.number = number
    issue.title = title
    issue.body = body
    issue.state = state
    issue.pull_request = pull_request
    issue.labels = [_make_mock_label(mocker, n) for n in (label_names or [])]
    if milestone_title is not None:
        ms = mocker.Mock()
        ms.title = milestone_title
        issue.milestone = ms
    else:
        issue.milestone = None
    issue.updated_at = updated_at or datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC)
    return issue


def _make_mock_repo(mocker: MockerFixture) -> Any:
    """Return a minimal mock PyGithub Repository."""
    repo = mocker.Mock()
    repo.get_label.return_value = mocker.Mock()
    return repo


# ---------------------------------------------------------------------------
# create_issue_for_item
# ---------------------------------------------------------------------------


class TestCreateIssueForItem:
    """create_issue_for_item creates a GH issue from a BacklogItem."""

    def test_create_issue_returns_issue_number(self, mocker: MockerFixture) -> None:
        """Returns the integer issue number when issue is created successfully.

        Tests: happy-path creation with valid title.
        How: Mock repo.get_label and repo.create_issue; call with a real BacklogItem.
        Why: Caller uses the return value to update the local cache.
        """
        # Arrange
        repo = _make_mock_repo(mocker)
        mock_issue = mocker.Mock()
        mock_issue.number = 42
        repo.create_issue.return_value = mock_issue
        item = BacklogItem(title="Add dark mode", item_type="feature", priority="P1")

        # Act
        result = create_issue_for_item(repo, item)

        # Assert
        assert result == 42
        repo.create_issue.assert_called_once()

    def test_create_issue_uses_correct_title_prefix(self, mocker: MockerFixture) -> None:
        """Issue title is prefixed with type-derived conventional-commit prefix.

        Tests: title formatting for each item_type.
        How: Check the ``title`` kwarg passed to repo.create_issue.
        Why: GH issues must follow conventional-commit prefix conventions.
        """
        # Arrange
        repo = _make_mock_repo(mocker)
        mock_issue = mocker.Mock()
        mock_issue.number = 7
        repo.create_issue.return_value = mock_issue
        item = BacklogItem(title="Fix null crash", item_type="bug", priority="P0")

        # Act
        create_issue_for_item(repo, item)

        # Assert
        call_kwargs = repo.create_issue.call_args.kwargs
        assert call_kwargs["title"].startswith("fix: Fix null crash")

    def test_create_issue_dry_run_returns_none_and_logs(self, mocker: MockerFixture) -> None:
        """dry_run=True returns None without calling repo.create_issue.

        Tests: dry-run mode leaves GH untouched.
        How: Call with dry_run=True; assert create_issue not called.
        Why: Dry-run must be safe to invoke without side effects.
        """
        # Arrange
        repo = _make_mock_repo(mocker)
        out = Output()
        item = BacklogItem(title="Dry run item", item_type="feature", priority="P1")

        # Act
        result = create_issue_for_item(repo, item, dry_run=True, output=out)

        # Assert
        assert result is None
        repo.create_issue.assert_not_called()
        assert any("dry-run" in m.lower() for m in out.messages)

    def test_create_issue_empty_title_returns_none(self, mocker: MockerFixture) -> None:
        """Empty item title returns None without touching GitHub.

        Tests: guard clause for missing title.
        How: BacklogItem with title="" passed to function.
        Why: An issue with no title is invalid — must not be created.
        """
        # Arrange
        repo = _make_mock_repo(mocker)
        item = BacklogItem(title="", item_type="feature", priority="P1")

        # Act
        result = create_issue_for_item(repo, item)

        # Assert
        assert result is None
        repo.create_issue.assert_not_called()

    def test_create_issue_attaches_labels(self, mocker: MockerFixture) -> None:
        """Issue is created with status, priority, and type labels.

        Tests: label list passed to repo.create_issue.
        How: Inspect the ``labels`` kwarg after a successful call.
        Why: Labels drive filtering and status tracking on GH.
        """
        # Arrange
        repo = _make_mock_repo(mocker)
        mock_issue = mocker.Mock()
        mock_issue.number = 10
        repo.create_issue.return_value = mock_issue
        item = BacklogItem(title="Implement search", item_type="feature", priority="P2")

        # Act
        create_issue_for_item(repo, item)

        # Assert
        call_kwargs = repo.create_issue.call_args.kwargs
        assert "labels" in call_kwargs
        assert len(call_kwargs["labels"]) > 0

    def test_create_issue_warns_on_missing_label(self, mocker: MockerFixture) -> None:
        """Warns via Output when a label does not exist on the repo.

        Tests: GithubException on get_label triggers warning, not a crash.
        How: repo.get_label raises GithubException; check out.warnings populated.
        Why: Missing labels must not abort issue creation.
        """
        # Arrange
        from github import GithubException

        repo = _make_mock_repo(mocker)
        repo.get_label.side_effect = GithubException(404, "Not Found", None)
        mock_issue = mocker.Mock()
        mock_issue.number = 5
        repo.create_issue.return_value = mock_issue
        out = Output()
        item = BacklogItem(title="Some feature", item_type="feature", priority="P1")

        # Act
        result = create_issue_for_item(repo, item, output=out)

        # Assert
        assert result == 5
        assert any("WARNING" in w for w in out.warnings)


# ---------------------------------------------------------------------------
# batch_fetch_statuses
# ---------------------------------------------------------------------------


class TestBatchFetchStatuses:
    """batch_fetch_statuses maps issue numbers to IssueStatus from a single GH call."""

    def test_batch_fetch_returns_status_for_known_issue(self, mocker: MockerFixture) -> None:
        """Returns IssueStatus for items whose issue numbers appear in GH results.

        Tests: happy-path mapping of open issues to IssueStatus.
        How: Mock try_get_github to return a repo with one matching issue.
        Why: Callers use the dict to display live status without N+1 queries.
        """
        # Arrange
        mock_gh_issue = _make_mock_issue(
            mocker, number=10, label_names=["status:in-progress", "priority:p1"], milestone_title="v1.0"
        )
        mock_repo = mocker.Mock()
        mock_repo.get_issues.return_value = [mock_gh_issue]
        mocker.patch("backlog_core.github.try_get_github", return_value=mock_repo)

        items = [BacklogItem(title="Feature A", issue="#10", priority="P1")]

        # Act
        result = batch_fetch_statuses(items)

        # Assert
        assert 10 in result
        assert result[10].status == "status:in-progress"
        assert result[10].milestone == "v1.0"

    def test_batch_fetch_skips_items_without_issue_number(self, mocker: MockerFixture) -> None:
        """Items with no issue field are silently skipped.

        Tests: guard clause for items without a GH issue reference.
        How: Pass BacklogItem with issue="" and verify result dict is empty.
        Why: Local-only items have no issue number to look up.
        """
        # Arrange
        mock_gh_issue = _make_mock_issue(mocker, number=20)
        mock_repo = mocker.Mock()
        mock_repo.get_issues.return_value = [mock_gh_issue]
        mocker.patch("backlog_core.github.try_get_github", return_value=mock_repo)

        items = [BacklogItem(title="No issue item", issue="", priority="P1")]

        # Act
        result = batch_fetch_statuses(items)

        # Assert
        assert result == {}

    def test_batch_fetch_offline_returns_empty_dict(self, mocker: MockerFixture) -> None:
        """Returns empty dict when try_get_github returns None (offline/no token).

        Tests: graceful degradation path.
        How: Patch try_get_github to return None.
        Why: Agents must work offline — empty status is acceptable, crash is not.
        """
        # Arrange
        mocker.patch("backlog_core.github.try_get_github", return_value=None)
        items = [BacklogItem(title="Item", issue="#5", priority="P1")]

        # Act
        result = batch_fetch_statuses(items)

        # Assert
        assert result == {}

    def test_batch_fetch_ignores_prs_in_issue_list(self, mocker: MockerFixture) -> None:
        """Pull requests returned by get_issues are excluded from the result.

        Tests: pull_request filter inside batch_fetch_statuses.
        How: Return a mock issue with pull_request set; verify the number is absent.
        Why: PRs appear in get_issues results; including them corrupts the status map.
        """
        # Arrange
        pr_mock = _make_mock_issue(mocker, number=99, pull_request=object())
        mock_repo = mocker.Mock()
        mock_repo.get_issues.return_value = [pr_mock]
        mocker.patch("backlog_core.github.try_get_github", return_value=mock_repo)

        items = [BacklogItem(title="PR item", issue="#99", priority="P1")]

        # Act
        result = batch_fetch_statuses(items)

        # Assert
        assert 99 not in result

    def test_batch_fetch_empty_milestone_is_empty_string(self, mocker: MockerFixture) -> None:
        """IssueStatus.milestone is "" when the issue has no milestone.

        Tests: None milestone handling.
        How: Return issue with milestone=None.
        Why: Callers string-format the milestone field — None would crash.
        """
        # Arrange
        mock_gh_issue = _make_mock_issue(mocker, number=30, milestone_title=None)
        mock_repo = mocker.Mock()
        mock_repo.get_issues.return_value = [mock_gh_issue]
        mocker.patch("backlog_core.github.try_get_github", return_value=mock_repo)

        items = [BacklogItem(title="No milestone", issue="#30", priority="P1")]

        # Act
        result = batch_fetch_statuses(items)

        # Assert
        assert result[30].milestone == ""


# ---------------------------------------------------------------------------
# check_open_prs_for_issue
# ---------------------------------------------------------------------------


class TestCheckOpenPrsForIssue:
    """check_open_prs_for_issue returns PullRequestRef list for matching PRs."""

    def test_found_prs_returned_as_list(self, mocker: MockerFixture) -> None:
        """Returns a list of PullRequestRef for each matching open PR.

        Tests: happy-path PR search result mapping.
        How: Mock Github.search_issues to return one PR result.
        Why: Callers block close/resolve when PRs are open.
        """
        # Arrange
        mock_pr = mocker.Mock()
        mock_pr.number = 55
        mock_pr.title = "Fix: implement feature"
        mock_pr.html_url = "https://github.com/test/repo/pull/55"

        mock_gh = mocker.Mock()
        mock_gh.search_issues.return_value = [mock_pr]
        mocker.patch("backlog_core.github.Github", return_value=mock_gh)
        mocker.patch.dict("os.environ", {"GITHUB_TOKEN": "fake-token"})

        # Act
        result = check_open_prs_for_issue(10, "test/repo")

        # Assert
        assert len(result) == 1
        assert result[0].number == 55
        assert result[0].title == "Fix: implement feature"
        assert result[0].url == "https://github.com/test/repo/pull/55"

    def test_no_prs_found_returns_empty_list(self, mocker: MockerFixture) -> None:
        """Returns empty list when search yields no open PRs.

        Tests: no-match case.
        How: search_issues returns empty iterable.
        Why: Empty list is the expected signal that close/resolve is safe.
        """
        # Arrange
        mock_gh = mocker.Mock()
        mock_gh.search_issues.return_value = []
        mocker.patch("backlog_core.github.Github", return_value=mock_gh)
        mocker.patch.dict("os.environ", {"GITHUB_TOKEN": "fake-token"})

        # Act
        result = check_open_prs_for_issue(99, "test/repo")

        # Assert
        assert result == []

    def test_exception_during_search_returns_empty_list(self, mocker: MockerFixture) -> None:
        """GithubException during search returns empty list without raising.

        Tests: exception guard clause.
        How: search_issues raises GithubException; assert empty list returned.
        Why: Network errors or rate limits must not crash the caller.
        """
        # Arrange
        from github import GithubException

        mock_gh = mocker.Mock()
        mock_gh.search_issues.side_effect = GithubException(403, "Forbidden", None)
        mocker.patch("backlog_core.github.Github", return_value=mock_gh)
        mocker.patch.dict("os.environ", {"GITHUB_TOKEN": "fake-token"})

        # Act
        result = check_open_prs_for_issue(5, "test/repo")

        # Assert
        assert result == []

    def test_bad_credentials_returns_empty_list(self, mocker: MockerFixture) -> None:
        """Returns empty list when GitHub raises a 401 auth error during search.

        Tests: authentication failure path.
        How: Mock Github.search_issues to raise GithubException(401); assert [] returned.
        Why: Bad/expired tokens must not crash callers; empty list signals unavailability.
        """
        # Arrange
        from github import GithubException

        mocker.patch.dict("os.environ", {"GITHUB_TOKEN": "expired-token"})
        mock_gh = mocker.Mock()
        mock_gh.search_issues.side_effect = GithubException(401, "Bad credentials", None)
        mocker.patch("backlog_core.github.Github", return_value=mock_gh)

        # Act
        result = check_open_prs_for_issue(1, "test/repo")

        # Assert
        assert result == []


# ---------------------------------------------------------------------------
# issue_to_local_fields
# ---------------------------------------------------------------------------


class TestIssueToLocalFields:
    """issue_to_local_fields extracts BacklogItem-compatible fields from a GH Issue."""

    def test_maps_title_and_body(self, mocker: MockerFixture) -> None:
        """Title and body are copied verbatim into IssueLocalFields.

        Tests: basic field mapping.
        How: Pass mock issue with distinct title/body; assert fields match.
        Why: Callers use title/body to populate or update local cache files.
        """
        # Arrange
        issue = _make_mock_issue(mocker, title="feat: New feature", body="## Story\n\nAs a user...")

        # Act
        result = issue_to_local_fields(issue)

        # Assert
        assert result.title == "feat: New feature"
        assert result.body == "## Story\n\nAs a user..."

    def test_maps_priority_from_label(self, mocker: MockerFixture) -> None:
        """Priority is extracted from the ``priority:`` label.

        Tests: priority label parsing.
        How: Pass issue with label "priority:p2"; verify result.priority == "P2".
        Why: Priority drives backlog ordering and GH-first migration logic.
        """
        # Arrange
        issue = _make_mock_issue(mocker, label_names=["priority:p2", "type:feature"])

        # Act
        result = issue_to_local_fields(issue)

        # Assert
        assert result.priority == "P2"

    def test_default_priority_when_no_label(self, mocker: MockerFixture) -> None:
        """Priority defaults to P1 when no priority label is present.

        Tests: missing priority label fallback.
        How: Pass issue with no priority-prefixed label.
        Why: P1 is the safe default — items without a label must not be lost.
        """
        # Arrange
        issue = _make_mock_issue(mocker, label_names=["type:bug"])

        # Act
        result = issue_to_local_fields(issue)

        # Assert
        assert result.priority == "P1"

    def test_maps_type_from_label(self, mocker: MockerFixture) -> None:
        """item_type is extracted from the ``type:`` label and capitalized.

        Tests: type label parsing.
        How: Pass issue with label "type:bug"; verify result.item_type == "Bug".
        Why: item_type is used for conventional-commit prefix and GH label logic.
        """
        # Arrange
        issue = _make_mock_issue(mocker, label_names=["type:bug", "priority:p1"])

        # Act
        result = issue_to_local_fields(issue)

        # Assert
        assert result.item_type == "Bug"

    def test_default_type_when_no_type_label(self, mocker: MockerFixture) -> None:
        """item_type defaults to Feature when no type label is present.

        Tests: missing type label fallback.
        How: Pass issue with only a priority label.
        Why: Feature is the safe default for unclassified items.
        """
        # Arrange
        issue = _make_mock_issue(mocker, label_names=["priority:p0"])

        # Act
        result = issue_to_local_fields(issue)

        # Assert
        assert result.item_type == "Feature"

    def test_closed_issue_maps_to_done_status(self, mocker: MockerFixture) -> None:
        """Closed GH issues map to status="done" regardless of labels.

        Tests: closed-state status mapping.
        How: Pass issue with state="closed".
        Why: Closed issues must appear as done in the local cache.
        """
        # Arrange
        issue = _make_mock_issue(mocker, state="closed")

        # Act
        result = issue_to_local_fields(issue)

        # Assert
        assert result.status == "done"

    def test_open_issue_status_from_status_label(self, mocker: MockerFixture) -> None:
        """Open issues use status from the ``status:`` label.

        Tests: status label extraction for open issues.
        How: Pass open issue with "status:in-progress" label.
        Why: Status label drives workflow state in the backlog display.
        """
        # Arrange
        issue = _make_mock_issue(mocker, state="open", label_names=["status:in-progress"])

        # Act
        result = issue_to_local_fields(issue)

        # Assert
        assert result.status == "in-progress"

    def test_open_issue_default_status_when_no_label(self, mocker: MockerFixture) -> None:
        """Open issues default to status="open" when no status label is present.

        Tests: missing status label fallback for open issues.
        How: Pass open issue with no status-prefixed label.
        Why: "open" is the safe default that keeps items visible.
        """
        # Arrange
        issue = _make_mock_issue(mocker, state="open", label_names=[])

        # Act
        result = issue_to_local_fields(issue)

        # Assert
        assert result.status == "open"

    def test_milestone_mapped_when_present(self, mocker: MockerFixture) -> None:
        """milestone field is set from issue.milestone.title when a milestone exists.

        Tests: milestone mapping.
        How: Pass issue with milestone.title="v2.0".
        Why: Milestone tracks release targeting in the backlog view.
        """
        # Arrange
        issue = _make_mock_issue(mocker, milestone_title="v2.0")

        # Act
        result = issue_to_local_fields(issue)

        # Assert
        assert result.milestone == "v2.0"

    def test_milestone_is_empty_string_when_none(self, mocker: MockerFixture) -> None:
        """milestone is "" when issue has no milestone.

        Tests: None milestone sentinel handling.
        How: Pass issue with milestone=None.
        Why: Callers expect a string — None would break formatting.
        """
        # Arrange
        issue = _make_mock_issue(mocker, milestone_title=None)

        # Act
        result = issue_to_local_fields(issue)

        # Assert
        assert result.milestone == ""

    def test_body_none_becomes_empty_string(self, mocker: MockerFixture) -> None:
        """None body on GH issue is coerced to empty string.

        Tests: None body guard.
        How: Set issue.body = None on the mock.
        Why: Callers expect a string for display/write operations.
        """
        # Arrange
        issue = _make_mock_issue(mocker)
        issue.body = None

        # Act
        result = issue_to_local_fields(issue)

        # Assert
        assert result.body == ""


# ---------------------------------------------------------------------------
# view_enrich_from_github
# ---------------------------------------------------------------------------


class TestViewEnrichFromGithub:
    """view_enrich_from_github populates ViewItemResult from a live GH issue."""

    def test_sets_number_state_body_labels(self, mocker: MockerFixture) -> None:
        """Enrichment sets number, state, body, and labels on the result.

        Tests: core field population from GH issue.
        How: Mock try_get_github and repo.get_issue; check result fields.
        Why: Callers rely on these fields to render the view command output.
        """
        # Arrange
        gh_issue = _make_mock_issue(
            mocker,
            number=42,
            title="feat: Thing",
            body="Issue body",
            state="open",
            label_names=["status:in-progress", "priority:p1"],
        )
        mock_repo = mocker.Mock()
        mock_repo.get_issue.return_value = gh_issue
        mocker.patch("backlog_core.github.try_get_github", return_value=mock_repo)

        result = ViewItemResult()

        # Act
        enriched = view_enrich_from_github(result, "42")

        # Assert
        assert enriched is True
        assert result.number == 42
        assert result.state == "open"
        assert result.body == "Issue body"
        assert "status:in-progress" in result.labels

    def test_returns_false_when_github_unavailable(self, mocker: MockerFixture) -> None:
        """Returns False and leaves result unchanged when try_get_github returns None.

        Tests: offline fallback.
        How: Patch try_get_github to return None.
        Why: Callers check the return value to decide whether to show GH data.
        """
        # Arrange
        mocker.patch("backlog_core.github.try_get_github", return_value=None)
        result = ViewItemResult()

        # Act
        enriched = view_enrich_from_github(result, "10")

        # Assert
        assert enriched is False
        assert result.number is None

    def test_returns_false_on_github_exception(self, mocker: MockerFixture) -> None:
        """Returns False when get_issue raises GithubException.

        Tests: exception guard for missing / deleted issues.
        How: repo.get_issue raises GithubException(404).
        Why: Deleted or private issues must not crash the view command.
        """
        # Arrange
        from github import GithubException

        mock_repo = mocker.Mock()
        mock_repo.get_issue.side_effect = GithubException(404, "Not Found", None)
        mocker.patch("backlog_core.github.try_get_github", return_value=mock_repo)
        result = ViewItemResult()

        # Act
        enriched = view_enrich_from_github(result, "999")

        # Assert
        assert enriched is False

    def test_sets_milestone_when_present(self, mocker: MockerFixture) -> None:
        """Milestone title is set on the result when the GH issue has a milestone.

        Tests: milestone field enrichment.
        How: Mock issue with milestone_title="v3.0".
        Why: Milestone is displayed in the view output.
        """
        # Arrange
        gh_issue = _make_mock_issue(mocker, number=7, milestone_title="v3.0")
        mock_repo = mocker.Mock()
        mock_repo.get_issue.return_value = gh_issue
        mocker.patch("backlog_core.github.try_get_github", return_value=mock_repo)
        result = ViewItemResult()

        # Act
        view_enrich_from_github(result, "7")

        # Assert
        assert result.milestone == "v3.0"

    def test_parses_priority_from_labels(self, mocker: MockerFixture) -> None:
        """Priority field is set from priority: label during enrichment.

        Tests: label parsing for priority.
        How: Pass issue with "priority:p2" label.
        Why: Priority is surfaced in the view output derived from GH labels.
        """
        # Arrange
        gh_issue = _make_mock_issue(mocker, number=8, label_names=["priority:p2"])
        mock_repo = mocker.Mock()
        mock_repo.get_issue.return_value = gh_issue
        mocker.patch("backlog_core.github.try_get_github", return_value=mock_repo)
        result = ViewItemResult()

        # Act
        view_enrich_from_github(result, "8")

        # Assert
        assert result.priority == "P2"

    def test_parses_status_from_labels(self, mocker: MockerFixture) -> None:
        """Status field is set from status: label during enrichment.

        Tests: label parsing for status.
        How: Pass issue with "status:needs-grooming" label.
        Why: Status drives workflow state display in view output.
        """
        # Arrange
        gh_issue = _make_mock_issue(mocker, number=9, label_names=["status:needs-grooming"])
        mock_repo = mocker.Mock()
        mock_repo.get_issue.return_value = gh_issue
        mocker.patch("backlog_core.github.try_get_github", return_value=mock_repo)
        result = ViewItemResult()

        # Act
        view_enrich_from_github(result, "9")

        # Assert
        assert result.status == "needs-grooming"


# ---------------------------------------------------------------------------
# get_github
# ---------------------------------------------------------------------------


class TestGetGithub:
    """get_github raises on missing token and passes timeout to Github()."""

    def test_no_token_raises_github_unavailable_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Raises GitHubUnavailableError when GITHUB_TOKEN is absent.

        Tests: guard clause for missing token.
        How: Remove GITHUB_TOKEN; call get_github and assert the error type.
        Why: Callers expect this specific error type — not a KeyError or None.
        """
        # Arrange
        from backlog_core.models import GitHubUnavailableError

        monkeypatch.delenv("GITHUB_TOKEN", raising=False)

        # Act / Assert
        with pytest.raises(GitHubUnavailableError):
            get_github("test/repo")

    def test_passes_default_timeout_to_github_constructor(
        self, mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Github() is constructed with the default timeout=15.

        Tests: timeout kwarg forwarding — the fix for the MCP transport timeout bug.
        How: Patch Github; call get_github; inspect constructor call_args.
        Why: Without timeout, a slow GitHub API response blocks the entire
             asyncio.to_thread() worker until the 60-second MCP deadline fires.
        """
        # Arrange
        monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
        mock_repo = mocker.Mock()
        mock_gh_instance = mocker.Mock()
        mock_gh_instance.get_repo.return_value = mock_repo
        mock_github_cls = mocker.patch("backlog_core.github.Github", return_value=mock_gh_instance)

        # Act
        get_github("owner/repo")

        # Assert
        _, kwargs = mock_github_cls.call_args
        assert kwargs.get("timeout") == 15

    def test_passes_custom_timeout_to_github_constructor(
        self, mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Github() receives caller-supplied timeout when provided.

        Tests: timeout parameter passthrough for non-default values.
        How: Call get_github with timeout=5; verify Github() got timeout=5.
        Why: Callers may need a shorter timeout for time-sensitive contexts.
        """
        # Arrange
        monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
        mock_repo = mocker.Mock()
        mock_gh_instance = mocker.Mock()
        mock_gh_instance.get_repo.return_value = mock_repo
        mock_github_cls = mocker.patch("backlog_core.github.Github", return_value=mock_gh_instance)

        # Act
        get_github("owner/repo", timeout=5)

        # Assert
        _, kwargs = mock_github_cls.call_args
        assert kwargs.get("timeout") == 5

    def test_returns_repository_from_get_repo(self, mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch) -> None:
        """Returns the Repository object from gh.get_repo().

        Tests: return value is the repo object, not the Github client.
        How: Patch Github.get_repo to return a sentinel; assert it is returned.
        Why: Callers pass the return value directly to PyGithub Repository methods.
        """
        # Arrange
        monkeypatch.setenv("GITHUB_TOKEN", "valid-token")
        mock_repo = mocker.Mock()
        mock_gh_instance = mocker.Mock()
        mock_gh_instance.get_repo.return_value = mock_repo
        mocker.patch("backlog_core.github.Github", return_value=mock_gh_instance)

        # Act
        result = get_github("owner/repo")

        # Assert
        assert result is mock_repo


# ---------------------------------------------------------------------------
# try_get_github
# ---------------------------------------------------------------------------


class TestTryGetGithub:
    """try_get_github returns a Repository or None based on token availability."""

    def test_no_github_token_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Returns None when GITHUB_TOKEN is not set in the environment.

        Tests: no-token fast path.
        How: Remove GITHUB_TOKEN from env; call try_get_github.
        Why: The function must not attempt a network connection without credentials.
        """
        # Arrange
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)

        # Act
        result = try_get_github("test/repo")

        # Assert
        assert result is None

    def test_github_exception_returns_none(self, mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch) -> None:
        """Returns None when get_repo raises a GithubException (auth error, network).

        Tests: exception guard clause.
        How: Patch Github.get_repo to raise GithubException; assert None returned.
        Why: Connection failures must not propagate to callers.
        """
        # Arrange
        from github import GithubException

        monkeypatch.setenv("GITHUB_TOKEN", "bad-token")
        mock_gh_instance = mocker.Mock()
        mock_gh_instance.get_repo.side_effect = GithubException(401, "Bad credentials", None)
        mocker.patch("backlog_core.github.Github", return_value=mock_gh_instance)

        # Act
        result = try_get_github("test/repo")

        # Assert
        assert result is None

    def test_valid_token_returns_repo(self, mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch) -> None:
        """Returns a Repository object when token is valid and get_repo succeeds.

        Tests: happy-path connection.
        How: Patch Github.get_repo to return a mock repo; assert it is returned.
        Why: Callers rely on a non-None return to proceed with GH operations.
        """
        # Arrange
        monkeypatch.setenv("GITHUB_TOKEN", "valid-token")
        mock_repo = mocker.Mock()
        mock_gh_instance = mocker.Mock()
        mock_gh_instance.get_repo.return_value = mock_repo
        mocker.patch("backlog_core.github.Github", return_value=mock_gh_instance)

        # Act
        result = try_get_github("owner/repo")

        # Assert
        assert result is mock_repo


# ---------------------------------------------------------------------------
# Parametrized: item_type prefix mapping in create_issue_for_item
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("item_type", "expected_prefix"),
    [
        ("feature", "feat"),
        ("bug", "fix"),
        ("refactor", "refactor"),
        ("docs", "docs"),
        ("chore", "chore"),
        ("unknown_type", "feat"),  # unknown type falls back to "feat"
    ],
)
def test_create_issue_prefix_per_type(mocker: MockerFixture, item_type: str, expected_prefix: str) -> None:
    """Issue title prefix matches the type-to-conventional-commit map.

    Tests: type-to-prefix mapping for all supported item types.
    How: Parametrize over each item_type; assert title starts with correct prefix.
    Why: Breaking the prefix for any type silently corrupts GH issue titles.
    """
    # Arrange
    repo = _make_mock_repo(mocker)
    mock_issue = mocker.Mock()
    mock_issue.number = 1
    repo.create_issue.return_value = mock_issue
    item = BacklogItem(title="Some work", item_type=item_type, priority="P1")

    # Act
    create_issue_for_item(repo, item)

    # Assert
    call_kwargs = repo.create_issue.call_args.kwargs
    assert call_kwargs["title"].startswith(f"{expected_prefix}: ")


# ---------------------------------------------------------------------------
# SamTask GitHub operations
# ---------------------------------------------------------------------------

from backlog_core.github import create_task_issue, get_task_issues, update_task_status
from backlog_core.models import SamTask
from backlog_core.parsing import build_sam_task_body


def _make_sam_task(**kwargs: object) -> SamTask:
    defaults: dict[str, object] = {
        "task_id": "T1",
        "feature": "feat",
        "task_type": "research",
        "status": "not-started",
        "agent": "context-gathering",
        "priority": 1,
        "skills": [],
        "dependencies": [],
    }
    defaults.update(kwargs)
    return SamTask(**defaults)  # type: ignore[arg-type]


class TestCreateTaskIssue:
    def test_creates_issue_and_links_as_sub_issue(self, mocker: MockerFixture) -> None:
        repo = _make_mock_repo(mocker)
        task = _make_sam_task()
        mock_task_issue = mocker.Mock()
        mock_task_issue.number = 42
        repo.create_issue.return_value = mock_task_issue
        mock_parent = mocker.Mock()
        repo.get_issue.return_value = mock_parent

        result = create_task_issue(repo, parent_issue_number=10, task=task, description="Do the thing")

        assert result is mock_task_issue
        repo.create_issue.assert_called_once()
        mock_parent.add_sub_issue.assert_called_once_with(mock_task_issue)

    def test_returns_none_on_create_failure(self, mocker: MockerFixture) -> None:
        from github import GithubException

        repo = _make_mock_repo(mocker)
        repo.create_issue.side_effect = GithubException(422, "validation failed")
        task = _make_sam_task()

        result = create_task_issue(repo, parent_issue_number=10, task=task)

        assert result is None

    def test_still_returns_issue_if_sub_issue_link_fails(self, mocker: MockerFixture) -> None:
        from github import GithubException

        repo = _make_mock_repo(mocker)
        task = _make_sam_task()
        mock_task_issue = mocker.Mock()
        mock_task_issue.number = 99
        repo.create_issue.return_value = mock_task_issue
        mock_parent = mocker.Mock()
        mock_parent.add_sub_issue.side_effect = GithubException(404, "not found")
        repo.get_issue.return_value = mock_parent

        result = create_task_issue(repo, parent_issue_number=10, task=task)

        assert result is mock_task_issue


class TestGetTaskIssues:
    def test_returns_sorted_by_priority_position(self, mocker: MockerFixture) -> None:
        repo = _make_mock_repo(mocker)
        si_a = mocker.Mock()
        si_a.priority_position = 3
        si_b = mocker.Mock()
        si_b.priority_position = 1
        si_c = mocker.Mock()
        si_c.priority_position = 2
        mock_parent = mocker.Mock()
        mock_parent.get_sub_issues.return_value = [si_a, si_b, si_c]
        repo.get_issue.return_value = mock_parent

        result = get_task_issues(repo, parent_issue_number=5)

        assert result == [si_b, si_c, si_a]

    def test_returns_empty_on_github_error(self, mocker: MockerFixture) -> None:
        from github import GithubException

        repo = _make_mock_repo(mocker)
        repo.get_issue.side_effect = GithubException(404, "not found")

        result = get_task_issues(repo, parent_issue_number=5)

        assert result == []


class TestUpdateTaskStatus:
    def test_updates_status_in_body(self, mocker: MockerFixture) -> None:
        repo = _make_mock_repo(mocker)
        task = _make_sam_task(status="not-started")
        body = build_sam_task_body(task)
        mock_issue = mocker.Mock()
        mock_issue.body = body
        repo.get_issue.return_value = mock_issue

        changed = update_task_status(repo, issue_number=7, new_status="in-progress")

        assert changed is True
        mock_issue.edit.assert_called_once()
        updated_body: str = mock_issue.edit.call_args.kwargs["body"]
        assert "status: in-progress" in updated_body

    def test_no_op_when_status_already_matches(self, mocker: MockerFixture) -> None:
        repo = _make_mock_repo(mocker)
        task = _make_sam_task(status="complete")
        mock_issue = mocker.Mock()
        mock_issue.body = build_sam_task_body(task)
        repo.get_issue.return_value = mock_issue

        changed = update_task_status(repo, issue_number=7, new_status="complete")

        assert changed is False
        mock_issue.edit.assert_not_called()

    def test_returns_false_when_no_sam_block(self, mocker: MockerFixture) -> None:
        repo = _make_mock_repo(mocker)
        mock_issue = mocker.Mock()
        mock_issue.body = "## What\n\nNo metadata.\n"
        repo.get_issue.return_value = mock_issue

        changed = update_task_status(repo, issue_number=7, new_status="complete")

        assert changed is False
