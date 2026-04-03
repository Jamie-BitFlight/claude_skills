"""BacklogBackend Protocol — implementation-agnostic abstraction for backlog storage.

This module defines the BacklogBackend Protocol and BacklogConfig dataclass.
Operations and server modules depend on this interface; GitHub-specific
implementations live in gh_client, github_sync, and github_branches.

All protocol methods are synchronous.  The MCP layer wraps calls in
``asyncio.to_thread()`` when needed — see ArtifactBackend in
artifact_provider.py for the established pattern.

Dependency direction (must remain acyclic):
    models <- backend_protocol
    backend_protocol is imported by: operations.py, server.py
    backend_protocol does NOT import from: gh_client, github_sync, github_branches
"""

from __future__ import annotations

import contextlib
import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast, runtime_checkable

if TYPE_CHECKING:
    import types

_dh_paths: types.ModuleType | None = None
with contextlib.suppress(ImportError):
    import dh_paths as _dh_paths  # optional — only present inside the plugin

from typing_extensions import Protocol

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import datetime

    from github.Repository import Repository

    from .models import (
        BackendStatus,
        BacklogItem,
        BranchInfo,
        IssueLocalFields,
        IssueStatus,
        MergeResult,
        Output,
        PullRequestRef,
        SamTask,
        ViewItemResult,
    )

__all__ = [
    "BacklogBackend",
    "BacklogConfig",
    "IssueCommentNode",
    "IssueNode",
    "MilestoneFullNode",
    "create_backend",
    "get_config",
    "reset_config",
]


# ---------------------------------------------------------------------------
# TypedDicts that the protocol surface requires (mirror gh_client definitions)
# ---------------------------------------------------------------------------

from typing_extensions import TypedDict


class LabelNode(TypedDict):
    """Label node from GraphQL response."""

    id: str
    name: str


class MilestoneNode(TypedDict):
    """Milestone node nested inside an IssueNode."""

    id: str
    number: int
    title: str


class AssigneeNode(TypedDict):
    """Assignee node from GraphQL response."""

    login: str


class IssueNode(TypedDict):
    """Single issue from GraphQL query. Maps to repository.issue or issues.nodes[].

    Re-exported here so callers can import from backend_protocol rather than gh_client,
    preserving the implementation-agnostic boundary.
    """

    id: str
    number: int
    title: str
    state: str  # "OPEN" | "CLOSED"
    body: str
    createdAt: str
    updatedAt: str
    labels: list[LabelNode]
    milestone: MilestoneNode | None
    assignees: list[AssigneeNode]


class IssueCommentNode(TypedDict):
    """Comment node returned from issue comments listing query."""

    id: str
    body: str
    url: str
    author: str
    created_at: str
    updated_at: str


class MilestoneFullNode(TypedDict):
    """Milestone from GraphQL query with issue counts."""

    id: str
    number: int
    title: str
    state: str  # "OPEN" | "CLOSED"
    description: str
    dueOn: str | None
    openIssueCount: int
    closedIssueCount: int


