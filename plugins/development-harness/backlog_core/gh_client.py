"""GitHub API operations for the backlog MCP package.

Handles GitHub connection, issue CRUD, status/label management, and view enrichment.
All functions that previously used typer.echo() accept an optional Output parameter.

GraphQL migration: All public functions use GraphQL internally via _graphql_request()
except operations where GitHub GraphQL mutations do not exist (milestone creation,
label creation — see ADR-004). PyGithub's repo.requester.graphql_query() is the
transport (established in Phase 1, #773).
"""

from __future__ import annotations

import logging
import os
import re
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import dh_paths as _dh_paths
from github import Auth, Github, GithubException
from typing_extensions import TypedDict

from . import models as _models
from .backend_protocol import AssigneeNode, IssueCommentNode, IssueNode, LabelNode, MilestoneFullNode, MilestoneNode
from .models import (
    TYPE_TO_LABEL,
    BackendAvailability,
    BackendStatus,
    BacklogError,
    BacklogItem,
    GitHubUnavailableError,
    IssueLocalFields,
    IssueStatus,
    MilestoneInfo,
    Output,
    PullRequestRef,
    SamTask,
    ViewItemResult,
    parse_issue_number,
    resolve_repo,
)
from .parsing import (
    build_issue_body,
    build_sam_task_body,
    build_sam_task_issue_title,
    infer_type,
    normalize_issue_title,
    parse_sam_task_metadata,
    today,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from github.Repository import Repository

logger = logging.getLogger(__name__)

_HTTP_FORBIDDEN = 403
_HTTP_NOT_FOUND = 404

# ---------------------------------------------------------------------------
# DH label taxonomy — canonical label set with colours
# ---------------------------------------------------------------------------
#
# Used by ensure_dh_labels() to auto-create missing labels on first use.
# Label creation uses REST (ADR-004 — no GraphQL createLabel mutation).
# Colours are hex without '#' prefix (PyGithub convention).

DH_LABELS: dict[str, str] = {
    "priority:p0": "e11d48",
    "priority:p1": "f97316",
    "priority:p2": "eab308",
    "priority:ideas": "8b5cf6",
    "type:bug": "dc2626",
    "type:feature": "16a34a",
    "type:refactor": "2563eb",
    "type:chore": "6b7280",
    "type:docs": "0891b2",
    "status:needs-grooming": "f59e0b",
    "status:in-progress": "3b82f6",
    "status:verified": "10b981",
}


def ensure_dh_labels(repo: Repository, output: Output | None = None) -> None:
    """Create any missing dh labels on the repository.

    Iterates ``DH_LABELS`` and creates each label that does not yet exist.
    Idempotent — existing labels are left unchanged.  Label creation uses
    REST per ADR-004 (no GraphQL createLabel mutation).

    Args:
        repo: PyGithub Repository object.
        output: Optional Output collector for status/warning messages.
    """
    out = output or Output()
    for name, color in DH_LABELS.items():
        try:
            repo.get_label(name)
        except GithubException as exc:
            if exc.status != _HTTP_NOT_FOUND:
                raise
            repo.create_label(name=name, color=color)
            out.info(f"  Created label '{name}'")


# ---------------------------------------------------------------------------
# TypedDict response models — private to gh_client.py (ADR-002)
# ---------------------------------------------------------------------------


class CreatedIssueNode(TypedDict):
    """Issue data returned from createIssue mutation."""

    id: str
    number: int
    title: str
    url: str


class CommentNode(TypedDict):
    """Comment node returned from addComment mutation."""

    id: str
    url: str


class SearchPRNode(TypedDict):
    """PR node from search result."""

    number: int
    title: str
    url: str
    state: str


class SubIssueNode(TypedDict):
    """Sub-issue node from GetSubIssues query."""

    id: str
    number: int
    title: str
    state: str
    body: str
    labels: list[LabelNode]


# ---------------------------------------------------------------------------
# GraphQL query/mutation string constants
# ---------------------------------------------------------------------------

_ISSUE_BY_NUMBER_QUERY = """
query GetIssue($owner: String!, $repo: String!, $number: Int!) {
  repository(owner: $owner, name: $repo) {
    issue(number: $number) {
      id
      number
      title
      state
      body
      createdAt
      updatedAt
      labels(first: 50) {
        nodes { name id }
      }
      milestone {
        id
        number
        title
        dueOn
        state
      }
      assignees(first: 10) {
        nodes { login }
      }
    }
  }
}
"""

_ISSUES_LIST_QUERY = """
query ListIssues(
  $owner: String!, $repo: String!, $states: [IssueState!],
  $labels: [String!], $milestoneNumber: String, $since: DateTime, $first: Int!, $after: String
) {
  repository(owner: $owner, name: $repo) {
    issues(
      first: $first, after: $after,
      filterBy: {states: $states, labels: $labels, milestoneNumber: $milestoneNumber, since: $since},
      orderBy: {field: UPDATED_AT, direction: DESC}
    ) {
      nodes {
        id number title state body createdAt updatedAt
        labels(first: 50) { nodes { name id } }
        milestone { id number title dueOn state }
        assignees(first: 10) { nodes { login } }
      }
      pageInfo { hasNextPage endCursor }
    }
  }
}
"""

_CREATE_ISSUE_MUTATION = """
mutation CreateIssue(
  $repositoryId: ID!, $title: String!, $body: String, $labelIds: [ID!]
) {
  createIssue(input: {
    repositoryId: $repositoryId, title: $title, body: $body, labelIds: $labelIds
  }) {
    issue { id number title url }
  }
}
"""

_UPDATE_ISSUE_MUTATION = """
mutation UpdateIssue(
  $id: ID!, $state: IssueState, $body: String, $title: String,
  $labelIds: [ID!], $milestoneId: ID
) {
  updateIssue(input: {
    id: $id, state: $state, body: $body, title: $title,
    labelIds: $labelIds, milestoneId: $milestoneId
  }) {
    issue { id number state }
  }
}
"""

_ADD_COMMENT_MUTATION = """
mutation AddComment($subjectId: ID!, $body: String!) {
  addComment(input: {subjectId: $subjectId, body: $body}) {
    commentEdge { node { id url } }
  }
}
"""

_LIST_LABELS_QUERY = """
query ListLabels($owner: String!, $repo: String!, $first: Int!, $after: String) {
  repository(owner: $owner, name: $repo) {
    labels(first: $first, after: $after) {
      nodes { id name }
      pageInfo { hasNextPage endCursor }
    }
  }
}
"""

_LIST_MILESTONES_QUERY = """
query ListMilestones($owner: String!, $repo: String!, $states: [MilestoneState!]) {
  repository(owner: $owner, name: $repo) {
    milestones(first: 50, states: $states, orderBy: {field: DUE_DATE, direction: ASC}) {
      nodes {
        id number title state description
        dueOn
        issues(states: [OPEN]) { totalCount }
        closedIssues: issues(states: [CLOSED]) { totalCount }
      }
    }
  }
}
"""

_SEARCH_PRS_QUERY = """
query SearchPRs($query: String!, $first: Int!) {
  search(query: $query, type: ISSUE, first: $first) {
    nodes {
      ... on PullRequest { number title url state }
    }
  }
}
"""

_SUB_ISSUES_QUERY = """
query GetSubIssues($owner: String!, $repo: String!, $number: Int!, $first: Int!) {
  repository(owner: $owner, name: $repo) {
    issue(number: $number) {
      subIssues(first: $first) {
        nodes {
          id number title state body
          labels(first: 20) { nodes { name id } }
        }
      }
    }
  }
}
"""

_ADD_SUB_ISSUE_MUTATION = """
mutation AddSubIssue($parentId: ID!, $childId: ID!) {
  addSubIssue(input: {issueId: $parentId, subIssueId: $childId}) {
    issue { id number }
    subIssue { id number }
  }
}
"""

_ISSUE_COMMENTS_QUERY = """
query GetIssueComments($owner: String!, $repo: String!, $number: Int!, $first: Int!, $after: String) {
  repository(owner: $owner, name: $repo) {
    issue(number: $number) {
      comments(first: $first, after: $after) {
        nodes {
          id
          body
          url
          author { login }
          createdAt
          updatedAt
        }
        pageInfo { hasNextPage endCursor }
      }
    }
  }
}
"""

_COMMENT_BY_ID_QUERY = """
query GetComment($id: ID!) {
  node(id: $id) {
    ... on IssueComment {
      id
      body
      url
      author { login }
      createdAt
      updatedAt
    }
  }
}
"""

_UPDATE_COMMENT_MUTATION = """
mutation UpdateIssueComment($id: ID!, $body: String!) {
  updateIssueComment(input: {id: $id, body: $body}) {
    issueComment { id body }
  }
}
"""

# Used by _resolve_labels_graphql (existing implementation, retained)
_LABEL_RESOLUTION_QUERY_TEMPLATE = """\
query ResolveLabelsBatch($owner: String!, $repo: String!) {{
  repository(owner: $owner, name: $repo) {{
{aliases}
  }}
}}"""

_LABEL_ALIAS_TEMPLATE = '    label{i}: label(name: "{name}") {{ name }}'

_LABEL_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9:_\-. ]+$")


