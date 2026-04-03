"""Integration branch lifecycle management for the backlog MCP package.

Provides five PyGithub functions for creating, inspecting, merging, deleting,
and listing milestone integration branches.  All functions follow the
established patterns from ``gh_client.py``: ``get_github()`` for auth,
``Output`` parameter for status messages, ``GithubException`` catch-and-warn,
:func:`~backlog_core.models.resolve_repo` for repo slug resolution.

Branch naming convention: ``milestone/{N}-{slug}``
  e.g. ``milestone/3-v1.1-milestone-workflow``
"""

from __future__ import annotations

import logging
import operator
import re
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from github import GithubException

from .gh_client import _HTTP_NOT_FOUND, get_github
from .models import BacklogError, BranchConflictError, BranchInfo, MergeResult, Output, resolve_repo

if TYPE_CHECKING:
    from github.Branch import Branch
    from github.Repository import Repository

logger = logging.getLogger(__name__)

BRANCH_PREFIX = "milestone/"

# GitHub API status code for merge conflicts
_HTTP_CONFLICT = 409
_HTTP_UNPROCESSABLE = 422

# Slug validation: must start with alphanumeric and contain only alphanumeric, dots, underscores, hyphens
_SLUG_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")


def _validate_slug(slug: str) -> None:
    """Validate slug against the required pattern.

    Args:
        slug: Hyphenated slug string to validate.

    Raises:
        BacklogError: If slug does not match ``^[a-zA-Z0-9][a-zA-Z0-9._-]*$``.
    """
    if not _SLUG_PATTERN.match(slug):
        msg = (
            f"Invalid slug '{slug}': must match {_SLUG_PATTERN.pattern} "
            "(start with alphanumeric, contain only alphanumeric, dots, underscores, hyphens)"
        )
        raise BacklogError(msg)


def _validate_milestone_number(milestone_number: int) -> None:
    """Validate milestone_number is a positive integer.

    Args:
        milestone_number: Milestone number to validate.

    Raises:
        BacklogError: If milestone_number is not greater than zero.
    """
    if milestone_number <= 0:
        msg = f"Invalid milestone_number {milestone_number}: must be greater than zero"
        raise BacklogError(msg)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _branch_name(milestone_number: int, slug: str) -> str:
    """Build the canonical branch name for a milestone.

    Args:
        milestone_number: Milestone number (e.g. 3).
        slug: Hyphenated slug (e.g. ``v1.1-milestone-workflow``).

    Returns:
        Full branch name, e.g. ``milestone/3-v1.1-milestone-workflow``.
    """
    return f"{BRANCH_PREFIX}{milestone_number}-{slug}"


def _get_repo(repo: str) -> Repository:
    """Authenticate and return a PyGithub Repository object.

    Args:
        repo: ``owner/repo`` slug, or empty string to use the default.

    Returns:
        PyGithub ``Repository`` object.

    Raises:
        GitHubUnavailableError: If ``GITHUB_TOKEN`` is not set.
    """
    return get_github(resolve_repo(repo))


