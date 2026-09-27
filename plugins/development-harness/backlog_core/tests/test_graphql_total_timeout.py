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

import logging
import math
import threading
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import pytest

from backlog_core import gh_client
from backlog_core.gh_client import _graphql_request, _update_issues_graphql_batch
from backlog_core.github_client import GRAPHQL_TOTAL_TIMEOUT_DEFAULT, graphql_total_timeout_seconds
from backlog_core.models import BackendUnavailableError, GitHubMutationOutcomeUnknownError, GitHubRequestTimeoutError
from backlog_core.sync_state import SyncErrorKind, classify_sync_error

if TYPE_CHECKING:
    from collections.abc import Iterator

#: Deliberately far longer than any deadline these tests configure -- if the deadline mechanism
#: is missing or broken, the test itself would hang for this long instead of failing fast.
_FAKE_SLOW_RESPONSE_SECONDS = 5.0

#: Small enough that a correct deadline resolves near-instantly, large enough to be stable in CI.
_TEST_DEADLINE_SECONDS = 0.2

#: Generous margin above _TEST_DEADLINE_SECONDS for scheduling jitter -- must stay far below
#: _FAKE_SLOW_RESPONSE_SECONDS or a broken deadline would pass by accident.
_MAX_ACCEPTABLE_ELAPSED_SECONDS = 2.0

#: Slow fakes block on this rather than sleeping, so each test's teardown can release the workers
#: its timeouts abandoned. Left running, they would count against the process-wide cap on
#: abandoned workers and refuse requests in whichever test ran next.
_RELEASE = threading.Event()


class _SlowRequester:
    """Stands in for PyGithub's requester; blocks past any timeout under test."""

    def graphql_query(self, query: str, variables: dict[str, object]) -> tuple[dict, dict]:
        """Sleep well past the configured deadline, then answer as GitHub normally would."""
        _RELEASE.wait(_FAKE_SLOW_RESPONSE_SECONDS)
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


def _graphql_workers() -> list[threading.Thread]:
    return [t for t in threading.enumerate() if t.name == "gh-graphql-request"]


@pytest.fixture(autouse=True)
def _release_abandoned_workers() -> Iterator[None]:
    """Let every worker a test abandoned finish before the next test starts."""
    _RELEASE.clear()
    yield
    _RELEASE.set()
    for worker in _graphql_workers():
        worker.join(_FAKE_SLOW_RESPONSE_SECONDS)


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


@dataclass
class _RecordingSlowRequester:
    """Blocks past the deadline on every call and records each query it was sent."""

    queries: list[str] = field(default_factory=list)

    def graphql_query(self, query: str, variables: dict[str, object]) -> tuple[dict, dict]:
        """Record the query, then sleep well past the configured deadline."""
        self.queries.append(query)
        _RELEASE.wait(_FAKE_SLOW_RESPONSE_SECONDS)
        return {}, {"data": {}}


class TestATimedOutMutationIsNeverReportedRetryable:
    """The abandoned worker thread may still complete the mutation, so a retry could duplicate it."""

    def test_a_timed_out_mutation_reports_an_unknown_outcome_and_is_not_retryable(self) -> None:
        repo = _FakeRepo(_SlowRequester())

        with pytest.raises(GitHubMutationOutcomeUnknownError) as excinfo:
            _graphql_request(repo, "mutation AddComment($subjectId: ID!) { addComment { clientMutationId } }")

        assert excinfo.value.retryable is False
        assert not isinstance(excinfo.value, GitHubRequestTimeoutError)
        assert excinfo.value.timeout_seconds == _TEST_DEADLINE_SECONDS
        message = str(excinfo.value)
        assert "AddComment" in message
        assert "unknown" in message
        assert "before retrying" in message
        assert classify_sync_error(excinfo.value) is SyncErrorKind.NON_RETRYABLE

    def test_an_unrecognised_operation_is_treated_as_a_mutation(self) -> None:
        """Fail safe: only a document that is plainly a query stays retryable on timeout."""
        repo = _FakeRepo(_SlowRequester())

        with pytest.raises(GitHubMutationOutcomeUnknownError):
            _graphql_request(repo, "subscription Watch { viewer { login } }")

    def test_an_anonymous_shorthand_query_stays_retryable(self) -> None:
        repo = _FakeRepo(_SlowRequester())

        with pytest.raises(GitHubRequestTimeoutError) as excinfo:
            _graphql_request(repo, "{ viewer { login } }")

        assert excinfo.value.retryable is True

    def test_a_timed_out_batch_update_does_not_fall_back_to_per_item_mutations(self) -> None:
        requester = _RecordingSlowRequester()

        with pytest.raises(GitHubMutationOutcomeUnknownError):
            _update_issues_graphql_batch(_FakeRepo(requester), [("I_1", "body one"), ("I_2", "body two")])

        assert len(requester.queries) == 1, f"expected only the batch mutation, got {requester.queries}"
        assert requester.queries[0].startswith("mutation BatchUpdate")


