"""GitHubBackend — concrete BacklogBackend delegating to gh_client, github_sync, github_branches.

This module provides a thin wrapper class that implements BacklogBackend by
delegating every method to the corresponding module-level function in
gh_client, github_sync, or github_branches.  No business logic lives here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from backlog_core import gh_client, github_branches, github_sync

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import datetime

    from github.Repository import Repository

    from backlog_core.gh_client import IssueCommentNode, IssueNode, MilestoneFullNode
    from backlog_core.models import (
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

__all__ = ["GitHubBackend"]


class GitHubBackend:
    """BacklogBackend implementation delegating to gh_client, github_sync, and github_branches.

    Each method is a 1-3 line delegation.  The constructor accepts an optional
    default repo string that is used when callers pass an empty ``repo`` argument.
    """

    def __init__(self, repo: str = "") -> None:
        """Initialise with an optional default repo string.

        Args:
            repo: Optional ``owner/name`` string used as default for repo-optional methods.
        """
        self._repo = repo

    # ------------------------------------------------------------------
    # Repository access
    # ------------------------------------------------------------------

    def get_github(self, repo: str = "", timeout: int = 15) -> Repository:
        """Return a PyGithub Repository (raises GitHubUnavailableError on failure).

        Returns:
            Authenticated PyGithub Repository object.
        """
        return gh_client.get_github(repo or self._repo, timeout)

    def try_get_github(self, repo: str = "") -> Repository | None:
        """Return a PyGithub Repository or None if unavailable.

        Returns:
            Authenticated PyGithub Repository, or None on any failure.
        """
        return gh_client.try_get_github(repo or self._repo)

    def probe_backend_status(self, repo: str = "") -> BackendStatus:
        """Check backend availability and return a status report.

        Returns:
            BackendStatus with availability enum, last_check timestamp, and message.
        """
        return gh_client.probe_backend_status(repo or self._repo)

    # ------------------------------------------------------------------
    # GraphQL utilities
    # ------------------------------------------------------------------

    def _graphql_request(
        self, repo: Repository, query: str, variables: dict[str, object] | None = None
    ) -> dict[str, Any]:
        """Execute a raw GraphQL query/mutation against the backend.

        Returns:
            Parsed JSON response dict.
        """
        return gh_client._graphql_request(repo, query, variables)

    def _resolve_labels_graphql(
        self, repo: Repository, repo_owner: str, repo_name: str, label_names: list[str]
    ) -> list[str]:
        """Resolve label names to backend node IDs.

        Returns:
            List of node ID strings corresponding to the given names.
        """
        return gh_client._resolve_labels_graphql(repo, repo_owner, repo_name, label_names)

    # ------------------------------------------------------------------
    # Issue CRUD
    # ------------------------------------------------------------------

    def _fetch_issue_graphql(self, repo: Repository, owner: str, repo_name: str, issue_number: int) -> IssueNode:
        """Fetch a single issue by number.

        Returns:
            IssueNode TypedDict with issue fields.
        """
        return gh_client._fetch_issue_graphql(repo, owner, repo_name, issue_number)

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

        Returns:
            List of IssueNode TypedDicts.
        """
        return gh_client._fetch_issues_graphql(repo, owner, repo_name, state, labels, milestone_number, first, since)

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
        """Update an issue's mutable fields via mutation."""
        gh_client._update_issue_graphql(
            repo, issue_node_id, state=state, body=body, title=title, label_ids=label_ids, milestone_id=milestone_id
        )

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

        Returns:
            List of IssueNode TypedDicts.
        """
        return gh_client.sync_issues_graphql(
            repo,
            owner,
            repo_name,
            state=state,
            labels=labels,
            milestone_number=milestone_number,
            since=since,
            callback=callback,
            track_timestamp=track_timestamp,
        )

    def create_issue_for_item(
        self, repo: Repository, item: BacklogItem, dry_run: bool = False, output: Output | None = None
    ) -> int | None:
        """Create a backend issue from a BacklogItem.

        Returns:
            Issue number on success, or None on failure / dry_run.
        """
        return gh_client.create_issue_for_item(repo, item, dry_run, output)

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
        """Close an issue with a reason comment."""
        gh_client.close_github_issue(
            issue_ref, reason, reference=reference, comment=comment, repo=repo or self._repo, output=output
        )

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
        """Resolve an issue with a structured resolution comment."""
        gh_client.resolve_github_issue(
            issue_ref,
            summary=summary,
            method=method,
            notes=notes,
            follow_ups=follow_ups,
            findings=findings,
            repo=repo or self._repo,
            output=output,
        )

    def fetch_open_issues_by_title(self, repo: Repository) -> dict[str, int]:
        """Return a mapping of open issue titles to issue numbers.

        Returns:
            Dict mapping issue title string to issue number int.
        """
        return gh_client.fetch_open_issues_by_title(repo)

    def fetch_github_issue_body(self, repo_obj: Repository, issue_num: int, output: Output | None = None) -> str | None:
        """Fetch the raw body of an issue.

        Returns:
            Issue body markdown string, or None on failure.
        """
        return gh_client.fetch_github_issue_body(repo_obj, issue_num, output)

    def check_open_prs_for_issue(self, issue_num: int, repo: str = "") -> list[PullRequestRef]:
        """Find open pull requests referencing a given issue.

        Returns:
            List of PullRequestRef models for each matching PR.
        """
        return gh_client.check_open_prs_for_issue(issue_num, repo or self._repo)

    def batch_fetch_statuses(self, items: list[BacklogItem], repo: str = "") -> dict[int, IssueStatus]:
        """Fetch the current status for multiple items in one operation.

        Returns:
            Dict mapping issue_number to IssueStatus model.
        """
        return gh_client.batch_fetch_statuses(items, repo or self._repo)

    def fetch_item_status(self, item: BacklogItem, repo: str = "", output: Output | None = None) -> str:
        """Fetch the current status string for a single item.

        Returns:
            Status string (e.g. "open", "closed").
        """
        return gh_client.fetch_item_status(item, repo or self._repo, output)

    def view_enrich_from_github(self, result: ViewItemResult, issue_num: str, repo: str = "") -> bool:
        """Enrich a ViewItemResult with live data from the backend.

        Returns:
            True if enrichment succeeded, False if the issue was not found.
        """
        return gh_client.view_enrich_from_github(result, issue_num, repo or self._repo)

    def issue_to_local_fields(self, issue: IssueNode) -> IssueLocalFields:
        """Convert a raw IssueNode to a typed IssueLocalFields model.

        Returns:
            IssueLocalFields model with parsed metadata.
        """
        return gh_client.issue_to_local_fields(issue)

    # ------------------------------------------------------------------
    # Issue comments
    # ------------------------------------------------------------------

    def _add_comment_graphql(self, repo: Repository, issue_node_id: str, body: str) -> str:
        """Add a comment to an issue.

        Returns:
            GraphQL node ID of the new comment.
        """
        return gh_client._add_comment_graphql(repo, issue_node_id, body)

    def _fetch_issue_comments_graphql(
        self, repo: Repository, owner: str, repo_name: str, issue_number: int
    ) -> list[IssueCommentNode]:
        """Fetch all comments on an issue.

        Returns:
            List of IssueCommentNode TypedDicts.
        """
        return gh_client._fetch_issue_comments_graphql(repo, owner, repo_name, issue_number)

    def _fetch_comment_by_id_graphql(self, repo: Repository, comment_node_id: str) -> IssueCommentNode:
        """Fetch a single comment by its GraphQL node ID.

        Returns:
            IssueCommentNode TypedDict.
        """
        return gh_client._fetch_comment_by_id_graphql(repo, comment_node_id)

    def _update_issue_comment_graphql(self, repo: Repository, comment_node_id: str, body: str) -> None:
        """Update an existing comment's body."""
        gh_client._update_issue_comment_graphql(repo, comment_node_id, body)

    # ------------------------------------------------------------------
    # Status mutations
    # ------------------------------------------------------------------

    def apply_status_in_progress(self, item: BacklogItem, repo: str = "", output: Output | None = None) -> None:
        """Transition an item to in-progress state on the backend."""
        gh_client.apply_status_in_progress(item, repo or self._repo, output)

    def apply_status_verified(self, item: BacklogItem, repo: str = "", output: Output | None = None) -> None:
        """Transition an item to verified state on the backend."""
        gh_client.apply_status_verified(item, repo or self._repo, output)

    def apply_status_groomed(self, item: BacklogItem, repo: str = "", output: Output | None = None) -> None:
        """Transition an item to groomed state on the backend."""
        gh_client.apply_status_groomed(item, repo or self._repo, output)

    def sync_groomed_to_github_issue(
        self,
        repo_obj: Repository,
        issue_num: int,
        groomed_content: str,
        section_name: str | None = None,
        output: Output | None = None,
    ) -> bool:
        """Write groomed content into a specific section of an issue body.

        Returns:
            True if the issue body was updated, False if no change was needed.
        """
        return gh_client.sync_groomed_to_github_issue(repo_obj, issue_num, groomed_content, section_name, output)

    # ------------------------------------------------------------------
    # Milestones and projects
    # ------------------------------------------------------------------

    def _fetch_milestones_graphql(
        self, repo: Repository, owner: str, repo_name: str, states: list[str] | None = None
    ) -> list[MilestoneFullNode]:
        """Fetch milestones from the backend.

        Returns:
            List of MilestoneFullNode TypedDicts.
        """
        return gh_client._fetch_milestones_graphql(repo, owner, repo_name, states)

    def _projects_v2_list_query(self, owner: str, limit: int = 20) -> tuple[str, dict[str, object]]:
        """Build a ProjectsV2 list query string and variables.

        Returns:
            Tuple of (query_string, variables_dict).
        """
        return gh_client._projects_v2_list_query(owner, limit)

    def _projects_v2_create_mutation(self, owner_id: str, title: str) -> tuple[str, dict[str, object]]:
        """Build a ProjectsV2 create mutation string and variables.

        Returns:
            Tuple of (mutation_string, variables_dict).
        """
        return gh_client._projects_v2_create_mutation(owner_id, title)

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

        Returns:
            IssueNode of the created issue, or None on failure.
        """
        return gh_client.create_task_issue(
            repo, parent_issue_number, task, description, acceptance_criteria, labels, output
        )

    def get_task_issues(
        self, repo: Repository, parent_issue_number: int, output: Output | None = None
    ) -> list[IssueNode]:
        """Fetch all child task issues for a parent issue.

        Returns:
            List of IssueNode TypedDicts for child task issues.
        """
        return gh_client.get_task_issues(repo, parent_issue_number, output)

    def update_task_status(
        self, repo: Repository, issue_number: int, new_status: str, output: Output | None = None
    ) -> bool:
        """Update the status label on a task issue.

        Returns:
            True if the status was updated, False if no change was needed.
        """
        return gh_client.update_task_status(repo, issue_number, new_status, output)

    # ------------------------------------------------------------------
    # Sync / serialisation
    # ------------------------------------------------------------------

    def render_issue_body(self, item: BacklogItem, original_body: str | None = None) -> str:
        """Serialise a BacklogItem to backend issue body markdown.

        Returns:
            Markdown string suitable for use as an issue body.
        """
        return github_sync.render_issue_body(item, original_body)

    def parse_issue_body(self, body: str, existing: BacklogItem | None = None) -> BacklogItem:
        """Deserialise a backend issue body into a BacklogItem.

        Returns:
            Populated BacklogItem model.
        """
        return github_sync.parse_issue_body(body, existing)

    def merge_item(self, local: BacklogItem, remote: BacklogItem) -> BacklogItem:
        """Merge a local BacklogItem with a remote version, resolving conflicts.

        Returns:
            Merged BacklogItem with conflicts resolved.
        """
        return github_sync.merge_item(local, remote)

    def unknown_key_to_heading(self, key: str) -> str:
        """Convert an unknown section key to a markdown heading string.

        Returns:
            Heading text string (e.g. ``"My Section"``).
        """
        return github_sync.unknown_key_to_heading(key)

    # ------------------------------------------------------------------
    # Integration branches
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

        Returns:
            BranchInfo TypedDict describing the created branch.
        """
        return github_branches.create_integration_branch(
            milestone_number, slug, base_branch=base_branch, repo=repo or self._repo, output=output
        )

    def get_integration_branch_status(
        self, branch_name: str, *, repo: str = "", output: Output | None = None
    ) -> BranchInfo | None:
        """Get the current status of an integration branch.

        Returns:
            BranchInfo TypedDict, or None if the branch does not exist.
        """
        return github_branches.get_integration_branch_status(branch_name, repo=repo or self._repo, output=output)

    def merge_integration_branch(
        self, head_branch: str, base_branch: str, commit_message: str, *, repo: str = "", output: Output | None = None
    ) -> MergeResult:
        """Merge an integration branch into a base branch.

        Returns:
            MergeResult TypedDict with merge outcome.
        """
        return github_branches.merge_integration_branch(
            head_branch, base_branch, commit_message, repo=repo or self._repo, output=output
        )

    def delete_integration_branch(self, branch_name: str, *, repo: str = "", output: Output | None = None) -> bool:
        """Delete an integration branch.

        Returns:
            True if the branch was deleted, False if it did not exist.
        """
        return github_branches.delete_integration_branch(branch_name, repo=repo or self._repo, output=output)

    def list_integration_branches(self, *, repo: str = "", output: Output | None = None) -> list[BranchInfo]:
        """List all integration branches in the repository.

        Returns:
            List of BranchInfo TypedDicts for all integration branches.
        """
        return github_branches.list_integration_branches(repo=repo or self._repo, output=output)
