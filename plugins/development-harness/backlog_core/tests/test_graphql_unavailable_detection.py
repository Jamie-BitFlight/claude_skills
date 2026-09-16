"""Tests for detecting an environment that refuses GitHub's GraphQL API.

Some sandboxes serve GitHub's REST API and reject every GraphQL request with HTTP 403.
`_graphql_request` previously flattened that into a generic `BacklogError`, so no caller
could tell "this environment refuses GraphQL, use REST" apart from "this query is wrong"
or "the token lacks a scope".

The distinction these tests protect: a 403 carrying the environment-refusal marker is a
routing signal, and every other 403 stays a generic failure. Widening the detector to all
403s would swallow genuine permission errors, which no REST fallback can fix either.
"""

from __future__ import annotations

import pytest
from github import GithubException

from backlog_core.gh_client import (
    GRAPHQL_UNAVAILABLE_MARKERS,
    _github_exception_message,
    _graphql_request,
    is_graphql_unavailable,
)
from backlog_core.models import BackendUnavailableError, BacklogError, GraphQLUnavailableError
from backlog_core.sync_state import RETRYABLE_TRANSIENT_EXCEPTIONS

#: The message body observed verbatim from a Claude Code sandbox on 2026-09-14.
_SANDBOX_MESSAGE = (
    "GitHub GraphQL is not available from Claude Code sessions; use the REST API "
    "(gh api repos/{owner}/{repo}/...). For review threads, auto-merge, and "
    "draft/ready-for-review use the CCR routes on api.github.com: ..."
)


def _github_exception(status: int, data: object) -> GithubException:
    """Build a GithubException shaped the way PyGithub raises one."""
    return GithubException(status=status, data=data, headers={})


class _FakeRequester:
    """Stands in for PyGithub's requester, raising whatever the test supplies."""

    def __init__(self, error: Exception) -> None:
        self._error = error

    def graphql_query(self, query: str, variables: dict[str, object]) -> tuple[dict, dict]:
        """Raise the configured error instead of issuing a request."""
        raise self._error


class _FakeRepo:
    """Minimal stand-in satisfying the `.requester` surface `_graphql_request` needs."""

    def __init__(self, error: Exception) -> None:
        self.requester = _FakeRequester(error)


class TestMessageExtraction:
    """PyGithub puts the parsed response body on `data`, which is not always a dict."""

    def test_reads_the_message_key_from_a_dict_body(self):
        exc = _github_exception(403, {"message": _SANDBOX_MESSAGE})

        assert _github_exception_message(exc) == _SANDBOX_MESSAGE

    def test_falls_back_to_the_whole_body_when_not_a_dict(self):
        exc = _github_exception(403, "Forbidden")

        assert "Forbidden" in _github_exception_message(exc)

    def test_falls_back_when_the_dict_carries_no_message(self):
        exc = _github_exception(403, {"documentation_url": "https://example.invalid"})

        assert "example.invalid" in _github_exception_message(exc)

    def test_falls_back_when_message_is_not_a_string(self):
        exc = _github_exception(403, {"message": {"nested": "value"}})

        assert "nested" in _github_exception_message(exc)


class TestIsGraphqlUnavailable:
    """A 403 alone is not the signal. The message is what distinguishes the cause."""

    def test_the_observed_sandbox_403_matches(self):
        exc = _github_exception(403, {"message": _SANDBOX_MESSAGE})

        assert is_graphql_unavailable(exc) is True

    def test_matching_ignores_case(self):
        exc = _github_exception(403, {"message": "GITHUB GRAPHQL IS NOT AVAILABLE HERE"})

        assert is_graphql_unavailable(exc) is True

    def test_a_permissions_403_does_not_match(self):
        """A token missing a scope also returns 403, and REST cannot fix that either."""
        exc = _github_exception(403, {"message": "Resource not accessible by integration"})

        assert is_graphql_unavailable(exc) is False

    def test_a_rate_limit_403_does_not_match(self):
        exc = _github_exception(403, {"message": "API rate limit exceeded for user ID 1."})

        assert is_graphql_unavailable(exc) is False

    @pytest.mark.parametrize("status", [401, 404, 422, 500, 502])
    def test_other_statuses_never_match(self, status):
        """Even carrying the marker text, a non-403 is a different condition."""
        exc = _github_exception(status, {"message": _SANDBOX_MESSAGE})

        assert is_graphql_unavailable(exc) is False

    def test_every_declared_marker_is_detected(self):
        """Each entry in the constant is live, so none rots into a dead string."""
        for marker in GRAPHQL_UNAVAILABLE_MARKERS:
            exc = _github_exception(403, {"message": f"prefix {marker} suffix"})

            assert is_graphql_unavailable(exc) is True, f"marker not detected: {marker!r}"