# ---------------------------------------------------------------------------
# BacklogBackend Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class BacklogBackend(Protocol):
    """Protocol defining the backend contract for backlog storage and operations.

    All methods are synchronous.  The MCP layer wraps calls in
    ``asyncio.to_thread()`` when needed.

    Method groups:
    - **Repository access**: get_github, try_get_github, probe_backend_status
    - **GraphQL utilities**: _graphql_request, _resolve_labels_graphql
    - **Issue CRUD**: _fetch_issue_graphql, _fetch_issues_graphql, _update_issue_graphql,
      sync_issues_graphql, create_issue_for_item, close_github_issue,
      resolve_github_issue, fetch_open_issues_by_title, fetch_github_issue_body,
      check_open_prs_for_issue, batch_fetch_statuses, fetch_item_status,
      view_enrich_from_github, issue_to_local_fields
    - **Issue comments**: _add_comment_graphql, _fetch_issue_comments_graphql,
      _fetch_comment_by_id_graphql, _update_issue_comment_graphql
    - **Status mutations**: apply_status_in_progress, apply_status_verified,
      apply_status_groomed, sync_groomed_to_github_issue
    - **Milestones / projects**: _fetch_milestones_graphql,
      _projects_v2_list_query, _projects_v2_create_mutation
    - **Task issues**: create_task_issue, get_task_issues, update_task_status
    - **Sync / serialisation**: render_issue_body, parse_issue_body, merge_item,
      unknown_key_to_heading
    - **Branches**: create_integration_branch, get_integration_branch_status,
      merge_integration_branch, delete_integration_branch, list_integration_branches
    """

    # ------------------------------------------------------------------
    # Repository access
    # ------------------------------------------------------------------

    def get_github(self, repo: str = "", timeout: int = 15) -> Repository:
        """Return a PyGithub Repository (raises GitHubUnavailableError on failure).

        Args:
            repo: Optional ``owner/name`` string; resolved from env when empty.
            timeout: Connection timeout in seconds.

        Returns:
            Authenticated PyGithub Repository object.
        """
        ...

    def try_get_github(self, repo: str = "") -> Repository | None:
        """Return a PyGithub Repository or None if unavailable.

        Args:
            repo: Optional ``owner/name`` string; resolved from env when empty.

        Returns:
            Authenticated PyGithub Repository, or None on any failure.
        """
        ...

    def probe_backend_status(self, repo: str = "") -> BackendStatus:
        """Check backend availability and return a status report.

        Args:
            repo: Optional ``owner/name`` string; resolved from env when empty.

        Returns:
            BackendStatus with availability enum, last_check timestamp, and message.
        """
        ...

    # ------------------------------------------------------------------
    # GraphQL utilities
    # ------------------------------------------------------------------

    def _graphql_request(
        self, repo: Repository, query: str, variables: dict[str, object] | None = None
    ) -> dict[str, Any]:
        """Execute a raw GraphQL query/mutation against the backend.

        Args:
            repo: PyGithub Repository (provides transport).
            query: GraphQL query or mutation string.
            variables: Optional variable mapping.

        Returns:
            Parsed JSON response dict.
        """
        ...

    def _resolve_labels_graphql(
        self, repo: Repository, repo_owner: str, repo_name: str, label_names: list[str]
    ) -> list[str]:
        """Resolve label names to backend node IDs.

        Args:
            repo: PyGithub Repository.
            repo_owner: Repository owner login.
            repo_name: Repository name.
            label_names: Human-readable label names.

        Returns:
            List of node ID strings corresponding to the given names.
        """
        ...

    # ------------------------------------------------------------------
    # Issue CRUD
    # ------------------------------------------------------------------

    def _fetch_issue_graphql(self, repo: Repository, owner: str, repo_name: str, issue_number: int) -> IssueNode:
        """Fetch a single issue by number.

        Args:
            repo: PyGithub Repository.
            owner: Repository owner login.
            repo_name: Repository name.
            issue_number: Issue number to fetch.

        Returns:
            IssueNode TypedDict with issue fields.
        """
        ...

    def _fetch_issues_graphql(
        self,
        repo: Repository,
        owner: str,
        repo_name: str,
        state: str = "OPEN",
        labels: list[str] | None = None,
        milestone_number: int | None = None,
        first: int = 100,
        since: str | None = None,
    ) -> list[IssueNode]:
        """Fetch multiple issues with optional filters.

        Args:
            repo: PyGithub Repository.
            owner: Repository owner login.
            repo_name: Repository name.
            state: Issue state filter ("OPEN" or "CLOSED").
            labels: Optional label names to filter by.
            milestone_number: Optional milestone number to filter by.
            first: Maximum number of issues to return.
            since: Optional ISO 8601 timestamp to filter by update time.

        Returns:
            List of IssueNode TypedDicts.
        """
        ...

    def _update_issue_graphql(
        self,
        repo: Repository,
        issue_node_id: str,
        *,
        state: str | None = None,
        body: str | None = None,
        title: str | None = None,
        label_ids: list[str] | None = None,
        milestone_id: str | None = None,
    ) -> None:
        """Update an issue's mutable fields via mutation.

        Args:
            repo: PyGithub Repository.
            issue_node_id: GraphQL node ID of the issue.
            state: New state ("OPEN" or "CLOSED"), or None to leave unchanged.
            body: New body markdown, or None to leave unchanged.
            title: New title, or None to leave unchanged.
            label_ids: Replacement label node IDs, or None to leave unchanged.
            milestone_id: Replacement milestone node ID, or None to leave unchanged.
        """
        ...

    def sync_issues_graphql(
        self,
        repo: Repository,
        owner: str,
        repo_name: str,
        *,
        state: str = "OPEN",
        labels: list[str] | None = None,
        milestone_number: int | None = None,
        since: datetime | None = None,
        callback: Callable[[IssueNode], None] | None = None,
        track_timestamp: bool = False,
    ) -> list[IssueNode]:
        """Bulk-fetch issues with optional progress callback.

        Args:
            repo: PyGithub Repository.
            owner: Repository owner login.
            repo_name: Repository name.
            state: Issue state filter.
            labels: Optional label names to filter by.
            milestone_number: Optional milestone number to filter by.
            since: Optional datetime to filter issues updated after this time.
            callback: Optional function called for each fetched IssueNode.
            track_timestamp: When True, persist the sync timestamp.

        Returns:
            List of IssueNode TypedDicts.
        """
        ...

    def create_issue_for_item(
        self, repo: Repository, item: BacklogItem, dry_run: bool = False, output: Output | None = None
    ) -> int | None:
        """Create a backend issue from a BacklogItem.

        Args:
            repo: PyGithub Repository.
            item: BacklogItem to create an issue for.
            dry_run: When True, log the action but do not create the issue.
            output: Optional Output collector for progress messages.

        Returns:
            Issue number on success, or None on failure / dry_run.
        """
        ...

    def close_github_issue(
        self,
        issue_ref: str,
        reason: str,
        *,
        reference: str = "",
        comment: str = "",
        repo: str = "",
        output: Output | None = None,
    ) -> None:
        """Close an issue with a reason comment.

        Args:
            issue_ref: Issue reference (number or selector string).
            reason: Human-readable reason for closing.
            reference: Optional URL or issue reference explaining the close.
            comment: Optional additional comment body.
            repo: Optional ``owner/name`` string.
            output: Optional Output collector.
        """
        ...

    def resolve_github_issue(
        self,
        issue_ref: str,
        *,
        summary: str,
        method: str = "",
        notes: str = "",
        follow_ups: str = "",
        findings: str = "",
        repo: str = "",
        output: Output | None = None,
    ) -> None:
        """Resolve an issue with a structured resolution comment.

        Args:
            issue_ref: Issue reference (number or selector string).
            summary: Resolution summary text.
            method: Resolution method description.
            notes: Additional notes.
            follow_ups: Follow-up action items.
            findings: Key findings from the investigation.
            repo: Optional ``owner/name`` string.
            output: Optional Output collector.
        """
        ...

    def fetch_open_issues_by_title(self, repo: Repository) -> dict[str, int]:
        """Return a mapping of open issue titles to issue numbers.

        Args:
            repo: PyGithub Repository.

        Returns:
            Dict mapping issue title string to issue number int.
        """
        ...

    def fetch_github_issue_body(self, repo_obj: Repository, issue_num: int, output: Output | None = None) -> str | None:
        """Fetch the raw body of an issue.

        Args:
            repo_obj: PyGithub Repository.
            issue_num: Issue number.
            output: Optional Output collector.

        Returns:
            Issue body markdown string, or None on failure.
        """
        ...

    def check_open_prs_for_issue(self, issue_num: int, repo: str = "") -> list[PullRequestRef]:
        """Find open pull requests referencing a given issue.

        Args:
            issue_num: Issue number to search for.
            repo: Optional ``owner/name`` string.

        Returns:
            List of PullRequestRef models for each matching PR.
        """
        ...

    def batch_fetch_statuses(self, items: list[BacklogItem], repo: str = "") -> dict[int, IssueStatus]:
        """Fetch the current status for multiple items in one operation.

        Args:
            items: BacklogItems to query (must have issue_number set).
            repo: Optional ``owner/name`` string.

        Returns:
            Dict mapping issue_number to IssueStatus model.
        """
        ...

    def fetch_item_status(self, item: BacklogItem, repo: str = "", output: Output | None = None) -> str:
        """Fetch the current status string for a single item.

        Args:
            item: BacklogItem to query.
            repo: Optional ``owner/name`` string.
            output: Optional Output collector.

        Returns:
            Status string (e.g. "open", "closed").
        """
        ...

    def view_enrich_from_github(self, result: ViewItemResult, issue_num: str, repo: str = "") -> bool:
        """Enrich a ViewItemResult with live data from the backend.

        Args:
            result: ViewItemResult to enrich in place.
            issue_num: Issue number string.
            repo: Optional ``owner/name`` string.

        Returns:
            True if enrichment succeeded, False if the issue was not found.
        """
        ...

    def issue_to_local_fields(self, issue: IssueNode) -> IssueLocalFields:
        """Convert a raw IssueNode to a typed IssueLocalFields model.

        Args:
            issue: IssueNode TypedDict from a GraphQL response.

        Returns:
            IssueLocalFields model with parsed metadata.
        """
        ...

    # ------------------------------------------------------------------
    # Issue comments
    # ------------------------------------------------------------------

    def _add_comment_graphql(self, repo: Repository, issue_node_id: str, body: str) -> str:
        """Add a comment to an issue.

        Args:
            repo: PyGithub Repository.
            issue_node_id: GraphQL node ID of the issue.
            body: Comment body markdown.

        Returns:
            GraphQL node ID of the new comment.
        """
        ...

    def _fetch_issue_comments_graphql(
        self, repo: Repository, owner: str, repo_name: str, issue_number: int
    ) -> list[IssueCommentNode]:
        """Fetch all comments on an issue.

        Args:
            repo: PyGithub Repository.
            owner: Repository owner login.
            repo_name: Repository name.
            issue_number: Issue number.

        Returns:
            List of IssueCommentNode TypedDicts.
        """
        ...

    def _fetch_comment_by_id_graphql(self, repo: Repository, comment_node_id: str) -> IssueCommentNode:
        """Fetch a single comment by its GraphQL node ID.

        Args:
            repo: PyGithub Repository.
            comment_node_id: GraphQL node ID of the comment.

        Returns:
            IssueCommentNode TypedDict.
        """
        ...

    def _update_issue_comment_graphql(self, repo: Repository, comment_node_id: str, body: str) -> None:
        """Update an existing comment's body.

        Args:
            repo: PyGithub Repository.
            comment_node_id: GraphQL node ID of the comment.
            body: New comment body markdown.
        """
        ...

    # ------------------------------------------------------------------
    # Status mutations
    # ------------------------------------------------------------------

    def apply_status_in_progress(self, item: BacklogItem, repo: str = "", output: Output | None = None) -> None:
        """Transition an item to in-progress state on the backend.

        Args:
            item: BacklogItem to update.
            repo: Optional ``owner/name`` string.
            output: Optional Output collector.
        """
        ...

    def apply_status_verified(self, item: BacklogItem, repo: str = "", output: Output | None = None) -> None:
        """Transition an item to verified state on the backend.

        Args:
            item: BacklogItem to update.
            repo: Optional ``owner/name`` string.
            output: Optional Output collector.
        """
        ...

    def apply_status_groomed(self, item: BacklogItem, repo: str = "", output: Output | None = None) -> None:
        """Transition an item to groomed state on the backend.

        Args:
            item: BacklogItem to update.
            repo: Optional ``owner/name`` string.
            output: Optional Output collector.
        """
        ...

    def sync_groomed_to_github_issue(
        self,
        repo_obj: Repository,
        issue_num: int,
        groomed_content: str,
        section_name: str | None = None,
        output: Output | None = None,
    ) -> bool:
        """Write groomed content into a specific section of an issue body.

        Args:
            repo_obj: PyGithub Repository.
            issue_num: Issue number to update.
            groomed_content: Markdown content for the groomed section.
            section_name: Optional override for the section heading name.
            output: Optional Output collector.

        Returns:
            True if the issue body was updated, False if no change was needed.
        """
        ...

    # ------------------------------------------------------------------
    # Milestones and projects
    # ------------------------------------------------------------------

    def _fetch_milestones_graphql(
        self, repo: Repository, owner: str, repo_name: str, states: list[str] | None = None
    ) -> list[MilestoneFullNode]:
        """Fetch milestones from the backend.

        Args:
            repo: PyGithub Repository.
            owner: Repository owner login.
            repo_name: Repository name.
            states: Optional list of state filters (e.g. ["OPEN", "CLOSED"]).

        Returns:
            List of MilestoneFullNode TypedDicts.
        """
        ...

    def _projects_v2_list_query(self, owner: str, limit: int = 20) -> tuple[str, dict[str, object]]:
        """Build a ProjectsV2 list query string and variables.

        Args:
            owner: Repository owner login.
            limit: Maximum number of projects to return.

        Returns:
            Tuple of (query_string, variables_dict).
        """
        ...

    def _projects_v2_create_mutation(self, owner_id: str, title: str) -> tuple[str, dict[str, object]]:
        """Build a ProjectsV2 create mutation string and variables.

        Args:
            owner_id: GraphQL node ID of the owner (user or organisation).
            title: Title for the new project.

        Returns:
            Tuple of (mutation_string, variables_dict).
        """
        ...

    # ------------------------------------------------------------------
    # Task issues
    # ------------------------------------------------------------------

    def create_task_issue(
        self,
        repo: Repository,
        parent_issue_number: int,
        task: SamTask,
        description: str = "",
        acceptance_criteria: list[str] | None = None,
        labels: list[str] | None = None,
        output: Output | None = None,
    ) -> IssueNode | None:
        """Create a child issue for a SAM task under a parent issue.

        Args:
            repo: PyGithub Repository.
            parent_issue_number: Parent issue number to link.
            task: SamTask model describing the task.
            description: Optional additional description.
            acceptance_criteria: Optional list of acceptance criteria strings.
            labels: Optional label names to apply.
            output: Optional Output collector.

        Returns:
            IssueNode of the created issue, or None on failure.
        """
        ...

    def get_task_issues(
        self, repo: Repository, parent_issue_number: int, output: Output | None = None
    ) -> list[IssueNode]:
        """Fetch all child task issues for a parent issue.

        Args:
            repo: PyGithub Repository.
            parent_issue_number: Parent issue number.
            output: Optional Output collector.

        Returns:
            List of IssueNode TypedDicts for child task issues.
        """
        ...

    def update_task_status(
        self, repo: Repository, issue_number: int, new_status: str, output: Output | None = None
    ) -> bool:
        """Update the status label on a task issue.

        Args:
            repo: PyGithub Repository.
            issue_number: Issue number to update.
            new_status: New status string.
            output: Optional Output collector.

        Returns:
            True if the status was updated, False if no change was needed.
        """
        ...

    # ------------------------------------------------------------------
    # Sync / serialisation (mirrors github_sync public surface)
    # ------------------------------------------------------------------

    def render_issue_body(self, item: BacklogItem, original_body: str | None = None) -> str:
        """Serialise a BacklogItem to backend issue body markdown.

        Args:
            item: BacklogItem to serialise.
            original_body: Optional existing body to preserve non-managed sections.

        Returns:
            Markdown string suitable for use as an issue body.
        """
        ...

    def parse_issue_body(self, body: str, existing: BacklogItem | None = None) -> BacklogItem:
        """Deserialise a backend issue body into a BacklogItem.

        Args:
            body: Raw issue body markdown string.
            existing: Optional existing BacklogItem to merge parsed data into.

        Returns:
            Populated BacklogItem model.
        """
        ...

    def merge_item(self, local: BacklogItem, remote: BacklogItem) -> BacklogItem:
        """Merge a local BacklogItem with a remote version, resolving conflicts.

        Args:
            local: Local BacklogItem state.
            remote: Remote BacklogItem state fetched from the backend.

        Returns:
            Merged BacklogItem with conflicts resolved.
        """
        ...

    def unknown_key_to_heading(self, key: str) -> str:
        """Convert an unknown section key to a markdown heading string.

        Args:
            key: Section key string (e.g. ``"my_section"``).

        Returns:
            Heading text string (e.g. ``"My Section"``).
        """
        ...

    # ------------------------------------------------------------------
    # Integration branches (mirrors github_branches public surface)
    # ------------------------------------------------------------------

    def create_integration_branch(
        self,
        milestone_number: int,
        slug: str,
        *,
        base_branch: str = "main",
        repo: str = "",
        output: Output | None = None,
    ) -> BranchInfo:
        """Create an integration branch for a milestone.

        Args:
            milestone_number: Milestone number for naming the branch.
            slug: Short identifier appended to the branch name.
            base_branch: Base branch to branch from.
            repo: Optional ``owner/name`` string.
            output: Optional Output collector.

        Returns:
            BranchInfo TypedDict describing the created branch.
        """
        ...

    def get_integration_branch_status(
        self, branch_name: str, *, repo: str = "", output: Output | None = None
    ) -> BranchInfo | None:
        """Get the current status of an integration branch.

        Args:
            branch_name: Full branch name to query.
            repo: Optional ``owner/name`` string.
            output: Optional Output collector.

        Returns:
            BranchInfo TypedDict, or None if the branch does not exist.
        """
        ...

    def merge_integration_branch(
        self, head_branch: str, base_branch: str, commit_message: str, *, repo: str = "", output: Output | None = None
    ) -> MergeResult:
        """Merge an integration branch into a base branch.

        Args:
            head_branch: Source branch to merge from.
            base_branch: Target branch to merge into.
            commit_message: Commit message for the merge commit.
            repo: Optional ``owner/name`` string.
            output: Optional Output collector.

        Returns:
            MergeResult TypedDict with merge outcome.
        """
        ...

    def delete_integration_branch(self, branch_name: str, *, repo: str = "", output: Output | None = None) -> bool:
        """Delete an integration branch.

        Args:
            branch_name: Full branch name to delete.
            repo: Optional ``owner/name`` string.
            output: Optional Output collector.

        Returns:
            True if the branch was deleted, False if it did not exist.
        """
        ...

    def list_integration_branches(self, *, repo: str = "", output: Output | None = None) -> list[BranchInfo]:
        """List all integration branches in the repository.

        Args:
            repo: Optional ``owner/name`` string.
            output: Optional Output collector.

        Returns:
            List of BranchInfo TypedDicts for all integration branches.
        """
        ...


