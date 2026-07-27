"""BranchBackend protocol tests — Git branch CRUD surface.

Parametrizes the ``BranchBackend`` methods
(``create_integration_branch``, ``get_integration_branch_status``,
``list_integration_branches``, ``delete_integration_branch``) over backends
where ``supports_branches`` is True.  Currently: ``GitHubBackend`` (skipped
unless ``BACKLOG_CROSS_BACKEND_GITHUB`` is set) and ``InMemoryBackend``.
``SQLiteBackend`` has ``supports_branches = False`` and is skipped.

Marked with ``pytest.mark.cross_backend`` — excluded from the default pytest
run and executed exclusively by the ``test-cross-backend`` CI matrix job.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest
from backlog_core.backend_types import BranchBackend, WorkItemBackend
from github.Repository import Repository as GithubRepository

pytestmark = pytest.mark.cross_backend

_MOCK_REPO: GithubRepository = MagicMock(spec=GithubRepository)

_GITHUB_MARKER = pytest.mark.skipif(
    not os.environ.get("BACKLOG_CROSS_BACKEND_GITHUB"),
    reason="Set BACKLOG_CROSS_BACKEND_GITHUB=1 to run GitHub backend tests",
)


@pytest.fixture(
    params=[
        pytest.param("memory", id="InMemoryBackend"),
        pytest.param("github", id="GitHubBackend", marks=_GITHUB_MARKER),
    ]
)
def branch_backend(request: pytest.FixtureRequest) -> BranchBackend:
    """Return a backend that supports branch operations.

    Skips backends where ``supports_branches`` is False (defensive guard;
    ``SQLiteBackend`` is not in the parametrization, but a future backend
    added here with the flag off should skip rather than raise).
    """
    name: str = request.param
    if name == "memory":
        from backlog_core.backends.memory_backend import InMemoryBackend

        backend: WorkItemBackend = InMemoryBackend()
    else:  # github — only reached when BACKLOG_CROSS_BACKEND_GITHUB is set
        from backlog_core.backends.github_backend import GitHubBackend

        backend = GitHubBackend()

    if not getattr(backend, "supports_branches", False):
        pytest.skip("backend does not support branch operations")
    return backend  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# TestBranchOps — create / get / list / delete integration branches.
# ---------------------------------------------------------------------------


class TestBranchOps:
    """Integration branch CRUD: create / get / list / delete."""

    def test_create_branch_returns_branch_info(self, branch_backend: BranchBackend) -> None:
        """create_integration_branch returns a BranchInfo with a non-empty name.

        Why: BranchInfo.name is the canonical branch identifier used by all
             downstream operations; an empty name breaks every branch op.
        """
        # Arrange / Act
        info = branch_backend.create_integration_branch(42, "feature-slug")

        # Assert
        assert info["name"] != ""
        assert "42" in info["name"]

    def test_get_nonexistent_branch_returns_none(self, branch_backend: BranchBackend) -> None:
        """get_integration_branch_status returns None for a branch that does not exist.

        Why: None signals callers to create the branch; KeyError would require
             a try/except that the protocol does not mandate.
        """
        # Act
        result = branch_backend.get_integration_branch_status("milestone/99-nonexistent")

        # Assert
        assert result is None

    def test_created_branch_appears_in_list(self, branch_backend: BranchBackend) -> None:
        """A created branch appears in list_integration_branches.

        Why: Branch listing drives milestone CI status; a created branch missing
             from the list would cause CI to believe no branch exists.
        """
        # Arrange
        branch_backend.create_integration_branch(7, "alpha")

        # Act
        branches = branch_backend.list_integration_branches()

        # Assert
        assert len(branches) >= 1
        assert any("7" in b["name"] for b in branches)

    def test_delete_branch_returns_true_and_removes_it(self, branch_backend: BranchBackend) -> None:
        """delete_integration_branch returns True and the branch is no longer listed.

        Why: Deletion must be idempotent-detectable; True signals a real delete
             rather than a no-op, letting callers log the action correctly.
        """
        # Arrange
        info = branch_backend.create_integration_branch(8, "beta")

        # Act
        deleted = branch_backend.delete_integration_branch(info["name"])
        after = branch_backend.get_integration_branch_status(info["name"])

        # Assert
        assert deleted is True
        assert after is None

    def test_delete_nonexistent_branch_returns_false(self, branch_backend: BranchBackend) -> None:
        """delete_integration_branch returns False for a branch that does not exist.

        Why: False signals a no-op to callers; an exception would require
             defensive try/except blocks throughout calling code.
        """
        # Act
        result = branch_backend.delete_integration_branch("milestone/999-ghost")

        # Assert
        assert result is False
