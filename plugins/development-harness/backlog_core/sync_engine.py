"""Background sync engine for the backlog MCP server.

Provides the startup sync loop that runs as a long-lived asyncio task for the
life of the server process.  The loop is launched once via the FastMCP lifespan
hook in ``server.py`` and cancelled on server shutdown.

Error policy (design doc section 5.3):
    - Non-retryable errors (auth, config, filesystem): set OFFLINE immediately, stop.
    - Retryable errors (5xx, rate-limit): bounded exponential backoff, then ERROR.
    - Attempt 1: immediate.
    - Attempt 2: 30 s wait.
    - Attempt 3: 120 s wait.
    - After MAX_RETRIES failures: ERROR state, loop terminates.

Important: ``asyncio.sleep`` is called via the module-level reference
``asyncio.sleep(...)`` so that test mocks patching
``backlog_core.sync_engine.asyncio.sleep`` intercept the call correctly.

Source: design doc sections 5.3, 6.2.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Protocol

from github import GithubException

from . import operations
from .models import BacklogError
from .sync_state import SyncErrorKind, SyncState, SyncStatus, classify_sync_error

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = ["_startup_sync_loop"]

_log = logging.getLogger(__name__)

# Bounded retry policy: attempt 1 immediate, wait before attempt 2, wait before attempt 3.
# After MAX_RETRIES failures the loop sets ERROR and terminates.
MAX_RETRIES: int = 3
_BACKOFF_DELAYS: tuple[float, ...] = (30.0, 120.0)  # seconds between attempts 1→2, 2→3


class ProgressCallback(Protocol):
    """Protocol for incremental progress reporting during a sync pass."""

    def __call__(self, items_done: int, items_total: int | None) -> None:
        """Update sync progress.

        Args:
            items_done: Number of issues written to cache so far.
            items_total: Total issues in the fetch batch, or ``None`` during
                the initial GraphQL fetch phase when the total is unknown.
        """
        ...


def _make_progress_callback(state: SyncState) -> Callable[[int, int | None], None]:
    """Return a closure that marshals progress updates back to the event-loop thread.

    ``refresh_local_cache_from_github`` runs inside ``asyncio.to_thread``; the
    callback it invokes executes on the worker thread.  Direct mutation of
    ``SyncState`` from the worker thread is not safe under strict thread-safety
    semantics.  Capturing the running event loop before the thread starts and
    dispatching mutations via ``loop.call_soon_threadsafe`` ensures visibility.

    Args:
        state: The process-singleton SyncState to update.

    Returns:
        Callable matching the ProgressCallback protocol.

    Raises:
        RuntimeError: When called outside a running event loop (programming error).
    """
    loop = asyncio.get_running_loop()

    def _callback(items_done: int, items_total: int | None) -> None:
        def _apply() -> None:
            state.items_done = items_done
            state.items_total = items_total

        loop.call_soon_threadsafe(_apply)

    return _callback


async def _run_single_sync(state: SyncState, full_refresh: bool = False) -> None:
    """Execute one sync pass by calling ``refresh_local_cache_from_github`` in a thread.

    Updates ``state.items_done`` and ``state.items_total`` via progress callback
    as pages arrive.  On success, sets ``state.status = IDLE`` and records
    ``state.last_success_at``.  On error, raises the original exception for
    the caller to classify and handle.

    Args:
        state: Process-singleton SyncState — written by progress callback.
        full_refresh: When True, ignore ``.last_sync`` and do a full two-pass sync.

    Raises:
        Exception: Any exception from ``refresh_local_cache_from_github`` is
            re-raised for the caller to classify.
    """
    callback = _make_progress_callback(state)
    await asyncio.to_thread(
        operations.refresh_local_cache_from_github, full_refresh=full_refresh, progress_callback=callback
    )
    # The progress callback marshals mutations via loop.call_soon_threadsafe.
    # Yield once so those callbacks run before we mark the sync complete.
    await asyncio.sleep(0)
    now = datetime.now(UTC)
    state.status = SyncStatus.IDLE
    state.completed_at = now
    state.last_success_at = now
    state.last_error = ""
    state.retry_count = 0
    _log.info("Background sync completed successfully.")


def _compute_backoff_delay(attempt: int) -> float:
    """Return the backoff delay in seconds before a retry attempt.

    Args:
        attempt: Zero-based retry index (0 = first retry, after the first failure).

    Returns:
        Delay in seconds; uses the last configured delay for any attempt beyond
        the configured sequence.
    """
    delay_index = attempt - 1
    if delay_index < len(_BACKOFF_DELAYS):
        return _BACKOFF_DELAYS[delay_index]
    return _BACKOFF_DELAYS[-1]


async def _attempt_sync(state: SyncState, attempt: int, full_refresh: bool) -> bool:
    """Run one sync attempt inside the lock.

    Sets state fields appropriately and returns True on success, False when the
    caller should retry after a delay.  Raises on non-retryable errors and on
    ``asyncio.CancelledError`` (caller must propagate cancellation).

    Args:
        state: Process-singleton SyncState to update.
        attempt: Zero-based attempt index used for logging.
        full_refresh: Passed through to ``_run_single_sync``.

    Returns:
        True if the sync succeeded and the loop should stop.
        False if a retryable error occurred and a retry should follow.

    Raises:
        asyncio.CancelledError: When the task is cancelled during the sync.
        Exception: When a non-retryable error terminates the loop.
    """
    async with state.lock:
        state.status = SyncStatus.RUNNING
        state.started_at = datetime.now(UTC)
        state.items_done = 0
        state.items_total = None
        _log.info("Background sync starting (attempt %d/%d).", attempt + 1, MAX_RETRIES)

        try:
            await _run_single_sync(state, full_refresh=full_refresh)
        except asyncio.CancelledError:
            state.status = SyncStatus.IDLE
            _log.info("Background sync cancelled during attempt %d.", attempt + 1)
            raise
        except (BacklogError, GithubException, OSError, ValueError) as exc:
            # Catch the exception types refresh_local_cache_from_github is documented to
            # raise (the set classify_sync_error handles — BacklogError covers its
            # BackendUnavailableError subclass).  Any other
            # exception is a programming bug and propagates to the task done-callback
            # (_log_sync_task_exc), which logs it — never silently masked as OFFLINE.
            state.completed_at = datetime.now(UTC)
            kind = classify_sync_error(exc)
            error_msg = str(exc)
            _log.warning("Sync attempt %d failed (%s): %s", attempt + 1, kind, error_msg)

            if kind != SyncErrorKind.RETRYABLE:
                state.status = SyncStatus.OFFLINE
                state.offline_reason = error_msg
                state.last_error = error_msg
                _log.error("Sync entered OFFLINE state (non-retryable): %s", error_msg)
                return True  # loop terminates — non-retryable

            state.retry_count += 1
            state.last_error = error_msg
            return False  # retryable — caller will sleep and retry
        else:
            return True  # success — loop terminates


async def _startup_sync_loop(state: SyncState, full_refresh: bool = False) -> None:
    """Background coroutine: run sync at startup with bounded retry on failure.

    Acquires ``state.lock`` for the duration of each sync attempt to prevent
    concurrent sync workers.  On non-retryable error, sets OFFLINE and returns.
    On retryable error, retries with exponential backoff up to ``MAX_RETRIES``
    times total, then sets ERROR.  On cancellation (server shutdown), propagates
    ``asyncio.CancelledError`` cleanly.

    Args:
        state: Process-singleton SyncState to mutate during the sync lifecycle.
        full_refresh: Passed through to ``_run_single_sync``.

    Raises:
        asyncio.CancelledError: Propagated from task cancellation during shutdown.
    """
    attempt = 0
    try:
        while attempt < MAX_RETRIES:
            done = await _attempt_sync(state, attempt, full_refresh)
            if done:
                return

            # Retryable — check budget before sleeping.
            attempt += 1
            if attempt >= MAX_RETRIES:
                state.status = SyncStatus.ERROR
                _log.error("Sync ERROR: exhausted %d retries. Last error: %s", MAX_RETRIES, state.last_error)
                return

            delay = _compute_backoff_delay(attempt)
            _log.info("Retrying in %.0f s (attempt %d/%d).", delay, attempt + 1, MAX_RETRIES)
            # Sleep outside the lock so other tool calls can proceed during the wait.
            await asyncio.sleep(delay)
    except BaseException as exc:
        # Exceptions outside the narrow (BacklogError, GithubException,
        # OSError, ValueError) catch in _attempt_sync — e.g. RuntimeError (bug),
        # KeyboardInterrupt — must not leave status=RUNNING permanently.
        # Set ERROR and re-raise so the done-callback (_log_sync_task_exc) still logs it.
        if state.status == SyncStatus.RUNNING:
            state.status = SyncStatus.ERROR
            state.last_error = str(exc)
        raise
