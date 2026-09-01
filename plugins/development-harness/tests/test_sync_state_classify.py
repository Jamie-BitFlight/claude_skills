"""Regression tests for classify_sync_error's ContentProviderError handling.

A Codex review on PR #3360 found that a prior fix in this same PR — adding
ContentProviderError to classify_sync_error's NON_RETRYABLE branch — was too
broad: ``_GitHubContentsStore.get_many()`` wraps *any* ``GithubException``,
including a transient 503 or a rate-limited 429, in ``ContentUnavailableError``
via ``raise ... from exc``. Blanket-classifying every ContentProviderError as
non-retryable sends a merely-overloaded GitHub API straight to OFFLINE instead
of the bounded retry policy transient failures are supposed to get.
"""

from __future__ import annotations

import pytest
from backlog_core.models import ContentConflictError, ContentUnavailableError, UnsupportedCapabilityError
from backlog_core.sync_state import SyncErrorKind, classify_sync_error
from github import GithubException


def _raise_content_unavailable_from(cause: GithubException) -> None:
    """Raise ContentUnavailableError chained to cause, mirroring get_many()'s own shape."""
    raise ContentUnavailableError(f"GitHub content discovery failed: {cause.status}") from cause


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


def test_content_provider_error_without_a_github_cause_is_non_retryable() -> None:
    """A structural ContentProviderError (no wrapped GithubException) stays non-retryable.

    Tests: UnsupportedCapabilityError and ContentConflictError, raised with no
        `from exc` chain, are genuinely structural — retrying can't fix a
        missing capability or a stale revision — so they still classify as
        NON_RETRYABLE, same as before this fix.
    """
    assert classify_sync_error(UnsupportedCapabilityError("provider-private")) == SyncErrorKind.NON_RETRYABLE
    assert classify_sync_error(ContentConflictError("revision mismatch")) == SyncErrorKind.NON_RETRYABLE
