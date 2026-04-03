"""GraphQL response fixture factories for backlog_core tests.

These factories produce dict shapes that match the TypedDict response models
defined in backlog_core/gh_client.py (IssueNode, MilestoneFullNode, etc.).

All factories accept **overrides so individual tests can customise specific
fields without spelling out the full structure every time.

Usage in tests::

    from tests.graphql_factories import make_issue_node, make_issues_list_response

    issue = make_issue_node(number=42, title="My bug", state="OPEN")
    graphql_data = make_issues_list_response([issue])

All factories return plain dicts — no TypedDict annotation at runtime so tests
can import them without triggering circular imports.

Reused by: T02 (gh_client.py tests), T04 (operations.py tests),
           T07 (server.py tests), T08 (artifact_provider.py tests).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from backlog_core.gh_client import IssueNode

# ---------------------------------------------------------------------------
# Node factories
# ---------------------------------------------------------------------------


def make_label_node(name: str = "status:open", node_id: str = "LBL_abc123") -> dict[str, str]:
    """Return a LabelNode-shaped dict.

    Args:
        name: Label name string.
        node_id: GraphQL node ID.

    Returns:
        Dict matching LabelNode TypedDict shape.
    """
    return {"name": name, "id": node_id}


def make_milestone_node(
    node_id: str = "MS_001", number: int = 1, title: str = "v1.0", due_on: str | None = None, state: str = "OPEN"
) -> dict[str, Any]:
    """Return a MilestoneNode-shaped dict (minimal reference embedded in issues).

    Args:
        node_id: GraphQL node ID.
        number: Milestone number.
        title: Milestone title.
        due_on: ISO 8601 due date string, or None if not set.
        state: Milestone state, ``"OPEN"`` or ``"CLOSED"``.

    Returns:
        Dict matching MilestoneNode TypedDict shape.
    """
    return {"id": node_id, "number": number, "title": title, "dueOn": due_on, "state": state}


def make_issue_node(**overrides: Any) -> dict[str, Any]:
    """Return a raw GraphQL IssueNode-shaped dict with sensible defaults.

    Labels and assignees use the nested ``{"nodes": [...]}`` structure that
    the real GitHub GraphQL API returns and ``_parse_issue_node`` expects.
    Use this factory when mocking ``_graphql_request`` responses that will be
    processed by ``_parse_issue_node`` (e.g., ``batch_fetch_statuses``,
    ``view_enrich_from_github``, ``apply_status_in_progress``).

    For tests that call ``issue_to_local_fields`` directly with an
    already-parsed ``IssueNode`` (flat labels list), use
    ``make_parsed_issue_node`` instead.

    Args:
        **overrides: Any IssueNode field to override. Common keys:
            number (int), title (str), state (str), body (str),
            labels (list[dict] | dict with "nodes" key),
            milestone (dict | None), assignees (list[dict]).

    Returns:
        Dict with raw GraphQL shape: labels as ``{"nodes": [...]}``.
    """
    labels = overrides.pop("labels", [])
    assignees = overrides.pop("assignees", [])
    # Wrap flat lists in the GraphQL nested structure.
    labels_wrapped: Any = {"nodes": labels} if isinstance(labels, list) else labels
    assignees_wrapped: Any = {"nodes": assignees} if isinstance(assignees, list) else assignees

    base: dict[str, Any] = {
        "id": "MDU6SXNzdWUx",
        "number": 1,
        "title": "Test issue",
        "state": "OPEN",
        "body": "Test body",
        "createdAt": "2026-01-01T00:00:00Z",
        "updatedAt": "2026-01-15T00:00:00Z",
        "labels": labels_wrapped,
        "milestone": None,
        "assignees": assignees_wrapped,
    }
    base.update(overrides)
    return base


def make_parsed_issue_node(**overrides: Any) -> IssueNode:
    """Return an already-parsed IssueNode-shaped dict with flat label/assignee lists.

    Use this factory when calling functions that operate on a parsed
    ``IssueNode`` (after ``_parse_issue_node`` has already been applied),
    such as ``issue_to_local_fields``.  Labels and assignees are plain lists
    of ``LabelNode`` / ``AssigneeNode`` dicts — not nested under ``"nodes"``.

    Args:
        **overrides: Any IssueNode field to override. Common keys:
            number (int), title (str), state (str), body (str),
            labels (list[dict]), milestone (dict | None),
            assignees (list[dict]).

    Returns:
        Dict matching the post-parse IssueNode TypedDict shape (flat lists).
    """
    base: dict[str, Any] = {
        "id": "MDU6SXNzdWUx",
        "number": 1,
        "title": "Test issue",
        "state": "OPEN",
        "body": "Test body",
        "createdAt": "2026-01-01T00:00:00Z",
        "updatedAt": "2026-01-15T00:00:00Z",
        "labels": [],
        "milestone": None,
        "assignees": [],
    }
    base.update(overrides)
    return cast("IssueNode", base)


def make_milestone_full_node(**overrides: Any) -> dict[str, Any]:
    """Return a MilestoneFullNode-shaped dict with sensible defaults.

    Args:
        **overrides: Any MilestoneFullNode field to override. Common keys:
            number (int), title (str), state (str), dueOn (str | None),
            openIssueCount (int), closedIssueCount (int).

    Returns:
        Dict matching MilestoneFullNode TypedDict shape.
    """
    base: dict[str, Any] = {
        "id": "MI_001",
        "number": 1,
        "title": "v1.0",
        "state": "OPEN",
        "description": "",
        "dueOn": "2026-06-30T00:00:00Z",
        "openIssueCount": 3,
        "closedIssueCount": 7,
    }
    base.update(overrides)
    return base


def make_created_issue_node(**overrides: Any) -> dict[str, Any]:
    """Return a CreatedIssueNode-shaped dict (from createIssue mutation response).

    Args:
        **overrides: Any CreatedIssueNode field to override.

    Returns:
        Dict matching CreatedIssueNode TypedDict shape.
    """
    base: dict[str, Any] = {
        "id": "MDU6SXNzdWUy",
        "number": 42,
        "title": "feat: new feature",
        "url": "https://github.com/test-owner/test-repo/issues/42",
    }
    base.update(overrides)
    return base


def make_search_pr_node(**overrides: Any) -> dict[str, Any]:
    """Return a SearchPRNode-shaped dict.

    Args:
        **overrides: Any SearchPRNode field to override.

    Returns:
        Dict matching SearchPRNode TypedDict shape.
    """
    base: dict[str, Any] = {
        "number": 55,
        "title": "fix: implement feature",
        "url": "https://github.com/test-owner/test-repo/pull/55",
        "state": "OPEN",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Response envelope factories (full GraphQL data payloads)
# ---------------------------------------------------------------------------


def make_issue_by_number_response(issue: dict[str, Any] | None = None) -> dict[str, Any]:
    """Wrap an issue node in a GetIssue query response envelope.

    Args:
        issue: IssueNode dict or None to simulate not-found.

    Returns:
        Full ``data`` dict as returned by _graphql_request for _ISSUE_BY_NUMBER_QUERY.
    """
    if issue is None:
        issue = make_issue_node()
    return {"repository": {"issue": issue}}


def make_issues_list_response(
    issues: list[dict[str, Any]] | None = None, has_next: bool = False, end_cursor: str | None = None
) -> dict[str, Any]:
    """Wrap a list of issue nodes in a ListIssues query response envelope.

    Args:
        issues: List of IssueNode dicts. Defaults to empty list.
        has_next: Whether pagination has more results.
        end_cursor: Cursor for the next page (used when has_next=True).

    Returns:
        Full ``data`` dict as returned by _graphql_request for _ISSUES_LIST_QUERY.
    """
    if issues is None:
        issues = []
    page_info: dict[str, Any] = {"hasNextPage": has_next, "endCursor": end_cursor}
    return {"repository": {"issues": {"nodes": issues, "pageInfo": page_info}}}


def make_create_issue_response(issue: dict[str, Any] | None = None) -> dict[str, Any]:
    """Wrap a created issue node in a CreateIssue mutation response envelope.

    Args:
        issue: CreatedIssueNode dict. Defaults to make_created_issue_node().

    Returns:
        Full ``data`` dict as returned by _graphql_request for _CREATE_ISSUE_MUTATION.
    """
    if issue is None:
        issue = make_created_issue_node()
    return {"createIssue": {"issue": issue}}


def make_update_issue_response(node_id: str = "MDU6SXNzdWUx", number: int = 1, state: str = "CLOSED") -> dict[str, Any]:
    """Return an UpdateIssue mutation response envelope.

    Args:
        node_id: GraphQL node ID of the updated issue.
        number: Issue number.
        state: New issue state.

    Returns:
        Full ``data`` dict as returned by _graphql_request for _UPDATE_ISSUE_MUTATION.
    """
    return {"updateIssue": {"issue": {"id": node_id, "number": number, "state": state}}}


def make_add_comment_response(comment_id: str = "IC_001", comment_url: str = "") -> dict[str, Any]:
    """Return an AddComment mutation response envelope.

    Args:
        comment_id: GraphQL node ID for the new comment.
        comment_url: HTML URL for the new comment.

    Returns:
        Full ``data`` dict as returned by _graphql_request for _ADD_COMMENT_MUTATION.
    """
    return {"addComment": {"commentEdge": {"node": {"id": comment_id, "url": comment_url}}}}


def make_label_resolution_response(labels: list[tuple[str, str | None]]) -> dict[str, Any]:
    """Build an aliased label resolution response (for _resolve_label_ids_graphql).

    Args:
        labels: List of (label_name, node_id_or_None) tuples. Use None to simulate
            a missing label (alias resolves to null).

    Returns:
        Full ``data`` dict as returned by _graphql_request for the aliased label query.
        Shape: {"repository": {"label0": {"id": ..., "name": ...} | None, ...}}
    """
    repo_data: dict[str, Any] = {}
    for i, (name, node_id) in enumerate(labels):
        alias = f"label{i}"
        if node_id is not None:
            repo_data[alias] = {"id": node_id, "name": name}
        else:
            repo_data[alias] = None
    return {"repository": repo_data}


def make_milestones_response(milestones: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Wrap milestone nodes in a ListMilestones query response envelope.

    Args:
        milestones: List of MilestoneFullNode dicts. Defaults to empty list.

    Returns:
        Full ``data`` dict as returned by _graphql_request for _LIST_MILESTONES_QUERY.
    """
    if milestones is None:
        milestones = []
    return {"repository": {"milestones": {"nodes": milestones}}}


