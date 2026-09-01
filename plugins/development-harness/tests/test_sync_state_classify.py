"""Regression tests for classify_sync_error's ContentProviderError handling.

ContentProviderError is a separate exception tree from BacklogError (see
models.py), so classify_sync_error needs its own branch for it — and that
branch is not always NON_RETRYABLE. ``_GitHubContentsStore.get_many()`` wraps
*any* ``GithubException`` it sees, including a transient 503 or a
rate-limited 429, in ``ContentUnavailableError`` via ``raise ... from exc``.
Blanket-classifying every ContentProviderError as non-retryable would send a
merely-overloaded GitHub API straight to OFFLINE instead of the bounded retry
policy transient failures are supposed to get.

The ``__cause__`` inspection must walk the full chain, not stop at one level:
``_fetch_blobs_graphql()`` double-wraps — ``gh_client._graphql_request()``
wraps the GithubException in ``BacklogError`` first, then
``_fetch_blobs_graphql()`` wraps that ``BacklogError`` in
``ContentUnavailableError`` — so the GithubException sits two ``__cause__``
links down, not one.
"""

from __future__ import annotations

import pytest
from backlog_core.models import BacklogError, ContentConflictError, ContentUnavailableError, UnsupportedCapabilityError
from backlog_core.sync_state import SyncErrorKind, classify_sync_error
from github import GithubException


def _raise_content_unavailable_from(cause: GithubException) -> None:
    """Raise ContentUnavailableError chained to cause, mirroring get_many()'s own shape."""
    raise ContentUnavailableError(f"GitHub content discovery failed: {cause.status}") from cause


def _raise_double_wrapped_content_unavailable_from(github_exc: GithubException) -> None:
    """Mirrors _fetch_blobs_graphql()'s actual double-wrap shape (see module docstring)."""
    try:
        try:
            raise github_exc
        except GithubException as exc:
            raise BacklogError(f"GraphQL request failed: {exc}") from exc
    except BacklogError as exc:
        raise ContentUnavailableError(f"GitHub content discovery failed: {exc}") from exc


def test_content_unavailable_wrapping_a_503_is_retryable() -> None:
    """A ContentUnavailableError wrapping a transient 503 GithubException retries.

    Tests: classify_sync_error's ContentProviderError branch inspects __cause__.
    How: Build a ContentUnavailableError the way get_many() actually raises one
        — via `raise ContentUnavailableError(...) from exc` — with exc a 503
        GithubException, and classify it.
    Why: This fails (returns NON_RETRYABLE) without the __cause__ inspection —
        that was exactly the bug Codex flagged: a transient GitHub server error
        would send the sync straight to OFFLINE instead of retrying.
    """
    cause = GithubException(503, {"message": "Service Unavailable"}, {})
    with pytest.raises(ContentUnavailableError) as exc_info:
        _raise_content_unavailable_from(cause)

    assert classify_sync_error(exc_info.value) == SyncErrorKind.RETRYABLE


def test_content_unavailable_wrapping_a_404_is_non_retryable() -> None:
    """A ContentUnavailableError wrapping a 404 stays non-retryable.

    Tests: the __cause__ inspection still classifies a permanent GitHub error
        as NON_RETRYABLE, not blanket RETRYABLE.
    """
    cause = GithubException(404, {"message": "Not Found"}, {})
    with pytest.raises(ContentUnavailableError) as exc_info:
        _raise_content_unavailable_from(cause)

    assert classify_sync_error(exc_info.value) == SyncErrorKind.NON_RETRYABLE


def test_double_wrapped_content_unavailable_from_a_503_is_retryable() -> None:
    """A ContentUnavailableError wrapping a BacklogError wrapping a 503 GithubException retries.

    Tests: classify_sync_error's ContentProviderError branch walks the full
        __cause__ chain, not just one level.
    How: Build the exact double-wrap shape _fetch_blobs_graphql() produces
        and classify it.
    Why: This fails (returns NON_RETRYABLE) with only a single-level
        __cause__ check — that was the follow-up bug Codex flagged: a
        transient 503 hitting the blob-fetch path would still send the sync
        straight to OFFLINE.
    """
    github_exc = GithubException(503, {"message": "Service Unavailable"}, {})
    with pytest.raises(ContentUnavailableError) as exc_info:
        _raise_double_wrapped_content_unavailable_from(github_exc)

    assert classify_sync_error(exc_info.value) == SyncErrorKind.RETRYABLE


def test_content_provider_error_without_a_github_cause_is_non_retryable() -> None:
    """A structural ContentProviderError (no wrapped GithubException) stays non-retryable.

    Tests: UnsupportedCapabilityError and ContentConflictError, raised with no
        `from exc` chain, are genuinely structural — retrying can't fix a
        missing capability or a stale revision — so they still classify as
        NON_RETRYABLE, same as before this fix.
    """
    assert classify_sync_error(UnsupportedCapabilityError("provider-private")) == SyncErrorKind.NON_RETRYABLE
    assert classify_sync_error(ContentConflictError("revision mismatch")) == SyncErrorKind.NON_RETRYABLE
