"""GitHubExtras protocol tests — GitHub-specific surface only.

Tests the ``GitHubExtras`` methods (``_fetch_issue_graphql``,
``_fetch_issues_graphql``, ``_update_issue_graphql``, ``_add_comment_graphql``,
``_fetch_issue_comments_graphql``, ``_fetch_comment_by_id_graphql``,
``_update_issue_comment_graphql``, ``_fetch_milestones_graphql``,
``_projects_v2_list_query``, ``_projects_v2_create_mutation``) that the
generic ``WorkItemBackend`` protocol does not expose.

These tests parametrize over ``GitHubBackend`` only (skipped by default —
requires network access and a valid ``GITHUB_TOKEN``).  Set
``BACKLOG_CROSS_BACKEND_GITHUB=1`` to enable them.

Marked with ``pytest.mark.cross_backend`` — excluded from the default pytest
run and executed exclusively by the ``test-cross-backend`` CI matrix job.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest
from backlog_core.backend_types import BacklogBackend
from backlog_core.models import BacklogItem, BacklogItemMetadata
from github.Repository import Repository as GithubRepository

pytestmark = pytest.mark.cross_backend

_GITHUB_MARKER = pytest.mark.skipif(
    not os.environ.get("BACKLOG_CROSS_BACKEND_GITHUB"),
    reason="Set BACKLOG_CROSS_BACKEND_GITHUB=1 to run GitHub backend tests",
)

_MOCK_REPO: GithubRepository = MagicMock(spec=GithubRepository)


def _make_item(title: str = "Test Feature", description: str = "A test item") -> BacklogItem:
    """Construct a minimal BacklogItem suitable for create_issue_for_item."""
    return BacklogItem(
        title=title,
        description=description,
        metadata=BacklogItemMetadata(
            source="test", added="2026-01-01", priority="P1", item_type="Feature", status="open"
        ),
    )


@pytest.fixture
def github_backend() -> BacklogBackend:
    """Return a GitHubBackend instance.

    Skipped unless ``BACKLOG_CROSS_BACKEND_GITHUB`` is set, because
    ``GitHubBackend`` requires network access and a valid ``GITHUB_TOKEN``.
    """
    from backlog_core.backends.github_backend import GitHubBackend

    return GitHubBackend()


# ---------------------------------------------------------------------------
# TestUpdateItem — _update_issue_graphql mutates fields in place.
# ---------------------------------------------------------------------------


class TestUpdateItem:
    """_update_issue_graphql mutates issue fields in place."""

    @_GITHUB_MARKER
    def test_update_title_is_reflected_on_fetch(self, github_backend: BacklogBackend) -> None:
        """_update_issue_graphql with a new title is reflected on re-fetch.

        Why: Callers rely on updates being durable; a title update that does
             not persist would silently lose user data.
        """
        # Arrange
        item = _make_item("Original Title")
        number = github_backend.create_issue_for_item(_MOCK_REPO, item)
        assert number is not None
        node = github_backend._fetch_issue_graphql(_MOCK_REPO, "", "", number)

        # Act
        github_backend._update_issue_graphql(_MOCK_REPO, node["id"], title="Updated Title")
        refreshed = github_backend._fetch_issue_graphql(_MOCK_REPO, "", "", number)

        # Assert
        assert refreshed["title"] == "Updated Title"

    @_GITHUB_MARKER
    def test_update_body_is_reflected_on_fetch(self, github_backend: BacklogBackend) -> None:
        """_update_issue_graphql with a new body is reflected on re-fetch.

        Why: Body updates drive grooming workflows; persistence is required
             for groomed content to survive session restarts.
        """
        # Arrange
        item = _make_item()
        number = github_backend.create_issue_for_item(_MOCK_REPO, item)
        assert number is not None
        node = github_backend._fetch_issue_graphql(_MOCK_REPO, "", "", number)

        # Act
        github_backend._update_issue_graphql(_MOCK_REPO, node["id"], body="Updated body content")
        refreshed = github_backend._fetch_issue_graphql(_MOCK_REPO, "", "", number)

        # Assert
        assert refreshed["body"] == "Updated body content"

    @_GITHUB_MARKER
    def test_update_state_to_closed(self, github_backend: BacklogBackend) -> None:
        """_update_issue_graphql with state=CLOSED transitions the issue to CLOSED.

        Why: State transitions drive workflow gating; an update that does not
             change state would block issue close and resolve flows.
        """
        # Arrange
        item = _make_item()
        number = github_backend.create_issue_for_item(_MOCK_REPO, item)
        assert number is not None
        node = github_backend._fetch_issue_graphql(_MOCK_REPO, "", "", number)

        # Act
        github_backend._update_issue_graphql(_MOCK_REPO, node["id"], state="CLOSED")
        refreshed = github_backend._fetch_issue_graphql(_MOCK_REPO, "", "", number)

        # Assert
        assert refreshed["state"] == "CLOSED"


# ---------------------------------------------------------------------------
# TestListItems — _fetch_issues_graphql with state filters.
# ---------------------------------------------------------------------------


class TestListItems:
    """_fetch_issues_graphql returns issues filtered by state."""

    @_GITHUB_MARKER
    def test_empty_backend_returns_empty_list(self, github_backend: BacklogBackend) -> None:
        """_fetch_issues_graphql on an empty backend returns an empty list.

        Why: Empty-list semantics must be consistent; callers should not
             receive None or raise an error on an empty store.
        """
        # Arrange — backend has no issues

        # Act
        result = github_backend._fetch_issues_graphql(_MOCK_REPO, "", "")

        # Assert
        assert result == []

    @_GITHUB_MARKER
    def test_list_closed_returns_only_closed_issues(self, github_backend: BacklogBackend) -> None:
        """_fetch_issues_graphql with state=CLOSED returns only closed issues.

        Why: Closed-issue queries drive archive views; mixing states would
             show resolved issues as active work.
        """
        # Arrange
        item = _make_item("Will Close")
        number = github_backend.create_issue_for_item(_MOCK_REPO, item)
        assert number is not None
        github_backend.close_github_issue(str(number), "done")

        github_backend.create_issue_for_item(_MOCK_REPO, _make_item("Stays Open"))

        # Act
        closed = github_backend._fetch_issues_graphql(_MOCK_REPO, "", "", state="CLOSED")

        # Assert
        assert all(issue["state"] == "CLOSED" for issue in closed)
        assert any(issue["title"] == "Will Close" for issue in closed)


# ---------------------------------------------------------------------------
# TestComments — _add_comment_graphql / _fetch_issue_comments_graphql /
#                _update_issue_comment_graphql / _fetch_comment_by_id_graphql.
# ---------------------------------------------------------------------------


class TestComments:
    """Comment operations round-trip: add / fetch / update."""

    @_GITHUB_MARKER
    def test_add_comment_and_fetch_returns_comment(self, github_backend: BacklogBackend) -> None:
        """A comment added via _add_comment_graphql appears in _fetch_issue_comments_graphql.

        Why: Comment round-trip is required for grooming notes and review
             threads to persist correctly.
        """
        # Arrange
        item = _make_item()
        number = github_backend.create_issue_for_item(_MOCK_REPO, item)
        assert number is not None
        node = github_backend._fetch_issue_graphql(_MOCK_REPO, "", "", number)

        # Act
        github_backend._add_comment_graphql(_MOCK_REPO, node["id"], "First comment")
        comments = github_backend._fetch_issue_comments_graphql(_MOCK_REPO, "", "", number)

        # Assert
        assert len(comments) >= 1
        assert any(c["body"] == "First comment" for c in comments)

    @_GITHUB_MARKER
    def test_update_comment_body_is_reflected_on_fetch(self, github_backend: BacklogBackend) -> None:
        """Updating a comment body via _update_issue_comment_graphql persists the change.

        Why: Comment edits must be durable; a non-persistent update silently
             discards user edits.
        """
        # Arrange
        item = _make_item()
        number = github_backend.create_issue_for_item(_MOCK_REPO, item)
        assert number is not None
        node = github_backend._fetch_issue_graphql(_MOCK_REPO, "", "", number)
        comment_id = github_backend._add_comment_graphql(_MOCK_REPO, node["id"], "Original")

        # Act
        github_backend._update_issue_comment_graphql(_MOCK_REPO, comment_id, "Updated body")
        comment = github_backend._fetch_comment_by_id_graphql(_MOCK_REPO, comment_id)

        # Assert
        assert comment["body"] == "Updated body"


# ---------------------------------------------------------------------------
# TestMilestones — _fetch_milestones_graphql empty initially.
# ---------------------------------------------------------------------------


class TestMilestones:
    """_fetch_milestones_graphql returns empty list initially."""

    @_GITHUB_MARKER
    def test_fetch_milestones_empty_initially(self, github_backend: BacklogBackend) -> None:
        """_fetch_milestones_graphql returns an empty list on a fresh backend.

        Why: An empty list is the correct initial state; non-empty results on
             a fresh backend indicate state leakage between tests.
        """
        # Arrange — fresh backend

        # Act
        milestones = github_backend._fetch_milestones_graphql(_MOCK_REPO, "", "")

        # Assert
        assert milestones == []
