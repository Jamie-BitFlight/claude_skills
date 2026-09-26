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
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

import requests
from github import GithubException
from pydantic import BaseModel, ConfigDict

from .models import BackendUnavailableError, BacklogError, ContentProviderError, UnsupportedBackendCapabilityError

# Transient-network exceptions that are also OSError subclasses, so they must be
# checked before the generic OSError branch: asyncio.TimeoutError (Python 3.11+
# aliases it to OSError) and the requests exceptions PyGithub's Requester can raise
# for a dropped/failed HTTP transport (via requests.exceptions.RequestException).
# ConnectTimeout/ReadTimeout subclass Timeout; SSLError/ProxyError subclass
# ConnectionError -- covered without listing them. ContentDecodingError covers a
# corrupted/truncated compressed response body -- also transient transport noise,
# not a config or filesystem failure.
RETRYABLE_TRANSIENT_EXCEPTIONS = (
    asyncio.TimeoutError,
    requests.exceptions.ConnectionError,
    requests.exceptions.Timeout,
    requests.exceptions.ChunkedEncodingError,
    requests.exceptions.ContentDecodingError,
)

__all__ = [
    "RETRYABLE_TRANSIENT_EXCEPTIONS",
    "SyncClaim",
    "SyncErrorKind",
    "SyncState",
    "SyncStatus",
    "classify_github_failure",
    "classify_sync_error",
    "get_sync_state",
    "reset_sync_state",
]

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


class SyncClaim(BaseModel):
    """State captured atomically when a caller claims the sync slot."""

    model_config = ConfigDict(frozen=True)

    status: SyncStatus
    started_at: datetime | None


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
        pending_mutations: Offline-queue depth as of the last completed sync.
        rejected_mutations: Dead-lettered mutation count as of the last
            completed sync (key mismatches plus schema-invalid entries).
        lock: asyncio.Lock serialising sync workers for the duration of a full
            sync attempt.  Named without underscore so sync_engine can access
            it without triggering SLF001.  Only ever awaited from the event
            loop thread — never safe to acquire from a worker thread (see
            ``try_claim``/``release_claim`` below for the cross-thread case).
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
    pending_mutations: int = 0
    rejected_mutations: int = 0
    lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False, compare=False)
    # Guards the ``status``/``started_at`` check-and-set in try_claim()/try_start()
    # so it is atomic across OS threads, not just across coroutines. A plain
    # ``threading.Lock`` (not the asyncio.Lock above) because callers include
    # asyncio.to_thread worker threads (operations.list_items's implicit
    # cold-cache read-through), where an asyncio.Lock cannot safely be awaited.
    # Never accessed outside this class, so it stays private -- unlike ``lock``,
    # which is genuinely public API for sync_engine.
    _claim_lock: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)

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

    def try_claim(self, *, track_started_at: bool = True) -> SyncClaim | None:
        """Atomically claim the sync slot, returning the state held before the claim.

        The single-flight primitive underlying both ``try_start()`` (startup
        sync and ``sync_now``, always called from the event-loop thread) and
        the implicit cold-cache read-through in ``operations.list_items``
        (called from an ``asyncio.to_thread`` worker thread, and potentially
        from two such worker threads racing each other on overlapping
        ``backlog_list`` calls). The check-and-set is guarded by
        ``_claim_lock``, a plain ``threading.Lock``, so it is atomic across
        OS threads — the single-threaded-event-loop assumption a bare
        ``if status == RUNNING`` check relies on does not hold once a worker
        thread is a caller.

        Returns the pre-claim status and start time (rather than assuming the
        caller should restore ``IDLE`` or reading the timestamp before taking
        the lock) so a transient, one-shot claim can hand the atomic snapshot
        back to ``release_claim()``. This leaves the state exactly as the
        preceding sync completed it, even if another claim completed before
        this caller acquired the slot.

        Args:
            track_started_at: Whether to replace ``started_at`` when taking
                the claim. Transient callers that restore prior state after a
                handled failure leave this false so they do not corrupt the
                previous sync's bookkeeping.

        Returns:
            The state that prevailed before the claim when the slot was
            claimed (status was not ``RUNNING``, and is now); ``None`` when a
            sync is already ``RUNNING`` and the claim was refused.
        """
        with self._claim_lock:
            if self.status == SyncStatus.RUNNING:
                return None
            previous = SyncClaim(status=self.status, started_at=self.started_at)
            self.status = SyncStatus.RUNNING
            if track_started_at:
                self.started_at = datetime.now(UTC)
            return previous

    def release_claim(self, previous: SyncClaim) -> None:
        """Restore the status that prevailed before a matching ``try_claim()``.

        Args:
            previous: The state ``try_claim()`` returned when it succeeded.
                Passing the value from an unsuccessful claim (``None``) is a
                caller bug — every ``try_claim()`` caller must guard on
                ``None`` before running the claimed work, so ``release_claim``
                is never reached in that case.
        """
        with self._claim_lock:
            self.status = previous.status
            self.started_at = previous.started_at

    def complete_claim(self) -> None:
        """Complete a successful transient claim without changing when it started."""
        with self._claim_lock:
            now = datetime.now(UTC)
            self.status = SyncStatus.IDLE
            self.completed_at = now
            self.last_success_at = now
            self.last_error = ""
            self.retry_count = 0
            self.offline_reason = ""

    def try_start(self) -> bool:
        """Atomically claim the sync slot, returning True when claimed.

        Thread-safe wrapper around ``try_claim()`` for callers — startup sync
        and ``sync_now`` — that only need a boolean claim result and always
        run the full sync to completion (never restoring a prior status).

        Returns:
            True if the slot was claimed (status was not RUNNING); False if a
            sync is already RUNNING.
        """
        return self.try_claim() is not None

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
            "pending_mutations": self.pending_mutations,
            "rejected_mutations": self.rejected_mutations,
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


