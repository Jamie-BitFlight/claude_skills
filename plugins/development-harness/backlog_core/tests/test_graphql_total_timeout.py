"""Regression test for a GraphQL request that never trips PyGithub's own timeout.

Observed 2026-09-27: ``backlog list`` hung for more than 5 minutes. A faulthandler dump at
45 seconds showed the process blocked in ``ssl.py read`` <- ``urllib3 read_chunked`` <-
``requests sessions.post`` <- PyGithub's ``Requester.graphql_query`` <- ``_graphql_request`` <-
``_fetch_issues_graphql``, reading the first ``ListIssues`` page's response body. The GraphQL
rate counter never moved, so this was a slow response, not request volume.

``requests``'/``urllib3``'s ``timeout=`` only bounds the gap between two consecutive reads on the
socket -- not the request's total duration. A response that trickles bytes slowly enough to keep
every individual read under that bound can block indefinitely without ever raising. Nothing in
``make_github_client``'s ``timeout=DEFAULT_TIMEOUT`` can catch that; only a caller-imposed total
deadline can.

These tests fake ``repo.requester.graphql_query`` as a slow call and confirm ``_graphql_request``
itself imposes and enforces a bound, converting expiry into a typed, retryable error rather than
letting the calling thread hang. No network is touched.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import pytest

from backlog_core.gh_client import _graphql_request
from backlog_core.models import GitHubRequestTimeoutError

#: Deliberately far longer than any deadline these tests configure -- if the deadline mechanism
#: is missing or broken, the test itself would hang for this long instead of failing fast.
_FAKE_SLOW_RESPONSE_SECONDS = 5.0

#: Small enough that a correct deadline resolves near-instantly, large enough to be stable in CI.
_TEST_DEADLINE_SECONDS = 0.2

#: Generous margin above _TEST_DEADLINE_SECONDS for scheduling jitter -- must stay far below
#: _FAKE_SLOW_RESPONSE_SECONDS or a broken deadline would pass by accident.
_MAX_ACCEPTABLE_ELAPSED_SECONDS = 2.0


class _SlowRequester:
    """Stands in for PyGithub's requester; blocks past any timeout under test."""

    def graphql_query(self, query: str, variables: dict[str, object]) -> tuple[dict, dict]:
        """Sleep well past the configured deadline, then answer as GitHub normally would."""
        time.sleep(_FAKE_SLOW_RESPONSE_SECONDS)
        return {}, {"data": {"viewer": {"login": "octocat"}}}


class _FastRequester:
    """Stands in for a normal, promptly-answering requester."""

    def graphql_query(self, query: str, variables: dict[str, object]) -> tuple[dict, dict]:
        """Answer immediately."""
        return {}, {"data": {"viewer": {"login": "octocat"}}}


@dataclass
class _FakeRepo:
    """Minimal stand-in satisfying the `.requester` surface `_graphql_request` needs."""

    requester: Any


@pytest.fixture(autouse=True)
def _small_total_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force the total-deadline this call site reads down to a CI-fast value.

    Isolates the deadline mechanism from the production default so this test suite never
    waits out the real (much larger) configured value.
    """
    monkeypatch.setattr("backlog_core.gh_client._graphql_total_timeout_seconds", lambda: _TEST_DEADLINE_SECONDS)


class TestTotalTimeoutBoundsATricklingResponse:
    """A response that never stalls long enough to trip the per-read timeout must still end."""

    def test_a_slow_response_is_bounded_by_the_deadline(self) -> None:
        repo = _FakeRepo(_SlowRequester())
        started = time.monotonic()

        with pytest.raises(GitHubRequestTimeoutError):
            _graphql_request(repo, "query ListIssues { viewer { login } }")

        elapsed = time.monotonic() - started
        assert elapsed < _MAX_ACCEPTABLE_ELAPSED_SECONDS, (
            f"expected the deadline ({_TEST_DEADLINE_SECONDS}s) to end the call quickly; "
            f"took {elapsed:.2f}s instead (fake response sleeps {_FAKE_SLOW_RESPONSE_SECONDS}s)"
        )

    def test_the_timeout_error_is_retryable_and_names_the_deadline(self) -> None:
        repo = _FakeRepo(_SlowRequester())

        with pytest.raises(GitHubRequestTimeoutError) as excinfo:
            _graphql_request(repo, "query ListIssues { viewer { login } }")

        assert excinfo.value.retryable is True
        assert excinfo.value.timeout_seconds == _TEST_DEADLINE_SECONDS
        assert str(_TEST_DEADLINE_SECONDS) in str(excinfo.value)
        assert "ListIssues" in str(excinfo.value)

    def test_a_prompt_response_within_the_deadline_is_unaffected(self) -> None:
        """Negative control: the deadline wrapper must not disturb the ordinary happy path."""
        repo = _FakeRepo(_FastRequester())

        data = _graphql_request(repo, "query ListIssues { viewer { login } }")

        assert data == {"viewer": {"login": "octocat"}}