# ---------------------------------------------------------------------------
# BacklogConfig — holds the active backend instance
# ---------------------------------------------------------------------------


@dataclass
class BacklogConfig:
    """Container for the active BacklogBackend instance.

    This dataclass replaces direct imports from gh_client, github_sync, and
    github_branches.  Pass a BacklogConfig to operations and server functions
    so they can work against any conforming backend.

    Attributes:
        backend: The active BacklogBackend implementation.
    """

    backend: BacklogBackend


# ---------------------------------------------------------------------------
# Module-level config accessor
# ---------------------------------------------------------------------------

_active_config: BacklogConfig | None = None


def get_config() -> BacklogConfig:
    """Return the active BacklogConfig, auto-initialising on first call.

    Resolution order for the backend (when no config has been registered via
    :func:`set_config`):

    1. ``BACKLOG_BACKEND`` environment variable.
    2. ``[backend] name`` key in ``backend.toml`` (project root or ``~/.dh/``).
    3. Default: ``"github"``.

    The result is cached as a module-level singleton.  Call :func:`reset_config`
    to clear the cache (useful in tests).

    Returns:
        The active BacklogConfig instance.

    Raises:
        ValueError: When the resolved backend name is not recognised.
    """
    global _active_config  # noqa: PLW0603
    if _active_config is None:
        _active_config = BacklogConfig(backend=create_backend())
    return _active_config


