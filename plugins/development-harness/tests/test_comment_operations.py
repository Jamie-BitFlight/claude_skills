"""Tests for list_comments and read_comment operations.

All tests mock at the ``_graphql_request`` boundary or at the PyGithub REST
boundary, keeping tests independent of live API calls.

Functions under test:
  - backlog_core.gh_client._parse_comment_node
  - backlog_core.gh_client._fetch_issue_comments_graphql
  - backlog_core.gh_client._fetch_comment_by_id_graphql
  - backlog_core.operations.list_comments
  - backlog_core.operations.read_comment
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from backlog_core.backend_types import AddedCommentNode, IssueCommentNode
from backlog_core.gh_client import _fetch_comment_by_id_graphql, _fetch_issue_comments_graphql, _parse_comment_node
from backlog_core.models import BacklogError, ValidationError
from backlog_core.operations import comment_issue, list_comments, read_comment

from tests.graphql_factories import make_comment_by_id_response, make_issue_comment_node, make_issue_comments_response

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_mock_repo(mocker: MockerFixture, full_name: str = "test-owner/test-repo") -> Any:
    """Return a minimal mock PyGithub Repository for GraphQL tests.

    Args:
        mocker: pytest-mock fixture.
        full_name: Repository full name (owner/repo).

    Returns:
        Mock object with .full_name, .node_id, and .requester.graphql_query set up.
    """
    repo = mocker.Mock()
    repo.full_name = full_name
    repo.node_id = "R_kgDOABCDEF"
    return repo


# ---------------------------------------------------------------------------
# _parse_comment_node
# ---------------------------------------------------------------------------


class TestParseCommentNode:
    """Unit tests for _parse_comment_node helper."""

    def test_parse_comment_node_all_fields_populated(self) -> None:
        """_parse_comment_node maps all GraphQL fields to IssueCommentNode keys.

        Tests: Happy path with author login, ISO timestamps, body, id, url.
        How: Pass a raw GraphQL node dict with all expected keys.
        Why: Validates the field-mapping contract between GraphQL shape and TypedDict.
        """
        # Arrange
        raw = make_issue_comment_node(
            comment_id="IC_abc",
            body="Hello world",
            url="https://github.com/o/r/issues/1#issuecomment-1",
            author="alice",
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-02T12:00:00Z",
        )

        # Act
        result = _parse_comment_node(raw)

        # Assert
        assert result.id == "IC_abc"
        assert result.body == "Hello world"
        assert result.url == "https://github.com/o/r/issues/1#issuecomment-1"
        assert result.author == "alice"
        assert result.created_at == "2026-01-01T00:00:00Z"
        assert result.updated_at == "2026-01-02T12:00:00Z"

    def test_parse_comment_node_missing_author_defaults_empty_string(self) -> None:
        """_parse_comment_node returns empty string author when author is absent.

        Tests: Defensive handling of deleted/ghost user (GitHub returns null author).
        How: Pass node dict with author=None.
        Why: Ghost accounts and deleted users return null author from GitHub API.
        """
        # Arrange
        raw: dict[str, Any] = {
            "id": "IC_xyz",
            "body": "body text",
            "url": "",
            "author": None,
            "createdAt": "2026-01-01T00:00:00Z",
            "updatedAt": "2026-01-01T00:00:00Z",
        }

        # Act
        result = _parse_comment_node(raw)

        # Assert
        assert result.author == ""

    def test_parse_comment_node_missing_fields_default_to_empty_string(self) -> None:
        """_parse_comment_node returns empty strings for absent optional fields.

        Tests: Resilience when GraphQL omits optional fields.
        How: Pass a dict with only id set.
        Why: Prevents KeyError on partial GraphQL responses.
        """
        # Arrange
        raw: dict[str, Any] = {"id": "IC_min"}

        # Act
        result = _parse_comment_node(raw)

        # Assert
        assert result.id == "IC_min"
        assert result.body == ""
        assert result.author == ""
        assert result.created_at == ""
        assert result.updated_at == ""


# ---------------------------------------------------------------------------
# _fetch_issue_comments_graphql
# ---------------------------------------------------------------------------


class TestFetchIssueCommentsGraphql:
    """Tests for _fetch_issue_comments_graphql pagination and parsing."""

    def test_fetch_issue_comments_returns_parsed_nodes(self, mocker: MockerFixture) -> None:
        """_fetch_issue_comments_graphql returns list of IssueCommentNode dicts.

        Tests: Single-page response with two comments.
        How: Mock _graphql_request to return one page with two nodes.
        Why: Verifies parsing pipeline from raw GraphQL dict to IssueCommentNode.
        """
        # Arrange
        repo = _make_mock_repo(mocker)
        comment_a = make_issue_comment_node(comment_id="IC_001", body="first comment", author="alice")
        comment_b = make_issue_comment_node(comment_id="IC_002", body="second comment", author="bob")
        mocker.patch(
            "backlog_core.gh_client._graphql_request", return_value=make_issue_comments_response([comment_a, comment_b])
        )

        # Act
        result = _fetch_issue_comments_graphql(repo, "owner", "repo", 42)

        # Assert
        assert len(result) == 2
        assert result[0].id == "IC_001"
        assert result[0].author == "alice"
        assert result[1].id == "IC_002"
        assert result[1].author == "bob"

    def test_fetch_issue_comments_empty_list_returns_empty(self, mocker: MockerFixture) -> None:
        """_fetch_issue_comments_graphql returns empty list when issue has no comments.

        Tests: Empty comments response.
        How: Mock _graphql_request to return has_next=False, empty nodes.
        Why: Operations must handle zero-comment issues without error.
        """
        # Arrange
        repo = _make_mock_repo(mocker)
        mocker.patch("backlog_core.gh_client._graphql_request", return_value=make_issue_comments_response([]))

        # Act
        result = _fetch_issue_comments_graphql(repo, "owner", "repo", 1)

        # Assert
        assert result == []

    def test_fetch_issue_comments_paginates_across_pages(self, mocker: MockerFixture) -> None:
        """_fetch_issue_comments_graphql concatenates results across multiple pages.

        Tests: Two-page pagination (first has hasNextPage=True, second terminates).
        How: Mock _graphql_request with side_effect returning page 1 then page 2.
        Why: Verifies the while-loop pagination works end-to-end.
        """
        # Arrange
        repo = _make_mock_repo(mocker)
        page1 = make_issue_comments_response(
            [make_issue_comment_node(comment_id="IC_001")], has_next=True, end_cursor="cursor_abc"
        )
        page2 = make_issue_comments_response([make_issue_comment_node(comment_id="IC_002")], has_next=False)
        mocker.patch("backlog_core.gh_client._graphql_request", side_effect=[page1, page2])

        # Act
        result = _fetch_issue_comments_graphql(repo, "owner", "repo", 5)

        # Assert
        assert len(result) == 2
        assert result[0].id == "IC_001"
        assert result[1].id == "IC_002"


# ---------------------------------------------------------------------------
# _fetch_comment_by_id_graphql
# ---------------------------------------------------------------------------


class TestFetchCommentByIdGraphql:
    """Tests for _fetch_comment_by_id_graphql single-comment fetch."""

    def test_fetch_comment_by_id_returns_parsed_comment(self, mocker: MockerFixture) -> None:
        """_fetch_comment_by_id_graphql returns parsed IssueCommentNode for valid ID.

        Tests: Happy path with all fields present in response.
        How: Mock _graphql_request to return a node() response with IssueComment data.
        Why: Validates field mapping from GetComment query response.
        """
        # Arrange
        repo = _make_mock_repo(mocker)
        mocker.patch(
            "backlog_core.gh_client._graphql_request",
            return_value=make_comment_by_id_response(comment_id="IC_abc", body="Full comment body", author="carol"),
        )

        # Act
        result = _fetch_comment_by_id_graphql(repo, "IC_abc")

        # Assert
        assert result.id == "IC_abc"
        assert result.body == "Full comment body"
        assert result.author == "carol"

    def test_fetch_comment_by_id_missing_node_raises_backlog_error(self, mocker: MockerFixture) -> None:
        """_fetch_comment_by_id_graphql raises BacklogError when node is null.

        Tests: Not-found case where GitHub GraphQL returns data.node=null.
        How: Mock _graphql_request to return {"node": None}.
        Why: Caller must receive BacklogError, not a KeyError on None.
        """
        # Arrange
        repo = _make_mock_repo(mocker)
        mocker.patch("backlog_core.gh_client._graphql_request", return_value={"node": None})

        # Act + Assert
        with pytest.raises(BacklogError, match="Could not resolve comment node"):
            _fetch_comment_by_id_graphql(repo, "IC_missing")

    def test_fetch_comment_by_id_non_issue_comment_raises_backlog_error(self, mocker: MockerFixture) -> None:
        """_fetch_comment_by_id_graphql raises BacklogError when node has no 'id' field.

        Tests: Node resolves but is not an IssueComment (GraphQL inline fragment
        returns empty object when type doesn't match).
        How: Mock _graphql_request to return {"node": {}}.
        Why: Prevents silent data corruption when a non-comment node ID is passed.
        """
        # Arrange
        repo = _make_mock_repo(mocker)
        mocker.patch("backlog_core.gh_client._graphql_request", return_value={"node": {}})

        # Act + Assert
        with pytest.raises(BacklogError, match="is not an IssueComment"):
            _fetch_comment_by_id_graphql(repo, "IC_wrongtype")


# ---------------------------------------------------------------------------
# list_comments operation
# ---------------------------------------------------------------------------


class TestListComments:
    """Tests for the list_comments operation."""

    def test_list_comments_returns_comment_list_with_preview(self, mocker: MockerFixture) -> None:
        """list_comments returns comments with id, author, timestamps, and preview.

        Tests: Happy path — two comments, preview truncated to 200 chars.
        How: Mock get_github and _fetch_issue_comments_graphql.
        Why: Verifies the output shape matches the documented contract.
        """
        # Arrange
        long_body = "x" * 300
        mock_repo = _make_mock_repo(mocker)
        mocker.patch("backlog_core.operations.get_github", return_value=mock_repo)
        mocker.patch(
            "backlog_core.operations._fetch_issue_comments_graphql",
            return_value=[
                IssueCommentNode(
                    id="IC_001",
                    body="short comment",
                    url="",
                    author="alice",
                    created_at="2026-01-01T00:00:00Z",
                    updated_at="2026-01-01T00:00:00Z",
                ),
                IssueCommentNode(
                    id="IC_002",
                    body=long_body,
                    url="",
                    author="bob",
                    created_at="2026-01-02T00:00:00Z",
                    updated_at="2026-01-02T00:00:00Z",
                ),
            ],
        )

        # Act
        result = list_comments(issue_number=42)

        # Assert
        assert isinstance(result, dict)
        assert result["count"] == 2
        assert result["has_more"] is False
        comments = result["comments"]
        assert isinstance(comments, list)
        assert len(comments) == 2
        assert comments[0].id == "IC_001"
        assert comments[0].author == "alice"
        assert comments[0].preview == "short comment"
        # Second comment body is 300 chars; preview truncates to 200.
        assert len(comments[1].preview) == 200

    def test_list_comments_database_id_is_the_rest_id_read_comment_needs(self, mocker: MockerFixture) -> None:
        """A listed comment's database_id is exactly what backlog_read_comment's comment_id needs.

        Tests: End-to-end reachability — the whole point of this feature (#3546) is
        that a database_id obtained from list_comments can be fed straight into
        read_comment's REST-addressed comment_id without a separate REST call.
        How: list_comments returns a comment whose database_id is populated (not
        None/missing); that exact integer is then passed as read_comment's
        comment_id, and read_comment's REST resolution call
        (PyGithub Issue.get_comment) is asserted to have received it unchanged.
        Why: Before this fix, list_comments discarded database_id and only
        emitted the GraphQL node id, so no value it returned could ever reach
        read_comment's comment_id parameter — the feature was unreachable
        through the public API despite the GraphQL fetch side carrying the field.
        """
        # Arrange: list_comments sees a comment with both a GraphQL node id and a
        # REST database_id, as the live GraphQL query (which now selects
        # databaseId) would return.
        rest_database_id = 5659363376
        mock_repo = _make_mock_repo(mocker)
        mocker.patch("backlog_core.operations.get_github", return_value=mock_repo)
        mocker.patch(
            "backlog_core.operations._fetch_issue_comments_graphql",
            return_value=[
                IssueCommentNode(
                    id="IC_kwDOAbCdEf4AbCdEf",
                    body="short comment",
                    url="",
                    author="alice",
                    created_at="2026-01-01T00:00:00Z",
                    updated_at="2026-01-01T00:00:00Z",
                    database_id=rest_database_id,
                )
            ],
        )

        # Act
        listed = list_comments(issue_number=42)

        # Assert: database_id is populated on the listing entry, not None/missing.
        comments = listed["comments"]
        assert isinstance(comments, list)
        assert comments[0].database_id == rest_database_id

        # Arrange: wire up read_comment's REST resolution path to expect exactly
        # the database_id list_comments returned.
        mock_issue = mocker.Mock()
        mock_comment = mocker.Mock()
        mock_comment.node_id = "IC_kwDOAbCdEf4AbCdEf"
        mock_issue.get_comment.return_value = mock_comment
        mock_repo.get_issue.return_value = mock_issue
        mocker.patch(
            "backlog_core.operations._fetch_comment_by_id_graphql",
            return_value=IssueCommentNode(
                id="IC_kwDOAbCdEf4AbCdEf",
                body="short comment",
                url="",
                author="alice",
                created_at="2026-01-01T00:00:00Z",
                updated_at="2026-01-01T00:00:00Z",
                database_id=rest_database_id,
            ),
        )

        # Act: feed the listing's database_id straight into read_comment's
        # comment_id, exactly as a caller of the public API would.
        comment_id = comments[0].database_id
        assert isinstance(comment_id, int)
        read = read_comment(issue_number=42, comment_id=comment_id)

        # Assert: the REST database ID reached PyGithub's REST call unchanged,
        # and the same comment came back.
        mock_issue.get_comment.assert_called_once_with(rest_database_id)
        assert read["id"] == "IC_kwDOAbCdEf4AbCdEf"

    def test_list_comments_invalid_issue_number_raises_validation_error(self) -> None:
        """list_comments raises ValidationError when issue_number <= 0.

        Tests: Input validation for issue_number=0.
        How: Call list_comments with issue_number=0.
        Why: Prevents nonsensical API calls for invalid issue numbers.
        """
        with pytest.raises(ValidationError, match="issue_number must be a positive integer"):
            list_comments(issue_number=0)

    def test_list_comments_respects_limit_and_offset(self, mocker: MockerFixture) -> None:
        """list_comments applies offset and limit to the full comment list.

        Tests: offset=1, limit=1 from a 3-comment list returns middle comment.
        How: Mock _fetch_issue_comments_graphql to return 3 comments.
        Why: Verifies pagination slicing is correct.
        """
        # Arrange
        mock_repo = _make_mock_repo(mocker)
        mocker.patch("backlog_core.operations.get_github", return_value=mock_repo)
        all_comments = [
            IssueCommentNode(id=f"IC_{i:03d}", body=f"body {i}", url="", author="u", created_at="", updated_at="")
            for i in range(3)
        ]
        mocker.patch("backlog_core.operations._fetch_issue_comments_graphql", return_value=all_comments)

        # Act
        result = list_comments(issue_number=1, limit=1, offset=1)

        # Assert
        assert result["count"] == 1
        assert result["has_more"] is True
        comments = result["comments"]
        assert isinstance(comments, list)
        assert comments[0].id == "IC_001"

    def test_list_comments_has_more_false_when_all_fit(self, mocker: MockerFixture) -> None:
        """list_comments sets has_more=False when all comments fit in the window.

        Tests: 2 comments, limit=5 — all fit, no more pages.
        How: Mock _fetch_issue_comments_graphql to return 2 comments.
        Why: has_more must be accurate so callers know when to paginate.
        """
        # Arrange
        mock_repo = _make_mock_repo(mocker)
        mocker.patch("backlog_core.operations.get_github", return_value=mock_repo)
        mocker.patch(
            "backlog_core.operations._fetch_issue_comments_graphql",
            return_value=[
                IssueCommentNode(id="IC_001", body="a", url="", author="u", created_at="", updated_at=""),
                IssueCommentNode(id="IC_002", body="b", url="", author="u", created_at="", updated_at=""),
            ],
        )

        # Act
        result = list_comments(issue_number=1, limit=5)

        # Assert
        assert result["has_more"] is False

    def test_list_comments_github_error_raises_backlog_error(self, mocker: MockerFixture) -> None:
        """list_comments raises BacklogError when GitHub API fails.

        Tests: GithubException from get_github is wrapped in BacklogError.
        How: Mock get_github to raise GithubException.
        Why: Callers rely on BacklogError for consistent error handling.
        """
        # Arrange
        from github import GithubException

        mocker.patch("backlog_core.operations.get_github", side_effect=GithubException(500, "server error", None))

        # Act + Assert
        with pytest.raises(BacklogError, match="GitHub API error fetching comments"):
            list_comments(issue_number=1)


# ---------------------------------------------------------------------------
# read_comment operation
# ---------------------------------------------------------------------------


class TestReadComment:
    """Tests for the read_comment operation."""

    def test_read_comment_returns_full_body(self, mocker: MockerFixture) -> None:
        """read_comment returns the full comment body without truncation.

        Tests: Happy path — full body returned, all fields present.
        How: Mock get_github, get_issue, get_comment, and _fetch_comment_by_id_graphql.
        Why: Verifies the output contract and that body is not truncated.
        """
        # Arrange
        full_body = "A" * 1000
        mock_repo = _make_mock_repo(mocker)
        mock_issue = mocker.Mock()
        mock_comment = mocker.Mock()
        mock_comment.node_id = "IC_kwDOabc"
        mock_issue.get_comment.return_value = mock_comment
        mock_repo.get_issue.return_value = mock_issue
        mocker.patch("backlog_core.operations.get_github", return_value=mock_repo)
        mocker.patch(
            "backlog_core.operations._fetch_comment_by_id_graphql",
            return_value=IssueCommentNode(
                id="IC_kwDOabc",
                body=full_body,
                url="https://github.com/o/r/issues/1#issuecomment-99",
                author="dave",
                created_at="2026-01-01T00:00:00Z",
                updated_at="2026-01-02T00:00:00Z",
            ),
        )

        # Act
        result = read_comment(issue_number=1, comment_id=99)

        # Assert
        assert result["id"] == "IC_kwDOabc"
        assert result["author"] == "dave"
        assert result["body"] == full_body
        assert len(result["body"]) == 1000  # no truncation

    def test_read_comment_invalid_issue_number_raises_validation_error(self) -> None:
        """read_comment raises ValidationError when issue_number is 0.

        Tests: Validation guard for issue_number=0.
        How: Call read_comment with issue_number=0, comment_id=1.
        Why: Must reject invalid input before any API call.
        """
        with pytest.raises(ValidationError, match="issue_number must be a positive integer"):
            read_comment(issue_number=0, comment_id=1)

    def test_read_comment_invalid_comment_id_raises_validation_error(self) -> None:
        """read_comment raises ValidationError when comment_id is 0.

        Tests: Validation guard for comment_id=0.
        How: Call read_comment with issue_number=1, comment_id=0.
        Why: Must reject invalid input before any API call.
        """
        with pytest.raises(ValidationError, match="comment_id must be a positive integer"):
            read_comment(issue_number=1, comment_id=0)

    def test_read_comment_github_error_raises_backlog_error(self, mocker: MockerFixture) -> None:
        """read_comment raises BacklogError when GitHub API fails.

        Tests: GithubException from get_github is wrapped in BacklogError.
        How: Mock get_github to raise GithubException.
        Why: Callers rely on BacklogError for consistent error handling.
        """
        from github import GithubException

        mocker.patch("backlog_core.operations.get_github", side_effect=GithubException(404, "not found", None))

        with pytest.raises(BacklogError, match="GitHub API error reading comment"):
            read_comment(issue_number=1, comment_id=99)

    def test_read_comment_uses_issue_number_to_resolve_node_id(self, mocker: MockerFixture) -> None:
        """read_comment calls get_issue and get_comment with correct arguments.

        Tests: The REST resolution path passes issue_number and comment_id correctly.
        How: Mock all dependencies and inspect call arguments.
        Why: Ensures correct REST IDs are used to resolve the GraphQL node ID.
        """
        # Arrange
        mock_repo = _make_mock_repo(mocker)
        mock_issue = mocker.Mock()
        mock_comment = mocker.Mock()
        mock_comment.node_id = "IC_node123"
        mock_issue.get_comment.return_value = mock_comment
        mock_repo.get_issue.return_value = mock_issue
        mocker.patch("backlog_core.operations.get_github", return_value=mock_repo)
        fetch_mock = mocker.patch(
            "backlog_core.operations._fetch_comment_by_id_graphql",
            return_value=IssueCommentNode(
                id="IC_node123", body="body", url="", author="u", created_at="", updated_at=""
            ),
        )

        # Act
        read_comment(issue_number=42, comment_id=99)

        # Assert
        mock_repo.get_issue.assert_called_once_with(42)
        mock_issue.get_comment.assert_called_once_with(99)
        fetch_mock.assert_called_once_with(mock_repo, "IC_node123")


# ---------------------------------------------------------------------------
# comment_issue operation
# ---------------------------------------------------------------------------


class TestCommentIssue:
    """Tests for the comment_issue operation."""

    def test_comment_issue_database_id_is_the_rest_id_read_comment_needs(self, mocker: MockerFixture) -> None:
        """A created comment's database_id is exactly what backlog_read_comment's comment_id needs.

        Tests: End-to-end reachability -- the create-comment counterpart to
        ``test_list_comments_database_id_is_the_rest_id_read_comment_needs``.
        Before this fix, the ``addComment`` mutation never selected
        ``fullDatabaseId``, so a comment created via ``comment_issue`` could
        only be read back by first calling ``list_comments`` to discover its
        REST ID separately -- the create path was unreachable through the
        public API despite the listing and single-comment paths already
        carrying the field.
        How: comment_issue returns a database_id (as the live GraphQL
        mutation, which now selects fullDatabaseId, would return); that exact
        integer is fed straight into read_comment's comment_id, and
        read_comment's REST resolution call (PyGithub Issue.get_comment) is
        asserted to have received it unchanged.
        Why: Confirms full identifier symmetry across create, list, and read
        -- the whole point of #3546.
        """
        # Arrange: comment_issue sees a created comment with both a GraphQL
        # node id and a REST database_id, as the live GraphQL mutation (which
        # now selects fullDatabaseId) would return.
        rest_database_id = 5659363377
        mock_repo = _make_mock_repo(mocker)
        mocker.patch("backlog_core.operations.get_github", return_value=mock_repo)
        mocker.patch(
            "backlog_core.operations._fetch_issue_graphql",
            return_value={
                "id": "I_kwDOAbCdEf4AbCdEf",
                "number": 42,
                "title": "t",
                "state": "OPEN",
                "body": "",
                "createdAt": "",
                "updatedAt": "",
                "labels": [],
                "milestone": None,
                "assignees": [],
            },
        )
        mocker.patch(
            "backlog_core.operations._add_comment_graphql",
            return_value=AddedCommentNode(id="IC_kwDOAbCdEf4AbCdEf", database_id=rest_database_id),
        )

        # Act
        created = comment_issue(issue_number=42, body="LGTM!")

        # Assert: database_id is populated on the create response, not None/missing.
        assert created["database_id"] == rest_database_id
        assert created["comment_id"] == "IC_kwDOAbCdEf4AbCdEf"

        # Arrange: wire up read_comment's REST resolution path to expect
        # exactly the database_id comment_issue returned.
        mock_issue = mocker.Mock()
        mock_comment = mocker.Mock()
        mock_comment.node_id = "IC_kwDOAbCdEf4AbCdEf"
        mock_issue.get_comment.return_value = mock_comment
        mock_repo.get_issue.return_value = mock_issue
        mocker.patch(
            "backlog_core.operations._fetch_comment_by_id_graphql",
            return_value=IssueCommentNode(
                id="IC_kwDOAbCdEf4AbCdEf",
                body="LGTM!",
                url="",
                author="alice",
                created_at="2026-01-01T00:00:00Z",
                updated_at="2026-01-01T00:00:00Z",
                database_id=rest_database_id,
            ),
        )

        # Act: feed the create response's database_id straight into
        # read_comment's comment_id, exactly as a caller of the public API would.
        comment_id = created["database_id"]
        assert isinstance(comment_id, int)
        read = read_comment(issue_number=42, comment_id=comment_id)

        # Assert: the REST database ID reached PyGithub's REST call unchanged,
        # and the same comment came back.
        mock_issue.get_comment.assert_called_once_with(rest_database_id)
        assert read["id"] == "IC_kwDOAbCdEf4AbCdEf"
        assert read["body"] == "LGTM!"
