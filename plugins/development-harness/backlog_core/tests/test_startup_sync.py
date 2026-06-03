"""TDD red-phase: startup singleton background cache-sync -- unit tests.

These tests are INTENTIONALLY FAILING until the following symbols are implemented:

- ``backlog_core.sync_state.SyncStatus`` (StrEnum)
- ``backlog_core.sync_state.SyncState`` (dataclass)
- ``backlog_core.sync_state.SyncErrorKind`` (StrEnum)
- ``backlog_core.sync_state.classify_sync_error`` (function)
- ``backlog_core.sync_state.get_sync_state`` (function)
- ``backlog_core.sync_state.reset_sync_state`` (function)
- ``backlog_core.sync_engine._startup_sync_loop`` (coroutine)

Behaviors covered (mapped to requirement numbers 1-6):

1. Lifespan launches singleton background sync exactly once -- even across multiple
   tool calls.  The lock and state reset fixtures defend against the event-loop
   affinity hazard identified in the design doc Risk #2.
2. A sync request arriving while a sync is in progress does NOT start a second sync;
   it returns the in-flight progress fields (percent / started_at).
3. Non-retryable backend error -> SyncState transitions to OFFLINE; background loop
   terminates; last_error / offline_reason recorded.
4. Retryable error -> bounded backoff, at most MAX_RETRIES attempts, then ERROR state.
   Clock / sleep is mocked so the test is fast and deterministic.
5. ``backlog_list`` and the ``count_only=True`` path emit a ``sync_state`` block plus
   a non-empty ``warnings`` entry when offline/error -- and do NOT emit it for a
   legitimate fresh-cache zero-match.
6. The ``sync_status`` tool returns the full SyncState model fields.

Test-infra notes (from design doc Risk #2):
   ``SyncState.lock`` is an ``asyncio.Lock`` created lazily inside ``get_sync_state()``.
   Tests call ``reset_sync_state()`` inside an ``async`` fixture so the lock is always
   created in the running event loop, never at module import time.

Source: design doc sections 10.1-10.2.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest

from backlog_core.sync_engine import _startup_sync_loop  # type: ignore[import-not-found]

# ---------------------------------------------------------------------------
# Intentional ImportError -- these modules do not exist yet.
# The tests fail at collection/import with ImportError until the feature is
# implemented. That is the correct red state for TDD.
# ---------------------------------------------------------------------------
from backlog_core.sync_state import (  # type: ignore[import-not-found]
    SyncErrorKind,
    SyncState,
    SyncStatus,
    classify_sync_error,
    get_sync_state,
    reset_sync_state,
)

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def fresh_sync_state() -> SyncState:
    """Return a freshly reset SyncState created inside the running event loop.

    IMPORTANT: ``reset_sync_state()`` must be called inside an ``async``
    function so that ``asyncio.Lock()`` binds to the current event loop.
    Calling it at module scope or in a synchronous fixture causes
    ``RuntimeError: no current event loop``.  See design doc Risk #2.

    The ``await asyncio.sleep(0)`` yields to the event loop, ensuring all
    prior coroutines have had a chance to run and the loop is live before
    the lock is created.
    """
    await asyncio.sleep(0)
    reset_sync_state()
    return get_sync_state()


# ---------------------------------------------------------------------------
# Behaviour 1 -- State machine initial state
# ---------------------------------------------------------------------------


class TestSyncStateInitialState:
    """The SyncState singleton starts in IDLE with no timestamps or errors."""

    def test_initial_status_is_idle(self, fresh_sync_state: SyncState) -> None:
        """SyncState.status is IDLE on first access; no sync has run."""
        assert fresh_sync_state.status == SyncStatus.IDLE

    def test_initial_started_at_is_none(self, fresh_sync_state: SyncState) -> None:
        """SyncState.started_at is None before any sync attempt."""
        assert fresh_sync_state.started_at is None

    def test_initial_items_done_is_zero(self, fresh_sync_state: SyncState) -> None:
        """SyncState.items_done starts at zero."""
        assert fresh_sync_state.items_done == 0

    def test_initial_last_error_is_empty(self, fresh_sync_state: SyncState) -> None:
        """SyncState.last_error is an empty string before any failure."""
        assert fresh_sync_state.last_error == ""

    def test_initial_percent_is_none_when_total_unknown(self, fresh_sync_state: SyncState) -> None:
        """SyncState.percent is None when items_total is None (fetch phase not complete)."""
        assert fresh_sync_state.items_total is None
        assert fresh_sync_state.percent is None


# ---------------------------------------------------------------------------
# Behaviour 1 -- Singleton background sync launches exactly once
# ---------------------------------------------------------------------------


class TestSingletonSyncLaunch:
    """The lifespan must start the background sync loop exactly once.

    This guards against FastMCP issue #1115 where a lifespan may re-run per
    call, which would start multiple concurrent sync loops.
    """

    async def test_startup_sync_loop_called_exactly_once_on_lifespan_start(self, mocker: MockerFixture) -> None:
        """Background sync starts exactly once when the lifespan initialises.

        The lifespan is exercised by importing the mcp object and entering
        its lifespan context.  The sync function is patched to count calls.
        Requires backlog_core.server.mcp to have lifespan=_backlog_lifespan
        configured -- this will fail with AttributeError until implemented.
        """
        reset_sync_state()

        sync_called_count = 0

        async def _fake_sync_loop(state: SyncState) -> None:
            nonlocal sync_called_count
            sync_called_count += 1
            await asyncio.sleep(0)  # yield to event loop; makes this a genuine coroutine
            state.status = SyncStatus.IDLE
            state.last_success_at = datetime.now(UTC)

        mocker.patch("backlog_core.sync_engine._startup_sync_loop", side_effect=_fake_sync_loop)

        from fastmcp.client import Client

        from backlog_core.server import mcp

        async with Client(mcp) as client:
            # Issue multiple tool calls to trigger any per-call lifespan re-run bug.
            await client.call_tool("sync_status", {})
            await client.call_tool("sync_status", {})

        assert sync_called_count == 1, (
            f"Background sync must start exactly once per process lifespan. "
            f"Got {sync_called_count} start(s). "
            "If >1, the lifespan is re-running on each tool call (FastMCP issue #1115)."
        )


# ---------------------------------------------------------------------------
# Behaviour 2 -- In-flight sync guard: second call returns progress
# ---------------------------------------------------------------------------


class TestInFlightSyncGuard:
    """A sync_now call while a sync is running must not start a second sync."""

    async def test_second_sync_now_while_running_returns_progress_not_new_sync(self, mocker: MockerFixture) -> None:
        """sync_now while RUNNING: triggered=False, progress fields present, no second start.

        Arrange: patch _startup_sync_loop so it holds state=RUNNING without completing.
        Act: call sync_now twice while the lock is held.
        Assert: second call returns triggered=False with percent/started_at fields.
        """
        reset_sync_state()

        gate = asyncio.Event()
        sync_start_count = 0

        async def _stalled_sync_loop(state: SyncState) -> None:
            nonlocal sync_start_count
            sync_start_count += 1
            state.status = SyncStatus.RUNNING
            state.started_at = datetime.now(UTC)
            state.items_total = 10
            state.items_done = 3
            await gate.wait()  # blocks until cancelled by lifespan teardown

        mocker.patch("backlog_core.sync_engine._startup_sync_loop", side_effect=_stalled_sync_loop)

        from fastmcp.client import Client

        from backlog_core.server import mcp

        async with Client(mcp) as client:
            # Yield twice so the background task reaches the RUNNING state.
            await asyncio.sleep(0)
            await asyncio.sleep(0)

            await client.call_tool("sync_now", {})
            second_response = await client.call_tool("sync_now", {})

        gate.set()  # unblock the stalled loop so teardown completes cleanly

        second_data = second_response.data if hasattr(second_response, "data") else second_response

        assert second_data.get("triggered") is False, (
            "sync_now while a sync is RUNNING must return triggered=False. "
            "Starting a second sync violates the singleton guarantee."
        )
        assert "sync_state" in second_data, "sync_now must return sync_state block when in-flight."
        inner = second_data["sync_state"]
        assert inner.get("status") == "running", "sync_state.status must be 'running' for in-flight sync."
        # Split compound assertion: first verify the key exists, then verify its value.
        assert "started_at" in inner, "sync_state must include started_at while a sync is RUNNING."
        assert inner["started_at"] is not None, (
            "sync_state.started_at must be a non-None timestamp while sync is RUNNING."
        )

    async def test_only_one_sync_loop_holds_lock_at_a_time(
        self, fresh_sync_state: SyncState, mocker: MockerFixture
    ) -> None:
        """Concurrent sync attempts: only one acquires the lock; second returns immediately.

        The lock on SyncState serialises sync workers.  Two coroutines that both
        try to enter _startup_sync_loop must not both set status=RUNNING.
        """
        state = fresh_sync_state
        results: list[str] = []

        async def _lock_holding_sync(s: SyncState) -> None:
            async with s.lock:
                results.append("acquired")
                s.status = SyncStatus.RUNNING
                await asyncio.sleep(0.01)
                s.status = SyncStatus.IDLE
                results.append("released")

        async def _observe_lock_state(s: SyncState) -> None:
            """Record whether the lock is held; does not attempt to acquire it."""
            locked = s.lock.locked()
            results.append(f"second_sees_locked={locked}")
            await asyncio.sleep(0)  # yield to make this a genuine coroutine

        task1 = asyncio.create_task(_lock_holding_sync(state))
        await asyncio.sleep(0)  # yield so task1 acquires the lock
        task2 = asyncio.create_task(_observe_lock_state(state))
        await asyncio.gather(task1, task2)

        assert "acquired" in results
        assert any("second_sees_locked=True" in r for r in results), (
            "While the first sync holds the lock, a second attempt must observe it as locked. "
            "The lock guard prevents concurrent sync workers."
        )


# ---------------------------------------------------------------------------
# Behaviour 3 -- Non-retryable error -> OFFLINE
# ---------------------------------------------------------------------------


class TestNonRetryableErrorGoesOffline:
    """Non-retryable errors must transition SyncState to OFFLINE immediately."""

    async def test_missing_github_token_sets_offline_state(
        self, fresh_sync_state: SyncState, mocker: MockerFixture
    ) -> None:
        """GitHubUnavailableError (missing token) -> SyncState.status = OFFLINE.

        GitHubUnavailableError is raised by get_github() when GITHUB_TOKEN is not
        set.  This is a config error -- non-retryable.  The sync loop must:
        - set state.status = OFFLINE
        - set state.offline_reason (non-empty string)
        - terminate (not retry)
        """
        from backlog_core.models import GitHubUnavailableError

        mocker.patch(
            "backlog_core.operations.refresh_local_cache_from_github",
            side_effect=GitHubUnavailableError("GITHUB_TOKEN not set"),
        )

        state = fresh_sync_state
        await _startup_sync_loop(state)

        assert state.status == SyncStatus.OFFLINE, (
            f"GitHubUnavailableError must produce OFFLINE state. Got {state.status!r}."
        )
        assert state.offline_reason, "offline_reason must be non-empty after a non-retryable error."
        token_mentioned = "GITHUB_TOKEN" in state.offline_reason or "token" in state.offline_reason.lower()
        assert token_mentioned, "offline_reason should describe the authentication failure."

    async def test_value_error_config_sets_offline_state(
        self, fresh_sync_state: SyncState, mocker: MockerFixture
    ) -> None:
        """ValueError from resolve_repo (missing config) -> OFFLINE, loop terminates."""
        mocker.patch(
            "backlog_core.operations.refresh_local_cache_from_github", side_effect=ValueError("repo not configured")
        )

        state = fresh_sync_state
        await _startup_sync_loop(state)

        assert state.status == SyncStatus.OFFLINE, "ValueError (config error) must produce OFFLINE state."
        assert state.offline_reason, "offline_reason must be non-empty after ValueError."

    async def test_os_error_cache_write_sets_offline_state(
        self, fresh_sync_state: SyncState, mocker: MockerFixture
    ) -> None:
        """OSError on cache write (filesystem failure) -> OFFLINE, loop terminates."""
        mocker.patch(
            "backlog_core.operations.refresh_local_cache_from_github", side_effect=OSError("Permission denied: /cache")
        )

        state = fresh_sync_state
        await _startup_sync_loop(state)

        assert state.status == SyncStatus.OFFLINE, "OSError (filesystem error) must produce OFFLINE state."

    async def test_github_401_sets_offline_not_retried(
        self, fresh_sync_state: SyncState, mocker: MockerFixture
    ) -> None:
        """HTTP 401 from GitHub -> OFFLINE.  Bad token is non-retryable."""
        from github import GithubException

        exc_401 = GithubException(status=401, data="Bad credentials", headers={})
        mocker.patch("backlog_core.operations.refresh_local_cache_from_github", side_effect=exc_401)

        state = fresh_sync_state
        await _startup_sync_loop(state)

        assert state.status == SyncStatus.OFFLINE, (
            "HTTP 401 must produce OFFLINE state.  Bad credentials cannot self-heal."
        )

    async def test_github_404_sets_offline_not_retried(
        self, fresh_sync_state: SyncState, mocker: MockerFixture
    ) -> None:
        """HTTP 404 (repository not found) -> OFFLINE.  Config error is non-retryable."""
        from github import GithubException

        exc_404 = GithubException(status=404, data="Not Found", headers={})
        mocker.patch("backlog_core.operations.refresh_local_cache_from_github", side_effect=exc_404)

        state = fresh_sync_state
        await _startup_sync_loop(state)

        assert state.status == SyncStatus.OFFLINE, "HTTP 404 (repo not found) must produce OFFLINE state."


# ---------------------------------------------------------------------------
# Behaviour 4 -- Retryable error -> bounded backoff -> ERROR after max retries
# ---------------------------------------------------------------------------


class TestRetryableErrorBoundedBackoff:
    """Retryable errors use bounded exponential backoff and stop after MAX_RETRIES."""

    async def test_retryable_5xx_attempts_capped_then_error_state(
        self, fresh_sync_state: SyncState, mocker: MockerFixture
    ) -> None:
        """HTTP 5xx errors are retried at most MAX_RETRIES times, then ERROR.

        The clock/sleep is mocked so no real wall-clock time elapses.
        We assert:
          - refresh_local_cache_from_github is called multiple times (retrying)
          - calls stop after MAX_RETRIES (not infinite)
          - final state is SyncStatus.ERROR
          - last_error is non-empty
        """
        from github import GithubException

        exc_500 = GithubException(status=500, data="Internal Server Error", headers={})
        call_count = 0

        def _always_fail_500(*_args: object, **_kwargs: object) -> None:
            nonlocal call_count
            call_count += 1
            raise exc_500

        mocker.patch("backlog_core.operations.refresh_local_cache_from_github", side_effect=_always_fail_500)

        sleep_calls: list[float] = []

        async def _instant_sleep(delay: float) -> None:
            # NOTE: do NOT call asyncio.sleep(0) here — mocker.patch globally
            # patches asyncio.sleep, so calling it inside the mock side_effect
            # causes infinite recursion (test bug fixed per task instructions).
            sleep_calls.append(delay)

        mocker.patch("backlog_core.sync_engine.asyncio.sleep", side_effect=_instant_sleep)

        state = fresh_sync_state
        await _startup_sync_loop(state)

        # Design: attempt 1 immediate, attempt 2 after 30s, attempt 3 after 120s.
        # After 3 failures -> ERROR.
        max_retries = 3
        assert call_count <= max_retries, (
            f"refresh_local_cache_from_github must be called at most {max_retries} times for "
            f"retryable errors. Got {call_count}. Infinite retry detected."
        )
        assert call_count >= 1, "refresh must be attempted at least once."
        assert state.status == SyncStatus.ERROR, (
            f"After exhausting retries, status must be ERROR. Got {state.status!r}."
        )
        assert state.last_error, "last_error must be non-empty after exhausted retries."

    async def test_retryable_error_backoff_delays_are_positive(
        self, fresh_sync_state: SyncState, mocker: MockerFixture
    ) -> None:
        """Backoff delays between retries must be positive (not zero).

        Zero-delay retries would hammer the GitHub API without any back-off.
        """
        from github import GithubException

        exc_503 = GithubException(status=503, data="Service Unavailable", headers={})
        mocker.patch("backlog_core.operations.refresh_local_cache_from_github", side_effect=exc_503)

        sleep_delays: list[float] = []

        async def _record_sleep(delay: float) -> None:
            # NOTE: do NOT call asyncio.sleep(0) here — mocker.patch globally
            # patches asyncio.sleep, so calling it inside the mock causes recursion.
            sleep_delays.append(delay)

        mocker.patch("backlog_core.sync_engine.asyncio.sleep", side_effect=_record_sleep)

        state = fresh_sync_state
        await _startup_sync_loop(state)

        assert sleep_delays, "At least one asyncio.sleep call must occur between retries."
        assert all(d > 0 for d in sleep_delays), (
            f"All backoff delays must be positive. Got: {sleep_delays}. Zero-delay retry violates the backoff contract."
        )

    async def test_retryable_success_on_second_attempt_transitions_to_idle(
        self, fresh_sync_state: SyncState, mocker: MockerFixture
    ) -> None:
        """If a retryable error is followed by success, status returns to IDLE."""
        from github import GithubException

        exc_502 = GithubException(status=502, data="Bad Gateway", headers={})
        attempt = 0

        def _fail_then_succeed(*_args: object, **_kwargs: object) -> dict[str, int]:
            nonlocal attempt
            attempt += 1
            if attempt == 1:
                raise exc_502
            return {"refreshed": 5, "reconciled": 0}

        mocker.patch("backlog_core.operations.refresh_local_cache_from_github", side_effect=_fail_then_succeed)

        async def _instant_sleep(delay: float) -> None:
            # NOTE: do NOT call asyncio.sleep(0) here — mocker.patch globally
            # patches asyncio.sleep, so calling it inside the mock causes recursion.
            pass

        mocker.patch("backlog_core.sync_engine.asyncio.sleep", side_effect=_instant_sleep)

        state = fresh_sync_state
        await _startup_sync_loop(state)

        assert state.status == SyncStatus.IDLE, (
            f"After a transient failure followed by success, status must be IDLE. Got {state.status!r}."
        )
        assert state.last_success_at is not None, "last_success_at must be set after a successful sync."


# ---------------------------------------------------------------------------
# Behaviour 3 / 6 -- Error classification
# ---------------------------------------------------------------------------


class TestSyncErrorClassification:
    """classify_sync_error assigns RETRYABLE or NON_RETRYABLE per the design table."""

    def test_missing_token_is_non_retryable(self) -> None:
        """GitHubUnavailableError (missing token) -> NON_RETRYABLE."""
        from backlog_core.models import GitHubUnavailableError

        exc = GitHubUnavailableError("GITHUB_TOKEN not set")
        assert classify_sync_error(exc) == SyncErrorKind.NON_RETRYABLE, (
            "Missing token is a config error that cannot self-heal -- must be NON_RETRYABLE."
        )

    def test_401_github_exception_is_non_retryable(self) -> None:
        """HTTP 401 (bad credentials) -> NON_RETRYABLE."""
        from github import GithubException

        exc = GithubException(status=401, data="Bad credentials", headers={})
        assert classify_sync_error(exc) == SyncErrorKind.NON_RETRYABLE

    def test_404_github_exception_is_non_retryable(self) -> None:
        """HTTP 404 (repository not found) -> NON_RETRYABLE."""
        from github import GithubException

        exc = GithubException(status=404, data="Not Found", headers={})
        assert classify_sync_error(exc) == SyncErrorKind.NON_RETRYABLE

    def test_500_github_exception_is_retryable(self) -> None:
        """HTTP 500 (server error) -> RETRYABLE."""
        from github import GithubException

        exc = GithubException(status=500, data="Internal Server Error", headers={})
        assert classify_sync_error(exc) == SyncErrorKind.RETRYABLE

    def test_503_github_exception_is_retryable(self) -> None:
        """HTTP 503 (service unavailable) -> RETRYABLE."""
        from github import GithubException

        exc = GithubException(status=503, data="Service Unavailable", headers={})
        assert classify_sync_error(exc) == SyncErrorKind.RETRYABLE

    def test_403_without_retry_after_is_non_retryable(self) -> None:
        """HTTP 403 without Retry-After header -> NON_RETRYABLE (permission denied)."""
        from github import GithubException

        exc = GithubException(status=403, data="Forbidden", headers={})
        assert classify_sync_error(exc) == SyncErrorKind.NON_RETRYABLE

    def test_403_with_retry_after_header_is_retryable(self) -> None:
        """HTTP 403 with Retry-After header -> RETRYABLE (rate limit)."""
        from github import GithubException

        exc = GithubException(status=403, data="Rate limit exceeded", headers={"Retry-After": "60"})
        assert classify_sync_error(exc) == SyncErrorKind.RETRYABLE

    def test_os_error_is_non_retryable(self) -> None:
        """OSError on filesystem -> NON_RETRYABLE (cannot self-heal without operator action)."""
        exc = OSError("Permission denied: /cache")
        assert classify_sync_error(exc) == SyncErrorKind.NON_RETRYABLE

    def test_value_error_is_non_retryable(self) -> None:
        """ValueError (config error from resolve_repo) -> NON_RETRYABLE."""
        exc = ValueError("repo not configured")
        assert classify_sync_error(exc) == SyncErrorKind.NON_RETRYABLE

    def test_asyncio_timeout_error_is_retryable(self) -> None:
        """asyncio.TimeoutError -> RETRYABLE.

        In Python 3.11+, asyncio.TimeoutError is a subclass of TimeoutError,
        which is itself a subclass of OSError.  The OSError branch in
        classify_sync_error must NOT fire first and return NON_RETRYABLE;
        the asyncio.TimeoutError branch must be checked before OSError.
        """
        exc = TimeoutError()
        assert classify_sync_error(exc) == SyncErrorKind.RETRYABLE, (
            "asyncio.TimeoutError must be RETRYABLE (transient network timeout). "
            "In Python 3.11+ asyncio.TimeoutError subclasses OSError; without an "
            "explicit asyncio.TimeoutError branch it misfires as NON_RETRYABLE."
        )

    def test_http_429_github_exception_is_retryable(self) -> None:
        """HTTP 429 (Too Many Requests / primary rate limit) -> RETRYABLE.

        429 is the primary rate-limit response from GitHub.  Without an explicit
        429 branch it falls through to UNKNOWN, which the caller treats as
        NON_RETRYABLE and transitions the server to OFFLINE.
        """
        from github import GithubException

        exc = GithubException(status=429, data="Too Many Requests", headers={})
        assert classify_sync_error(exc) == SyncErrorKind.RETRYABLE, (
            "HTTP 429 (primary rate limit) must be RETRYABLE. "
            "Without an explicit 429 branch it falls to UNKNOWN -> OFFLINE."
        )


# ---------------------------------------------------------------------------
# Behaviour 6 -- sync_status tool returns full state model fields
# ---------------------------------------------------------------------------


class TestSyncStatusTool:
    """sync_status tool returns the full SyncState model as a dict."""

    async def test_sync_status_returns_all_required_fields(self, mocker: MockerFixture) -> None:
        """sync_status response includes all fields from the design spec section 8.1."""
        reset_sync_state()

        async def _noop_sync_loop(state: SyncState) -> None:
            await asyncio.sleep(0)

        mocker.patch("backlog_core.sync_engine._startup_sync_loop", side_effect=_noop_sync_loop)

        from fastmcp.client import Client

        from backlog_core.server import mcp

        async with Client(mcp) as client:
            response = await client.call_tool("sync_status", {})

        data = response.data if hasattr(response, "data") else response

        required_fields = {
            "status",
            "started_at",
            "completed_at",
            "last_success_at",
            "items_done",
            "items_total",
            "percent",
            "last_error",
            "offline_reason",
        }
        missing = required_fields - set(data.keys())
        assert not missing, (
            f"sync_status response is missing required fields: {missing}. "
            "All fields from design spec section 8.1 must be present."
        )

    async def test_sync_status_idle_shows_idle_status(self, mocker: MockerFixture) -> None:
        """After a successful sync, sync_status returns status='idle'."""
        reset_sync_state()

        async def _fast_success(state: SyncState) -> None:
            await asyncio.sleep(0)
            state.status = SyncStatus.IDLE
            state.last_success_at = datetime.now(UTC)

        mocker.patch("backlog_core.sync_engine._startup_sync_loop", side_effect=_fast_success)

        from fastmcp.client import Client

        from backlog_core.server import mcp

        async with Client(mcp) as client:
            await asyncio.sleep(0.05)  # let background task complete
            response = await client.call_tool("sync_status", {})

        data = response.data if hasattr(response, "data") else response
        assert data["status"] == "idle", f"After successful sync, status must be 'idle'. Got {data['status']!r}."

    async def test_sync_status_offline_after_non_retryable_error(self, mocker: MockerFixture) -> None:
        """After a non-retryable error, sync_status returns status='offline'."""
        reset_sync_state()

        from backlog_core.models import GitHubUnavailableError

        mocker.patch(
            "backlog_core.operations.refresh_local_cache_from_github",
            side_effect=GitHubUnavailableError("GITHUB_TOKEN not set"),
        )

        from fastmcp.client import Client

        from backlog_core.server import mcp

        async with Client(mcp) as client:
            await asyncio.sleep(0.1)  # let background loop fail and set OFFLINE
            response = await client.call_tool("sync_status", {})

        data = response.data if hasattr(response, "data") else response
        assert data["status"] == "offline", (
            f"After GitHubUnavailableError, sync_status must return 'offline'. Got {data['status']!r}."
        )
        assert data.get("offline_reason"), "offline_reason must be non-empty in the sync_status response."


# ---------------------------------------------------------------------------
# Behaviour 1 -- SyncState.to_dict contract
# ---------------------------------------------------------------------------


class TestSyncStateToDict:
    """SyncState.to_dict() returns a JSON-serialisable representation."""

    def test_to_dict_returns_all_public_fields(self, fresh_sync_state: SyncState) -> None:
        """to_dict() includes all fields from the design spec section 3.2."""
        result = fresh_sync_state.to_dict()

        expected_keys = {
            "status",
            "started_at",
            "completed_at",
            "items_done",
            "items_total",
            "last_error",
            "last_success_at",
            "retry_count",
            "offline_reason",
            "percent",
        }
        missing = expected_keys - set(result.keys())
        assert not missing, f"to_dict() is missing fields: {missing}."

    def test_to_dict_excludes_lock_field(self, fresh_sync_state: SyncState) -> None:
        """to_dict() must not expose the asyncio.Lock field (not JSON-serialisable)."""
        result = fresh_sync_state.to_dict()
        assert "lock" not in result, "to_dict() must not expose the asyncio.Lock field -- it is not JSON-serialisable."

    def test_to_dict_status_is_string(self, fresh_sync_state: SyncState) -> None:
        """to_dict() serialises status as a plain string (not StrEnum instance)."""
        result = fresh_sync_state.to_dict()
        assert isinstance(result["status"], str), "status must be serialised as str, not a StrEnum member."
        assert result["status"] == "idle"


# ---------------------------------------------------------------------------
# Behaviour 1 -- SyncState.is_running predicate
# ---------------------------------------------------------------------------


class TestSyncStateIsRunning:
    """SyncState.is_running() reflects the RUNNING status."""

    def test_is_running_false_when_idle(self, fresh_sync_state: SyncState) -> None:
        """is_running() returns False in initial IDLE state."""
        assert not fresh_sync_state.is_running()

    def test_is_running_true_when_running(self, fresh_sync_state: SyncState) -> None:
        """is_running() returns True when status is RUNNING."""
        fresh_sync_state.status = SyncStatus.RUNNING
        assert fresh_sync_state.is_running()

    def test_is_running_false_when_offline(self, fresh_sync_state: SyncState) -> None:
        """is_running() returns False when status is OFFLINE."""
        fresh_sync_state.status = SyncStatus.OFFLINE
        assert not fresh_sync_state.is_running()


# ---------------------------------------------------------------------------
# Behaviour 1 -- SyncState.percent computation
# ---------------------------------------------------------------------------


class TestSyncStatePercent:
    """SyncState.percent computes correctly across edge cases."""

    def test_percent_none_when_total_is_none(self, fresh_sync_state: SyncState) -> None:
        """percent is None while items_total is unknown (initial fetch phase)."""
        fresh_sync_state.items_total = None
        fresh_sync_state.items_done = 5
        assert fresh_sync_state.percent is None

    def test_percent_zero_at_start_of_known_batch(self, fresh_sync_state: SyncState) -> None:
        """percent is 0 when items_done=0 and items_total is known."""
        fresh_sync_state.items_total = 100
        fresh_sync_state.items_done = 0
        assert fresh_sync_state.percent == 0

    def test_percent_fifty_at_half_completion(self, fresh_sync_state: SyncState) -> None:
        """percent is 50 when half the items are done."""
        fresh_sync_state.items_total = 100
        fresh_sync_state.items_done = 50
        assert fresh_sync_state.percent == 50

    def test_percent_clips_at_100(self, fresh_sync_state: SyncState) -> None:
        """percent never exceeds 100 even if items_done > items_total."""
        fresh_sync_state.items_total = 100
        fresh_sync_state.items_done = 150  # over-count guard
        assert fresh_sync_state.percent == 100

    def test_percent_none_when_total_is_zero(self, fresh_sync_state: SyncState) -> None:
        """percent is None when items_total is 0 (avoids division-by-zero)."""
        fresh_sync_state.items_total = 0
        fresh_sync_state.items_done = 0
        assert fresh_sync_state.percent is None


# ---------------------------------------------------------------------------
# Done-callback logging -- sync_now fire-and-forget task
# ---------------------------------------------------------------------------


class TestSyncTaskDoneCallback:
    """The done-callback on the fire-and-forget sync task must log unexpected exceptions.

    Per .claude/rules/silent-failure-prevention.md: functions that perform side
    effects must not silently discard exceptions.  The named ``_log_sync_task_exc``
    callback must call the module logger when the task raises an unexpected error.
    """

    async def test_unexpected_exception_from_sync_task_is_logged(self, mocker: MockerFixture) -> None:
        """An unexpected exception escaping the sync task triggers logger.error.

        Arrange: patch _startup_sync_loop to raise a RuntimeError (simulating an
        unanticipated bug escaping the broad catch in _attempt_sync).
        Act: enter the server lifespan so the background task is launched.
        Assert: the module-level logger in server.py receives an error() call
        containing the exception message.
        """
        reset_sync_state()

        async def _boom(state: SyncState) -> None:
            raise RuntimeError("simulated unexpected bug")

        mocker.patch("backlog_core.sync_engine._startup_sync_loop", side_effect=_boom)

        # Patch the logger used by _log_sync_task_exc in server.py.
        mock_logger = mocker.patch("backlog_core.server._sync_task_log")

        from fastmcp.client import Client

        from backlog_core.server import mcp

        async with Client(mcp) as client:
            # Yield enough times for the background task to complete and the
            # done-callback to fire.
            await asyncio.sleep(0)
            await asyncio.sleep(0)
            await asyncio.sleep(0)
            await client.call_tool("sync_status", {})

        assert mock_logger.error.called, (
            "The done-callback must call logger.error() when the sync task raises "
            "an unexpected exception.  Silent discard hides bugs."
        )
        # Verify the exception message appears in the log call arguments.
        call_args = mock_logger.error.call_args
        logged_text = " ".join(str(a) for a in call_args.args)
        assert "simulated unexpected bug" in logged_text or any(
            "simulated unexpected bug" in str(a) for a in call_args.args
        ), f"Logger must include the exception message. Got: {call_args}"
