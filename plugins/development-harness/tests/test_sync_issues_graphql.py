"""Tests for sync_issues_graphql() in backlog_core/gh_client.py.

Covers: pagination delegation, since-filter passthrough, callback invocation,
timestamp read/write, and error propagation.

All PyGithub boundary objects are mocked — no live API calls.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import pytest
from backlog_core.gh_client import sync_issues_graphql
from backlog_core.models import BacklogError

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_repo(mocker: MockerFixture) -> Any:
    """Return a minimal mock PyGithub Repository.

    Args:
        mocker: pytest-mock fixture.

    Returns:
        Mock object with .full_name set to ``"test-owner/test-repo"``.
    """
    repo = mocker.Mock()
    repo.full_name = "test-owner/test-repo"
    return repo


def _make_issue_node(number: int) -> dict[str, Any]:
    """Build a minimal IssueNode dict for testing.

    Args:
        number: GitHub issue number.

    Returns:
        Dict with required IssueNode keys populated.
    """
    return {
        "number": number,
        "title": f"Issue {number}",
        "body": "",
        "state": "OPEN",
        "labels": [],
        "assignees": [],
        "milestone": None,
        "createdAt": "2024-01-01T00:00:00Z",
        "updatedAt": "2024-01-01T00:00:00Z",
        "closedAt": None,
        "url": f"https://github.com/test-owner/test-repo/issues/{number}",
        "id": f"node_{number}",
    }


# ---------------------------------------------------------------------------
# TestSyncIssuesGraphqlPagination
# ---------------------------------------------------------------------------


class TestSyncIssuesGraphqlPaginationFetchesAllPages:
    """sync_issues_graphql delegates pagination to _fetch_issues_graphql."""

    def test_sync_issues_graphql_pagination_fetches_all_pages(self, mocker: MockerFixture) -> None:
        """Arrange: _fetch_issues_graphql returns 6 issues.
        Act: call sync_issues_graphql.
        Assert: all 6 issues are returned.
        """
        # Arrange
        repo = _make_mock_repo(mocker)
        issues = [_make_issue_node(i) for i in range(1, 7)]
        mock_fetch = mocker.patch("backlog_core.gh_client._fetch_issues_graphql", return_value=issues)

        # Act
        result = sync_issues_graphql(repo, "test-owner", "test-repo")

        # Assert
        assert len(result) == 6
        assert result == issues
        mock_fetch.assert_called_once()


# ---------------------------------------------------------------------------
# TestSyncIssuesGraphqlSinceFilter
# ---------------------------------------------------------------------------


class TestSyncIssuesGraphqlSinceFilterPassthrough:
    """sync_issues_graphql converts datetime since to ISO string for _fetch_issues_graphql."""

    def test_sync_issues_graphql_since_filter_passthrough(self, mocker: MockerFixture) -> None:
        """Arrange: since=datetime(2024,1,1,tzinfo=UTC).
        Act: call sync_issues_graphql.
        Assert: _fetch_issues_graphql called with since="2024-01-01T00:00:00+00:00".
        """
        # Arrange
        repo = _make_mock_repo(mocker)
        since_dt = datetime(2024, 1, 1, tzinfo=UTC)
        mock_fetch = mocker.patch("backlog_core.gh_client._fetch_issues_graphql", return_value=[])

        # Act
        sync_issues_graphql(repo, "test-owner", "test-repo", since=since_dt)

        # Assert
        call_kwargs = mock_fetch.call_args
        assert call_kwargs.kwargs["since"] == "2024-01-01T00:00:00+00:00"


# ---------------------------------------------------------------------------
# TestSyncIssuesGraphqlCallback
# ---------------------------------------------------------------------------


class TestSyncIssuesGraphqlCallbackCalledPerIssue:
    """sync_issues_graphql calls callback once per issue."""

    def test_sync_issues_graphql_callback_called_per_issue(self, mocker: MockerFixture) -> None:
        """Arrange: 3 issues, a list-appending callback.
        Act: call sync_issues_graphql with callback.
        Assert: callback called 3 times with each IssueNode; full list still returned.
        """
        # Arrange
        repo = _make_mock_repo(mocker)
        issues = [_make_issue_node(i) for i in range(1, 4)]
        mocker.patch("backlog_core.gh_client._fetch_issues_graphql", return_value=issues)
        received: list[Any] = []

        # Act
        result = sync_issues_graphql(repo, "test-owner", "test-repo", callback=received.append)

        # Assert
        assert received == issues
        assert result == issues


# ---------------------------------------------------------------------------
# TestSyncIssuesGraphqlTimestampRead
# ---------------------------------------------------------------------------


class TestSyncIssuesGraphqlTrackTimestampReadsLastSync:
    """When track_timestamp=True and .last_sync exists, its value is passed as since."""

    def test_sync_issues_graphql_track_timestamp_reads_last_sync(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Arrange: .last_sync file contains a timestamp; track_timestamp=True; since=None.
        Act: call sync_issues_graphql.
        Assert: _fetch_issues_graphql called with since equal to the file content.
        """
        # Arrange
        repo = _make_mock_repo(mocker)
        stored_ts = "2024-06-01T12:00:00+00:00"
        last_sync_file = tmp_path / ".last_sync"
        last_sync_file.write_text(stored_ts, encoding="utf-8")

        mocker.patch("backlog_core.gh_client._dh_paths.state_root", return_value=tmp_path)
        mock_fetch = mocker.patch("backlog_core.gh_client._fetch_issues_graphql", return_value=[])

        # Act
        sync_issues_graphql(repo, "test-owner", "test-repo", track_timestamp=True)

        # Assert
        call_kwargs = mock_fetch.call_args
        assert call_kwargs.kwargs["since"] == stored_ts