# ---------------------------------------------------------------------------
# Parser functions for GraphQL response shapes
# ---------------------------------------------------------------------------


def _parse_issue_node(raw: dict[str, Any]) -> IssueNode:
    """Parse raw GraphQL issue dict into typed IssueNode.

    Flattens nested labels.nodes and assignees.nodes. Handles missing fields
    with safe defaults.

    Args:
        raw: Raw dict from GraphQL response (repository.issue or issues.nodes[]).

    Returns:
        Typed IssueNode with all required fields populated.
    """
    labels_data = raw.get("labels") or {}
    label_nodes_raw = (labels_data.get("nodes") or []) if isinstance(labels_data, dict) else []
    labels: list[LabelNode] = [
        {"name": str(n.get("name", "")), "id": str(n.get("id", ""))} for n in label_nodes_raw if isinstance(n, dict)
    ]

    assignees_data = raw.get("assignees") or {}
    assignee_nodes_raw = (assignees_data.get("nodes") or []) if isinstance(assignees_data, dict) else []
    assignees: list[AssigneeNode] = [
        {"login": str(n.get("login", ""))} for n in assignee_nodes_raw if isinstance(n, dict)
    ]

    milestone_raw: dict[str, Any] | None = raw.get("milestone")
    milestone: MilestoneNode | None = None
    if isinstance(milestone_raw, dict):
        due_on_raw = milestone_raw.get("dueOn")
        milestone = {
            "id": str(milestone_raw["id"]) if "id" in milestone_raw else "",
            "number": int(milestone_raw["number"]) if "number" in milestone_raw else 0,
            "title": str(milestone_raw["title"]) if "title" in milestone_raw else "",
            "dueOn": str(due_on_raw) if due_on_raw is not None else None,
            "state": ("CLOSED" if str(milestone_raw.get("state", "OPEN")) == "CLOSED" else "OPEN"),
        }

    return {
        "id": str(raw["id"]) if "id" in raw else "",
        "number": int(raw["number"]) if "number" in raw else 0,
        "title": str(raw["title"]) if "title" in raw else "",
        "state": str(raw["state"]) if "state" in raw else "OPEN",
        "body": str(raw["body"]) if raw.get("body") else "",
        "createdAt": str(raw["createdAt"]) if "createdAt" in raw else "",
        "updatedAt": str(raw["updatedAt"]) if "updatedAt" in raw else "",
        "labels": labels,
        "milestone": milestone,
        "assignees": assignees,
    }


def _parse_milestone_node(raw: dict[str, Any]) -> MilestoneFullNode:
    """Parse raw GraphQL milestone dict into typed MilestoneFullNode.

    Derives openIssueCount and closedIssueCount from nested totalCount fields.

    Args:
        raw: Raw dict from milestones.nodes[].

    Returns:
        Typed MilestoneFullNode with issue counts populated.
    """
    issues_data = raw.get("issues") or {}
    open_count = int(issues_data.get("totalCount", 0)) if isinstance(issues_data, dict) else 0

    closed_issues_data = raw.get("closedIssues") or {}
    closed_count = int(closed_issues_data.get("totalCount", 0)) if isinstance(closed_issues_data, dict) else 0

    return {
        "id": str(raw["id"]) if "id" in raw else "",
        "number": int(raw["number"]) if "number" in raw else 0,
        "title": str(raw["title"]) if "title" in raw else "",
        "state": str(raw["state"]) if "state" in raw else "OPEN",
        "description": str(raw["description"]) if raw.get("description") else "",
        "dueOn": str(raw["dueOn"]) if raw.get("dueOn") else None,
        "openIssueCount": open_count,
        "closedIssueCount": closed_count,
    }


def _parse_search_pr_node(raw: dict[str, Any]) -> SearchPRNode | None:
    """Parse raw search result node. Returns None for non-PR results.

    The search query uses fragment ``... on PullRequest`` so non-PR nodes
    return an empty dict.

    Args:
        raw: Raw dict from search.nodes[].

    Returns:
        Typed SearchPRNode or None if node is not a PullRequest.
    """
    if not raw.get("number"):
        return None
    return {
        "number": int(raw["number"]) if "number" in raw else 0,
        "title": str(raw["title"]) if "title" in raw else "",
        "url": str(raw["url"]) if "url" in raw else "",
        "state": str(raw["state"]) if "state" in raw else "",
    }


# ---------------------------------------------------------------------------
# GraphQL helpers — generic request + Projects V2 queries
# ---------------------------------------------------------------------------


def _graphql_request(repo: Repository, query: str, variables: dict[str, object] | None = None) -> dict[str, Any]:
    """Execute a raw GraphQL query using PyGithub's requester.

    Follows the same pattern as ``_resolve_labels_graphql``.  Raises
    ``BacklogError`` when the GraphQL response contains an ``errors`` key
    or when the requester raises ``GithubException`` (including
    ``UnknownObjectException`` for NOT_FOUND / 404 responses).

    Args:
        repo: PyGithub Repository object (provides requester access).
        query: GraphQL query or mutation string.
        variables: Optional dict of GraphQL variables.

    Returns:
        The ``data`` dict from the GraphQL response.

    Raises:
        BacklogError: On GraphQL errors, NOT_FOUND (404), or network/auth failures.
    """
    try:
        _headers, response = repo.requester.graphql_query(query, variables or {})
    except GithubException as exc:
        msg = f"GraphQL request failed: {exc}"
        raise BacklogError(msg) from exc
    if "errors" in response:
        first_error = response["errors"][0] if response["errors"] else {}
        msg = first_error.get("message", str(response["errors"]))
        msg_0 = f"GraphQL error: {msg}"
        raise BacklogError(msg_0)
    if (data := response.get("data")) is None:
        msg_0 = f"Unexpected GraphQL response — missing 'data' key: {response!r}"
        raise BacklogError(msg_0)
    return data


def _is_not_found_error(error: BacklogError) -> bool:
    """Check if a GraphQL BacklogError indicates a not-found condition.

    GraphQL returns 'Could not resolve to ...' for 404-equivalent errors
    (where REST would return HTTP 404).

    Args:
        error: BacklogError raised by _graphql_request.

    Returns:
        True if the error indicates a resource was not found.
    """
    msg = str(error).lower()
    return "could not resolve" in msg or "not found" in msg


def _get_repo_node_id(repo: Repository) -> str:
    """Get the GraphQL node ID for the repository.

    PyGithub's Repository object exposes node_id as a property without
    requiring an additional API call (it is populated when the repo object
    is created via gh.get_repo()).

    Args:
        repo: PyGithub Repository object.

    Returns:
        Repository GraphQL node ID string.
    """
    return str(repo.node_id)


# ---------------------------------------------------------------------------
# GraphQL helper functions — issue queries
# ---------------------------------------------------------------------------


def _fetch_issue_graphql(repo: Repository, owner: str, repo_name: str, issue_number: int) -> IssueNode:
    """Fetch a single issue via GraphQL.

    Args:
        repo: PyGithub Repository object (provides GraphQL transport).
        owner: GitHub repository owner login.
        repo_name: GitHub repository name (without owner prefix).
        issue_number: Issue number (without ``#``).

    Returns:
        Typed IssueNode with labels, milestone, and assignees.

    Raises:
        BacklogError: If the issue is not found or on GraphQL errors.
    """
    data = _graphql_request(repo, _ISSUE_BY_NUMBER_QUERY, {"owner": owner, "repo": repo_name, "number": issue_number})
    repo_data = data.get("repository") or {}
    raw_issue = repo_data.get("issue") if isinstance(repo_data, dict) else None
    if raw_issue is None:
        msg = f"GraphQL error: Could not resolve to issue #{issue_number}"
        raise BacklogError(msg)
    return _parse_issue_node(raw_issue)


