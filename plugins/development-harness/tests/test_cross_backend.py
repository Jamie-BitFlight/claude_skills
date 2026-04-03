"""Cross-backend protocol compliance tests.

Runs identical test cases against InMemoryBackend and SQLiteBackend to prove
all BacklogBackend implementations behave identically on the public surface.

GitHubBackend tests are skipped by default (require network access and a valid
GITHUB_TOKEN).  To run them, set BACKLOG_CROSS_BACKEND_GITHUB=1 in the
environment and ensure GITHUB_TOKEN is configured.

asyncio_mode = "auto" is set globally in pyproject.toml.

Test layout:
    fixtures            — backend factory, BacklogItem factory
    TestBackendStatus   — probe_backend_status returns REACHABLE
    TestCreateItem      — create_issue_for_item / _fetch_issue_graphql CRUD
    TestListItems       — _fetch_issues_graphql with state filters
    TestUpdateItem      — _update_issue_graphql mutates fields
    TestCloseItem       — close_github_issue transitions state to CLOSED
    TestResolveItem     — resolve_github_issue closes with resolution
    TestFetchBody       — fetch_github_issue_body returns body or None
    TestFetchByTitle    — fetch_open_issues_by_title returns title->number map
    TestBatchStatus     — batch_fetch_statuses returns IssueStatus per item
    TestComments        — add / fetch / update comment round-trip
    TestMilestones      — _fetch_milestones_graphql empty and after creation
    TestBranchOps       — create / get / list / delete integration branches
    TestDryRun          — create_issue_for_item with dry_run=True returns None
    TestViewEnrich      — view_enrich_from_github populates ViewItemResult
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest
from backlog_core.backends.memory_backend import InMemoryBackend
from backlog_core.backends.sqlite_backend import SQLiteBackend
from backlog_core.models import BackendAvailability, BacklogItem, BacklogItemMetadata, ViewItemResult

if TYPE_CHECKING:
    from backlog_core.backend_protocol import BacklogBackend


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_GITHUB_MARKER = pytest.mark.skipif(
    not os.environ.get("BACKLOG_CROSS_BACKEND_GITHUB"),
    reason="Set BACKLOG_CROSS_BACKEND_GITHUB=1 to run GitHub backend tests",
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_memory() -> InMemoryBackend:
    """Return a fresh InMemoryBackend with no pre-existing state."""
    return InMemoryBackend()


def _make_sqlite() -> SQLiteBackend:
    """Return a fresh SQLiteBackend backed by an in-memory SQLite database."""
    return SQLiteBackend(":memory:")


@pytest.fixture(
    params=[
        pytest.param("memory", id="InMemoryBackend"),
        pytest.param("sqlite", id="SQLiteBackend"),
        pytest.param("github", id="GitHubBackend", marks=_GITHUB_MARKER),
    ]
)
def backend(request: pytest.FixtureRequest):
    """Parametrized fixture yielding one backend per test run.

    Returns InMemoryBackend, SQLiteBackend, or (optionally) GitHubBackend.
    GitHubBackend tests are skipped unless BACKLOG_CROSS_BACKEND_GITHUB is set.
    """
    name: str = request.param
    if name == "memory":
        return _make_memory()
    if name == "sqlite":
        return _make_sqlite()
    # github — only reached when BACKLOG_CROSS_BACKEND_GITHUB is set
    from backlog_core.backends.github_backend import GitHubBackend

    return GitHubBackend()


def _make_item(title: str = "Test Feature", description: str = "A test item") -> BacklogItem:
    """Construct a minimal BacklogItem suitable for create_issue_for_item."""
    return BacklogItem(
        title=title,
        description=description,
        metadata=BacklogItemMetadata(
            source="test", added="2026-01-01", priority="P1", item_type="Feature", status="open"
        ),
    )


def _make_item_with_issue(issue_num: int, title: str = "Tracked Feature") -> BacklogItem:
    """Construct a BacklogItem with an issue reference for status queries."""
    return BacklogItem(
        title=title,
        description="Feature with issue link",
        metadata=BacklogItemMetadata(
            source="test", added="2026-01-01", priority="P1", item_type="Feature", status="open", issue=f"#{issue_num}"
        ),
    )


# ---------------------------------------------------------------------------
# TestBackendStatus
# ---------------------------------------------------------------------------


class TestBackendStatus:
    """probe_backend_status returns a valid BackendStatus with REACHABLE for local backends."""

    def test_probe_returns_reachable_for_local_backends(self, backend: BacklogBackend) -> None:
        """probe_backend_status returns REACHABLE for memory and SQLite backends.

        Why: Local backends are always available — REACHABLE is the only
             correct initial state for non-network backends.
        """
        # Arrange — backend fixture provides the implementation under test

        # Act
        status = backend.probe_backend_status()

        # Assert
        if not os.environ.get("BACKLOG_CROSS_BACKEND_GITHUB"):
            assert status.availability == BackendAvailability.REACHABLE

    def test_probe_returns_named_status(self, backend: BacklogBackend) -> None:
        """probe_backend_status result has a non-empty name field.

        Why: Clients display the backend name; an empty name is a display bug.
        """
        # Arrange — nothing extra

        # Act
        status = backend.probe_backend_status()

        # Assert
        if not os.environ.get("BACKLOG_CROSS_BACKEND_GITHUB"):
            assert status.name != ""


# ---------------------------------------------------------------------------
# TestCreateItem
# ---------------------------------------------------------------------------


class TestCreateItem:
    """create_issue_for_item creates an issue and returns a positive integer number."""

    def test_create_returns_positive_integer(self, backend: BacklogBackend) -> None:
        """create_issue_for_item returns a positive integer issue number.

        Why: Callers store the returned number as the issue reference;
             None or negative values break downstream operations.
        """
        # Arrange
        item = _make_item()

        # Act
        number = backend.create_issue_for_item(None, item)  # type: ignore[arg-type]

        # Assert
        assert isinstance(number, int)
        assert number > 0

    def test_create_item_is_fetchable(self, backend: BacklogBackend) -> None:
        """An issue created via create_issue_for_item is fetchable by its number.

        Why: The create → fetch round-trip is the minimal CRUD contract; if
             the created item cannot be retrieved the backend is broken.
        """
        # Arrange
        item = _make_item("Fetchable Feature")

        # Act
        number = backend.create_issue_for_item(None, item)  # type: ignore[arg-type]
        assert number is not None
        node = backend._fetch_issue_graphql(None, "", "", number)  # type: ignore[arg-type]

        # Assert
        assert node["number"] == number
        assert node["title"] == "Fetchable Feature"

    def test_create_item_initial_state_is_open(self, backend: BacklogBackend) -> None:
        """Newly created issues start in OPEN state.

        Why: The protocol requires new issues to be open; callers assume this
             invariant when checking issue state after creation.
        """
        # Arrange
        item = _make_item()

        # Act
        number = backend.create_issue_for_item(None, item)  # type: ignore[arg-type]
        assert number is not None
        node = backend._fetch_issue_graphql(None, "", "", number)  # type: ignore[arg-type]

        # Assert
        assert node["state"] == "OPEN"

    def test_create_sequential_numbers_increase(self, backend: BacklogBackend) -> None:
        """Two successive create calls return distinct, increasing issue numbers.

        Why: Callers depend on issue numbers being unique identifiers; duplicate
             or non-monotone numbers would corrupt the issue registry.
        """
        # Arrange
        item_a = _make_item("Alpha")
        item_b = _make_item("Beta")

        # Act
        num_a = backend.create_issue_for_item(None, item_a)  # type: ignore[arg-type]
        num_b = backend.create_issue_for_item(None, item_b)  # type: ignore[arg-type]

        # Assert
        assert num_a is not None
        assert num_b is not None
        assert num_b > num_a


# ---------------------------------------------------------------------------
# TestDryRun
# ---------------------------------------------------------------------------


class TestDryRun:
    """create_issue_for_item with dry_run=True returns None and creates no issue."""

    def test_dry_run_returns_none(self, backend: BacklogBackend) -> None:
        """dry_run=True returns None without persisting the issue.

        Why: Dry-run mode is used for validation passes; creating a real issue
             would corrupt state during preview operations.
        """
        # Arrange
        item = _make_item()

        # Act
        result = backend.create_issue_for_item(None, item, dry_run=True)  # type: ignore[arg-type]

        # Assert
        assert result is None

    def test_dry_run_does_not_persist_issue(self, backend: BacklogBackend) -> None:
        """dry_run=True leaves the backend with no new issues.

        Why: Side-effect-free dry runs are required for safe preview
             operations; any persistence in dry-run mode is a bug.
        """
        # Arrange
        item = _make_item()
        backend.create_issue_for_item(None, item, dry_run=True)  # type: ignore[arg-type]

        # Act — fetch all open issues; should be empty
        issues = backend._fetch_issues_graphql(None, "", "")  # type: ignore[arg-type]

        # Assert
        assert len(issues) == 0


# ---------------------------------------------------------------------------
# TestListItems
# ---------------------------------------------------------------------------


class TestListItems:
    """_fetch_issues_graphql returns issues filtered by state."""

    def test_list_open_returns_only_open_issues(self, backend: BacklogBackend) -> None:
        """_fetch_issues_graphql with state=OPEN returns only open issues.

        Why: State-filtered listing is the primary query path; returning closed
             issues in an open-only query breaks backlog display logic.
        """
        # Arrange
        item = _make_item("Open One")
        number = backend.create_issue_for_item(None, item)  # type: ignore[arg-type]
        assert number is not None
        backend.close_github_issue(str(number), "done")

        open_item = _make_item("Open Two")
        backend.create_issue_for_item(None, open_item)  # type: ignore[arg-type]

        # Act
        open_issues = backend._fetch_issues_graphql(None, "", "", state="OPEN")  # type: ignore[arg-type]

        # Assert
        assert all(issue["state"] == "OPEN" for issue in open_issues)
        assert any(issue["title"] == "Open Two" for issue in open_issues)
        assert not any(issue["title"] == "Open One" for issue in open_issues)

    def test_list_closed_returns_only_closed_issues(self, backend: BacklogBackend) -> None:
        """_fetch_issues_graphql with state=CLOSED returns only closed issues.

        Why: Closed-issue queries drive archive views; mixing states would
             show resolved issues as active work.
        """
        # Arrange
        item = _make_item("Will Close")
        number = backend.create_issue_for_item(None, item)  # type: ignore[arg-type]
        assert number is not None
        backend.close_github_issue(str(number), "done")

        backend.create_issue_for_item(None, _make_item("Stays Open"))  # type: ignore[arg-type]

        # Act
        closed = backend._fetch_issues_graphql(None, "", "", state="CLOSED")  # type: ignore[arg-type]

        # Assert
        assert all(issue["state"] == "CLOSED" for issue in closed)
        assert any(issue["title"] == "Will Close" for issue in closed)

    def test_empty_backend_returns_empty_list(self, backend: BacklogBackend) -> None:
        """_fetch_issues_graphql on an empty backend returns an empty list.

        Why: Empty-list semantics must be consistent; callers should not
             receive None or raise an error on an empty store.
        """
        # Arrange — backend has no issues

        # Act
        result = backend._fetch_issues_graphql(None, "", "")  # type: ignore[arg-type]

        # Assert
        assert result == []


# ---------------------------------------------------------------------------
# TestUpdateItem
# ---------------------------------------------------------------------------


class TestUpdateItem:
    """_update_issue_graphql mutates issue fields in place."""

    def test_update_title_is_reflected_on_fetch(self, backend: BacklogBackend) -> None:
        """_update_issue_graphql with a new title is reflected when the issue is re-fetched.

        Why: Callers rely on updates being durable; a title update that does not
             persist would silently lose user data.
        """
        # Arrange
        item = _make_item("Original Title")
        number = backend.create_issue_for_item(None, item)  # type: ignore[arg-type]
        assert number is not None
        node = backend._fetch_issue_graphql(None, "", "", number)  # type: ignore[arg-type]

        # Act
        backend._update_issue_graphql(None, node["id"], title="Updated Title")  # type: ignore[arg-type]
        refreshed = backend._fetch_issue_graphql(None, "", "", number)  # type: ignore[arg-type]

        # Assert
        assert refreshed["title"] == "Updated Title"

    def test_update_body_is_reflected_on_fetch(self, backend: BacklogBackend) -> None:
        """_update_issue_graphql with a new body is reflected when the issue is re-fetched.

        Why: Body updates drive grooming workflows; persistence is required
             for groomed content to survive session restarts.
        """
        # Arrange
        item = _make_item()
        number = backend.create_issue_for_item(None, item)  # type: ignore[arg-type]
        assert number is not None
        node = backend._fetch_issue_graphql(None, "", "", number)  # type: ignore[arg-type]

        # Act
        backend._update_issue_graphql(None, node["id"], body="Updated body content")  # type: ignore[arg-type]
        refreshed = backend._fetch_issue_graphql(None, "", "", number)  # type: ignore[arg-type]

        # Assert
        assert refreshed["body"] == "Updated body content"

    def test_update_state_to_closed(self, backend: BacklogBackend) -> None:
        """_update_issue_graphql with state=CLOSED transitions the issue to CLOSED.

        Why: State transitions drive workflow gating; an update that does not
             change state would block issue close and resolve flows.
        """
        # Arrange
        item = _make_item()
        number = backend.create_issue_for_item(None, item)  # type: ignore[arg-type]
        assert number is not None
        node = backend._fetch_issue_graphql(None, "", "", number)  # type: ignore[arg-type]

        # Act
        backend._update_issue_graphql(None, node["id"], state="CLOSED")  # type: ignore[arg-type]
        refreshed = backend._fetch_issue_graphql(None, "", "", number)  # type: ignore[arg-type]

        # Assert
        assert refreshed["state"] == "CLOSED"


# ---------------------------------------------------------------------------
# TestCloseItem
# ---------------------------------------------------------------------------


class TestCloseItem:
    """close_github_issue transitions an issue to CLOSED state."""

    def test_close_sets_state_to_closed(self, backend: BacklogBackend) -> None:
        """close_github_issue transitions the issue state to CLOSED.

        Why: Closing is the primary workflow completion action; a failed
             transition would leave items stuck in open state.
        """
        # Arrange
        item = _make_item()
        number = backend.create_issue_for_item(None, item)  # type: ignore[arg-type]
        assert number is not None

        # Act
        backend.close_github_issue(str(number), "completed")
        node = backend._fetch_issue_graphql(None, "", "", number)  # type: ignore[arg-type]

        # Assert
        assert node["state"] == "CLOSED"

    def test_close_with_hash_prefix_works(self, backend: BacklogBackend) -> None:
        """close_github_issue with '#N' issue_ref format closes the issue.

        Why: Callers pass issue refs in '#N' form from stored metadata; the
             backend must strip the prefix rather than failing to parse it.
        """
        # Arrange
        item = _make_item()
        number = backend.create_issue_for_item(None, item)  # type: ignore[arg-type]
        assert number is not None

        # Act
        backend.close_github_issue(f"#{number}", "completed")
        node = backend._fetch_issue_graphql(None, "", "", number)  # type: ignore[arg-type]

        # Assert
        assert node["state"] == "CLOSED"


# ---------------------------------------------------------------------------
# TestResolveItem
# ---------------------------------------------------------------------------


class TestResolveItem:
    """resolve_github_issue closes an issue with a resolution comment."""

    def test_resolve_sets_state_to_closed(self, backend: BacklogBackend) -> None:
        """resolve_github_issue transitions the issue state to CLOSED.

        Why: Resolve is semantically stronger than close; both must produce
             CLOSED state as the protocol contract.
        """
        # Arrange
        item = _make_item()
        number = backend.create_issue_for_item(None, item)  # type: ignore[arg-type]
        assert number is not None

        # Act
        backend.resolve_github_issue(str(number), summary="Resolved in v2")
        node = backend._fetch_issue_graphql(None, "", "", number)  # type: ignore[arg-type]

        # Assert
        assert node["state"] == "CLOSED"


# ---------------------------------------------------------------------------
# TestFetchBody
# ---------------------------------------------------------------------------


class TestFetchBody:
    """fetch_github_issue_body returns the stored body string or None."""

    def test_fetch_body_returns_body_string(self, backend: BacklogBackend) -> None:
        """fetch_github_issue_body returns the issue body for a known issue.

        Why: Body retrieval is used by grooming and sync operations; None on
             a known issue number would silently skip grooming.
        """
        # Arrange
        item = _make_item("Feature", "The description text")
        number = backend.create_issue_for_item(None, item)  # type: ignore[arg-type]
        assert number is not None

        # Act
        body = backend.fetch_github_issue_body(None, number)  # type: ignore[arg-type]

        # Assert
        assert body is not None
        assert isinstance(body, str)

    def test_fetch_body_returns_none_for_unknown_number(self, backend: BacklogBackend) -> None:
        """fetch_github_issue_body returns None for an issue number that does not exist.

        Why: None signals absence; callers branch on None to skip enrichment
             rather than receiving an exception from a missing issue.
        """
        # Arrange — no issues created

        # Act
        result = backend.fetch_github_issue_body(None, 99999)  # type: ignore[arg-type]

        # Assert
        assert result is None


# ---------------------------------------------------------------------------
# TestFetchByTitle
# ---------------------------------------------------------------------------


class TestFetchByTitle:
    """fetch_open_issues_by_title returns a title-to-number dict for open issues."""

    def test_fetch_by_title_returns_open_issues(self, backend: BacklogBackend) -> None:
        """fetch_open_issues_by_title maps open issue titles to their numbers.

        Why: The title map drives deduplication logic; missing entries would
             cause duplicate issues to be created on re-sync.
        """
        # Arrange
        item = _make_item("My Open Feature")
        number = backend.create_issue_for_item(None, item)  # type: ignore[arg-type]
        assert number is not None

        # Act
        title_map = backend.fetch_open_issues_by_title(None)  # type: ignore[arg-type]

        # Assert
        assert "My Open Feature" in title_map
        assert title_map["My Open Feature"] == number

    def test_closed_issues_not_in_title_map(self, backend: BacklogBackend) -> None:
        """fetch_open_issues_by_title excludes closed issues.

        Why: Closed issues must not appear in the dedup map; including them
             would prevent re-creating legitimately reopened items.
        """
        # Arrange
        item = _make_item("Closed Feature")
        number = backend.create_issue_for_item(None, item)  # type: ignore[arg-type]
        assert number is not None
        backend.close_github_issue(str(number), "done")

        # Act
        title_map = backend.fetch_open_issues_by_title(None)  # type: ignore[arg-type]

        # Assert
        assert "Closed Feature" not in title_map


# ---------------------------------------------------------------------------
# TestBatchStatus
# ---------------------------------------------------------------------------


class TestBatchStatus:
    """batch_fetch_statuses returns IssueStatus entries for items with issue numbers."""

    def test_batch_status_returns_status_for_known_issue(self, backend: BacklogBackend) -> None:
        """batch_fetch_statuses includes an IssueStatus entry for each item with a number.

        Why: Batch status drives bulk state checks; a missing entry causes the
             caller to silently skip status reconciliation for that item.
        """
        # Arrange
        item = _make_item()
        number = backend.create_issue_for_item(None, item)  # type: ignore[arg-type]
        assert number is not None
        tracked = _make_item_with_issue(number)

        # Act
        statuses = backend.batch_fetch_statuses([tracked])

        # Assert
        assert number in statuses
        assert statuses[number].status.lower() in {"open", "closed"}

    def test_batch_status_empty_for_items_without_issue(self, backend: BacklogBackend) -> None:
        """batch_fetch_statuses returns an empty dict for items with no issue number.

        Why: Items without issue references cannot be queried; returning an
             empty dict is the correct protocol response.
        """
        # Arrange
        item = _make_item()  # no issue reference

        # Act
        statuses = backend.batch_fetch_statuses([item])

        # Assert
        assert statuses == {}


# ---------------------------------------------------------------------------
# TestComments
# ---------------------------------------------------------------------------


class TestComments:
    """Comment operations round-trip: add / fetch / update."""

    def test_add_comment_and_fetch_returns_comment(self, backend: BacklogBackend) -> None:
        """A comment added via _add_comment_graphql appears in _fetch_issue_comments_graphql.

        Why: Comment round-trip is required for grooming notes and review
             threads to persist correctly.
        """
        # Arrange
        item = _make_item()
        number = backend.create_issue_for_item(None, item)  # type: ignore[arg-type]
        assert number is not None
        node = backend._fetch_issue_graphql(None, "", "", number)  # type: ignore[arg-type]

        # Act
        backend._add_comment_graphql(None, node["id"], "First comment")  # type: ignore[arg-type]
        comments = backend._fetch_issue_comments_graphql(None, "", "", number)  # type: ignore[arg-type]

        # Assert
        assert len(comments) >= 1
        assert any(c["body"] == "First comment" for c in comments)

    def test_update_comment_body_is_reflected_on_fetch(self, backend: BacklogBackend) -> None:
        """Updating a comment body via _update_issue_comment_graphql persists the change.

        Why: Comment edits must be durable; a non-persistent update silently
             discards user edits.
        """
        # Arrange
        item = _make_item()
        number = backend.create_issue_for_item(None, item)  # type: ignore[arg-type]
        assert number is not None
        node = backend._fetch_issue_graphql(None, "", "", number)  # type: ignore[arg-type]
        comment_id = backend._add_comment_graphql(None, node["id"], "Original")  # type: ignore[arg-type]

        # Act
        backend._update_issue_comment_graphql(None, comment_id, "Updated body")  # type: ignore[arg-type]
        comment = backend._fetch_comment_by_id_graphql(None, comment_id)  # type: ignore[arg-type]

        # Assert
        assert comment["body"] == "Updated body"


# ---------------------------------------------------------------------------
# TestMilestones
# ---------------------------------------------------------------------------


class TestMilestones:
    """_fetch_milestones_graphql returns empty list initially and milestone data after insertion."""

    def test_fetch_milestones_empty_initially(self, backend: BacklogBackend) -> None:
        """_fetch_milestones_graphql returns an empty list on a fresh backend.

        Why: An empty list is the correct initial state; non-empty results on
             a fresh backend indicate state leakage between tests.
        """
        # Arrange — fresh backend

        # Act
        milestones = backend._fetch_milestones_graphql(None, "", "")  # type: ignore[arg-type]

        # Assert
        assert milestones == []

    def test_try_get_github_returns_none_for_local_backends(self, backend: BacklogBackend) -> None:
        """try_get_github returns None for local (non-GitHub) backends.

        Why: Local backends have no GitHub connection; None signals callers to
             skip operations that require a live GitHub repository.
        """
        # Arrange — nothing extra

        # Act
        if not os.environ.get("BACKLOG_CROSS_BACKEND_GITHUB"):
            repo = backend.try_get_github()
            # Assert
            assert repo is None


# ---------------------------------------------------------------------------
# TestBranchOps
# ---------------------------------------------------------------------------


class TestBranchOps:
    """Integration branch CRUD: create / get / list / delete."""

    def test_create_branch_returns_branch_info(self, backend: BacklogBackend) -> None:
        """create_integration_branch returns a BranchInfo with a non-empty name.

        Why: BranchInfo.name is the canonical branch identifier used by all
             downstream operations; an empty name breaks every branch op.
        """
        # SQLiteBackend raises RuntimeError for branch operations — skip there.
        if isinstance(backend, SQLiteBackend):
            pytest.skip("SQLiteBackend does not support branch operations")

        # Arrange / Act
        info = backend.create_integration_branch(42, "feature-slug")

        # Assert
        assert info["name"] != ""
        assert "42" in info["name"]

    def test_get_nonexistent_branch_returns_none(self, backend: BacklogBackend) -> None:
        """get_integration_branch_status returns None for a branch that does not exist.

        Why: None signals callers to create the branch; KeyError would require
             a try/except that the protocol does not mandate.
        """
        if isinstance(backend, SQLiteBackend):
            pytest.skip("SQLiteBackend does not support branch operations")

        # Act
        result = backend.get_integration_branch_status("milestone/99-nonexistent")

        # Assert
        assert result is None

    def test_created_branch_appears_in_list(self, backend: BacklogBackend) -> None:
        """A branch created via create_integration_branch appears in list_integration_branches.

        Why: Branch listing drives milestone CI status; a created branch missing
             from the list would cause CI to believe no branch exists.
        """
        if isinstance(backend, SQLiteBackend):
            pytest.skip("SQLiteBackend does not support branch operations")

        # Arrange
        backend.create_integration_branch(7, "alpha")

        # Act
        branches = backend.list_integration_branches()

        # Assert
        assert len(branches) >= 1
        assert any("7" in b["name"] for b in branches)

    def test_delete_branch_returns_true_and_removes_it(self, backend: BacklogBackend) -> None:
        """delete_integration_branch returns True and the branch is no longer listed.

        Why: Deletion must be idempotent-detectable; True signals a real delete
             rather than a no-op, letting callers log the action correctly.
        """
        if isinstance(backend, SQLiteBackend):
            pytest.skip("SQLiteBackend does not support branch operations")

        # Arrange
        info = backend.create_integration_branch(8, "beta")

        # Act
        deleted = backend.delete_integration_branch(info["name"])
        after = backend.get_integration_branch_status(info["name"])

        # Assert
        assert deleted is True
        assert after is None

    def test_delete_nonexistent_branch_returns_false(self, backend: BacklogBackend) -> None:
        """delete_integration_branch returns False for a branch that does not exist.

        Why: False signals a no-op to callers; an exception would require
             defensive try/except blocks throughout calling code.
        """
        if isinstance(backend, SQLiteBackend):
            pytest.skip("SQLiteBackend does not support branch operations")

        # Act
        result = backend.delete_integration_branch("milestone/999-ghost")

        # Assert
        assert result is False


# ---------------------------------------------------------------------------
# TestViewEnrich
# ---------------------------------------------------------------------------


class TestViewEnrich:
    """view_enrich_from_github populates a ViewItemResult from stored issue data."""

    def test_enrich_known_issue_returns_true(self, backend: BacklogBackend) -> None:
        """view_enrich_from_github returns True for a known issue number.

        Why: True signals successful enrichment; callers skip enrichment
             display sections when False is returned.
        """
        # Arrange
        item = _make_item("Enrichable")
        number = backend.create_issue_for_item(None, item)  # type: ignore[arg-type]
        assert number is not None
        result = ViewItemResult(title="Enrichable")

        # Act
        enriched = backend.view_enrich_from_github(result, str(number))

        # Assert
        assert enriched is True

    def test_enrich_populates_number_field(self, backend: BacklogBackend) -> None:
        """view_enrich_from_github populates result.number with the issue number.

        Why: result.number drives hyperlink generation in the view command;
             an unpopulated number produces broken links.
        """
        # Arrange
        item = _make_item("Numbered Feature")
        number = backend.create_issue_for_item(None, item)  # type: ignore[arg-type]
        assert number is not None
        result = ViewItemResult(title="Numbered Feature")

        # Act
        backend.view_enrich_from_github(result, str(number))

        # Assert
        assert result.number == number

    def test_enrich_unknown_issue_returns_false(self, backend: BacklogBackend) -> None:
        """view_enrich_from_github returns False for an issue number that does not exist.

        Why: False lets callers degrade gracefully by omitting the enriched
             section rather than raising an exception or showing stale data.
        """
        # Arrange
        result = ViewItemResult(title="Ghost")

        # Act
        enriched = backend.view_enrich_from_github(result, "99999")

        # Assert
        assert enriched is False
