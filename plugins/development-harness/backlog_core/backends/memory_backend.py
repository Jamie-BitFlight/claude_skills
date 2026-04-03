"""In-memory test double implementing the BacklogBackend Protocol.

This module provides InMemoryBackend, a pure-Python implementation that
stores all state in plain dicts and lists.  Designed for use in tests as a
drop-in replacement for the GitHub-backed implementation without requiring
network access or individual gh_client mocking.

Usage::

    from backlog_core.backends.memory_backend import InMemoryBackend
    from backlog_core.backend_protocol import BacklogBackend, BacklogConfig, set_config

    backend = InMemoryBackend()
    set_config(BacklogConfig(backend=backend))
    assert isinstance(backend, BacklogBackend)
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from github.Repository import Repository

    from backlog_core.models import Output, SamTask

from backlog_core.backend_protocol import IssueCommentNode, IssueNode, LabelNode, MilestoneFullNode, MilestoneNode
from backlog_core.models import (
    BackendAvailability,
    BackendStatus,
    BacklogItem,
    BacklogItemMetadata,
    BranchInfo,
    IssueLocalFields,
    IssueStatus,
    MergeResult,
    PullRequestRef,
    ViewItemResult,
)

__all__ = ["InMemoryBackend"]


def _now() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(UTC).isoformat()


def _make_issue_node(
    number: int,
    title: str,
    body: str,
    state: str = "OPEN",
    labels: list[LabelNode] | None = None,
    milestone: MilestoneNode | None = None,
) -> IssueNode:
    """Construct an IssueNode with sensible defaults."""
    ts = _now()
    return IssueNode(
        id=f"issue-node-{number}",
        number=number,
        title=title,
        state=state,
        body=body,
        createdAt=ts,
        updatedAt=ts,
        labels=labels or [],
        milestone=milestone,
        assignees=[],
    )


class InMemoryBackend:
    """In-memory BacklogBackend for use in tests.

    All state lives in plain Python dicts and lists.  Every method is
    synchronous and has no side effects outside this instance.  No imports
    from gh_client, github_sync, or github_branches.
    """

    def __init__(self) -> None:
        """Initialise empty in-memory storage for all backend state."""
        # Issues: {number: IssueNode}
        self._issues: dict[int, IssueNode] = {}
        self._next_issue_number: int = 1

        # Comments: {issue_number: list[IssueCommentNode]}
        self._comments: dict[int, list[IssueCommentNode]] = {}
        # comment_id -> (issue_number, list_index)
        self._comment_index: dict[str, tuple[int, int]] = {}

        # Milestones: {number: MilestoneFullNode}
        self._milestones: dict[int, MilestoneFullNode] = {}
        self._next_milestone_number: int = 1

        # Labels: {name: node_id}
        self._labels: dict[str, str] = {}

        # Branches: {name: BranchInfo}
        self._branches: dict[str, BranchInfo] = {}

    # ------------------------------------------------------------------
    # Repository access
    # ------------------------------------------------------------------

    def get_github(self, repo: str = "", timeout: int = 15) -> Repository:  # type: ignore[return]
        """Raise RuntimeError — InMemoryBackend has no GitHub connection."""
        msg = "InMemoryBackend.get_github: no GitHub connection available"
        raise RuntimeError(msg)

    def try_get_github(self, repo: str = "") -> Repository | None:  # type: ignore[return]
        """Return None — InMemoryBackend has no GitHub connection."""
        return None

    def probe_backend_status(self, repo: str = "") -> BackendStatus:
        """Return REACHABLE status — in-memory backend is always available."""
        return BackendStatus(name="InMemory", availability=BackendAvailability.REACHABLE)

    # ------------------------------------------------------------------
    # GraphQL utilities
    # ------------------------------------------------------------------

    def _graphql_request(
        self, repo: Repository, query: str, variables: dict[str, object] | None = None
    ) -> dict[str, Any]:
        """Return empty dict — in-memory backend has no GraphQL layer."""
        return {}

    def _resolve_labels_graphql(
        self, repo: Repository, repo_owner: str, repo_name: str, label_names: list[str]
    ) -> list[str]:
        """Return or create label node IDs for the given names."""
        result: list[str] = []
        for name in label_names:
            if name not in self._labels:
                self._labels[name] = f"label-node-{name}"
            result.append(self._labels[name])
        return result

    # ------------------------------------------------------------------
    # Issue CRUD
    # ------------------------------------------------------------------

    def _fetch_issue_graphql(self, repo: Repository, owner: str, repo_name: str, issue_number: int) -> IssueNode:
        """Return the stored IssueNode for the given number."""
        if issue_number not in self._issues:
            msg = f"InMemoryBackend: issue #{issue_number} not found"
            raise KeyError(msg)
        return self._issues[issue_number]

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
        """Return issues filtered by state, labels, and milestone."""
        results = [issue for issue in self._issues.values() if issue["state"] == state]
        if labels:
            label_set = set(labels)
            results = [issue for issue in results if any(lbl["name"] in label_set for lbl in issue["labels"])]
        if milestone_number is not None:
            results = [
                issue
                for issue in results
                if issue["milestone"] is not None and issue["milestone"]["number"] == milestone_number
            ]
        return results[:first]

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
        """Update an issue's mutable fields in place."""
        number = self._issue_number_for_node_id(issue_node_id)
        issue = self._issues[number]
        if state is not None:
            issue["state"] = state
        if body is not None:
            issue["body"] = body
        if title is not None:
            issue["title"] = title
        issue["updatedAt"] = _now()

    def _issue_number_for_node_id(self, node_id: str) -> int:
        """Resolve a node ID string to an issue number."""
        for number, issue in self._issues.items():
            if issue["id"] == node_id:
                return number
        msg = f"InMemoryBackend: no issue with node ID {node_id!r}"
        raise KeyError(msg)

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
        """Return stored issues, calling callback for each."""
        issues = self._fetch_issues_graphql(
            repo, owner, "", state=state, labels=labels, milestone_number=milestone_number
        )
        if callback is not None:
            for issue in issues:
                callback(issue)
        return issues

    def create_issue_for_item(
        self, repo: Repository, item: BacklogItem, dry_run: bool = False, output: Output | None = None
    ) -> int | None:
        """Create an issue from a BacklogItem and return its number."""
        if dry_run:
            return None
        number = self._next_issue_number
        self._next_issue_number += 1
        issue = _make_issue_node(number=number, title=item.title, body=item.description)
        self._issues[number] = issue
        return number

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
        """Close an issue by reference (number string or #N form)."""
        number = int(issue_ref.lstrip("#"))
        if number in self._issues:
            self._issues[number]["state"] = "CLOSED"
            self._issues[number]["updatedAt"] = _now()

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
        """Resolve (close) an issue with a resolution comment."""
        number = int(issue_ref.lstrip("#"))
        if number in self._issues:
            self._issues[number]["state"] = "CLOSED"
            self._issues[number]["updatedAt"] = _now()

    def fetch_open_issues_by_title(self, repo: Repository) -> dict[str, int]:
        """Return a mapping of open issue titles to issue numbers."""
        return {issue["title"]: issue["number"] for issue in self._issues.values() if issue["state"] == "OPEN"}

    def fetch_github_issue_body(self, repo_obj: Repository, issue_num: int, output: Output | None = None) -> str | None:
        """Return the body of the stored issue, or None if not found."""
        issue = self._issues.get(issue_num)
        return issue["body"] if issue is not None else None

    def check_open_prs_for_issue(self, issue_num: int, repo: str = "") -> list[PullRequestRef]:
        """Return empty list — in-memory backend has no pull requests."""
        return []

    def batch_fetch_statuses(self, items: list[BacklogItem], repo: str = "") -> dict[int, IssueStatus]:
        """Return statuses for items that have issue numbers."""
        result: dict[int, IssueStatus] = {}
        for item in items:
            raw_issue = getattr(item.metadata, "issue", "") or ""
            if not raw_issue:
                continue
            num = int(str(raw_issue).lstrip("#"))
            issue = self._issues.get(num)
            if issue is not None:
                result[num] = IssueStatus(status=issue["state"].lower())
        return result

    def fetch_item_status(self, item: BacklogItem, repo: str = "", output: Output | None = None) -> str:
        """Return the status string for a single item."""
        raw_issue = getattr(item.metadata, "issue", "") or ""
        if not raw_issue:
            return "open"
        num = int(str(raw_issue).lstrip("#"))
        issue = self._issues.get(num)
        return issue["state"].lower() if issue is not None else "open"

    def view_enrich_from_github(self, result: ViewItemResult, issue_num: str, repo: str = "") -> bool:
        """Enrich a ViewItemResult from stored issue data."""
        try:
            num = int(issue_num.lstrip("#"))
        except ValueError:
            return False
        issue = self._issues.get(num)
        if issue is None:
            return False
        result.state = issue["state"].lower()
        result.body = issue["body"]
        result.number = issue["number"]
        return True

    def issue_to_local_fields(self, issue: IssueNode) -> IssueLocalFields:
        """Convert an IssueNode to IssueLocalFields."""
        return IssueLocalFields(title=issue["title"], body=issue["body"], status=issue["state"].lower())

    # ------------------------------------------------------------------
    # Issue comments
    # ------------------------------------------------------------------

    def _add_comment_graphql(self, repo: Repository, issue_node_id: str, body: str) -> str:
        """Add a comment to an issue and return its node ID."""
        number = self._issue_number_for_node_id(issue_node_id)
        comment_id = f"comment-{uuid.uuid4().hex[:8]}"
        ts = _now()
        comment = IssueCommentNode(
            id=comment_id,
            body=body,
            url=f"https://example.com/issues/{number}#comment-{comment_id}",
            author="test-user",
            created_at=ts,
            updated_at=ts,
        )
        if number not in self._comments:
            self._comments[number] = []
        idx = len(self._comments[number])
        self._comments[number].append(comment)
        self._comment_index[comment_id] = (number, idx)
        return comment_id

    def _fetch_issue_comments_graphql(
        self, repo: Repository, owner: str, repo_name: str, issue_number: int
    ) -> list[IssueCommentNode]:
        """Return all comments on the issue."""
        return list(self._comments.get(issue_number, []))

    def _fetch_comment_by_id_graphql(self, repo: Repository, comment_node_id: str) -> IssueCommentNode:
        """Return a comment by its node ID."""
        loc = self._comment_index.get(comment_node_id)
        if loc is None:
            msg = f"InMemoryBackend: comment {comment_node_id!r} not found"
            raise KeyError(msg)
        issue_num, idx = loc
        return self._comments[issue_num][idx]

    def _update_issue_comment_graphql(self, repo: Repository, comment_node_id: str, body: str) -> None:
        """Update a comment's body."""
        loc = self._comment_index.get(comment_node_id)
        if loc is None:
            msg = f"InMemoryBackend: comment {comment_node_id!r} not found"
            raise KeyError(msg)
        issue_num, idx = loc
        self._comments[issue_num][idx]["body"] = body
        self._comments[issue_num][idx]["updated_at"] = _now()

    # ------------------------------------------------------------------
    # Status mutations
    # ------------------------------------------------------------------

    def apply_status_in_progress(self, item: BacklogItem, repo: str = "", output: Output | None = None) -> None:
        """No-op — status is tracked via item metadata in this backend."""

    def apply_status_verified(self, item: BacklogItem, repo: str = "", output: Output | None = None) -> None:
        """No-op — status is tracked via item metadata in this backend."""

    def apply_status_groomed(self, item: BacklogItem, repo: str = "", output: Output | None = None) -> None:
        """No-op — status is tracked via item metadata in this backend."""

    def sync_groomed_to_github_issue(
        self,
        repo_obj: Repository,
        issue_num: int,
        groomed_content: str,
        section_name: str | None = None,
        output: Output | None = None,
    ) -> bool:
        """Append groomed content to an issue body; return True if changed."""
        issue = self._issues.get(issue_num)
        if issue is None:
            return False
        heading = section_name or "Groomed"
        issue["body"] = f"{issue['body']}\n\n## {heading}\n\n{groomed_content}"
        issue["updatedAt"] = _now()
        return True

    # ------------------------------------------------------------------
    # Milestones and projects
    # ------------------------------------------------------------------

    def _fetch_milestones_graphql(
        self, repo: Repository, owner: str, repo_name: str, states: list[str] | None = None
    ) -> list[MilestoneFullNode]:
        """Return stored milestones, optionally filtered by state."""
        milestones = list(self._milestones.values())
        if states:
            state_set = set(states)
            milestones = [m for m in milestones if m["state"] in state_set]
        return milestones

    def _projects_v2_list_query(self, owner: str, limit: int = 20) -> tuple[str, dict[str, object]]:
        """Return stub query/variables — no ProjectsV2 in in-memory backend."""
        return ("", {"owner": owner, "limit": limit})

    def _projects_v2_create_mutation(self, owner_id: str, title: str) -> tuple[str, dict[str, object]]:
        """Return stub mutation/variables — no ProjectsV2 in in-memory backend."""
        return ("", {"ownerId": owner_id, "title": title})

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
        """Create a child task issue and return its IssueNode."""
        number = self._next_issue_number
        self._next_issue_number += 1
        task_type = getattr(task, "task_type", "") or ""
        task_desc = getattr(task, "description", "") or task.task_id
        title = (
            f"[{task.feature}/{task.task_id}] {task_type}: {task_desc}"
            if task_type
            else f"[{task.feature}/{task.task_id}] {task_desc}"
        )
        issue = _make_issue_node(number=number, title=title, body=description or task_desc)
        self._issues[number] = issue
        return issue

    def get_task_issues(
        self, repo: Repository, parent_issue_number: int, output: Output | None = None
    ) -> list[IssueNode]:
        """Return all stored issues (in-memory backend has no parent tracking)."""
        return list(self._issues.values())

    def update_task_status(
        self, repo: Repository, issue_number: int, new_status: str, output: Output | None = None
    ) -> bool:
        """Update issue state; return True if the state changed."""
        issue = self._issues.get(issue_number)
        if issue is None:
            return False
        new_state = "CLOSED" if new_status.lower() in {"closed", "done", "complete", "resolved"} else "OPEN"
        if issue["state"] == new_state:
            return False
        issue["state"] = new_state
        issue["updatedAt"] = _now()
        return True

    # ------------------------------------------------------------------
    # Sync / serialisation
    # ------------------------------------------------------------------

    def render_issue_body(self, item: BacklogItem, original_body: str | None = None) -> str:
        """Render a BacklogItem to a minimal markdown body."""
        return f"# {item.title}\n\n{item.description}"

    def parse_issue_body(self, body: str, existing: BacklogItem | None = None) -> BacklogItem:
        """Parse a markdown body into a BacklogItem.

        Returns existing unchanged when provided.  Otherwise extracts the
        title from the first heading and treats the remainder as description.
        """
        if existing is not None:
            return existing
        lines = body.splitlines()
        title = lines[0].lstrip("# ").strip() if lines else "Untitled"
        description = "\n".join(lines[1:]).strip()
        return BacklogItem(
            title=title,
            description=description,
            metadata=BacklogItemMetadata(
                source="memory",
                added=datetime.now(UTC).date().isoformat(),
                priority="P1",
                item_type="Feature",
                status="open",
            ),
        )

    def merge_item(self, local: BacklogItem, remote: BacklogItem) -> BacklogItem:
        """Return remote as the merge winner (remote is source of truth)."""
        return remote

    def unknown_key_to_heading(self, key: str) -> str:
        """Convert a snake_case key to a Title Case heading."""
        return key.replace("_", " ").title()

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
        """Create and store an in-memory branch record."""
        name = f"milestone/{milestone_number}-{slug}"
        info = BranchInfo(name=name, sha=f"deadbeef{milestone_number:04d}", last_commit_date=_now(), age_days=0)
        self._branches[name] = info
        return info

    def get_integration_branch_status(
        self, branch_name: str, *, repo: str = "", output: Output | None = None
    ) -> BranchInfo | None:
        """Return stored branch info, or None if the branch does not exist."""
        return self._branches.get(branch_name)

    def merge_integration_branch(
        self, head_branch: str, base_branch: str, commit_message: str, *, repo: str = "", output: Output | None = None
    ) -> MergeResult:
        """Record a merge, remove the head branch, and return a MergeResult."""
        self._branches.pop(head_branch, None)
        return MergeResult(sha=f"merged-{uuid.uuid4().hex[:8]}", message=commit_message)

    def delete_integration_branch(self, branch_name: str, *, repo: str = "", output: Output | None = None) -> bool:
        """Delete a branch record; return True if it existed."""
        if branch_name in self._branches:
            del self._branches[branch_name]
            return True
        return False

    def list_integration_branches(self, *, repo: str = "", output: Output | None = None) -> list[BranchInfo]:
        """Return all stored branch records."""
        return list(self._branches.values())
