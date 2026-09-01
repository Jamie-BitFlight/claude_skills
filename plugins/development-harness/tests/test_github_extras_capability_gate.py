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

from collections.abc import Iterator

import pytest
from backlog_core import operations
from backlog_core.backend_protocol import reset_config, set_config
from backlog_core.backend_types import BacklogConfig
from backlog_core.backends.sqlite_backend import SQLiteBackend
from backlog_core.models import UnsupportedBackendCapabilityError


@pytest.fixture
def sqlite_backend() -> Iterator[SQLiteBackend]:
    """Configure an in-memory SQLiteBackend as the active backend, then tear it down.

    Closes the backend's sqlite3.Connection and resets the config singleton on
    teardown — a bare `SQLiteBackend()` with no cleanup leaves its connection
    open, which fails this repo's strict warning-as-error validation policy
    (AGENTS.md #18) with a ResourceWarning/PytestUnraisableExceptionWarning.
    """
    backend = SQLiteBackend()
    set_config(BacklogConfig(backend=backend))
    yield backend
    reset_config()
    backend._conn.close()


def test_list_milestones_under_sqlite_backend_no_longer_requires_github_extras(sqlite_backend: SQLiteBackend) -> None:
    """list_milestones() under SQLiteBackend no longer routes through get_github().

    Tests: slice C's milestone capability gate (require_milestone_support)
        supersedes the old GitHubExtras-only routing for milestones.
    How: Configure SQLiteBackend (supports_github_extras=False, but
        supports_milestones=True as of slice C) as the active backend, then
        call list_milestones() — it must succeed (empty list), not raise.
    Why: Before slice C, list_milestones() called get_github() unconditionally,
        so every non-GitHub backend raised UnsupportedBackendCapabilityError
        for the "github_extras" capability regardless of whether it could
        genuinely support milestones. Slice C gives SQLite (and Memory) a
        real milestone implementation, gated on the new "milestones"
        capability instead — this test fails if that routing regresses back
        to the GitHubExtras gate.
    """
    # Act
    result = operations.list_milestones()

    # Assert
    assert result["milestones"] == []
    assert result["count"] == 0


def test_list_milestones_under_beads_backend_raises_typed_milestones_capability_error() -> None:
    """list_milestones() under BeadsBackend raises UnsupportedBackendCapabilityError for "milestones".

    Tests: require_milestone_support() gates on supports_milestones, not
        supports_github_extras.
    How: Configure a BeadsBackend (supports_milestones=False — beads
        milestone IDs are strings, see ADR-003 in beads_backend.py) as the
        active backend, then call list_milestones() and assert the typed
        error's structured fields name the "milestones" capability.
    Why: BeadsBackend is the one backend that genuinely cannot satisfy the
        int-typed generic milestone Protocol methods; this proves it still
        fails loudly with a typed, caller-recognisable error rather than a
        bare NotImplementedError leaking out of operations.py.
    """
    from unittest.mock import MagicMock

    from backlog_core.backends.beads_backend import BeadsBackend

    backend = BeadsBackend(runner=MagicMock())
    set_config(BacklogConfig(backend=backend))
    try:
        with pytest.raises(UnsupportedBackendCapabilityError) as exc_info:
            operations.list_milestones()
    finally:
        reset_config()

    assert exc_info.value.backend == "BeadsBackend"
    assert exc_info.value.capability == "milestones"
    assert exc_info.value.operation == "list_milestones"


def test_list_issues_under_sqlite_backend_raises_typed_capability_error_not_wrapped(
    sqlite_backend: SQLiteBackend,
) -> None:
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
    # Act / Assert
    with pytest.raises(UnsupportedBackendCapabilityError) as exc_info:
        operations.list_issues()

    assert exc_info.value.backend == "SQLiteBackend"
    assert exc_info.value.capability == "github_extras"
    assert "GitHub API error" not in str(exc_info.value)