def _fetch_issues_graphql(
    repo: Repository,
    owner: str,
    repo_name: str,
    state: str = "OPEN",
    labels: list[str] | None = None,
    milestone_number: int | None = None,
    first: int = 100,
    since: str | None = None,
) -> list[IssueNode]:
    """Fetch a list of issues via GraphQL with optional filters.

    Handles pagination automatically (follows hasNextPage/endCursor).

    Args:
        repo: PyGithub Repository object.
        owner: GitHub repository owner login.
        repo_name: GitHub repository name.
        state: Issue state filter — ``"OPEN"`` or ``"CLOSED"``. Defaults to ``"OPEN"``.
            Pass a comma-joined value like ``"OPEN,CLOSED"`` or use a list via the
            ``states`` variable when fetching both states in one call.
        labels: Optional list of label names to filter by.
        milestone_number: Optional milestone number to filter by.
        first: Page size (max 100 per GitHub GraphQL limits).
        since: Optional ISO 8601 timestamp.  When provided, only issues updated
            at or after this time are returned (GitHub GraphQL ``filterBy.since``).

    Returns:
        List of typed IssueNode dicts (may be empty).

    Raises:
        BacklogError: On GraphQL errors.
    """
    all_issues: list[IssueNode] = []
    cursor: str | None = None
    states: list[str] = [s.strip() for s in state.split(",")] if "," in state else [state]

    while True:
        variables: dict[str, object] = {
            "owner": owner,
            "repo": repo_name,
            "states": states,
            "labels": labels,
            "milestoneNumber": str(milestone_number) if milestone_number is not None else None,
            "since": since,
            "first": first,
            "after": cursor,
        }
        data = _graphql_request(repo, _ISSUES_LIST_QUERY, variables)
        repo_data = data.get("repository") or {}
        issues_conn = repo_data.get("issues") if isinstance(repo_data, dict) else None
        if not isinstance(issues_conn, dict):
            break
        nodes = issues_conn.get("nodes") or []
        all_issues.extend(_parse_issue_node(raw) for raw in nodes if isinstance(raw, dict))

        page_info = issues_conn.get("pageInfo") or {}
        if not (isinstance(page_info, dict) and page_info.get("hasNextPage")):
            break
        cursor = str(page_info["endCursor"])

    return all_issues


