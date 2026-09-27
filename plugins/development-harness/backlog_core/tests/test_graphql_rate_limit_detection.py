"""Regression tests for classifying a GraphQL rate-limit refusal.

Observed 2026-09-27: a ListIssues query answered with a GitHub secondary rate limit gets no
special handling. GitHub answers a GraphQL query that trips a rate limit with HTTP 200 and a
body shaped ``{"data": null, "errors": [{"type": "RATE_LIMITED", ...}]}`` -- there is no
exception for ``_graphql_request`` to catch, only an ordinary-looking ``errors`` entry, so it
fell into the generic "GraphQL error" branch and raised a plain ``BacklogError`` with no
``retryable`` verdict. A caller cannot tell that condition apart from a malformed query.

Follows the same fake-repo pattern as ``test_graphql_unavailable_detection.py``: no network.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from backlog_core.gh_client import _graphql_request
from backlog_core.models import BackendUnavailableError, BacklogError, GitHubRateLimitedError


@dataclass
class _FakeRequester:
    """Returns the configured (headers, response) pair instead of issuing a request."""

    response: dict[str, object]
    headers: dict[str, str] | None = None

    def graphql_query(self, query: str, variables: dict[str, object]) -> tuple[dict, dict]:
        """Return the configured headers and body."""
        return self.headers or {}, self.response


@dataclass
class _FakeRepo:
    """Minimal stand-in satisfying the `.requester` surface `_graphql_request` needs."""

    requester: Any


def _rate_limited_response(message: str = "API rate limit exceeded for installation ID 1.") -> dict[str, object]:
    """Build the response body GitHub sends for a GraphQL rate-limited query."""
    return {"data": None, "errors": [{"type": "RATE_LIMITED", "message": message}]}


class TestGraphQLRateLimitIsClassified:
    """A RATE_LIMITED GraphQL error must raise a distinguishable, retryable type."""

    def test_it_raises_the_dedicated_retryable_type(self) -> None:
        repo = _FakeRepo(_FakeRequester(_rate_limited_response()))

        with pytest.raises(GitHubRateLimitedError) as excinfo:
            _graphql_request(repo, "query ListIssues { viewer { login } }")

        assert excinfo.value.retryable is True

    def test_it_is_still_a_backend_unavailable_error(self) -> None:
        """Existing `except BackendUnavailableError` handlers must keep catching it."""
        assert issubclass(GitHubRateLimitedError, BackendUnavailableError)

    def test_it_carries_the_retry_after_header_when_github_sends_one(self) -> None:
        repo = _FakeRepo(_FakeRequester(_rate_limited_response(), headers={"Retry-After": "30"}))

        with pytest.raises(GitHubRateLimitedError) as excinfo:
            _graphql_request(repo, "query ListIssues { viewer { login } }")

        assert excinfo.value.retry_after == pytest.approx(30.0)

    def test_retry_after_is_none_when_github_sends_no_hint(self) -> None:
        repo = _FakeRepo(_FakeRequester(_rate_limited_response()))

        with pytest.raises(GitHubRateLimitedError) as excinfo:
            _graphql_request(repo, "query ListIssues { viewer { login } }")

        assert excinfo.value.retry_after is None

    def test_a_non_rate_limit_graphql_error_stays_a_plain_backlog_error(self) -> None:
        """Negative control: an ordinary query error must not be swept into this type."""
        repo = _FakeRepo(_FakeRequester({"data": None, "errors": [{"message": "field invalid"}]}))

        with pytest.raises(BacklogError) as excinfo:
            _graphql_request(repo, "query ListIssues { viewer { login } }")

        assert not isinstance(excinfo.value, GitHubRateLimitedError)
