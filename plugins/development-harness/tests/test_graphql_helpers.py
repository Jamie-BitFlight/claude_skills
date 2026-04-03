"""Tests for _resolve_labels_graphql() in backlog_core/gh_client.py.

Covers: all-found, partial-found, all-missing, empty-input, exception propagation,
deduplication, and invalid label name rejection.

All PyGithub boundary objects are mocked — no live API calls.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from backlog_core.gh_client import _resolve_labels_graphql
from github import GithubException

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_repo(mocker: MockerFixture) -> Any:
    """Return a minimal mock PyGithub Repository with configurable graphql_query.

    The returned repo.requester.graphql_query mock has no return value pre-set;
    individual tests configure it via return_value or side_effect.

    Args:
        mocker: pytest-mock fixture.

    Returns:
        Mock object with .full_name and .requester.graphql_query attributes.
    """
    repo = mocker.Mock()
    repo.full_name = "test-owner/test-repo"
    return repo


def _graphql_response(label_map: dict[str, dict[str, str] | None]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build a (headers, data) tuple mimicking Requester.graphql_query return value.

    Args:
        label_map: Dict of alias -> {"name": "..."} or None for missing labels.
                   Example: {"label0": {"name": "status:open"}, "label1": None}

    Returns:
        Tuple of (empty headers dict, GraphQL data dict).
    """
    return ({}, {"data": {"repository": label_map}})


# ---------------------------------------------------------------------------
# TestResolveLabelsBatchAllFound
# ---------------------------------------------------------------------------


class TestResolveLabelsBatchAllFound:
    """_resolve_labels_graphql returns all names when all labels exist in repo."""

    def test_all_labels_found_returns_all_names(self, mocker: MockerFixture) -> None:
        """Returns each requested label name when all aliases resolve in GraphQL.

        Tests: Happy-path resolution of three labels.
        How: Configure graphql_query to return non-null nodes for all aliases.
             Call _resolve_labels_graphql with three label names.
        Why: The primary use case — all requested labels exist, they must all be
             returned so create_issue can attach them.
        """
        # Arrange
        repo = _make_mock_repo(mocker)
        repo.requester.graphql_query.return_value = _graphql_response({
            "label0": {"name": "status:needs-grooming"},
            "label1": {"name": "priority:p1"},
            "label2": {"name": "type:feature"},
        })

        # Act
        result = _resolve_labels_graphql(
            repo, "test-owner", "test-repo", ["status:needs-grooming", "priority:p1", "type:feature"]
        )

        # Assert
        assert result == ["status:needs-grooming", "priority:p1", "type:feature"]
        repo.requester.graphql_query.assert_called_once()

    def test_single_label_found_returns_list_with_one_item(self, mocker: MockerFixture) -> None:
        """Single label input resolves to single-element list when it exists.

        Tests: Minimal input scenario (one label).
        How: Pass list with one label name, mock one alias in response.
        Why: Call sites may pass a single-element list; result must be a list.
        """
        # Arrange
        repo = _make_mock_repo(mocker)
        repo.requester.graphql_query.return_value = _graphql_response({"label0": {"name": "sam-task"}})

        # Act
        result = _resolve_labels_graphql(repo, "org", "repo", ["sam-task"])

        # Assert
        assert result == ["sam-task"]


# ---------------------------------------------------------------------------
# TestResolveLabelsSomeNull
# ---------------------------------------------------------------------------


class TestResolveLabelsSomeNull:
    """_resolve_labels_graphql omits null aliases and returns only existing labels."""

    def test_some_labels_null_returns_only_existing(self, mocker: MockerFixture) -> None:
        """Labels with null aliases are silently omitted from the result.

        Tests: Partial resolution — some labels exist, some do not.
        How: Return label0 as found node, label1 as None (missing), label2 as found.
        Why: GitHub issues must be created with only the labels that exist; passing a
             non-existent label string to create_issue raises a 422 validation error.
        """
        # Arrange
        repo = _make_mock_repo(mocker)
        repo.requester.graphql_query.return_value = _graphql_response({
            "label0": {"name": "status:needs-grooming"},
            "label1": None,
            "label2": {"name": "type:feature"},
        })

        # Act
        result = _resolve_labels_graphql(
            repo, "owner", "repo", ["status:needs-grooming", "priority:missing", "type:feature"]
        )

        # Assert
        assert result == ["status:needs-grooming", "type:feature"]
        assert "priority:missing" not in result

    def test_first_label_null_middle_present_last_null(self, mocker: MockerFixture) -> None:
        """Null aliases in any position are correctly skipped.

        Tests: Alias index ordering does not affect null-skip logic.
        How: First and last aliases null, middle present.
        Why: Ensures iteration over aliases is position-independent.
        """
        # Arrange
        repo = _make_mock_repo(mocker)
        repo.requester.graphql_query.return_value = _graphql_response({
            "label0": None,
            "label1": {"name": "priority:p2"},
            "label2": None,
        })

        # Act
        result = _resolve_labels_graphql(repo, "owner", "repo", ["missing-first", "priority:p2", "missing-last"])

        # Assert
        assert result == ["priority:p2"]