# ---------------------------------------------------------------------------
# TestSyncIssuesGraphqlTimestampWrite
# ---------------------------------------------------------------------------


class TestSyncIssuesGraphqlTrackTimestampWritesAfterFetch:
    """When track_timestamp=True, .last_sync is written after a successful fetch."""

    def test_sync_issues_graphql_track_timestamp_writes_after_fetch(
        self, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        """Arrange: no existing .last_sync; track_timestamp=True.
        Act: call sync_issues_graphql.
        Assert: .last_sync file is created and contains a valid ISO timestamp.
        """
        # Arrange
        repo = _make_mock_repo(mocker)
        mocker.patch("backlog_core.gh_client._dh_paths.state_root", return_value=tmp_path)
        mocker.patch("backlog_core.gh_client._fetch_issues_graphql", return_value=[])

        # Act
        sync_issues_graphql(repo, "test-owner", "test-repo", track_timestamp=True)

        # Assert
        last_sync_file = tmp_path / ".last_sync"
        assert last_sync_file.exists()
        written = last_sync_file.read_text(encoding="utf-8").strip()
        # Should parse as a valid ISO datetime
        parsed = datetime.fromisoformat(written)
        assert parsed.tzinfo is not None


# ---------------------------------------------------------------------------
# TestSyncIssuesGraphqlErrorPropagation
# ---------------------------------------------------------------------------


class TestSyncIssuesGraphqlErrorPropagates:
    """BacklogError from _fetch_issues_graphql propagates to the caller."""

    def test_sync_issues_graphql_error_propagates(self, mocker: MockerFixture) -> None:
        """Arrange: _fetch_issues_graphql raises BacklogError.
        Act: call sync_issues_graphql.
        Assert: BacklogError propagates — not swallowed.
        """
        # Arrange
        repo = _make_mock_repo(mocker)
        mocker.patch(
            "backlog_core.gh_client._fetch_issues_graphql", side_effect=BacklogError("GraphQL rate limit exceeded")
        )

        # Act / Assert
        with pytest.raises(BacklogError, match="GraphQL rate limit exceeded"):
            sync_issues_graphql(repo, "test-owner", "test-repo")


# ---------------------------------------------------------------------------
# TestSyncIssuesGraphqlIntegration
# ---------------------------------------------------------------------------


class TestSyncIssuesGraphqlIntegration:
    """Integration test: multi-page pagination, since filter, and callback are composed correctly.

    Tests that sync_issues_graphql delegates pagination entirely to _fetch_issues_graphql
    (AC2: single call regardless of result count), passes the since datetime as an ISO string,
    and invokes the callback for every returned issue.
    """

    def test_sync_issues_graphql_multipagination_since_and_callback(self, mocker: MockerFixture) -> None:
        """Verify multi-page pagination delegation, since passthrough, and callback invocation.

        Tests: sync_issues_graphql integration of since filter + callback + pagination.
        How:
            1. Arrange — mock _fetch_issues_graphql to return 10 issues; provide a list-
               appending callback and a since datetime.
            2. Act — call sync_issues_graphql.
            3. Assert — _fetch_issues_graphql called exactly once (pagination is delegated),
               since kwarg is the correct ISO string, all 10 issues reached the callback,
               and the returned list has 10 items.
        Why: Confirms the primitive composes all three behaviours in a single call without
             introducing any internal pagination loop.
        """
        # Arrange
        repo = _make_mock_repo(mocker)
        issues = [_make_issue_node(i) for i in range(1, 11)]
        mock_fetch = mocker.patch("backlog_core.gh_client._fetch_issues_graphql", return_value=issues)
        received: list[Any] = []
        since_dt = datetime(2024, 3, 1, tzinfo=UTC)

        # Act
        result = sync_issues_graphql(repo, "test-owner", "test-repo", since=since_dt, callback=received.append)

        # Assert
        mock_fetch.assert_called_once()
        assert mock_fetch.call_args.kwargs["since"] == "2024-03-01T00:00:00+00:00"
        assert received == issues
        assert len(result) == 10


# ---------------------------------------------------------------------------
# TestSyncIssuesGraphqlNoNPlusOne
# ---------------------------------------------------------------------------


class TestSyncIssuesGraphqlNoNPlusOne:
    """Verify sync_issues_graphql makes at most 2 calls to _fetch_issues_graphql for any N issues.

    AC3: bulk operations must not degrade into N+1 query patterns where a separate
    GraphQL request is issued per issue. The primitive fetches all issues in bulk;
    callers that previously looped have been migrated to use this single call.
    """

    def test_sync_issues_graphql_bulk_makes_at_most_two_graphql_requests(self, mocker: MockerFixture) -> None:
        """Verify no per-issue GraphQL requests are made for 50 issues.

        Tests: sync_issues_graphql does not produce N+1 GraphQL calls.
        How:
            1. Arrange — mock _fetch_issues_graphql to return 50 issues; track call_count.
            2. Act — call sync_issues_graphql once for 50 issues.
            3. Assert — _fetch_issues_graphql.call_count <= 2; result has 50 items.
        Why: Any N+1 hotspot would call _fetch_issues_graphql once per issue (50 calls).
             This test catches regressions where a for-loop re-introduces per-issue fetches.
        """
        # Arrange
        repo = _make_mock_repo(mocker)
        issues = [_make_issue_node(i) for i in range(1, 51)]
        mock_fetch = mocker.patch("backlog_core.gh_client._fetch_issues_graphql", return_value=issues)

        # Act
        result = sync_issues_graphql(repo, "test-owner", "test-repo")

        # Assert
        assert mock_fetch.call_count <= 2, (
            f"Expected at most 2 GraphQL calls for 50 issues, got {mock_fetch.call_count}"
        )
        assert len(result) == 50


# ---------------------------------------------------------------------------
# TestSyncIssuesGraphqlIncrementalPerformance
# ---------------------------------------------------------------------------


class TestSyncIssuesGraphqlIncrementalPerformance:
    """Performance benchmark: incremental sync (with since) completes under 2s wall clock.

    AC4: The sync primitive with a since filter must process 20 issues in under 2 seconds
    when the GraphQL transport returns instantly (no network latency). This catches
    algorithmic regressions (O(N^2) processing, unnecessary loops) that would slow
    even mock scenarios beyond the SLA.
    """

    @pytest.mark.slow
    def test_sync_issues_graphql_incremental_since_completes_under_2s(self, mocker: MockerFixture) -> None:
        """Verify incremental sync of 20 issues completes in under 2s wall clock.

        Tests: sync_issues_graphql incremental-sync performance SLA.
        How:
            1. Arrange — mock _fetch_issues_graphql to return 20 issues instantly;
               provide a since datetime for incremental mode.
            2. Act — measure wall clock with time.perf_counter().
            3. Assert — elapsed < 2.0s.
        Why: Incremental sync is the hot path; any O(N) overhead in the primitive
             itself (not in network I/O) must remain negligible for small result sets.
        """
        # Arrange
        repo = _make_mock_repo(mocker)
        issues = [_make_issue_node(i) for i in range(1, 21)]
        mocker.patch("backlog_core.gh_client._fetch_issues_graphql", return_value=issues)
        since_dt = datetime(2024, 1, 1, tzinfo=UTC)

        # Act
        start = time.perf_counter()
        sync_issues_graphql(repo, "test-owner", "test-repo", since=since_dt)
        elapsed = time.perf_counter() - start

        # Assert
        assert elapsed < 2.0, f"Incremental sync took {elapsed:.3f}s, expected < 2s"


# ---------------------------------------------------------------------------
# TestSyncIssuesGraphqlFullSyncPerformance
# ---------------------------------------------------------------------------


class TestSyncIssuesGraphqlFullSyncPerformance:
    """Performance benchmark: full sync of 100 mock issues completes under 15s wall clock.

    AC5: The sync primitive without a since filter must process 100 issues in under 15
    seconds when the GraphQL transport returns instantly. This validates that the primitive
    itself introduces no algorithmic overhead that would violate the full-sync SLA.
    """

    @pytest.mark.slow
    def test_sync_issues_graphql_full_sync_100_issues_under_15s(self, mocker: MockerFixture) -> None:
        """Verify full sync of 100 issues completes in under 15s wall clock.

        Tests: sync_issues_graphql full-sync performance SLA.
        How:
            1. Arrange — mock _fetch_issues_graphql to return 100 issues instantly;
               no since filter (full refresh mode).
            2. Act — measure wall clock with time.perf_counter().
            3. Assert — elapsed < 15.0s.
        Why: Full sync is the baseline recovery path. Primitive-level overhead must
             remain negligible so the 15s budget is available entirely for network I/O.
        """
        # Arrange
        repo = _make_mock_repo(mocker)
        issues = [_make_issue_node(i) for i in range(1, 101)]
        mocker.patch("backlog_core.gh_client._fetch_issues_graphql", return_value=issues)

        # Act
        start = time.perf_counter()
        sync_issues_graphql(repo, "test-owner", "test-repo")
        elapsed = time.perf_counter() - start

        # Assert
        assert elapsed < 15.0, f"Full sync took {elapsed:.3f}s, expected < 15s"