def make_search_prs_response(prs: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Wrap PR search nodes in a SearchPRs query response envelope.

    Args:
        prs: List of SearchPRNode dicts. Defaults to empty list.

    Returns:
        Full ``data`` dict as returned by _graphql_request for _SEARCH_PRS_QUERY.
    """
    if prs is None:
        prs = []
    return {"search": {"nodes": prs}}


def make_sub_issues_response(
    sub_issues: list[dict[str, Any]] | None = None, parent_issue_id: str = "MDU6SXNzdWUx"
) -> dict[str, Any]:
    """Wrap sub-issue nodes in a GetSubIssues query response envelope.

    Args:
        sub_issues: List of IssueNode dicts for sub-issues. Defaults to empty list.
        parent_issue_id: GraphQL node ID of the parent issue.

    Returns:
        Full ``data`` dict as returned by _graphql_request for _SUB_ISSUES_QUERY.
    """
    if sub_issues is None:
        sub_issues = []
    return {"repository": {"issue": {"id": parent_issue_id, "subIssues": {"nodes": sub_issues}}}}


def make_add_sub_issue_response(
    parent_id: str = "MDU6SXNzdWUx", parent_number: int = 1, child_id: str = "MDU6SXNzdWUy", child_number: int = 2
) -> dict[str, Any]:
    """Return an AddSubIssue mutation response envelope.

    Args:
        parent_id: GraphQL node ID of the parent issue.
        parent_number: Parent issue number.
        child_id: GraphQL node ID of the sub-issue.
        child_number: Sub-issue number.

    Returns:
        Full ``data`` dict as returned by _graphql_request for _ADD_SUB_ISSUE_MUTATION.
    """
    return {
        "addSubIssue": {
            "issue": {"id": parent_id, "number": parent_number},
            "subIssue": {"id": child_id, "number": child_number},
        }
    }


def make_issue_comment_node(
    comment_id: str = "IC_001",
    body: str = "comment body",
    url: str = "https://github.com/test/issues/1#issuecomment-1",
    author: str = "test-user",
    created_at: str = "2026-01-01T00:00:00Z",
    updated_at: str = "2026-01-02T00:00:00Z",
) -> dict[str, Any]:
    """Return an IssueCommentNode-shaped dict for comment listing responses.

    The ``author`` field is nested under ``{"login": ...}`` to match the raw
    GraphQL shape that ``_parse_comment_node`` expects.

    Args:
        comment_id: GraphQL node ID for the comment.
        body: Comment body text.
        url: HTML URL for the comment.
        author: Login of the comment author.
        created_at: ISO 8601 creation timestamp.
        updated_at: ISO 8601 last-update timestamp.

    Returns:
        Dict matching raw GraphQL IssueCommentNode shape (before parsing).
    """
    return {
        "id": comment_id,
        "body": body,
        "url": url,
        "author": {"login": author},
        "createdAt": created_at,
        "updatedAt": updated_at,
    }


def make_issue_comments_response(
    comments: list[dict[str, Any]] | None = None, has_next: bool = False, end_cursor: str | None = None
) -> dict[str, Any]:
    """Wrap comment nodes in a GetIssueComments query response envelope.

    Args:
        comments: List of IssueCommentNode dicts. Defaults to empty list.
        has_next: Whether pagination has more results.
        end_cursor: Cursor for the next page (used when has_next=True).

    Returns:
        Full ``data`` dict as returned by _graphql_request for _ISSUE_COMMENTS_QUERY.
    """
    if comments is None:
        comments = []
    page_info: dict[str, Any] = {"hasNextPage": has_next, "endCursor": end_cursor}
    return {"repository": {"issue": {"comments": {"nodes": comments, "pageInfo": page_info}}}}


def make_comment_by_id_response(
    comment_id: str = "IC_001",
    body: str = "comment body",
    url: str = "https://github.com/test/issues/1#issuecomment-1",
    author: str = "test-user",
    created_at: str = "2026-01-01T00:00:00Z",
    updated_at: str = "2026-01-02T00:00:00Z",
) -> dict[str, Any]:
    """Return a GetComment (node query) response envelope.

    Args:
        comment_id: GraphQL node ID for the comment.
        body: Comment body text.
        url: HTML URL for the comment.
        author: Login of the comment author.
        created_at: ISO 8601 creation timestamp.
        updated_at: ISO 8601 last-update timestamp.

    Returns:
        Full ``data`` dict as returned by _graphql_request for _COMMENT_BY_ID_QUERY.
    """
    return {
        "node": {
            "id": comment_id,
            "body": body,
            "url": url,
            "author": {"login": author},
            "createdAt": created_at,
            "updatedAt": updated_at,
        }
    }


def make_update_comment_response(comment_id: str = "IC_001", body: str = "updated body") -> dict[str, Any]:
    """Return an UpdateIssueComment mutation response envelope.

    Args:
        comment_id: GraphQL node ID of the updated comment.
        body: Updated comment body.

    Returns:
        Full ``data`` dict as returned by _graphql_request for _UPDATE_COMMENT_MUTATION.
    """
    return {"updateIssueComment": {"issueComment": {"id": comment_id, "body": body}}}
