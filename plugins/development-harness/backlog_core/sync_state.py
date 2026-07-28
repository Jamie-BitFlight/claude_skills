"""Sync state singleton for the background cache-sync feature.

This module owns the process-scoped sync state and error classification.
All fields are module-level (not FastMCP session-scoped) so state persists
across multiple tool calls within one server process.

Design constraint — asyncio.Lock lazy initialisation:
    ``asyncio.Lock()`` must be created inside a running event loop.
    ``get_sync_state()`` is called from the lifespan context (after
    ``asyncio.run()`` starts), so the lock is always bound to the correct
    loop.  Never call ``get_sync_state()`` at module import time.
    In tests, always call ``reset_sync_state()`` inside an ``async`` fixture.

Source: design doc sections 2.3, 3.1-3.3, 5.2, Risk #2.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

from github import GithubException

from .models import BackendUnavailableError, BacklogError

__all__ = ["SyncErrorKind", "SyncState", "SyncStatus", "classify_sync_error", "get_sync_state", "reset_sync_state"]

# HTTP status code constants used in error classification (avoids PLR2004 magic values).
_HTTP_UNAUTHORIZED = 401
_HTTP_FORBIDDEN = 403
_HTTP_NOT_FOUND = 404
_HTTP_SERVER_ERROR_THRESHOLD = 500
_HTTP_TOO_MANY_REQUESTS = 429


class SyncStatus(StrEnum):
    """Lifecycle state of the background cache sync.

    Attributes:
        IDLE: No sync is running; last sync completed successfully (or none has run).
        RUNNING: A sync is currently in progress.
        OFFLINE: Last sync failed with a non-retryable error; serving stale cache.
        ERROR: Last sync failed after exhausting all retry attempts.
    """

    IDLE = "idle"
    RUNNING = "running"
    OFFLINE = "offline"
    ERROR = "error"


class SyncErrorKind(StrEnum):
    """Classification of a sync exception into retryable vs non-retryable.

    Attributes:
        RETRYABLE: Transient error — network, timeout, 5xx, rate-limit.
        NON_RETRYABLE: Permanent error — auth failure, config error, 404.
        UNKNOWN: Could not classify; treat conservatively as non-retryable.
    """

    RETRYABLE = "retryable"
    NON_RETRYABLE = "non_retryable"
    UNKNOWN = "unknown"


@dataclass
class SyncState:
    """Process-singleton dataclass holding all background sync bookkeeping.

    Attributes:
        status: Current sync lifecycle state.
        started_at: UTC timestamp when the current or last sync started.
        completed_at: UTC timestamp of the last completed sync (success or failure).
        items_done: Issues written to cache so far in the current run.
        items_total: Total issues expected; ``None`` while the total is unknown.
        last_error: Error message from the last failed sync attempt.
        last_success_at: UTC timestamp of the last *successful* sync.
        retry_count: Consecutive failed attempts in the current cycle.
        offline_reason: Human-readable explanation for OFFLINE state entry.
        lock: asyncio.Lock serialising sync workers.  Named without underscore
            so sync_engine can access it without triggering SLF001.
    """

    status: SyncStatus = SyncStatus.IDLE
    started_at: datetime | None = None
    completed_at: datetime | None = None
    items_done: int = 0
    items_total: int | None = None
    last_error: str = ""
    last_success_at: datetime | None = None
    retry_count: int = 0
    offline_reason: str = ""
    lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False, compare=False)

    @property
    def percent(self) -> int | None:
        """Completion percentage 0-100, or None when total is unknown or zero.

        Returns:
            Integer percentage clipped to 100, or None when ``items_total``
            is ``None`` or ``0`` (division-by-zero guard).
        """
        if self.items_total and self.items_total > 0:
            return min(100, int(self.items_done * 100 / self.items_total))
        return None

    def is_running(self) -> bool:
        """Return True when a sync is currently in progress.

        Returns:
            True only when ``status == SyncStatus.RUNNING``.
        """
        return self.status == SyncStatus.RUNNING

    def try_start(self) -> bool:
        """Atomically claim the sync slot, returning True when claimed.

        Synchronous and await-free: under the single-threaded event loop the
        check-and-set cannot interleave with another coroutine. Callers use this
        in place of a separate ``is_running()`` check followed by ``create_task``,
        which races and can launch duplicate sync workers.

        Returns:
            True if the slot was claimed (status was not RUNNING); False if a
            sync is already RUNNING.
        """
        if self.status == SyncStatus.RUNNING:
            return False
        self.status = SyncStatus.RUNNING
        self.started_at = datetime.now(UTC)
        return True

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serialisable representation of the sync state.

        The ``lock`` field is excluded — it is not JSON-serialisable.
        Datetime fields are serialised as ISO 8601 UTC strings or ``None``.

        Returns:
            Dict with all public fields plus the computed ``percent`` property.
        """

        def _fmt(dt: datetime | None) -> str | None:
            return dt.isoformat() if dt is not None else None

        return {
            "status": str(self.status),
            "started_at": _fmt(self.started_at),
            "completed_at": _fmt(self.completed_at),
            "items_done": self.items_done,
            "items_total": self.items_total,
            "last_error": self.last_error,
            "last_success_at": _fmt(self.last_success_at),
            "retry_count": self.retry_count,
            "offline_reason": self.offline_reason,
            "percent": self.percent,
        }