def set_config(config: BacklogConfig) -> None:
    """Register the active BacklogConfig.

    Args:
        config: BacklogConfig instance wrapping the chosen backend implementation.
    """
    global _active_config  # noqa: PLW0603
    _active_config = config


def reset_config() -> None:
    """Clear the cached BacklogConfig singleton.

    Intended for test teardown — call this between tests to force the next
    ``get_config()`` call to re-run backend selection.
    """
    global _active_config  # noqa: PLW0603
    _active_config = None


# ---------------------------------------------------------------------------
# Backend factory
# ---------------------------------------------------------------------------

_VALID_BACKENDS: tuple[str, ...] = ("github", "memory", "sqlite")
_BACKEND_TOML_FILENAME = "backend.toml"


def _load_backend_toml_name() -> str | None:
    """Read backend name from backend.toml if present.

    Searches the project root (via dh_paths) then ``~/.dh/``.  Missing files
    are silently ignored.  A present file that lacks the ``backend.name`` key
    is also ignored.

    Returns:
        Backend name string from ``[backend] name = "..."`` if found,
        otherwise ``None``.
    """
    search_paths: list[Path] = []
    if _dh_paths is not None:
        try:
            project_root = _dh_paths.git_project_root()
            search_paths.append(project_root / _BACKEND_TOML_FILENAME)
        except (FileNotFoundError, RuntimeError):
            pass

    search_paths.append(Path.home() / ".dh" / _BACKEND_TOML_FILENAME)

    for candidate in search_paths:
        if candidate.is_file():
            try:
                data = tomllib.loads(candidate.read_text(encoding="utf-8"))
            except (OSError, tomllib.TOMLDecodeError):
                continue
            name = data.get("backend", {}).get("name")
            if isinstance(name, str) and name:
                return name

    return None