# ---------------------------------------------------------------------------
# TestResolveLabelsAllNull
# ---------------------------------------------------------------------------


class TestResolveLabelsAllNull:
    """_resolve_labels_graphql returns empty list when all aliases are null."""

    def test_all_labels_null_returns_empty_list(self, mocker: MockerFixture) -> None:
        """Returns empty list when every requested label is missing from the repo.

        Tests: All-missing case — no labels exist on the repository.
        How: All aliases return None in GraphQL response.
        Why: Caller (create_issue_for_item) warns per missing label; must not crash
             when none resolve. Issue creation proceeds with empty labels list.
        """
        # Arrange
        repo = _make_mock_repo(mocker)
        repo.requester.graphql_query.return_value = _graphql_response({"label0": None, "label1": None, "label2": None})

        # Act
        result = _resolve_labels_graphql(
            repo, "owner", "repo", ["status:needs-grooming", "priority:p1", "type:feature"]
        )

        # Assert
        assert result == []
        repo.requester.graphql_query.assert_called_once()


# ---------------------------------------------------------------------------
# TestResolveLabelsEmptyInput
# ---------------------------------------------------------------------------


class TestResolveLabelsEmptyInput:
    """_resolve_labels_graphql returns immediately with empty list for empty input."""

    def test_empty_label_list_returns_empty_without_graphql_call(self, mocker: MockerFixture) -> None:
        """Empty input returns empty list with no GraphQL call issued.

        Tests: Fast-exit guard clause for empty input.
        How: Pass empty list; verify graphql_query is never called.
        Why: An empty query would generate invalid GraphQL; the guard must
             short-circuit before the request is issued.
        """
        # Arrange
        repo = _make_mock_repo(mocker)

        # Act
        result = _resolve_labels_graphql(repo, "owner", "repo", [])

        # Assert
        assert result == []
        repo.requester.graphql_query.assert_not_called()


# ---------------------------------------------------------------------------
# TestResolveLabelsException
# ---------------------------------------------------------------------------


class TestResolveLabelsException:
    """_resolve_labels_graphql propagates GithubException from graphql_query."""

    def test_github_exception_propagates_to_caller(self, mocker: MockerFixture) -> None:
        """GithubException raised by graphql_query is not swallowed.

        Tests: Error propagation — auth/network/permission failures surface to caller.
        How: Configure graphql_query.side_effect = GithubException(401, "bad creds").
             Assert pytest.raises catches the same exception.
        Why: Callers (create_issue_for_item) do not wrap _resolve_labels_graphql
             in try/except; failures must propagate so the caller's error handling fires.
        """
        # Arrange
        repo = _make_mock_repo(mocker)
        repo.requester.graphql_query.side_effect = GithubException(401, "bad credentials")

        # Act / Assert
        with pytest.raises(GithubException) as exc_info:
            _resolve_labels_graphql(repo, "owner", "repo", ["status:open"])

        assert exc_info.value.status == 401

    def test_rate_limit_exception_propagates(self, mocker: MockerFixture) -> None:
        """Rate-limit GithubException (403) propagates unchanged.

        Tests: 403 rate-limit error path.
        How: Raise GithubException(403, ...) from graphql_query.
        Why: Callers need to distinguish rate limits from auth failures; only the
             original exception carries that information.
        """
        # Arrange
        repo = _make_mock_repo(mocker)
        repo.requester.graphql_query.side_effect = GithubException(403, "rate limit exceeded")

        # Act / Assert
        with pytest.raises(GithubException) as exc_info:
            _resolve_labels_graphql(repo, "owner", "repo", ["some-label"])

        assert exc_info.value.status == 403

    def test_network_exception_propagates(self, mocker: MockerFixture) -> None:
        """GithubException(500, ...) from a network/server error propagates.

        Tests: Server-side error path.
        How: Raise GithubException(500, "internal server error").
        Why: Upstream failures must surface; silently returning empty would mask outages.
        """
        # Arrange
        repo = _make_mock_repo(mocker)
        repo.requester.graphql_query.side_effect = GithubException(500, "internal server error")

        # Act / Assert
        with pytest.raises(GithubException):
            _resolve_labels_graphql(repo, "owner", "repo", ["label-a"])


# ---------------------------------------------------------------------------
# TestResolveLabelsDeduplication
# ---------------------------------------------------------------------------