_MAX_CAUSE_CHAIN_DEPTH = 5


def _find_wrapped_github_exception(exc: BaseException) -> GithubException | None:
    """Walk ``exc``'s ``__cause__`` chain looking for a wrapped GithubException.

    A content-provider error can wrap through more than one layer before
    reaching the original GithubException. E.g. ``gh_client._graphql_request()``
    wraps a GithubException in ``BacklogError``, and
    ``_fetch_blobs_graphql()`` then wraps that ``BacklogError`` in
    ``ContentUnavailableError`` — the GithubException sits two ``__cause__``
    links down, not one.

    Args:
        exc: The outermost exception to search from.

    Returns:
        The first GithubException found while walking ``__cause__``, or
        ``None`` if none is present within ``_MAX_CAUSE_CHAIN_DEPTH`` links
        (bounded so a pathological or accidentally-cyclic chain can't loop
        forever — real exception chains here are 1-2 links deep).
    """
    cause: BaseException | None = exc.__cause__
    for _ in range(_MAX_CAUSE_CHAIN_DEPTH):
        if cause is None:
            return None
        if isinstance(cause, GithubException):
            return cause
        cause = cause.__cause__
    return None


def classify_github_failure(exc: BaseException) -> SyncErrorKind:
    """Classify a direct or cause-wrapped GitHub failure using the canonical status rules.

    Args:
        exc: A direct ``GithubException`` or an exception whose explicit cause chain may contain
            one.

    Returns:
        The GitHub exception's classification, or ``UNKNOWN`` when the exception and its cause
        chain contain no GitHub failure.
    """
    github_error = exc if isinstance(exc, GithubException) else _find_wrapped_github_exception(exc)
    return _classify_github_exception(github_error) if github_error is not None else SyncErrorKind.UNKNOWN


def _classify_content_provider_error(exc: ContentProviderError) -> SyncErrorKind:
    """Classify a ContentProviderError by inspecting its wrapped cause chain, if any.

    A ContentProviderError is not always structural: ``_GitHubContentsStore.get_many()``
    wraps *any* ``GithubException`` it sees — including a transient 503 or a
    rate-limited 429 — in ``ContentUnavailableError`` via ``raise ... from exc``.
    Blanket-classifying every ContentProviderError as non-retryable would send a
    merely-overloaded GitHub API straight to OFFLINE instead of the bounded retry
    policy transient failures are supposed to get.

    Args:
        exc: A ContentProviderError, possibly wrapping a GithubException
            somewhere in its ``__cause__`` chain (see
            ``_find_wrapped_github_exception``).

    Returns:
        The wrapped GithubException's own classification when one is present
        anywhere in the chain (delegates to ``_classify_github_exception``);
        otherwise ``NON_RETRYABLE`` — the error is genuinely structural (a
        capability gap, a not-found, a revision conflict), and retrying
        won't fix it.
    """
    classification = classify_github_failure(exc)
    return SyncErrorKind.NON_RETRYABLE if classification is SyncErrorKind.UNKNOWN else classification