class TestTotalTimeoutEnvValueIsValidated:
    """``thread.join`` raises on nan/inf, and zero/negative values time out every request at once."""

    @pytest.mark.parametrize("raw", ["nan", "inf", "-inf", "0", "-5", "not-a-number"])
    def test_an_unusable_value_falls_back_to_the_default_with_a_warning(
        self, raw: str, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        monkeypatch.setenv("DH_GRAPHQL_TOTAL_TIMEOUT_SECONDS", raw)

        with caplog.at_level(logging.WARNING, logger="backlog_core.github_client"):
            value = graphql_total_timeout_seconds()

        assert value == GRAPHQL_TOTAL_TIMEOUT_DEFAULT
        assert any(
            "DH_GRAPHQL_TOTAL_TIMEOUT_SECONDS" in r.getMessage() and raw in r.getMessage() for r in caplog.records
        )

    def test_a_finite_positive_value_is_used_without_a_warning(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        monkeypatch.setenv("DH_GRAPHQL_TOTAL_TIMEOUT_SECONDS", "12.5")

        with caplog.at_level(logging.WARNING, logger="backlog_core.github_client"):
            value = graphql_total_timeout_seconds()

        assert math.isclose(value, 12.5)
        assert not caplog.records


class TestAbandonedWorkersAreBounded:
    """A request that never returns leaves its worker alive; the count of those must stay bounded."""

    @pytest.fixture(autouse=True)
    def _cap_of_two(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(gh_client, "_MAX_LIVE_GRAPHQL_WORKERS", 2)

    def test_a_request_past_the_cap_is_refused_without_starting_a_worker(self) -> None:
        requester = _RecordingSlowRequester()
        repo = _FakeRepo(requester)
        for _ in range(2):
            with pytest.raises(GitHubRequestTimeoutError):
                _graphql_request(repo, "query ListIssues { viewer { login } }")

        with pytest.raises(BackendUnavailableError) as excinfo:
            _graphql_request(repo, "query ListIssues { viewer { login } }")

        assert not isinstance(excinfo.value, GitHubRequestTimeoutError)
        assert excinfo.value.retryable is True
        assert "still running" in str(excinfo.value)
        assert len(requester.queries) == 2, "the refused request must not reach the transport"
        assert len(_graphql_workers()) == 2

    def test_a_worker_that_finishes_leaves_the_count(self) -> None:
        repo = _FakeRepo(_RecordingSlowRequester())
        for _ in range(2):
            with pytest.raises(GitHubRequestTimeoutError):
                _graphql_request(repo, "query ListIssues { viewer { login } }")

        _RELEASE.set()
        for worker in _graphql_workers():
            worker.join(_FAKE_SLOW_RESPONSE_SECONDS)

        assert _graphql_request(_FakeRepo(_FastRequester()), "query ListIssues { viewer { login } }") == {
            "viewer": {"login": "octocat"}
        }


@dataclass
class _ConcurrencyRecordingRequester:
    """Blocks like a stalled transport and records the most calls it ever held at once."""

    lock: threading.Lock = field(default_factory=threading.Lock)
    active: int = 0
    peak: int = 0

    def graphql_query(self, query: str, variables: dict[str, object]) -> tuple[dict, dict]:
        """Count this call in, block past the deadline, count it out."""
        with self.lock:
            self.active += 1
            self.peak = max(self.peak, self.active)
        _RELEASE.wait(_FAKE_SLOW_RESPONSE_SECONDS)
        with self.lock:
            self.active -= 1
        return {}, {"data": {}}


class TestWorkerSlotsAreReservedBeforeStart:
    """Concurrent callers must not all pass the cap check before any of them registers."""

    @pytest.fixture(autouse=True)
    def _cap_of_two(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(gh_client, "_MAX_LIVE_GRAPHQL_WORKERS", 2)

    def test_concurrent_callers_cannot_overshoot_the_cap(self) -> None:
        requester = _ConcurrencyRecordingRequester()
        repo = _FakeRepo(requester)
        callers = 6
        start = threading.Barrier(callers)
        outcomes: list[type[BaseException]] = []
        outcomes_lock = threading.Lock()

        def _call() -> None:
            start.wait()
            try:
                _graphql_request(repo, "query ListIssues { viewer { login } }")
            except BackendUnavailableError as exc:
                with outcomes_lock:
                    outcomes.append(type(exc))

        threads = [threading.Thread(target=_call) for _ in range(callers)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(_FAKE_SLOW_RESPONSE_SECONDS)

        assert requester.peak <= 2, f"{requester.peak} requests reached the transport at once; the cap is 2"
        assert outcomes.count(GitHubRequestTimeoutError) == 2
        assert outcomes.count(BackendUnavailableError) == callers - 2

    def test_a_slot_is_released_when_the_thread_fails_to_start(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(gh_client, "_MAX_LIVE_GRAPHQL_WORKERS", 1)
        real_start = threading.Thread.start
        failures = iter([RuntimeError("can't start new thread")])

        def _start_once_failing(thread: threading.Thread) -> None:
            if thread.name == "gh-graphql-request" and (failure := next(failures, None)) is not None:
                raise failure
            real_start(thread)

        monkeypatch.setattr(threading.Thread, "start", _start_once_failing)
        repo = _FakeRepo(_FastRequester())
        with pytest.raises(RuntimeError):
            _graphql_request(repo, "query ListIssues { viewer { login } }")

        assert _graphql_request(repo, "query ListIssues { viewer { login } }") == {"viewer": {"login": "octocat"}}