def create_backend(name: str | None = None) -> BacklogBackend:
    """Instantiate and return a BacklogBackend by name.

    Resolution order when *name* is ``None``:

    1. ``BACKLOG_BACKEND`` environment variable.
    2. ``[backend] name`` in ``backend.toml`` (project root or ``~/.dh/``).
    3. Default: ``"github"``.

    Args:
        name: Backend identifier to instantiate.  Pass ``None`` to trigger
            automatic resolution.

    Returns:
        Configured BacklogBackend instance.

    Raises:
        ValueError: When *name* (or the resolved name) is not a recognised
            backend identifier.  The message lists all valid options.
    """
    resolved = name or os.environ.get("BACKLOG_BACKEND") or _load_backend_toml_name() or "github"

    if resolved == "github":
        # Deferred import: backends import TypedDicts from this module — circular at top level.
        from backlog_core.backends.github_backend import GitHubBackend  # noqa: PLC0415

        return cast("BacklogBackend", GitHubBackend())

    if resolved == "memory":
        # Deferred import: backends import TypedDicts from this module — circular at top level.
        from backlog_core.backends.memory_backend import InMemoryBackend  # noqa: PLC0415

        return cast("BacklogBackend", InMemoryBackend())

    if resolved == "sqlite":
        # Deferred import: backends import TypedDicts from this module — circular at top level.
        from backlog_core.backends.sqlite_backend import SQLiteBackend  # noqa: PLC0415

        return cast("BacklogBackend", SQLiteBackend())

    msg = f"Unknown backend {resolved!r}. Valid options: {', '.join(sorted(_VALID_BACKENDS))}"
    raise ValueError(msg)