def classify_sync_error(exc: BaseException) -> SyncErrorKind:
    """Classify a sync exception as retryable or non-retryable.

    Classification table (from design doc section 5.1):

    - ``BackendUnavailableError`` — its explicit ``retryable`` verdict wins; an unspecified
      verdict remains conservatively NON_RETRYABLE.
    - ``UnsupportedBackendCapabilityError`` (backend lacks an optional capability;
      retrying will not change what the backend supports) — NON_RETRYABLE.
    - ``ContentProviderError`` (unrelated exception tree from ``BacklogError``, so
      needs its own branch) — delegates to ``_classify_content_provider_error``,
      which inspects ``__cause__``: a wrapped ``GithubException`` (e.g. a transient
      503 from ``get_many()``) gets that exception's own classification; otherwise
      NON_RETRYABLE (a genuine capability gap, not-found, or conflict).
    - ``BacklogError`` (generic backend/GraphQL fetch failure) — RETRYABLE. An
      environment-wide GraphQL refusal is *not* generic: it raises
      ``GraphQLUnavailableError`` and is caught by the first entry above, so it is
      NON_RETRYABLE. That is the same verdict its underlying 403-without-``Retry-After``
      already gets as a raw ``GithubException`` (below); before the refusal had its own
      type, wrapping it in a plain ``BacklogError`` erased the status code and landed it
      here by accident. OFFLINE with the refusal named beats spending the retry budget on
      an environment that refuses the next attempt identically.
    - ``GithubException`` with status 401 or 404 — NON_RETRYABLE.
    - ``GithubException`` with status 403 and no ``Retry-After`` header — NON_RETRYABLE.
    - ``GithubException`` with status 403 and ``Retry-After`` header — RETRYABLE.
    - ``GithubException`` with status 429 — RETRYABLE (primary rate limit).
    - ``GithubException`` with status >= 500 — RETRYABLE.
    - ``asyncio.TimeoutError`` — RETRYABLE (transient network timeout; checked before
      OSError because Python 3.11+ aliases it to OSError).
    - ``requests.exceptions.ConnectionError``, ``.Timeout``, ``.ChunkedEncodingError``,
      ``.ContentDecodingError`` (and subclasses, e.g. ``ConnectTimeout``, ``ReadTimeout``,
      ``SSLError``, ``ProxyError``) — RETRYABLE (dropped/failed network transport or a
      corrupted compressed response body underlying a PyGithub call; checked before
      OSError because these are OSError subclasses).
    - ``OSError`` (any other instance, e.g. local cache-file write failure) —
      NON_RETRYABLE (filesystem failure; requires operator action).
    - ``ValueError`` — NON_RETRYABLE (config error from ``resolve_repo``).

    Args:
        exc: Exception raised during a sync attempt.

    Returns:
        ``SyncErrorKind`` indicating whether the sync should retry.
    """
    if isinstance(exc, (BackendUnavailableError, UnsupportedBackendCapabilityError)):
        return (
            SyncErrorKind.RETRYABLE
            if isinstance(exc, BackendUnavailableError) and exc.retryable is True
            else SyncErrorKind.NON_RETRYABLE
        )
    if isinstance(exc, ContentProviderError):
        # Unrelated exception tree from BacklogError (see models.py) — needs its own
        # branch or it falls through to UNKNOWN. Not always structural: see
        # _classify_content_provider_error's docstring.
        return _classify_content_provider_error(exc)
    if isinstance(exc, GithubException):
        return classify_github_failure(exc)
    if isinstance(exc, (BacklogError, *RETRYABLE_TRANSIENT_EXCEPTIONS)):
        # Generic BacklogError (e.g. from sync_issues_graphql) and the transient
        # network exceptions both mean "worth retrying" — merged into one branch to
        # stay under ruff's too-many-return-statements limit. Checked after the
        # structural non-retryable cases above so those stay non-retryable: a
        # GraphQLUnavailableError is a BacklogError by inheritance and must not reach
        # this branch, or an environment-wide refusal would burn the retry budget
        # before landing in the ERROR state it was never going to escape. Checked
        # after GithubException so a raw GithubException still gets status-code
        # classification rather than a blanket RETRYABLE.
        return SyncErrorKind.RETRYABLE
    if isinstance(exc, (OSError, ValueError)):
        return SyncErrorKind.NON_RETRYABLE
    return SyncErrorKind.UNKNOWN