class TestResolveLabelsDeduplication:
    """_resolve_labels_graphql deduplicates input before building the GraphQL query."""

    def test_duplicate_input_names_send_only_unique_aliases(self, mocker: MockerFixture) -> None:
        """Duplicate label names in input are collapsed to unique aliases.

        Tests: Deduplication of identical label names.
        How: Pass the same label name twice; inspect the GraphQL query string
             and confirm only one alias is present.
        Why: Sending duplicate aliases wastes query budget and may produce duplicate
             results in the resolved list.
        """
        # Arrange
        repo = _make_mock_repo(mocker)
        repo.requester.graphql_query.return_value = _graphql_response({"label0": {"name": "status:open"}})

        # Act
        result = _resolve_labels_graphql(repo, "owner", "repo", ["status:open", "status:open", "status:open"])

        # Assert
        assert result == ["status:open"]
        # Verify GraphQL was called with only one alias (label0, no label1/label2)
        call_args = repo.requester.graphql_query.call_args
        query_string: str = call_args.args[0] if call_args.args else call_args[0][0]
        assert "label0" in query_string
        assert "label1" not in query_string

    def test_duplicates_across_two_names_sends_two_aliases(self, mocker: MockerFixture) -> None:
        """Two distinct names each repeated once → exactly two aliases sent.

        Tests: Deduplication with multiple distinct duplicated names.
        How: Pass ["a", "b", "a", "b"]; expect two aliases in query.
        Why: Confirms deduplication handles mixed-duplicate inputs correctly.
        """
        # Arrange
        repo = _make_mock_repo(mocker)
        repo.requester.graphql_query.return_value = _graphql_response({
            "label0": {"name": "label-a"},
            "label1": {"name": "label-b"},
        })

        # Act
        result = _resolve_labels_graphql(repo, "owner", "repo", ["label-a", "label-b", "label-a", "label-b"])

        # Assert
        assert result == ["label-a", "label-b"]
        call_args = repo.requester.graphql_query.call_args
        query_string: str = call_args.args[0] if call_args.args else call_args[0][0]
        assert "label1" in query_string
        assert "label2" not in query_string


# ---------------------------------------------------------------------------
# TestResolveLabelsInvalidName
# ---------------------------------------------------------------------------


class TestResolveLabelsInvalidName:
    """_resolve_labels_graphql rejects label names with disallowed characters."""

    def test_label_with_injection_characters_raises_value_error(self, mocker: MockerFixture) -> None:
        """Label name containing '{' raises ValueError before any GraphQL call.

        Tests: Input validation / injection prevention.
        How: Pass label name with curly brace character; assert ValueError raised
             and graphql_query never called.
        Why: Label names are embedded in the query string template; characters
             that could break GraphQL syntax must be rejected at validation time.
        """
        # Arrange
        repo = _make_mock_repo(mocker)

        # Act / Assert
        with pytest.raises(ValueError, match="disallowed characters"):
            _resolve_labels_graphql(repo, "owner", "repo", ["valid-label", "bad{name}"])

        repo.requester.graphql_query.assert_not_called()

    def test_label_with_newline_raises_value_error(self, mocker: MockerFixture) -> None:
        """Label name containing newline raises ValueError.

        Tests: Newline in label name injection prevention.
        How: Pass label with embedded newline; assert ValueError raised.
        Why: Newlines in the query template would produce malformed GraphQL syntax.
        """
        # Arrange
        repo = _make_mock_repo(mocker)

        # Act / Assert
        with pytest.raises(ValueError, match="disallowed characters"):
            _resolve_labels_graphql(repo, "owner", "repo", ["valid", "bad\nname"])

        repo.requester.graphql_query.assert_not_called()


# ---------------------------------------------------------------------------
# TestResolveLabelsVariablesPassedCorrectly
# ---------------------------------------------------------------------------


class TestResolveLabelsVariablesPassedCorrectly:
    """_resolve_labels_graphql passes owner/repo as GraphQL variables."""

    def test_graphql_variables_contain_owner_and_repo(self, mocker: MockerFixture) -> None:
        """The variables dict passed to graphql_query contains owner and repo keys.

        Tests: GraphQL variable construction.
        How: Capture call args; inspect the variables dict argument.
        Why: owner/repo must be passed as variables (not interpolated into query
             string) to prevent injection and match the query parameter declarations.
        """
        # Arrange
        repo = _make_mock_repo(mocker)
        repo.requester.graphql_query.return_value = _graphql_response({"label0": {"name": "status:open"}})

        # Act
        _resolve_labels_graphql(repo, "my-org", "my-repo", ["status:open"])

        # Assert
        call_args = repo.requester.graphql_query.call_args
        variables: dict[str, str] = call_args.args[1] if len(call_args.args) > 1 else call_args[0][1]
        assert variables["owner"] == "my-org"
        assert variables["repo"] == "my-repo"