class TestGraphqlRequestRaisesTheDistinctType:
    """The chokepoint classifies, so no call site repeats the check."""

    def test_refusal_raises_graphql_unavailable_error(self):
        repo = _FakeRepo(_github_exception(403, {"message": _SANDBOX_MESSAGE}))

        with pytest.raises(GraphQLUnavailableError):
            _graphql_request(repo, "query { viewer { login } }")

    def test_the_raised_message_names_the_cause(self):
        repo = _FakeRepo(_github_exception(403, {"message": _SANDBOX_MESSAGE}))

        with pytest.raises(GraphQLUnavailableError) as excinfo:
            _graphql_request(repo, "query { viewer { login } }")

        assert "unavailable in this environment" in str(excinfo.value)

    def test_the_original_exception_is_chained(self):
        """A reader needs the underlying 403, not only the classification."""
        original = _github_exception(403, {"message": _SANDBOX_MESSAGE})
        repo = _FakeRepo(original)

        with pytest.raises(GraphQLUnavailableError) as excinfo:
            _graphql_request(repo, "query { viewer { login } }")

        assert excinfo.value.__cause__ is original

    def test_a_permissions_403_still_raises_the_generic_error(self):
        repo = _FakeRepo(_github_exception(403, {"message": "Resource not accessible by integration"}))

        with pytest.raises(BacklogError) as excinfo:
            _graphql_request(repo, "query { viewer { login } }")

        assert not isinstance(excinfo.value, GraphQLUnavailableError)

    def test_a_non_403_still_raises_the_generic_error(self):
        repo = _FakeRepo(_github_exception(500, {"message": "Server Error"}))

        with pytest.raises(BacklogError) as excinfo:
            _graphql_request(repo, "query { viewer { login } }")

        assert not isinstance(excinfo.value, GraphQLUnavailableError)

    @pytest.mark.parametrize("transport_type", RETRYABLE_TRANSIENT_EXCEPTIONS)
    def test_raw_transport_failures_raise_the_generic_error(self, transport_type: type[Exception]):
        transport_error = transport_type("transport failed")
        repo = _FakeRepo(transport_error)

        with pytest.raises(BacklogError) as excinfo:
            _graphql_request(repo, "query { viewer { login } }")

        assert "GraphQL transport failed" in str(excinfo.value)
        assert excinfo.value.__cause__ is transport_error


class TestErrorTypeRelationships:
    """Existing handlers must keep working, and the new type must stay distinguishable."""

    def test_it_is_a_backlog_error(self):
        """`except BacklogError` sites predate this type and must still catch it."""
        assert issubclass(GraphQLUnavailableError, BacklogError)

    def test_it_is_a_backend_unavailable_error(self):
        """The condition is a backend surface being unavailable, not a malformed request."""
        assert issubclass(GraphQLUnavailableError, BackendUnavailableError)

    def test_it_is_not_an_item_not_found_error(self):
        """A refused query says nothing about whether the item exists."""
        from backlog_core.models import ItemNotFoundError

        assert not issubclass(GraphQLUnavailableError, ItemNotFoundError)
        assert not issubclass(ItemNotFoundError, GraphQLUnavailableError)