def _branch_info_from_branch(branch: Branch) -> BranchInfo:
    """Convert a PyGithub Branch object to a ``BranchInfo`` TypedDict.

    Args:
        branch: PyGithub ``Branch`` object.

    Returns:
        Populated ``BranchInfo``.
    """
    commit = branch.commit
    sha = commit.sha
    raw_date = commit.commit.author.date
    if isinstance(raw_date, datetime):
        last_commit_dt = raw_date.replace(tzinfo=UTC) if raw_date.tzinfo is None else raw_date
    else:
        # Fallback: parse ISO string
        last_commit_dt = datetime.fromisoformat(str(raw_date))

    now = datetime.now(tz=UTC)
    age_days = (now - last_commit_dt).days

    return BranchInfo(
        name=branch.name, sha=sha, last_commit_date=last_commit_dt.strftime("%Y-%m-%dT%H:%M:%SZ"), age_days=age_days
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def create_integration_branch(
    milestone_number: int, slug: str, *, base_branch: str = "main", repo: str = "", output: Output | None = None
) -> BranchInfo:
    """Create a branch named ``milestone/{N}-{slug}`` from the HEAD of ``base_branch``.

    Args:
        milestone_number: Milestone number (e.g. 3).
        slug: Hyphenated slug (e.g. ``v1.1-milestone-workflow``).
        base_branch: Branch to fork from. Defaults to ``main``.
        repo: Repository in ``owner/repo`` format.
        output: Optional Output collector.

    Returns:
        BranchInfo with branch name and HEAD SHA.

    Raises:
        GitHubUnavailableError: If GITHUB_TOKEN is not set.
        BacklogError: If the branch already exists (caller decides
            delete-and-recreate vs resume).
        GithubException: On unexpected GitHub API failure.
    """
    _validate_milestone_number(milestone_number)
    _validate_slug(slug)
    name = _branch_name(milestone_number, slug)
    gh_repo = _get_repo(repo)

    # Resolve base branch HEAD SHA
    try:
        base = gh_repo.get_branch(base_branch)
    except GithubException as exc:
        if exc.status == _HTTP_NOT_FOUND:
            msg = f"Base branch '{base_branch}' not found in {resolve_repo(repo)}"
            raise BacklogError(msg) from exc
        raise

    base_sha = base.commit.sha

    # Create the new branch ref
    ref_path = f"refs/heads/{name}"
    try:
        gh_repo.create_git_ref(ref=ref_path, sha=base_sha)
    except GithubException as exc:
        if exc.status == _HTTP_UNPROCESSABLE:
            msg = f"Branch '{name}' already exists in {resolve_repo(repo)}"
            if output:
                output.warn(msg)
            raise BacklogError(msg) from exc
        raise

    if output:
        output.info(f"Created branch '{name}' from '{base_branch}' ({base_sha[:8]})")

    new_branch = gh_repo.get_branch(name)
    return _branch_info_from_branch(new_branch)


def get_integration_branch_status(
    branch_name: str, *, repo: str = "", output: Output | None = None
) -> BranchInfo | None:
    """Return HEAD SHA and last-commit timestamp for a branch.

    Non-raising on branch-not-found: returns ``None`` if the branch does not exist.

    Args:
        branch_name: Full branch name (e.g. ``milestone/3-v1.1-milestone-workflow``).
        repo: Repository in ``owner/repo`` format.
        output: Optional Output collector.

    Returns:
        BranchInfo if the branch exists, None otherwise.

    Raises:
        GitHubUnavailableError: If GITHUB_TOKEN is not set.
        GithubException: On unexpected GitHub API failure (not 404).
    """
    gh_repo = _get_repo(repo)

    try:
        branch = gh_repo.get_branch(branch_name)
    except GithubException as exc:
        if exc.status == _HTTP_NOT_FOUND:
            if output:
                output.info(f"Branch '{branch_name}' not found")
            return None
        raise

    info = _branch_info_from_branch(branch)
    if output:
        output.info(f"Branch '{branch_name}' at {info['sha'][:8]} ({info['age_days']}d old)")
    return info


def merge_integration_branch(
    head_branch: str, base_branch: str, commit_message: str, *, repo: str = "", output: Output | None = None
) -> MergeResult:
    """Merge ``head_branch`` into ``base_branch``.

    Uses PyGithub's ``repo.merge()`` for the merge operation.

    Two merge directions are supported by the same function:

    - Worker -> integration:
      ``merge_integration_branch("worktree/item-42-auth", "milestone/3-slug", "...")``
    - Integration -> main:
      ``merge_integration_branch("milestone/3-slug", "main", "...")``

    Args:
        head_branch: Source branch name to merge from.
        base_branch: Target branch name to merge into.
        commit_message: Descriptive commit message for the merge.
        repo: Repository in ``owner/repo`` format.
        output: Optional Output collector.

    Returns:
        MergeResult with the new HEAD SHA and merge message.

    Raises:
        GitHubUnavailableError: If GITHUB_TOKEN is not set.
        BranchConflictError: If the merge has conflicts.
        GithubException: On unexpected GitHub API failure.
    """
    if head_branch == base_branch:
        msg = f"head_branch and base_branch must differ: both are '{head_branch}'"
        raise BacklogError(msg)
    gh_repo = _get_repo(repo)

    try:
        merge_commit = gh_repo.merge(base=base_branch, head=head_branch, commit_message=commit_message)
    except GithubException as exc:
        if exc.status == _HTTP_CONFLICT:
            if output:
                output.warn(f"Merge conflict: '{head_branch}' -> '{base_branch}'")
            raise BranchConflictError(head_branch=head_branch, base_branch=base_branch, conflict_files=[]) from exc
        raise

    # merge_commit is None when head is already up-to-date (HTTP 204)
    if merge_commit is None:
        if output:
            output.info(f"'{head_branch}' already merged into '{base_branch}' (no-op)")
        # Return current HEAD of base branch as sha
        base = gh_repo.get_branch(base_branch)
        return MergeResult(sha=base.commit.sha, message=commit_message)

    sha = merge_commit.sha
    if output:
        output.info(f"Merged '{head_branch}' -> '{base_branch}' ({sha[:8]})")
    return MergeResult(sha=sha, message=commit_message)


def delete_integration_branch(branch_name: str, *, repo: str = "", output: Output | None = None) -> bool:
    """Delete a branch by name. Idempotent: returns True even if already deleted.

    Args:
        branch_name: Full branch name (e.g. ``milestone/3-v1.1-milestone-workflow``).
        repo: Repository in ``owner/repo`` format.
        output: Optional Output collector.

    Returns:
        True if the branch was deleted or was already absent; False on
        unexpected failure (the GithubException is not re-raised so callers
        can treat deletion as best-effort).
    """
    gh_repo = _get_repo(repo)
    ref_path = f"heads/{branch_name}"

    try:
        ref = gh_repo.get_git_ref(ref_path)
        ref.delete()
    except GithubException as exc:
        if exc.status == _HTTP_NOT_FOUND:
            if output:
                output.info(f"Branch '{branch_name}' already absent (idempotent delete)")
            return True
        if output:
            output.warn(f"Failed to delete branch '{branch_name}': {exc}")
        logger.warning("delete_integration_branch failed for '%s': %s", branch_name, exc)
        return False
    else:
        if output:
            output.info(f"Deleted branch '{branch_name}'")
        return True


def list_integration_branches(*, repo: str = "", output: Output | None = None) -> list[BranchInfo]:
    """List all branches matching the ``milestone/`` prefix.

    Args:
        repo: Repository in ``owner/repo`` format.
        output: Optional Output collector.

    Returns:
        List of BranchInfo for each matching branch, sorted by last commit
        date (most recent first). Empty list if none found or on GitHub error.
    """
    gh_repo = _get_repo(repo)

    results: list[BranchInfo] = []
    try:
        results.extend(
            _branch_info_from_branch(branch)
            for branch in gh_repo.get_branches()
            if branch.name.startswith(BRANCH_PREFIX)
        )
    except GithubException as exc:
        if output:
            output.warn(f"Error listing branches: {exc}")
        logger.warning("list_integration_branches error: %s", exc)
        return []

    results.sort(key=operator.itemgetter("last_commit_date"), reverse=True)

    if output:
        output.info(f"Found {len(results)} integration branch(es)")
    return results
