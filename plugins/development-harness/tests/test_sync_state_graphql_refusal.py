"""Regression tests for how background sync classifies an environment-wide GraphQL refusal.

Some sandboxes serve GitHub's REST API and reject every GraphQL request with a
403 whose body names the refusal. ``gh_client._graphql_request`` raises
``GraphQLUnavailableError`` for that shape — a ``BackendUnavailableError``, and
therefore also a ``BacklogError``.

Two branches of ``classify_sync_error`` can claim it, and they disagree. The
structural branch answers NON_RETRYABLE, the generic-BacklogError branch answers
RETRYABLE. The structural branch is checked first and is the correct one: the
same failure, unwrapped, is a 403 carrying no ``Retry-After``, which
``_classify_github_exception`` already calls NON_RETRYABLE. Retrying cannot
change an environment-level policy, so the sync parks in OFFLINE with the
refusal named instead of spending its retry budget and landing in ERROR.

These tests pin the ordering. Nothing here touches the network, and every
exception is constructed in-process.
"""

from __future__ import annotations

from backlog_core.models import BacklogError, GitHubUnavailableError, GraphQLUnavailableError
from backlog_core.sync_state import SyncErrorKind, classify_sync_error
from github import GithubException

_REFUSAL_MESSAGE = "GitHub GraphQL is not available from Claude Code sessions; use the REST API"


def _refusal() -> GraphQLUnavailableError:
    """Build the exception ``_graphql_request`` raises for an environment-wide refusal."""
    return GraphQLUnavailableError(f"GraphQL is unavailable in this environment: {_REFUSAL_MESSAGE}")


def test_a_graphql_refusal_is_non_retryable() -> None:
    """The environment refuses the next attempt on the same grounds as this one."""
    assert classify_sync_error(_refusal()) is SyncErrorKind.NON_RETRYABLE


def test_the_refusal_agrees_with_its_own_unwrapped_403() -> None:
    """A 403 without Retry-After is already NON_RETRYABLE; wrapping it must not flip that."""
    raw = GithubException(status=403, data={"message": _REFUSAL_MESSAGE}, headers={})

    assert classify_sync_error(_refusal()) is classify_sync_error(raw)


def test_the_structural_branch_wins_over_the_backlog_error_branch() -> None:
    """GraphQLUnavailableError is a BacklogError, and BacklogError alone is RETRYABLE."""
    assert isinstance(_refusal(), BacklogError)
    assert classify_sync_error(BacklogError(_REFUSAL_MESSAGE)) is SyncErrorKind.RETRYABLE
    assert classify_sync_error(_refusal()) is SyncErrorKind.NON_RETRYABLE


def test_a_generic_graphql_failure_stays_retryable() -> None:
    """Only the named refusal is structural — an ordinary query failure still retries."""
    assert classify_sync_error(BacklogError("GraphQL request failed: 502")) is SyncErrorKind.RETRYABLE


def test_a_missing_token_stays_non_retryable() -> None:
    """The sibling BackendUnavailableError subclass keeps its existing verdict."""
    assert classify_sync_error(GitHubUnavailableError("GITHUB_TOKEN not set")) is SyncErrorKind.NON_RETRYABLE
