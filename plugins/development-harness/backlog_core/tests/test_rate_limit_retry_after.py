"""GitHub's ``Retry-After`` hint must reach both consumers of a rate-limit failure.

``GitHubRateLimitedError.retry_after`` carries the seconds GitHub says to wait. The startup sync
loop's fixed 30s/120s schedule can spend every attempt before GitHub allows another request, and
an MCP caller that only sees ``retryable: true`` cannot tell when a retry would be allowed. These
tests confirm the sync loop waits at least that long and the MCP error response carries the hint,
including when a backend wrapped the rate-limit error in a plain ``BackendUnavailableError``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from fastmcp import Client

from backlog_core.models import BackendUnavailableError, GitHubRateLimitedError
from backlog_core.server import mcp
from backlog_core.sync_engine import _startup_sync_loop
from backlog_core.sync_state import SyncState, get_sync_state, reset_sync_state

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

_RETRY_AFTER_SECONDS = 600.0


def _wrapped_rate_limit() -> BackendUnavailableError:
    """Build the shape ``GitHubBackend.fetch_snapshot`` produces: a plain wrapper over the cause."""
    cause = GitHubRateLimitedError("rate limited", retry_after=_RETRY_AFTER_SECONDS)
    wrapped = BackendUnavailableError(f"GitHub snapshot unavailable: {cause}", retryable=True)
    wrapped.__cause__ = cause  # what ``raise ... from cause`` sets
    return wrapped


@pytest.fixture
async def fresh_sync_state() -> SyncState:
    """Reset the process-singleton sync state inside the running event loop."""
    reset_sync_state()
    return get_sync_state()


async def _sleeps_before_success(mocker: MockerFixture, state: SyncState, first_failure: BaseException) -> list[float]:
    """Fail the first sync attempt with ``first_failure``, succeed on the next; return every sleep."""
    calls = 0

    async def _fail_then_succeed(*_args: object, **_kwargs: object) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise first_failure

    delays: list[float] = []

    async def _record_sleep(delay: float) -> None:
        delays.append(delay)

    mocker.patch("backlog_core.sync_engine._run_single_sync", side_effect=_fail_then_succeed)
    mocker.patch("backlog_core.sync_engine.asyncio.sleep", side_effect=_record_sleep)
    await _startup_sync_loop(state)
    assert calls == 2, "the loop must retry exactly once and stop after the patched success"
    return delays


class TestSyncRetryWaitsForRetryAfter:
    async def test_the_retry_waits_at_least_the_retry_after_hint(
        self, fresh_sync_state: SyncState, mocker: MockerFixture
    ) -> None:
        failure = GitHubRateLimitedError("rate limited", retry_after=_RETRY_AFTER_SECONDS)

        assert await _sleeps_before_success(mocker, fresh_sync_state, failure) == [_RETRY_AFTER_SECONDS]

    async def test_a_wrapped_rate_limit_still_supplies_its_hint(
        self, fresh_sync_state: SyncState, mocker: MockerFixture
    ) -> None:
        assert await _sleeps_before_success(mocker, fresh_sync_state, _wrapped_rate_limit()) == [_RETRY_AFTER_SECONDS]

    async def test_a_hint_shorter_than_the_backoff_keeps_the_backoff(
        self, fresh_sync_state: SyncState, mocker: MockerFixture
    ) -> None:
        failure = GitHubRateLimitedError("rate limited", retry_after=1.0)

        assert await _sleeps_before_success(mocker, fresh_sync_state, failure) == [30.0]

    async def test_no_hint_keeps_the_fixed_backoff(self, fresh_sync_state: SyncState, mocker: MockerFixture) -> None:
        failure = GitHubRateLimitedError("rate limited")

        assert await _sleeps_before_success(mocker, fresh_sync_state, failure) == [30.0]


async def _call(tool: str, args: dict[str, Any]) -> dict[str, Any]:
    async with Client(mcp) as client:
        return (await client.call_tool(tool, args)).structured_content


class TestMcpErrorResponseCarriesRetryAfter:
    async def test_a_rate_limited_failure_reports_retry_after(self, mocker: MockerFixture) -> None:
        mocker.patch(
            "backlog_core.server.operations.list_labels",
            side_effect=GitHubRateLimitedError("rate limited", retry_after=45.0),
        )

        result = await _call("backlog_list_labels", {})

        assert (result["retryable"], result["retry_after"]) == (True, 45.0)

    async def test_a_wrapped_rate_limit_reports_the_cause_hint(self, mocker: MockerFixture) -> None:
        mocker.patch("backlog_core.server.operations.list_labels", side_effect=_wrapped_rate_limit())

        result = await _call("backlog_list_labels", {})

        assert result["retry_after"] == _RETRY_AFTER_SECONDS

    async def test_a_failure_without_a_hint_omits_retry_after(self, mocker: MockerFixture) -> None:
        mocker.patch("backlog_core.server.operations.list_labels", side_effect=GitHubRateLimitedError("rate limited"))

        result = await _call("backlog_list_labels", {})

        assert result["retryable"] is True
        assert "retry_after" not in result