# ---------------------------------------------------------------------------
# Module-level singleton — lazy, never created at import time.
# ---------------------------------------------------------------------------

_state: SyncState | None = None


def get_sync_state() -> SyncState:
    """Return the process-singleton SyncState, creating it on first call.

    Must be called from within a running asyncio event loop so that the
    ``asyncio.Lock`` inside ``SyncState`` binds to the correct loop.

    Returns:
        The module-level ``SyncState`` instance.
    """
    global _state  # ruff: ignore[global-statement] — intentional module-level singleton
    if _state is None:
        _state = SyncState()
    return _state


def reset_sync_state() -> None:
    """Reset the singleton to a fresh SyncState.

    Intended for tests only.  Must be called from within a running asyncio
    event loop so the new ``asyncio.Lock`` binds to the correct loop.
    """
    global _state  # ruff: ignore[global-statement] — intentional module-level singleton
    _state = SyncState()


# ---------------------------------------------------------------------------
# Error classification
# ---------------------------------------------------------------------------


def _classify_github_exception(exc: GithubException) -> SyncErrorKind:
    """Classify a GithubException by HTTP status and headers.

    Args:
        exc: A PyGitHub exception with a numeric HTTP status code.  The PyGitHub
            library declares ``status`` as ``int`` but may in practice provide
            ``None`` or a non-integer value (e.g. from a malformed response).
            A non-int status returns ``SyncErrorKind.UNKNOWN`` rather than raising
            ``TypeError``.

    Returns:
        ``SyncErrorKind`` for the given HTTP response.
    """
    raw_status = exc.status
    if not isinstance(raw_status, int):
        return SyncErrorKind.UNKNOWN
    status: int = raw_status
    if status in {_HTTP_UNAUTHORIZED, _HTTP_NOT_FOUND}:
        return SyncErrorKind.NON_RETRYABLE
    if status == _HTTP_FORBIDDEN:
        headers: dict[str, str] = exc.headers or {}  # type: ignore[assignment]
        return SyncErrorKind.RETRYABLE if "Retry-After" in headers else SyncErrorKind.NON_RETRYABLE
    if status == _HTTP_TOO_MANY_REQUESTS or status >= _HTTP_SERVER_ERROR_THRESHOLD:
        return SyncErrorKind.RETRYABLE
    return SyncErrorKind.UNKNOWN


def classify_sync_error(exc: BaseException) -> SyncErrorKind:
    """Classify a sync exception as retryable or non-retryable.

    Classification table (from design doc section 5.1):

    - ``BackendUnavailableError`` (includes ``GitHubUnavailableError``) — NON_RETRYABLE.
    - ``BacklogError`` (generic backend/GraphQL fetch failure) — RETRYABLE.
    - ``GithubException`` with status 401 or 404 — NON_RETRYABLE.
    - ``GithubException`` with status 403 and no ``Retry-After`` header — NON_RETRYABLE.
    - ``GithubException`` with status 403 and ``Retry-After`` header — RETRYABLE.
    - ``GithubException`` with status 429 — RETRYABLE (primary rate limit).
    - ``GithubException`` with status >= 500 — RETRYABLE.
    - ``asyncio.TimeoutError`` — RETRYABLE (transient network timeout; checked before
      OSError because Python 3.11+ aliases it to OSError).
    - ``OSError`` — NON_RETRYABLE (filesystem failure; requires operator action).
    - ``ValueError`` — NON_RETRYABLE (config error from ``resolve_repo``).

    Args:
        exc: Exception raised during a sync attempt.

    Returns:
        ``SyncErrorKind`` indicating whether the sync should retry.
    """
    if isinstance(exc, BackendUnavailableError):
        return SyncErrorKind.NON_RETRYABLE
    if isinstance(exc, BacklogError):
        # Generic backend/GraphQL failure (e.g. from sync_issues_graphql) — transient.
        # Checked after BackendUnavailableError (its subclass) so auth/config stays non-retryable.
        return SyncErrorKind.RETRYABLE
    if isinstance(exc, GithubException):
        return _classify_github_exception(exc)
    if isinstance(exc, asyncio.TimeoutError):
        return SyncErrorKind.RETRYABLE
    if isinstance(exc, (OSError, ValueError)):
        return SyncErrorKind.NON_RETRYABLE
    return SyncErrorKind.UNKNOWN
