"""Regression test for classifying a REST secondary rate limit with no Retry-After header.

Observed 2026-09-27: GitHub answers a request that trips its secondary rate limit with HTTP 403
and a body naming the limit -- "You have exceeded a secondary rate limit. Please wait a few
minutes before you try again." GitHub's own docs say a `Retry-After` header *may* be present;
when it is absent, the guidance is to wait at least a minute and retry anyway. Today
`_classify_github_exception` only checks for that header on a 403 -- absent it, the failure is
classified NON_RETRYABLE, the same verdict as a permissions failure no retry can fix. That
misclassifies a purely temporary condition as permanent.

Nothing here touches the network; every exception is constructed in-process, following
`test_sync_state_graphql_refusal.py`'s pattern.
"""

from __future__ import annotations

from backlog_core.sync_state import SyncErrorKind, classify_sync_error
from github import GithubException

_SECONDARY_LIMIT_MESSAGE = "You have exceeded a secondary rate limit. Please wait a few minutes before you try again."


class TestSecondaryRateLimitWithoutRetryAfterHeader:
    """The message alone must be enough to classify this as retryable."""

    def test_a_403_naming_the_secondary_limit_is_retryable_without_the_header(self) -> None:
        exc = GithubException(status=403, data={"message": _SECONDARY_LIMIT_MESSAGE}, headers={})

        assert classify_sync_error(exc) is SyncErrorKind.RETRYABLE

    def test_matching_ignores_case(self) -> None:
        exc = GithubException(status=403, data={"message": _SECONDARY_LIMIT_MESSAGE.upper()}, headers={})

        assert classify_sync_error(exc) is SyncErrorKind.RETRYABLE

    def test_a_403_with_the_header_stays_retryable(self) -> None:
        """Behavior-preserving: the pre-existing header-based path must not regress."""
        exc = GithubException(status=403, data={"message": _SECONDARY_LIMIT_MESSAGE}, headers={"Retry-After": "60"})

        assert classify_sync_error(exc) is SyncErrorKind.RETRYABLE

    def test_an_unrelated_403_without_the_header_stays_non_retryable(self) -> None:
        """Negative control: a permissions 403 must not be swept into this by a broad match."""
        exc = GithubException(status=403, data={"message": "Resource not accessible by integration"}, headers={})

        assert classify_sync_error(exc) is SyncErrorKind.NON_RETRYABLE

    def test_a_429_stays_retryable_regardless_of_message(self) -> None:
        """Behavior-preserving: the primary rate limit's existing 429 handling is untouched."""
        exc = GithubException(status=429, data={"message": "API rate limit exceeded"}, headers={})

        assert classify_sync_error(exc) is SyncErrorKind.RETRYABLE
