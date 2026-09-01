"""Regression test for the ``GitHubExtras`` capability gate (backlog #2287, slice 1).

Before this fix, ``operations.py`` gated every ``GitHubExtras``-only operation with
a bare ``isinstance(backend, GitHubExtras)`` check. ``GitHubExtras`` is a
``runtime_checkable`` Protocol, so that ``isinstance`` check verifies attribute
*names* only. ``SQLiteBackend`` and ``InMemoryBackend`` implement every
``GitHubExtras`` method as a local simulation, so both satisfied the check and
reached ``SQLiteBackend.get_github()``'s bare ``RuntimeError`` stub instead of a
caller-recognisable error.

This test proves the fix: ``require_github_extras()`` gates on the
``supports_github_extras`` flag first, so a flag-``False`` backend now raises the
typed, structured ``UnsupportedBackendCapabilityError`` instead.
"""

from __future__ import annotations

import pytest
from backlog_core import operations
from backlog_core.backend_protocol import set_config
from backlog_core.backend_types import BacklogConfig
from backlog_core.backends.sqlite_backend import SQLiteBackend
from backlog_core.models import UnsupportedBackendCapabilityError


def test_list_milestones_under_sqlite_backend_raises_typed_capability_error() -> None:
    """list_milestones() under SQLiteBackend raises UnsupportedBackendCapabilityError.

    Tests: the GitHubExtras capability gate (require_github_extras)
    How: Configure SQLiteBackend (supports_github_extras=False) as the active
        backend, then call list_milestones() — which calls get_github() first —
        and assert the typed error's structured fields.
    Why: This is the exact bug reported in backlog #2287: SQLite structurally
        satisfies GitHubExtras via isinstance, so the old gate let it reach a
        bare RuntimeError instead of a typed, caller-recognisable error. This
        test fails on pre-fix code with RuntimeError instead of
        UnsupportedBackendCapabilityError.
    """
    # Arrange
    set_config(BacklogConfig(backend=SQLiteBackend()))

    # Act / Assert
    with pytest.raises(UnsupportedBackendCapabilityError) as exc_info:
        operations.list_milestones()

    assert exc_info.value.backend == "SQLiteBackend"
    assert exc_info.value.capability == "github_extras"
    assert exc_info.value.operation == "get_github"


def test_list_issues_under_sqlite_backend_raises_typed_capability_error_not_wrapped() -> None:
    """list_issues() under SQLiteBackend raises UnsupportedBackendCapabilityError, not a generic BacklogError.

    Tests: list_issues()'s ``except (GithubException, BacklogError)`` handler
        does not re-wrap UnsupportedBackendCapabilityError.
    How: Configure SQLiteBackend as the active backend, call list_issues(),
        and assert the raised exception is still UnsupportedBackendCapabilityError
        with its structured fields intact.
    Why: list_issues(), comment_issue(), list_comments(), and read_comment()
        each catch ``(GithubException, BacklogError)`` around their internal
        ``get_github()`` call and re-raise a generic ``BacklogError`` labeled
        "GitHub API error: ...", discarding the capability/backend/operation
        fields. This test fails (wrong exception type, and ``.capability``
        raises ``AttributeError``) without the
        ``except UnsupportedBackendCapabilityError: raise`` guard preceding
        that generic handler.
    """
    # Arrange
    set_config(BacklogConfig(backend=SQLiteBackend()))

    # Act / Assert
    with pytest.raises(UnsupportedBackendCapabilityError) as exc_info:
        operations.list_issues()

    assert exc_info.value.backend == "SQLiteBackend"
    assert exc_info.value.capability == "github_extras"
    assert "GitHub API error" not in str(exc_info.value)