def sync_issues_graphql(
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
    """Shared GraphQL sync primitive — fetch issues with optional filtering, callback, and timestamp tracking.

    Wraps ``_fetch_issues_graphql`` with three optional behaviours:

    - **since filter**: pass a ``datetime`` to restrict results to issues updated at or after
      that time.  When ``track_timestamp=True`` and ``since`` is ``None``, the value is read
      from the ``.last_sync`` file automatically.
    - **per-issue callback**: when provided, ``callback`` is called with each ``IssueNode``
      dict as it is processed.
    - **timestamp tracking**: when ``track_timestamp=True``, reads ``.last_sync`` before the
      fetch and writes the sync-start timestamp after a successful fetch so the next call can
      run incrementally.

    No new pagination logic is introduced — all pagination is delegated to
    ``_fetch_issues_graphql`` / ``_graphql_request_paginated``.

    Args:
        repo: PyGithub Repository object.
        owner: GitHub repository owner login.
        repo_name: GitHub repository name without owner prefix.
        state: Issue state filter — ``"OPEN"``, ``"CLOSED"``, or ``"OPEN,CLOSED"``.
        labels: Optional list of label names to filter by.
        milestone_number: Optional milestone number to filter by.
        since: Optional lower-bound datetime.  Only issues updated at or after this time are
            returned.  When ``track_timestamp=True`` and this is ``None``, the value is read
            from the ``.last_sync`` file.
        callback: Optional callable invoked with each ``IssueNode`` dict.  The full list is
            still returned regardless of whether a callback is provided.
        track_timestamp: When ``True``, reads the ``.last_sync`` file to populate ``since``
            (if not already set) and writes the sync-start timestamp after a successful fetch.

    Returns:
        Full list of ``IssueNode`` dicts (may be empty).

    Raises:
        BacklogError: Propagated from ``_fetch_issues_graphql`` on GraphQL errors.
    """
    since_str: str | None = since.isoformat() if since is not None else None
    last_sync_path = None
    sync_start: str | None = None

    if track_timestamp:
        last_sync_path = _dh_paths.state_root() / ".last_sync"
        # Record start BEFORE fetching to avoid missing issues updated during the fetch.
        sync_start = datetime.now(UTC).isoformat()
        if since_str is None and last_sync_path.exists():
            since_str = last_sync_path.read_text(encoding="utf-8").strip() or None

    issues = _fetch_issues_graphql(
        repo, owner, repo_name, state=state, labels=labels, milestone_number=milestone_number, since=since_str
    )

    if callback is not None:
        for issue_node in issues:
            callback(issue_node)

    if track_timestamp and last_sync_path is not None and sync_start is not None:
        last_sync_path.parent.mkdir(parents=True, exist_ok=True)
        last_sync_path.write_text(sync_start, encoding="utf-8")

    return issues


# ---------------------------------------------------------------------------
# GraphQL helper functions — issue mutations
# ---------------------------------------------------------------------------


def _create_issue_graphql(
    repo: Repository, repo_node_id: str, title: str, body: str, label_ids: list[str]
) -> CreatedIssueNode:
    """Create an issue via GraphQL mutation.

    Args:
        repo: PyGithub Repository object.
        repo_node_id: GraphQL node ID of the repository.
        title: Issue title.
        body: Issue body text.
        label_ids: List of label node IDs to apply.

    Returns:
        Typed CreatedIssueNode with id, number, title, url.

    Raises:
        BacklogError: On GraphQL errors.
    """
    variables: dict[str, object] = {"repositoryId": repo_node_id, "title": title, "body": body, "labelIds": label_ids}
    data = _graphql_request(repo, _CREATE_ISSUE_MUTATION, variables)
    raw_issue = data.get("createIssue", {}).get("issue", {})
    return {
        "id": str(raw_issue.get("id", "")),
        "number": int(raw_issue.get("number", 0)),
        "title": str(raw_issue.get("title", "")),
        "url": str(raw_issue.get("url", "")),
    }


def _update_issue_graphql(
    repo: Repository,
    issue_node_id: str,
    *,
    state: str | None = None,
    body: str | None = None,
    title: str | None = None,
    label_ids: list[str] | None = None,
    milestone_id: str | None = None,
) -> None:
    """Update issue fields via GraphQL mutation.

    Only non-None arguments are included in the mutation input — GitHub GraphQL
    ignores fields absent from the input object.

    Args:
        repo: PyGithub Repository object.
        issue_node_id: GraphQL node ID of the issue.
        state: Target state — ``"OPEN"`` or ``"CLOSED"``.
        body: New body text (full replacement).
        title: New title.
        label_ids: Full replacement label ID list (ADR-003 — not additive).
        milestone_id: GraphQL node ID of target milestone, or ``None`` to clear.

    Raises:
        BacklogError: On GraphQL errors.
    """
    variables: dict[str, object] = {"id": issue_node_id}
    if state is not None:
        variables["state"] = state
    if body is not None:
        variables["body"] = body
    if title is not None:
        variables["title"] = title
    if label_ids is not None:
        variables["labelIds"] = label_ids
    if milestone_id is not None:
        variables["milestoneId"] = milestone_id
    _graphql_request(repo, _UPDATE_ISSUE_MUTATION, variables)


def _add_comment_graphql(repo: Repository, issue_node_id: str, body: str) -> str:
    """Add a comment to an issue via GraphQL.

    Args:
        repo: PyGithub Repository object.
        issue_node_id: GraphQL node ID of the issue (not the issue number).
        body: Comment body text.

    Returns:
        Comment node ID string.

    Raises:
        BacklogError: On GraphQL errors.
    """
    data = _graphql_request(repo, _ADD_COMMENT_MUTATION, {"subjectId": issue_node_id, "body": body})
    comment_node = data.get("addComment", {}).get("commentEdge", {}).get("node", {})
    return str(comment_node.get("id", ""))


def _parse_comment_node(node: dict[str, object]) -> IssueCommentNode:
    """Parse a raw GraphQL comment dict into a typed IssueCommentNode.

    Args:
        node: Raw dict from GraphQL response comments.nodes[] or node() query.

    Returns:
        IssueCommentNode with all fields populated.
    """
    raw_author = node.get("author")
    author = str(raw_author["login"]) if isinstance(raw_author, dict) and "login" in raw_author else ""  # ty: ignore[invalid-argument-type]
    return IssueCommentNode(
        id=str(node.get("id", "")),
        body=str(node.get("body", "")),
        url=str(node.get("url", "")),
        author=author,
        created_at=str(node.get("createdAt", "")),
        updated_at=str(node.get("updatedAt", "")),
    )


def _fetch_issue_comments_graphql(
    repo: Repository, owner: str, repo_name: str, issue_number: int
) -> list[IssueCommentNode]:
    """Fetch all comments for an issue via GraphQL, handling pagination.

    Args:
        repo: PyGithub Repository object (provides requester transport).
        owner: GitHub owner name.
        repo_name: GitHub repository name.
        issue_number: Issue number (positive integer).

    Returns:
        List of ``IssueCommentNode`` dicts with ``id``, ``body``, ``url``,
        ``author``, ``created_at``, and ``updated_at`` fields.

    Raises:
        BacklogError: On GraphQL errors.
    """
    comments: list[IssueCommentNode] = []
    cursor: str | None = None
    while True:
        variables: dict[str, object] = {
            "owner": owner,
            "repo": repo_name,
            "number": issue_number,
            "first": 100,
            "after": cursor,
        }
        data = _graphql_request(repo, _ISSUE_COMMENTS_QUERY, variables)
        issue_data = (data.get("repository") or {}).get("issue") or {}
        comments_data = issue_data.get("comments") or {}
        nodes: list[dict[str, object]] = list(comments_data.get("nodes") or [])
        comments.extend(_parse_comment_node(node) for node in nodes)
        page_info: dict[str, object] = comments_data.get("pageInfo") or {}
        if not page_info.get("hasNextPage"):
            break
        cursor = str(page_info.get("endCursor") or "")
    return comments


def _fetch_comment_by_id_graphql(repo: Repository, comment_node_id: str) -> IssueCommentNode:
    """Fetch a single comment by its GraphQL node ID.

    Args:
        repo: PyGithub Repository object (provides requester transport).
        comment_node_id: GraphQL node ID of the comment (e.g. ``IC_kwDO...``).

    Returns:
        IssueCommentNode with all fields populated.

    Raises:
        BacklogError: If the node is not found or is not an IssueComment, or on
            GraphQL errors.
    """
    data = _graphql_request(repo, _COMMENT_BY_ID_QUERY, {"id": comment_node_id})
    node = data.get("node")
    if node is None or not isinstance(node, dict):
        msg = f"GraphQL error: Could not resolve comment node {comment_node_id!r}"
        raise BacklogError(msg)
    if "id" not in node:
        msg = f"GraphQL error: Node {comment_node_id!r} is not an IssueComment"
        raise BacklogError(msg)
    return _parse_comment_node(node)


def _update_issue_comment_graphql(repo: Repository, comment_node_id: str, body: str) -> None:
    """Update an existing issue comment body via GraphQL mutation.

    Args:
        repo: PyGithub Repository object (provides requester transport).
        comment_node_id: GraphQL node ID of the comment to update.
        body: New comment body text.

    Raises:
        BacklogError: On GraphQL errors.
    """
    _graphql_request(repo, _UPDATE_COMMENT_MUTATION, {"id": comment_node_id, "body": body})


# ---------------------------------------------------------------------------
# GraphQL helper functions — label resolution
# ---------------------------------------------------------------------------


def _resolve_label_ids_graphql(repo: Repository, owner: str, repo_name: str, label_names: list[str]) -> dict[str, str]:
    """Resolve label names to their GraphQL node IDs.

    Uses the same aliased-label query pattern as _resolve_labels_graphql.
    Returns a ``{name: node_id}`` mapping for labels that exist.
    Missing labels are omitted (matches existing REST behavior).

    Args:
        repo: PyGithub Repository object.
        owner: GitHub repository owner login.
        repo_name: GitHub repository name.
        label_names: Label names to resolve.

    Returns:
        Dict mapping label name to GraphQL node ID.

    Raises:
        ValueError: If a label name contains disallowed characters.
        GithubException: On auth/network failures.
    """
    if not label_names:
        return {}

    seen: set[str] = set()
    unique_names: list[str] = []
    for name in label_names:
        if name not in seen:
            seen.add(name)
            unique_names.append(name)

    for name in unique_names:
        if not _LABEL_NAME_PATTERN.match(name):
            msg = f"Label name contains disallowed characters: {name!r}"
            raise ValueError(msg)

    # Build aliased query: labelN: label(name: "...") { id name }
    alias_lines = [f'    label{i}: label(name: "{n}") {{ id name }}' for i, n in enumerate(unique_names)]
    query = f"""
query ResolveLabelIds($owner: String!, $repo: String!) {{
  repository(owner: $owner, name: $repo) {{
{chr(10).join(alias_lines)}
  }}
}}
"""
    _headers, response = repo.requester.graphql_query(query, {"owner": owner, "repo": repo_name})
    repo_data = (response.get("data") or {}).get("repository") or {}
    result: dict[str, str] = {}
    for i, name in enumerate(unique_names):
        node = repo_data.get(f"label{i}")
        if isinstance(node, dict) and node.get("id"):
            result[name] = str(node["id"])
    return result


def _resolve_labels_graphql(repo: Repository, repo_owner: str, repo_name: str, label_names: list[str]) -> list[str]:
    """Resolve label names via a single GraphQL query.

    Returns the subset of label_names that exist in the repository.
    Raises GithubException for auth/network/permission failures.
    Missing individual labels are silently omitted (matches current REST behavior).

    Args:
        repo: PyGithub Repository object (provides requester access for GraphQL).
        repo_owner: GitHub repository owner (org or user name).
        repo_name: GitHub repository name (without owner prefix).
        label_names: List of label name strings to resolve.

    Returns:
        List of label name strings that exist in the repository.

    Raises:
        GithubException: If the GraphQL request fails (auth, network, permissions).
    """
    if not label_names:
        return []

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique_names: list[str] = []
    for name in label_names:
        if name not in seen:
            seen.add(name)
            unique_names.append(name)

    # Validate label names before embedding in query string (security: no injection)
    for name in unique_names:
        if not _LABEL_NAME_PATTERN.match(name):
            msg = f"Label name contains disallowed characters: {name!r}"
            raise ValueError(msg)

    aliases = "\n".join(_LABEL_ALIAS_TEMPLATE.format(i=i, name=name) for i, name in enumerate(unique_names))
    query = _LABEL_RESOLUTION_QUERY_TEMPLATE.format(aliases=aliases)
    variables = {"owner": repo_owner, "repo": repo_name}

    # graphql_query raises GithubException on all errors — never returns an errors dict
    _headers, data = repo.requester.graphql_query(query, variables)

    repo_node: dict[str, dict[str, str] | None] = data["data"]["repository"]
    resolved: list[str] = []
    for i in range(len(unique_names)):
        alias = f"label{i}"
        node: dict[str, str] | None = repo_node.get(alias)
        if node is not None:
            resolved.append(node["name"])
        # else: label missing — silently omit (matches current REST get_label() behavior)

    return resolved


# ---------------------------------------------------------------------------
# GraphQL helper functions — milestones
# ---------------------------------------------------------------------------


def _fetch_milestones_graphql(
    repo: Repository, owner: str, repo_name: str, states: list[str] | None = None
) -> list[MilestoneFullNode]:
    """Fetch repository milestones via GraphQL.

    Args:
        repo: PyGithub Repository object.
        owner: GitHub repository owner login.
        repo_name: GitHub repository name.
        states: Optional list of milestone states — ``["OPEN"]``, ``["CLOSED"]``,
            or ``["OPEN", "CLOSED"]`` (default when None).

    Returns:
        List of typed MilestoneFullNode dicts with issue counts.

    Raises:
        BacklogError: On GraphQL errors.
    """
    variables: dict[str, object] = {"owner": owner, "repo": repo_name, "states": states or ["OPEN", "CLOSED"]}
    data = _graphql_request(repo, _LIST_MILESTONES_QUERY, variables)
    repo_data = data.get("repository") or {}
    milestones_conn = repo_data.get("milestones") if isinstance(repo_data, dict) else None
    if not isinstance(milestones_conn, dict):
        return []
    nodes = milestones_conn.get("nodes") or []
    return [_parse_milestone_node(n) for n in nodes if isinstance(n, dict)]


# ---------------------------------------------------------------------------
# Projects V2 helpers (unchanged from Phase 1)
# ---------------------------------------------------------------------------


def _projects_v2_list_query(owner: str, limit: int = 20) -> tuple[str, dict[str, object]]:
    """Return (query_string, variables) for listing Projects V2.

    Args:
        owner: GitHub owner login (org or user).
        limit: Maximum number of projects to return.

    Returns:
        Tuple of (GraphQL query string, variables dict).
    """
    query = """
query ListProjectsV2($owner: String!, $limit: Int!) {
  repositoryOwner(login: $owner) {
    ... on ProjectV2Owner {
      projectsV2(first: $limit, orderBy: {field: UPDATED_AT, direction: DESC}) {
        nodes {
          id
          title
          number
          url
          closed
          shortDescription
        }
      }
    }
  }
}"""
    return query, {"owner": owner, "limit": limit}


def _projects_v2_create_mutation(owner_id: str, title: str) -> tuple[str, dict[str, object]]:
    """Return (mutation_string, variables) for creating a Projects V2 project.

    Args:
        owner_id: GraphQL node ID of the owner (org or user).
        title: Title for the new project.

    Returns:
        Tuple of (GraphQL mutation string, variables dict).
    """
    mutation = """
mutation CreateProjectV2($ownerId: ID!, $title: String!) {
  createProjectV2(input: {ownerId: $ownerId, title: $title}) {
    projectV2 {
      id
      title
      number
      url
    }
  }
}"""
    return mutation, {"ownerId": owner_id, "title": title}


# ---------------------------------------------------------------------------
# Connection helpers
# ---------------------------------------------------------------------------


def get_github(repo: str = "", timeout: int = 15) -> Repository:
    """Get a PyGithub Repository object.

    Args:
        repo: Repository name in ``owner/name`` format.
        timeout: HTTP request timeout in seconds. Defaults to 15 to prevent
            blocking the FastMCP async event loop when called via
            ``asyncio.to_thread()``. The MCP transport enforces a 60-second
            tool deadline; without a timeout here, a slow GitHub API response
            blocks the thread for the full 60 seconds before timing out.

    Returns:
        PyGithub Repository object.

    Raises:
        GitHubUnavailableError: If GITHUB_TOKEN is not set.
    """
    repo = resolve_repo(repo)
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        msg = "GITHUB_TOKEN not set"
        raise GitHubUnavailableError(msg)
    gh = Github(auth=Auth.Token(token), timeout=timeout)
    return gh.get_repo(repo)


def try_get_github(repo: str = "") -> Repository | None:
    """Try to get GitHub repo, return None if unavailable (no token, network error, etc.).

    Use this for operations where local-only fallback is acceptable.

    Returns:
        Repository object or None if GitHub is unavailable.
    """
    repo = resolve_repo(repo)
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        logger.error("try_get_github: GITHUB_TOKEN not set in environment — GitHub operations will be skipped")
        return None
    try:
        gh = Github(auth=Auth.Token(token), timeout=10)
        return gh.get_repo(repo)
    except GithubException:
        logger.exception("try_get_github: GitHub API error for repo %r", repo)
        return None


def probe_backend_status(repo: str = "") -> BackendStatus:
    """Probe GitHub backend availability and return a status summary.

    Checks authentication, connectivity, and issue counts without raising.
    All errors are captured into the returned ``BackendStatus`` object.

    Args:
        repo: Optional repository slug (``owner/name``).  Defaults to the
            value resolved by :func:`~backlog_core.models.resolve_repo`.

    Returns:
        BackendStatus with availability, open/total issue counts, cache
        total count, and last sync timestamp populated from observed state.
    """
    yaml_files = list(_models.get_backlog_dir().glob("*.yaml"))
    yaml_stems = {f.stem for f in yaml_files}
    md_files = [f for f in _models.get_backlog_dir().glob("*.md") if f.stem not in yaml_stems]
    cache_total_count = len(yaml_files) + len(md_files)

    last_sync_path = _dh_paths.state_root() / ".last_sync"
    try:
        last_sync = last_sync_path.read_text(encoding="utf-8").strip() if last_sync_path.exists() else ""
    except OSError:
        last_sync = ""

    if not os.environ.get("GITHUB_TOKEN"):
        return BackendStatus(
            availability=BackendAvailability.NEEDS_AUTHENTICATION,
            cache_total_count=cache_total_count,
            last_sync=last_sync,
            error="GITHUB_TOKEN not set",
        )

    if (repo_obj := try_get_github(repo)) is None:
        return BackendStatus(
            availability=BackendAvailability.ERROR,
            cache_total_count=cache_total_count,
            last_sync=last_sync,
            error="GitHub repository unavailable — token set but connection failed",
        )

    try:
        open_count: int | None = repo_obj.open_issues_count
        total_count: int | None = repo_obj.get_issues(state="all").totalCount
    except GithubException as exc:
        if exc.status == _HTTP_FORBIDDEN:
            return BackendStatus(
                availability=BackendAvailability.RATE_LIMITED,
                cache_total_count=cache_total_count,
                last_sync=last_sync,
                error=str(exc),
            )
        return BackendStatus(
            availability=BackendAvailability.REACHABLE,
            cache_total_count=cache_total_count,
            last_sync=last_sync,
            error=str(exc),
        )

    return BackendStatus(
        availability=BackendAvailability.REACHABLE,
        open_count=open_count,
        total_count=total_count,
        cache_total_count=cache_total_count,
        last_sync=last_sync,
    )


# ---------------------------------------------------------------------------
# Issue CRUD
# ---------------------------------------------------------------------------


def create_issue_for_item(
    repo: Repository, item: BacklogItem, dry_run: bool = False, output: Output | None = None
) -> int | None:
    """Create GitHub issue for backlog item.

    Uses GraphQL createIssue mutation with resolved label IDs.

    Returns:
        Issue number if created, None otherwise.
    """
    out = output or Output()
    if not item.title:
        return None
    type_map = {"feature": "feat", "bug": "fix", "refactor": "refactor", "docs": "docs", "chore": "chore"}
    issue_title = f"{type_map.get(item.item_type.lower(), 'feat')}: {item.title}"
    body = build_issue_body(item)
    type_gh = TYPE_TO_LABEL.get(item.item_type.lower()) or infer_type(item.description, item.title)
    if dry_run:
        out.info(f"  [dry-run] Would create: {issue_title}")
        return None
    labels = ["status:needs-grooming", f"priority:{(item.priority or 'P1').lower()}", type_gh]
    owner, repo_name = repo.full_name.split("/", 1)
    ensure_dh_labels(repo, out)
    label_id_map = _resolve_label_ids_graphql(repo, owner, repo_name, labels)
    for name in labels:
        if name not in label_id_map:
            out.warn(f"  WARNING: label '{name}' not found")
    created = _create_issue_graphql(repo, _get_repo_node_id(repo), issue_title, body, list(label_id_map.values()))
    out.info(f"  Created #{created['number']}: {issue_title[:60]}...")
    return created["number"]


def close_github_issue(
    issue_ref: str, reason: str, *, reference: str = "", comment: str = "", repo: str = "", output: Output | None = None
) -> None:
    """Close GitHub issue as dismissed (not completed). ADR-9."""
    out = output or Output()
    try:
        repository = get_github(repo)
        if (num := parse_issue_number(issue_ref)) is None:
            msg = f"Invalid issue ref: {issue_ref!r}"
            raise ValueError(msg)
        owner, repo_name = repository.full_name.split("/", 1)
        issue = _fetch_issue_graphql(repository, owner, repo_name, num)
        parts = [f"**Closed** ({reason})."]
        if reference:
            parts.append(f"**Reference**: {reference}")
        if comment:
            parts.append(f"\n{comment}")
        _add_comment_graphql(repository, issue["id"], " ".join(parts))
        _update_issue_graphql(repository, issue["id"], state="CLOSED")
        out.info(f"  GitHub issue #{num} closed ({reason}).")
    except BacklogError as e:
        out.warn(f"  WARNING: Could not close issue: {e}")


def resolve_github_issue(
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
    """Close GitHub issue as completed with structured evidence trail. ADR-9."""
    out = output or Output()
    try:
        repository = get_github(repo)
        if (num := parse_issue_number(issue_ref)) is None:
            msg = f"Invalid issue ref: {issue_ref!r}"
            raise ValueError(msg)
        owner, repo_name = repository.full_name.split("/", 1)
        issue = _fetch_issue_graphql(repository, owner, repo_name, num)
        body_parts = [f"## Resolved\n\n**Summary**: {summary}"]
        if method:
            body_parts.append(f"**Method**: {method}")
        if notes:
            body_parts.append(f"\n### Notes\n\n{notes}")
        if follow_ups:
            body_parts.append(f"\n### Follow-ups\n\n{follow_ups}")
        if findings:
            body_parts.append(f"\n### Findings\n\n{findings}")
        _add_comment_graphql(repository, issue["id"], "\n".join(body_parts))
        _update_issue_graphql(repository, issue["id"], state="CLOSED")
        out.info(f"  GitHub issue #{num} resolved.")
    except BacklogError as e:
        out.warn(f"  WARNING: Could not close issue: {e}")


# ---------------------------------------------------------------------------
# PR check
# ---------------------------------------------------------------------------


def check_open_prs_for_issue(issue_num: int, repo: str = "") -> list[PullRequestRef]:
    """Check for open pull requests that reference a given issue number.

    Uses GraphQL search query to find open PRs whose title or body contains
    ``#N`` (where N is the issue number).

    Args:
        issue_num: The GitHub issue number to search for.
        repo: Repository in ``owner/repo`` format.

    Returns:
        List of PullRequestRef models for each matching PR.
        Empty list if no open PRs found or GitHub is unavailable.
    """
    repo = resolve_repo(repo)
    try:
        repository = get_github(repo)
        search_query = f"repo:{repo} is:pr is:open #{issue_num}"
        data = _graphql_request(repository, _SEARCH_PRS_QUERY, {"query": search_query, "first": 20})
        nodes = (data.get("search") or {}).get("nodes") or []
        prs: list[PullRequestRef] = []
        for raw in nodes:
            if isinstance(raw, dict):
                parsed = _parse_search_pr_node(raw)
                if parsed is not None:
                    prs.append(PullRequestRef(number=parsed["number"], title=parsed["title"], url=parsed["url"]))
    except (BacklogError, GithubException):
        return []
    return prs


# ---------------------------------------------------------------------------
# Status / label management
# ---------------------------------------------------------------------------


def batch_fetch_statuses(items: list[BacklogItem], repo: str = "") -> dict[int, IssueStatus]:
    """Batch fetch status and milestone from GH for all items with issue numbers.

    Single GraphQL call replaces N+1 per-item get_issue() calls.

    Returns:
        Dict mapping issue_number -> IssueStatus model.
    """
    if (repo_obj := try_get_github(repo)) is None:
        return {}
    try:
        owner, repo_name = repo_obj.full_name.split("/", 1)
        all_issues = sync_issues_graphql(repo_obj, owner, repo_name, state="OPEN")
        issue_map = {iss["number"]: iss for iss in all_issues}
    except (BacklogError, GithubException):
        return {}
    result: dict[int, IssueStatus] = {}
    for item in items:
        if (num := parse_issue_number(item.issue)) is None:
            continue
        if num in issue_map:
            gh_issue = issue_map[num]
            status_labels = [lbl["name"] for lbl in gh_issue["labels"] if lbl["name"].startswith("status:")]
            ms = gh_issue["milestone"]
            result[num] = IssueStatus(
                status=status_labels[0] if status_labels else "", milestone=ms["title"] if ms else ""
            )
    return result


def fetch_item_status(item: BacklogItem, repo: str = "", output: Output | None = None) -> str:
    """Fetch status label from GitHub issue for an item (single-item fallback).

    Prefer batch_fetch_statuses() for listing multiple items.

    Returns:
        Status label string or empty string.
    """
    if not item.issue:
        return ""
    try:
        repository = get_github(repo)
        if (num := parse_issue_number(item.issue)) is None:
            msg = f"Invalid issue ref: {item.issue!r}"
            raise ValueError(msg)
        owner, repo_name = repository.full_name.split("/", 1)
        gh_issue = _fetch_issue_graphql(repository, owner, repo_name, num)
        labels = [lb["name"] for lb in gh_issue["labels"] if lb["name"].startswith("status:")]
        return labels[0] if labels else ""
    except (BacklogError, GithubException):
        return ""


def apply_status_in_progress(item: BacklogItem, repo: str = "", output: Output | None = None) -> None:
    """Set GitHub issue label to status:in-progress.

    Uses fetch-then-update pattern (ADR-003): fetches current labels, computes
    desired set (add in-progress, remove needs-grooming), updates via GraphQL
    with the full label list.
    """
    out = output or Output()
    try:
        repository = get_github(repo)
        if (num := parse_issue_number(item.issue)) is None:
            msg = f"Invalid issue ref: {item.issue!r}"
            raise ValueError(msg)
        owner, repo_name = repository.full_name.split("/", 1)
        issue = _fetch_issue_graphql(repository, owner, repo_name, num)
        current_names = [lbl["name"] for lbl in issue["labels"]]
        if "status:in-progress" in current_names:
            out.info("  Status: already in-progress")
            return
        # Compute desired label set: add in-progress, remove needs-grooming
        desired_names = [n for n in current_names if n != "status:needs-grooming"] + ["status:in-progress"]
        id_map = _resolve_label_ids_graphql(repository, owner, repo_name, desired_names)
        desired_ids = [id_map[n] for n in desired_names if n in id_map]
        _update_issue_graphql(repository, issue["id"], label_ids=desired_ids)
        out.info("  Status: in-progress")
    except BacklogError as e:
        out.warn(f"  WARNING: Could not set status: {e}")


def apply_status_verified(item: BacklogItem, repo: str = "", output: Output | None = None) -> None:
    """Set GitHub issue label to status:verified after quality gates pass.

    Adds the ``status:verified`` label and removes ``status:in-progress`` if
    present. Auto-creates the ``status:verified`` label when it does not exist
    (label creation stays REST per ADR-004 — no GraphQL createLabel mutation).
    Uses fetch-then-update pattern (ADR-003) for label replacement via GraphQL.
    Skips gracefully when the item has no issue number.

    Args:
        item: BacklogItem to mark verified. No-op when ``item.issue`` is empty.
        repo: Repository in ``owner/repo`` format.
        output: Optional Output collector for status/warning messages.

    Raises:
        GithubException: On GitHub API failure other than label-not-found (404).
    """
    if not item.issue:
        return
    out = output or Output()
    repository = get_github(repo)
    if (num := parse_issue_number(item.issue)) is None:
        msg = f"Invalid issue ref: {item.issue!r}"
        raise ValueError(msg)
    owner, repo_name = repository.full_name.split("/", 1)
    issue = _fetch_issue_graphql(repository, owner, repo_name, num)
    current_names = [lbl["name"] for lbl in issue["labels"]]
    if "status:verified" in current_names:
        out.info("  Status: already verified")
        return
    # Ensure status:verified label exists — label creation stays REST (ADR-004)
    try:
        repository.get_label("status:verified")
    except GithubException as e:
        if e.status != _HTTP_NOT_FOUND:
            raise
        repository.create_label(
            name="status:verified", color="0e8a16", description="Quality gates passed via /complete-implementation"
        )
    # Compute desired label set: add verified, remove in-progress
    desired_names = [n for n in current_names if n != "status:in-progress"] + ["status:verified"]
    id_map = _resolve_label_ids_graphql(repository, owner, repo_name, desired_names)
    desired_ids = [id_map[n] for n in desired_names if n in id_map]
    _update_issue_graphql(repository, issue["id"], label_ids=desired_ids)
    out.info("  Status: verified")


def apply_status_groomed(item: BacklogItem, repo: str = "", output: Output | None = None) -> None:
    """Set GitHub issue label to status:groomed after grooming completes.

    Adds the ``status:groomed`` label and removes ``status:needs-grooming``
    if present (idempotent). Auto-creates the ``status:groomed`` label
    when it does not exist (label creation stays REST per ADR-004 — no
    GraphQL createLabel mutation). Uses fetch-then-update pattern (ADR-003)
    for label replacement via GraphQL. Skips gracefully when the item has
    no issue number.

    Args:
        item: BacklogItem to mark groomed. No-op when ``item.issue`` is empty.
        repo: Repository in ``owner/repo`` format.
        output: Optional Output collector for status/warning messages.

    Raises:
        GithubException: On GitHub API failure other than label-not-found (404).
    """
    if not item.issue:
        return
    out = output or Output()
    repository = get_github(repo)
    if (num := parse_issue_number(item.issue)) is None:
        msg = f"Invalid issue ref: {item.issue!r}"
        raise ValueError(msg)
    owner, repo_name = repository.full_name.split("/", 1)
    issue = _fetch_issue_graphql(repository, owner, repo_name, num)
    current_names = [lbl["name"] for lbl in issue["labels"]]
    if "status:groomed" in current_names:
        out.info("  Status: already groomed")
        return
    # Ensure status:groomed label exists — label creation stays REST (ADR-004)
    try:
        repository.get_label("status:groomed")
    except GithubException as e:
        if e.status != _HTTP_NOT_FOUND:
            raise
        repository.create_label(
            name="status:groomed", color="0075ca", description="Grooming complete — all sections written and approved"
        )
    # Compute desired label set: add groomed, remove needs-grooming
    desired_names = [n for n in current_names if n != "status:needs-grooming"] + ["status:groomed"]
    id_map = _resolve_label_ids_graphql(repository, owner, repo_name, desired_names)
    desired_ids = [id_map[n] for n in desired_names if n in id_map]
    _update_issue_graphql(repository, issue["id"], label_ids=desired_ids)
    out.info("  Status: groomed")


# ---------------------------------------------------------------------------
# Issue queries
# ---------------------------------------------------------------------------


def fetch_open_issues_by_title(repo: Repository) -> dict[str, int]:
    """Fetch all open issues and return ``{normalized_title: issue_number}`` map.

    When duplicates exist, keeps the lowest issue number (the original).

    Returns:
        Dict mapping normalized title strings to their GitHub issue number.
    """
    owner, repo_name = repo.full_name.split("/", 1)
    issues = sync_issues_graphql(repo, owner, repo_name, state="OPEN")
    title_to_num: dict[str, int] = {}
    for issue in issues:
        key = normalize_issue_title(issue["title"])
        num = issue["number"]
        if key not in title_to_num or num < title_to_num[key]:
            title_to_num[key] = num
    return title_to_num


# ---------------------------------------------------------------------------
# View enrichment
# ---------------------------------------------------------------------------


def view_enrich_from_github(result: ViewItemResult, issue_num: str, repo: str = "") -> bool:
    """Enrich view result with live GitHub issue data.

    Returns:
        True if GitHub data was fetched, False if unavailable or errored.
    """
    gh_repo = try_get_github(repo)
    if gh_repo is None:
        return False
    try:
        owner, repo_name = gh_repo.full_name.split("/", 1)
        gh_issue = _fetch_issue_graphql(gh_repo, owner, repo_name, int(issue_num))
    except (BacklogError, GithubException):
        return False
    result.number = gh_issue["number"]
    result.title = gh_issue["title"]
    result.state = gh_issue["state"].lower()  # GraphQL returns "OPEN"/"CLOSED"; callers expect lowercase
    result.body = gh_issue["body"]
    result.labels = [lb["name"] for lb in gh_issue["labels"]]
    ms = gh_issue["milestone"]
    result.milestone = ms["title"] if ms else ""
    for lb in result.labels:
        if lb.startswith("priority:"):
            result.priority = lb.split(":", 1)[1].upper()
        if lb.startswith("status:"):
            result.status = lb.split(":", 1)[1]
    return True


# ---------------------------------------------------------------------------
# Issue data extraction
# ---------------------------------------------------------------------------


def issue_to_local_fields(issue: IssueNode) -> IssueLocalFields:
    """Extract backlog-relevant fields from a GraphQL IssueNode dict.

    Signature change from Phase 1 (ADR-005): accepts IssueNode TypedDict
    instead of PyGithub Issue object. All callers are in operations.py
    and are updated in T03.

    Args:
        issue: IssueNode TypedDict from _fetch_issue_graphql or _fetch_issues_graphql.

    Returns:
        IssueLocalFields model with title, body, priority, type, status, etc.
    """
    labels = [lbl["name"] for lbl in issue["labels"]]
    priority = "P1"
    for lbl in labels:
        if lbl.startswith("priority:"):
            priority = lbl.split(":")[1].upper()
            break
    item_type = "Feature"
    for lbl in labels:
        if lbl.startswith("type:"):
            item_type = lbl.split(":")[1].capitalize()
            break
    state = issue["state"]  # "OPEN" or "CLOSED" from GraphQL
    if state == "CLOSED":
        status = "done"
    else:
        status = "open"
        for lbl in labels:
            if lbl.startswith("status:"):
                status = lbl.split(":")[1]
                break
    ms = issue["milestone"]
    assignees = [a["login"] for a in issue["assignees"]]
    milestone_info = (
        MilestoneInfo(title=ms["title"], number=ms["number"], due_on=(ms["dueOn"] or ""), state=ms["state"])
        if ms
        else MilestoneInfo()
    )
    return IssueLocalFields(
        title=issue["title"],
        body=issue["body"],
        priority=priority,
        item_type=item_type,
        status=status,
        updated_at=issue["updatedAt"],
        milestone=ms["title"] if ms else "",
        milestone_info=milestone_info,
        assignees=assignees,
        labels=labels,
    )


# ---------------------------------------------------------------------------
# Groomed content sync
# ---------------------------------------------------------------------------


def _insert_named_section(body: str, section_name: str, content: str, today_str: str) -> str:
    """Insert or replace *section_name* content in *body* for GitHub issue bodies.

    Handles ``Fact-Check`` / ``RT-ICA`` as top-level ``##`` sections and all
    other names as ``###`` subsections under ``## Groomed``.

    Args:
        body: Current GitHub issue body string.
        section_name: Target section or subsection name.
        content: New content to place in that section.
        today_str: Today's date string (YYYY-MM-DD) for new Groomed headers.

    Returns:
        Updated body string.
    """
    section_lower = section_name.strip().lower()
    if section_lower in {"fact-check", "rt-ica"}:
        header = f"## {section_name.strip()}\n\n"
        section_re = re.compile(
            rf"\n## {re.escape(section_name.strip())}[^\n]*\n([\s\S]*?)(?=\n## |\Z)", re.IGNORECASE | re.MULTILINE
        )
        if section_re.search(body):
            new_block = header + content + "\n"
            return section_re.sub(lambda _: f"\n{new_block}", body)
        return body.rstrip() + "\n\n" + header + content + "\n"

    sub_header = f"### {section_name.strip()}\n\n"
    sub_re = re.compile(
        rf"\n?### {re.escape(section_name.strip())}[^\n]*\n([\s\S]*?)(?=\n### |\n## |\Z)", re.IGNORECASE | re.MULTILINE
    )
    groomed_block_re = re.compile(r"(## Groomed\s*\([^)]*\)\s*\n)([\s\S]*?)(?=\n## |\Z)", re.MULTILINE)
    gm = groomed_block_re.search(body)
    if gm:
        groomed_body = gm.group(2)
        if sub_re.search(groomed_body):
            new_groomed_body = sub_re.sub(lambda _: f"\n{sub_header}{content}\n", groomed_body)
        else:
            new_groomed_body = groomed_body.rstrip() + "\n\n" + sub_header + content + "\n"
        captured = gm.group(1) + new_groomed_body + "\n"
        return groomed_block_re.sub(lambda _: captured, body, count=1)
    return body.rstrip() + f"\n\n## Groomed ({today_str})\n\n{sub_header}{content}\n"


def sync_groomed_to_github_issue(
    repo_obj: Repository,
    issue_num: int,
    groomed_content: str,
    section_name: str | None = None,
    output: Output | None = None,
) -> bool:
    """Append or merge groomed content into GitHub issue body. GitHub is canonical.

    Returns:
        True if the issue body was actually updated, False otherwise.
    """
    out = output or Output()
    try:
        owner, repo_name = repo_obj.full_name.split("/", 1)
        issue = _fetch_issue_graphql(repo_obj, owner, repo_name, issue_num)
        body = issue["body"]
        content = groomed_content.strip()
        if not content:
            return False
        today_str = today()
        if section_name and section_name.lower() not in {"groomed", ""}:
            new_body = _insert_named_section(body, section_name, content, today_str)
        else:
            groomed_re = re.compile(r"\n## Groomed\s*\([^)]*\)\s*\n[\s\S]*?(?=\n## |\Z)", re.MULTILINE)
            block = f"\n## Groomed ({today_str})\n\n{content}\n"
            new_body = groomed_re.sub(block, body) if groomed_re.search(body) else body.rstrip() + "\n\n" + block
        if new_body == body:
            return False
        _update_issue_graphql(repo_obj, issue["id"], body=new_body)
    except BacklogError as e:
        out.warn(f"  WARNING: Could not sync to GitHub issue: {e}")
        return False
    else:
        return True


# ---------------------------------------------------------------------------
# Issue body fetch
# ---------------------------------------------------------------------------


def fetch_github_issue_body(repo_obj: Repository, issue_num: int, output: Output | None = None) -> str | None:
    """Fetch GitHub issue body text.

    Args:
        repo_obj: PyGithub Repository object.
        issue_num: Issue number (without '#').
        output: Optional Output collector for status/warning messages.

    Returns:
        Issue body string, or None on error.
    """
    out = output or Output()
    try:
        owner, repo_name = repo_obj.full_name.split("/", 1)
        issue = _fetch_issue_graphql(repo_obj, owner, repo_name, issue_num)
        return issue["body"]
    except BacklogError as e:
        out.warn(f"  WARNING: Could not fetch issue #{issue_num}: {e}")
        return None


# ---------------------------------------------------------------------------
# SAM task sub-issue operations
# ---------------------------------------------------------------------------


def create_task_issue(
    repo: Repository,
    parent_issue_number: int,
    task: SamTask,
    description: str = "",
    acceptance_criteria: list[str] | None = None,
    labels: list[str] | None = None,
    output: Output | None = None,
) -> IssueNode | None:
    """Create a GitHub issue for a SAM task and link it as a sub-issue of the parent story.

    The issue body uses ``build_sam_task_body()``: human-readable sections are
    visible in the GitHub UI, machine-readable metadata is stored in an invisible
    ``<!-- sam:task ... -->`` block for ``parse_sam_task_metadata()`` to read back.

    Title format: ``[{feature}/{task_id}] {task_type}: {description}``

    Args:
        repo: PyGithub Repository object.
        parent_issue_number: Issue number of the parent story (without ``#``).
        task: ``SamTask`` with ``task_id``, ``feature``, ``task_type``, and other fields.
        description: Short human-readable description of the task.
        acceptance_criteria: Optional list of acceptance criteria strings.
        labels: Optional list of label names to apply (e.g. ``["sam-task"]``).
        output: Optional Output collector.

    Returns:
        The created IssueNode dict, or None on failure.
    """
    out = output or Output()
    title = build_sam_task_issue_title(task, description)
    body = build_sam_task_body(task, description, acceptance_criteria)
    label_names = labels or []
    owner, repo_name = repo.full_name.split("/", 1)
    repo_node_id = _get_repo_node_id(repo)

    if label_names:
        id_map = _resolve_label_ids_graphql(repo, owner, repo_name, label_names)
        for name in label_names:
            if name not in id_map:
                out.warn(f"  WARNING: label '{name}' not found, skipping")
        label_ids = list(id_map.values())
    else:
        label_ids = []

    try:
        task_issue = _create_issue_graphql(repo, repo_node_id, title, body, label_ids)
        out.info(f"  Created task issue #{task_issue['number']}: {title[:70]}")
    except BacklogError as e:
        out.warn(f"  WARNING: Could not create task issue: {e}")
        return None

    # Link as sub-issue via GraphQL addSubIssue mutation
    try:
        parent = _fetch_issue_graphql(repo, owner, repo_name, parent_issue_number)
        _graphql_request(repo, _ADD_SUB_ISSUE_MUTATION, {"parentId": parent["id"], "childId": task_issue["id"]})
        out.info(f"  Linked #{task_issue['number']} as sub-issue of #{parent_issue_number}")
    except BacklogError as e:
        out.warn(f"  WARNING: Created issue #{task_issue['number']} but could not link as sub-issue: {e}")

    # Return a minimal IssueNode representing the created issue
    return {
        "id": task_issue["id"],
        "number": task_issue["number"],
        "title": task_issue["title"],
        "state": "OPEN",
        "body": body,
        "createdAt": "",
        "updatedAt": "",
        "labels": [],
        "milestone": None,
        "assignees": [],
    }


def get_task_issues(repo: Repository, parent_issue_number: int, output: Output | None = None) -> list[IssueNode]:
    """Return all sub-issues for a parent story issue via GraphQL.

    Args:
        repo: PyGithub Repository object.
        parent_issue_number: Issue number of the parent story (without ``#``).
        output: Optional Output collector.

    Returns:
        List of IssueNode dicts (empty on failure or when none exist).
    """
    out = output or Output()
    try:
        owner, repo_name = repo.full_name.split("/", 1)
        data = _graphql_request(
            repo, _SUB_ISSUES_QUERY, {"owner": owner, "repo": repo_name, "number": parent_issue_number, "first": 100}
        )
        repo_data = data.get("repository") or {}
        parent_issue = repo_data.get("issue") if isinstance(repo_data, dict) else None
        if parent_issue is None:
            return []
        sub_issues_conn = parent_issue.get("subIssues") if isinstance(parent_issue, dict) else None
        if not isinstance(sub_issues_conn, dict):
            return []
        nodes = sub_issues_conn.get("nodes") or []
        return [_parse_issue_node(n) for n in nodes if isinstance(n, dict)]
    except BacklogError as e:
        out.warn(f"  WARNING: Could not fetch sub-issues for #{parent_issue_number}: {e}")
        return []


def update_task_status(repo: Repository, issue_number: int, new_status: str, output: Output | None = None) -> bool:
    """Update the ``status`` field inside the ``<!-- sam:task ... -->`` block of a task issue body.

    Reads the current body, patches the YAML block's ``status`` value, and writes
    the updated body back. Returns ``False`` without writing if the body has no
    ``<!-- sam:task ... -->`` block, or if the status is already the target value.

    Args:
        repo: PyGithub Repository object.
        issue_number: Task issue number (without ``#``).
        new_status: Target status string, e.g. ``"in-progress"`` or ``"complete"``.
        output: Optional Output collector.

    Returns:
        ``True`` if the body was updated, ``False`` otherwise.
    """
    out = output or Output()
    try:
        owner, repo_name = repo.full_name.split("/", 1)
        issue = _fetch_issue_graphql(repo, owner, repo_name, issue_number)
        body = issue["body"]
        issue_id = issue["id"]
    except BacklogError as e:
        out.warn(f"  WARNING: Could not fetch issue #{issue_number}: {e}")
        return False
    task_meta = parse_sam_task_metadata(body)
    if task_meta is None:
        out.warn(f"  WARNING: Issue #{issue_number} has no sam:task block — cannot update status")
        return False
    if task_meta.status == new_status:
        return False
    # Replace only the status line inside the invisible block.
    updated_body = re.sub(
        r"(<!--\s*sam:task\s*\n(?:.*\n)*?status:\s*)(\S+)",
        lambda m: m.group(1) + new_status,
        body,
        count=1,
        flags=re.DOTALL,
    )
    if updated_body == body:
        out.warn(f"  WARNING: Issue #{issue_number}: sam:task block present but status line not found")
        return False
    try:
        _update_issue_graphql(repo, issue_id, body=updated_body)
    except BacklogError as e:
        out.warn(f"  WARNING: Could not update issue #{issue_number} body: {e}")
        return False
    out.info(f"  Updated #{issue_number} status: {task_meta.status} -> {new_status}")
    return True
