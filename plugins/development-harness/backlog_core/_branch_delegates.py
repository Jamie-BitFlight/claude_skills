"""Branch operation delegates — thin wrappers routing through the active BacklogBackend."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .backend_protocol import get_config

if TYPE_CHECKING:
    from .models import BranchInfo, MergeResult, Output

__all__ = [
    "create_integration_branch",
    "delete_integration_branch",
    "get_integration_branch_status",
    "list_integration_branches",
    "merge_integration_branch",
]


def create_integration_branch(
    milestone_number: int, slug: str, *, base_branch: str = "main", repo: str = "", output: Output | None = None
) -> BranchInfo:
    """Create an integration branch for a milestone via the active backend.

    Args:
        milestone_number: Milestone number for naming the branch.
        slug: Short identifier appended to the branch name.
        base_branch: Base branch to branch from.
        repo: Optional ``owner/name`` string.
        output: Optional Output collector.

    Returns:
        BranchInfo describing the created branch.
    """
    return get_config().backend.create_integration_branch(
        milestone_number, slug, base_branch=base_branch, repo=repo, output=output
    )


def get_integration_branch_status(
    branch_name: str, *, repo: str = "", output: Output | None = None
) -> BranchInfo | None:
    """Get the current status of an integration branch via the active backend.

    Args:
        branch_name: Full branch name to query.
        repo: Optional ``owner/name`` string.
        output: Optional Output collector.

    Returns:
        BranchInfo, or None if the branch does not exist.
    """
    return get_config().backend.get_integration_branch_status(branch_name, repo=repo, output=output)


def merge_integration_branch(
    head_branch: str, base_branch: str, commit_message: str, *, repo: str = "", output: Output | None = None
) -> MergeResult:
    """Merge an integration branch into a base branch via the active backend.

    Args:
        head_branch: Source branch to merge from.
        base_branch: Target branch to merge into.
        commit_message: Commit message for the merge commit.
        repo: Optional ``owner/name`` string.
        output: Optional Output collector.

    Returns:
        MergeResult with merge outcome.
    """
    return get_config().backend.merge_integration_branch(
        head_branch, base_branch, commit_message, repo=repo, output=output
    )


def delete_integration_branch(branch_name: str, *, repo: str = "", output: Output | None = None) -> bool:
    """Delete an integration branch via the active backend.

    Args:
        branch_name: Full branch name to delete.
        repo: Optional ``owner/name`` string.
        output: Optional Output collector.

    Returns:
        True if the branch was deleted, False if it did not exist.
    """
    return get_config().backend.delete_integration_branch(branch_name, repo=repo, output=output)


def list_integration_branches(*, repo: str = "", output: Output | None = None) -> list[BranchInfo]:
    """List all integration branches via the active backend.

    Args:
        repo: Optional ``owner/name`` string.
        output: Optional Output collector.

    Returns:
        List of BranchInfo for all integration branches.
    """
    return get_config().backend.list_integration_branches(repo=repo, output=output)
