"""High-level CRUD operations for backlog items.

Combines parsing, GitHub, and file I/O into public functions that return
dicts. Each public function accepts an optional ``output: Output | None``
parameter and returns ``{...result, **out.to_dict()}``.
"""

from __future__ import annotations

import operator
import re
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final, NotRequired, TypeGuard

from dispatch_schema.core.constants import MIN_CONFLICT_GROUP_SIZE
from dispatch_schema.core.models import ConflictGroup
from github import GithubException, GithubObject  # GithubObject used only by create_milestone (ADR-004)
from ruamel.yaml.error import YAMLError
from sam_schema.core.backends.content import parse_plan_content
from sam_schema.core.dependencies import SUCCESSFUL_STATUSES as _SAM_CORE_SUCCESSFUL_STATUSES
from sam_schema.core.models import Plan
from typing_extensions import TypedDict

from . import models as _models
from .backend_protocol import get_config
from .backend_types import ContentProvider, GitHubExtras, IssueCommentNode, IssueNode, MilestoneFullNode, SyncProvider
from .entry_blocks import ENTRY_RE, _render_entry_raw, parse_entries
from .models import (
    ITEM_TYPE_ALIASES,
    SECTION_HEADING_ALIAS,
    VALID_CLOSE_REASONS,
    VALID_ITEM_TYPES,
    VALID_NEW_ITEM_PRIORITIES,
    BackendUnavailableError,
    BacklogError,
    BacklogItem,
    ContentKind,
    ContentQuery,
    ContentUnavailableError,
    DuplicateItemError,
    Entry,
    GroomedData,
    GroomedSectionMetadata,
    IssueLocalFields,
    IssueStatus,
    ItemNotFoundError,
    MilestoneInfo,
    Output,
    PullRequestRef,
    ReconcileRequest,
    ReconcileScope,
    SamTask,
    Section,
    SectionEntryDict,
    SectionEntryMetadata,
    ValidationError,
    ViewItemResult,
    parse_issue_number,
    reference_is_title_derived,
)
from .parsing import (
    find_fuzzy_duplicates,
    find_item,
    items_needing_issues,
    items_with_issues,
    normalize_issue_title,
    now_iso,
    parse_issue_selector,
    parse_sam_task_metadata,
    title_to_slug,
    today,
    view_result_from_local_item,
)
from .rendering import SECTION_HEADING

_SAM_SUCCESSFUL_STATUSES: frozenset[str] = _SAM_CORE_SUCCESSFUL_STATUSES | {"closed", "done"}
_SAM_PLAN_PAGE_SIZE: Final = 100


class _SamTaskRow(TypedDict):
    task_id: str
    feature: str
    status: str
    agent: str
    priority: int
    skills: list[str]
    dependencies: list[str]
    issue_number: int
    issue_url: str
    title: str


class _SamTaskLookupResult(TypedDict):
    tasks: list[_SamTaskRow]
    count: int
    parent_issue_number: int | str
    stale: bool
    pending: bool
    unavailable: bool
    messages: list[str]
    warnings: list[str]
    errors: list[str]


if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from github.Repository import Repository


# ---------------------------------------------------------------------------
# Module-level backend delegates — thin wrappers preserving test patchability.
# Tests can patch via mocker.patch("backlog_core.operations.X").
# Each wrapper delegates to get_config().backend.X(...).
# ---------------------------------------------------------------------------


def _work_item(reference: str) -> BacklogItem:
    return get_config().backend.get_work_item(reference)


def get_github(repo: str = "", timeout: int = 15) -> Repository:
    """Return authenticated PyGithub Repository via the active backend.

    Returns:
        Authenticated Repository object.
    """
    backend = get_config().backend
    if not isinstance(backend, GitHubExtras):
        raise BacklogError("get_github requires a GitHub-backed backend")
    return backend.get_github(repo, timeout)


def try_get_github(repo: str = "") -> Repository | None:
    """Return PyGithub Repository or None if unavailable.

    Returns:
        Repository object, or None if the backend is unavailable.
    """
    return get_config().backend.try_get_github(repo)


def create_issue_for_item(
    repository: Repository, item: BacklogItem, dry_run: bool = False, output: Output | None = None
) -> int | None:
    """Create a backend issue from a BacklogItem.

    Returns:
        New issue number, or None if dry_run.
    """
    return get_config().backend.create_issue_for_item(repository, item, dry_run, output)


def fetch_github_issue_body(repo_obj: Repository, issue_num: int, output: Output | None = None) -> str | None:
    """Fetch the raw body of an issue.

    Returns:
        Issue body string, or None if the issue was not found.
    """
    return get_config().backend.fetch_github_issue_body(repo_obj, issue_num, output)


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
) -> list[IssueNode]:
    """Bulk-fetch issues with optional progress callback.

    Returns:
        List of IssueNode objects matching the query.
    """
    backend = get_config().backend
    if not isinstance(backend, GitHubExtras):
        raise BacklogError("sync_issues_graphql requires a GitHub-backed backend")
    return backend.sync_issues_graphql(
        repo,
        owner,
        repo_name,
        state=state,
        labels=labels,
        milestone_number=milestone_number,
        since=since,
        callback=callback,
    )


def batch_fetch_statuses(items: list[BacklogItem], repo: str = "") -> dict[int, IssueStatus]:
    """Fetch status for multiple items in one operation.

    Returns:
        Mapping of issue number to IssueStatus.
    """
    return get_config().backend.batch_fetch_statuses(items, repo)


def view_enrich_from_github(result: ViewItemResult, issue_num: str, repo: str = "") -> bool:
    """Enrich a ViewItemResult with live data from the backend.

    Returns:
        True if enrichment succeeded, False otherwise.
    """
    return get_config().backend.view_enrich_from_github(result, issue_num, repo)


def fetch_open_issues_by_title(repository: Repository) -> dict[str, int]:
    """Return a mapping of open issue titles to issue numbers.

    Returns:
        Dict mapping issue title strings to their issue numbers.
    """
    return get_config().backend.fetch_open_issues_by_title(repository)


def check_open_prs_for_issue(issue_num: int, repo: str = "") -> list[PullRequestRef]:
    """Find open pull requests referencing a given issue.

    Returns:
        List of PullRequestRef objects for matching open PRs.
    """
    return get_config().backend.check_open_prs_for_issue(issue_num, repo)


def close_github_issue(
    issue_ref: str, reason: str, *, reference: str = "", comment: str = "", repo: str = "", output: Output | None = None
) -> None:
    """Close an issue with a reason comment."""
    get_config().backend.close_github_issue(
        issue_ref, reason, reference=reference, comment=comment, repo=repo, output=output
    )


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
    """Resolve an issue with a structured resolution comment."""
    get_config().backend.resolve_github_issue(
        issue_ref,
        summary=summary,
        method=method,
        notes=notes,
        follow_ups=follow_ups,
        findings=findings,
        repo=repo,
        output=output,
    )


def apply_status_in_progress(item: BacklogItem, repo: str = "", output: Output | None = None) -> None:
    """Transition an item to in-progress state on the backend."""
    get_config().backend.apply_status_in_progress(item, repo, output)


def apply_status_verified(item: BacklogItem, repo: str = "", output: Output | None = None) -> None:
    """Transition an item to verified state on the backend."""
    get_config().backend.apply_status_verified(item, repo, output)


def apply_status_groomed(item: BacklogItem, repo: str = "", output: Output | None = None) -> None:
    """Transition an item to groomed state on the backend."""
    get_config().backend.apply_status_groomed(item, repo, output)


def apply_status_blocked(item: BacklogItem, repo: str = "", output: Output | None = None) -> None:
    """Transition an item to blocked state on the backend."""
    get_config().backend.apply_status_blocked(item, repo, output)


def issue_to_local_fields(issue: IssueNode) -> IssueLocalFields:
    """Convert a raw IssueNode to a typed IssueLocalFields model.

    Returns:
        Populated IssueLocalFields instance.
    """
    return get_config().backend.issue_to_local_fields(issue)


def create_task_issue(
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
        IssueNode for the created child issue, or None on failure.
    """
    backend = get_config().backend
    if not isinstance(backend, GitHubExtras):
        raise BacklogError("create_task_issue requires a GitHub-backed backend")
    return backend.create_task_issue(repo, parent_issue_number, task, description, acceptance_criteria, labels, output)


def get_task_issues(repo: Repository, parent_issue_number: int, output: Output | None = None) -> list[IssueNode]:
    """Fetch all child task issues for a parent issue.

    Returns:
        List of IssueNode objects for child task issues.
    """
    backend = get_config().backend
    if not isinstance(backend, GitHubExtras):
        raise BacklogError("get_task_issues requires a GitHub-backed backend")
    return backend.get_task_issues(repo, parent_issue_number, output)


def update_task_status(repo: Repository, issue_number: int, new_status: str, output: Output | None = None) -> bool:
    """Update the status label on a task issue.

    Returns:
        True if the status was updated, False otherwise.
    """
    backend = get_config().backend
    if not isinstance(backend, GitHubExtras):
        raise BacklogError("update_task_status requires a GitHub-backed backend")
    return backend.update_task_status(repo, issue_number, new_status, output)


def _fetch_issue_graphql(repo: Repository, owner: str, repo_name: str, issue_number: int) -> IssueNode:
    """Fetch a single issue by number via the active backend.

    Returns:
        IssueNode for the requested issue.
    """
    backend = get_config().backend
    if not isinstance(backend, GitHubExtras):
        raise BacklogError("_fetch_issue_graphql requires a GitHub-backed backend")
    return backend._fetch_issue_graphql(repo, owner, repo_name, issue_number)


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
    """Update an issue's mutable fields via the active backend."""
    backend = get_config().backend
    if not isinstance(backend, GitHubExtras):
        raise BacklogError("_update_issue_graphql requires a GitHub-backed backend")
    backend._update_issue_graphql(
        repo, issue_node_id, state=state, body=body, title=title, label_ids=label_ids, milestone_id=milestone_id
    )


def _update_issues_graphql_batch(repo: Repository, updates: list[tuple[str, str]]) -> None:
    """Update issue bodies in bulk via the active backend.

    Callers must check ``get_config().backend.supports_batch_issue_update``
    before calling this function.  Backends with ``supports_batch_issue_update
    = False`` raise :exc:`NotImplementedError`.
    """
    backend = get_config().backend
    if not isinstance(backend, GitHubExtras):
        raise BacklogError("_update_issues_graphql_batch requires a GitHub-backed backend")
    backend._update_issues_graphql_batch(repo, updates)


def _add_comment_graphql(repo: Repository, issue_node_id: str, body: str) -> str:
    """Add a comment to an issue via the active backend.

    Returns:
        GraphQL node ID of the newly created comment.
    """
    backend = get_config().backend
    if not isinstance(backend, GitHubExtras):
        raise BacklogError("_add_comment_graphql requires a GitHub-backed backend")
    return backend._add_comment_graphql(repo, issue_node_id, body)


def _fetch_issue_comments_graphql(
    repo: Repository, owner: str, repo_name: str, issue_number: int
) -> list[IssueCommentNode]:
    """Fetch all comments on an issue via the active backend.

    Returns:
        List of IssueCommentNode objects for the issue.
    """
    backend = get_config().backend
    if not isinstance(backend, GitHubExtras):
        raise BacklogError("_fetch_issue_comments_graphql requires a GitHub-backed backend")
    return backend._fetch_issue_comments_graphql(repo, owner, repo_name, issue_number)


def _fetch_comment_by_id_graphql(repo: Repository, comment_node_id: str) -> IssueCommentNode:
    """Fetch a single comment by its GraphQL node ID via the active backend.

    Returns:
        IssueCommentNode for the requested comment.
    """
    backend = get_config().backend
    if not isinstance(backend, GitHubExtras):
        raise BacklogError("_fetch_comment_by_id_graphql requires a GitHub-backed backend")
    return backend._fetch_comment_by_id_graphql(repo, comment_node_id)


def _fetch_milestones_graphql(
    repo: Repository, owner: str, repo_name: str, states: list[str] | None = None
) -> list[MilestoneFullNode]:
    """Fetch milestones from the active backend.

    Returns:
        List of MilestoneFullNode objects.
    """
    backend = get_config().backend
    if not isinstance(backend, GitHubExtras):
        raise BacklogError("_fetch_milestones_graphql requires a GitHub-backed backend")
    return backend._fetch_milestones_graphql(repo, owner, repo_name, states)


def _graphql_request(repo: Repository, query: str, variables: dict[str, object] | None = None) -> dict[str, Any]:
    """Execute a raw GraphQL query via the active backend.

    Returns:
        Parsed JSON response dict from the GraphQL endpoint.
    """
    backend = get_config().backend
    if not isinstance(backend, GitHubExtras):
        raise BacklogError("_graphql_request requires a GitHub-backed backend")
    return backend._graphql_request(repo, query, variables)


def _projects_v2_list_query(owner: str, limit: int = 20) -> tuple[str, dict[str, object]]:
    """Build a ProjectsV2 list query string and variables via the active backend.

    Returns:
        Tuple of (query_string, variables_dict).
    """
    backend = get_config().backend
    if not isinstance(backend, GitHubExtras):
        raise BacklogError("_projects_v2_list_query requires a GitHub-backed backend")
    return backend._projects_v2_list_query(owner, limit)


def _projects_v2_create_mutation(owner_id: str, title: str) -> tuple[str, dict[str, object]]:
    """Build a ProjectsV2 create mutation string and variables via the active backend.

    Returns:
        Tuple of (mutation_string, variables_dict).
    """
    backend = get_config().backend
    if not isinstance(backend, GitHubExtras):
        raise BacklogError("_projects_v2_create_mutation requires a GitHub-backed backend")
    return backend._projects_v2_create_mutation(owner_id, title)


# github_sync delegates — original alias names preserved for test patchability


def parse_issue_body_sync(body: str, existing: BacklogItem | None = None) -> BacklogItem:
    """Deserialise a backend issue body into a BacklogItem.

    Returns:
        Populated BacklogItem parsed from the issue body.
    """
    return get_config().backend.parse_issue_body(body, existing)


def merge_item_models(local: BacklogItem, remote: BacklogItem) -> BacklogItem:
    """Merge a local BacklogItem with a remote version.

    Returns:
        Merged BacklogItem combining local and remote fields.
    """
    return get_config().backend.merge_item(local, remote)


def render_issue_body(item: BacklogItem, original_body: str | None = None) -> str:
    """Serialise a BacklogItem to backend issue body markdown.

    Returns:
        Rendered markdown string for the issue body.
    """
    return get_config().backend.render_issue_body(item, original_body)


def unknown_key_to_heading(key: str) -> str:
    """Convert an unknown section key to a markdown heading string.

    Returns:
        Markdown heading string for the key.
    """
    return get_config().backend.unknown_key_to_heading(key)


# ---------------------------------------------------------------------------
# TypedDicts for operations.py return shapes (ADR-002: not in models.py)
# ---------------------------------------------------------------------------


class BacklogListItem(TypedDict):
    """A single backlog item as returned by list_items().

    Used by server.py to remove cast() call sites (T05).
    """

    section: str
    title: str
    issue: str
    plan: str
    type: str
    topic: str
    file_path: NotRequired[str]
    groomed: NotRequired[str]
    status: NotRequired[str]
    milestone: NotRequired[str]


class ListItemsResult(TypedDict):
    """Full result shape returned by list_items().

    Used by server.py to remove cast() call sites (T05).
    """

    items: list[BacklogListItem]
    count: int
    messages: list[str]
    warnings: list[str]
    errors: list[str]


# _SectionMetadata is the internal alias for the public SectionEntryMetadata type defined in
# models.py.  Internal operations.py code continues to use the private name unchanged.
_SectionMetadata = SectionEntryMetadata


def _is_section_entry_metadata(value: object) -> TypeGuard[SectionEntryMetadata]:
    """Return ``True`` when *value* is a :class:`SectionEntryMetadata` TypedDict.

    TypedDict classes are plain ``dict`` at runtime and cannot be used as the
    second argument to ``isinstance``.  The canonical discriminator documented on
    :class:`SectionEntryMetadata` is the presence of the ``'entries'`` key, which
    is absent from :class:`GroomedSectionMetadata`.

    Args:
        value: Any object to test.

    Returns:
        ``True`` when *value* is a dict with an ``'entries'`` key.
    """
    return isinstance(value, dict) and "entries" in value


class ListCommentsResult(TypedDict):
    """Result shape returned by list_comments()."""

    comments: list[dict[str, str]]
    count: int
    has_more: bool
    messages: list[str]
    warnings: list[str]
    errors: list[str]


def _md_reconstruct_body_from_sections(
    local_sections: dict[str, str], github_sections: dict[str, str], result_sections: dict[str, str]
) -> str:
    """Reconstruct body from merged sections for legacy .md format.

    Preserves local section order, then appends GitHub-only sections.

    Args:
        local_sections: Original local section map (preserves order).
        github_sections: GitHub section map (source of new sections).
        result_sections: Merged result to render from.

    Returns:
        Reconstructed body string ending with newline.
    """
    seen: set[str] = set()
    parts: list[str] = []
    for heading in local_sections:
        content = result_sections[heading]
        parts.append(f"{heading}\n\n{content}" if content else heading)
        seen.add(heading)
    for heading in github_sections:
        if heading not in seen:
            content = result_sections[heading]
            parts.append(f"{heading}\n\n{content}" if content else heading)
    return "\n\n".join(parts) + "\n"


# ---------------------------------------------------------------------------
# File metadata
# ---------------------------------------------------------------------------


def _apply_updates_to_item(reference: str, updates: dict[str, str | dict[str, object]], set_synced: bool) -> None:
    item = _work_item(reference)
    for key, value in updates.items():
        if key == "metadata" and isinstance(value, dict):
            for meta_key, meta_val in value.items():
                if hasattr(item.metadata, meta_key):
                    setattr(item.metadata, meta_key, meta_val)
        elif key == "name":
            item.title = str(value)
        elif key == "description":
            item.description = str(value)
        elif hasattr(item.metadata, key):
            setattr(item.metadata, key, str(value))
    if set_synced:
        item.metadata.last_synced = now_iso()
    get_config().backend.put_work_item(item)


def update_item_metadata(
    reference: str, updates: dict[str, str | dict[str, object]], set_synced: bool = False, output: Output | None = None
) -> dict[str, str | bool | list[str]]:
    """Update a work item through its opaque backend reference.

    When set_synced=True, also sets metadata.last_synced to current UTC time.

    Returns:
        Dict with compatibility filepath and updated flag plus output messages.
    """
    out = output or Output()
    _apply_updates_to_item(reference, updates, set_synced)
    return {"filepath": reference, "updated": True, **out.to_dict()}


# ---------------------------------------------------------------------------
# Internal helpers (not exported)
# ---------------------------------------------------------------------------


_CHANGES_KEY_MAP: dict[str, str] = {
    "renamed_to": "title",
    "description_updated": "description",
    "plan": "plan",
    "status": "status",
    "issue_num": "issue_num",
}


def _extract_changes(result: Mapping[str, object]) -> dict[str, str | int | bool]:
    """Build a changes summary from update_item result keys.

    Returns:
        Dict mapping changed field names to their new values.
    """
    changes: dict[str, str | int | bool] = {}
    for key, target in _CHANGES_KEY_MAP.items():
        if key not in result:
            continue
        val = result[key]
        if target == "issue_num":
            changes[target] = int(str(val))
        elif target == "description":
            changes[target] = True
        else:
            changes[target] = str(val)
    return changes


def _create_issue_and_update_item(item: BacklogItem, repo: str, output: Output | None = None) -> int | None:
    """Create GitHub issue for item and update backend-owned metadata.

    Returns:
        Issue number if created, None otherwise.
    """
    out = output or Output()
    repository = try_get_github(repo)
    if repository is None:
        return None
    try:
        issue_num = create_issue_for_item(repository, item, dry_run=False, output=out)
    except (GithubException, BacklogError) as e:
        out.warn(f"  WARNING: Issue creation failed: {e}")
        return None
    else:
        if not issue_num:
            return None
        reference = item.reference
        if reference:
            update_item_metadata(reference, {"metadata": {"issue": f"#{issue_num}"}}, output=out)
        return issue_num


def _rename_item_title(item: BacklogItem, title: str, repo: str = "", output: Output | None = None) -> bool:
    """Update the backend-owned item title. Syncs to GitHub issue title if linked.

    Returns:
        True if updated, False if no backend reference on item.
    """
    out = output or Output()
    reference = item.reference
    if not reference:
        return False
    update_item_metadata(reference, {"name": title}, output=out)

    issue_ref = item.issue
    if issue_ref:
        if get_config().backend.issue_id_type == "string":
            # String-ID backend (e.g. beads): issue ref is a nanoid, not a GitHub number.
            # Backend-owned title was already updated above; no GitHub sync needed.
            return True
        repository = try_get_github(repo)
        if repository is not None:
            try:
                num = parse_issue_number(issue_ref)
                if num is None:
                    msg = f"Expected numeric GitHub issue ref, got {issue_ref!r}"
                    raise ValueError(msg)
                owner, repo_name = repository.full_name.split("/", 1)
                issue_node = _fetch_issue_graphql(repository, owner, repo_name, num)
                _update_issue_graphql(repository, issue_node["id"], title=title)
                out.info(f"  GitHub issue {issue_ref} title updated to: {title}")
            except (GithubException, BacklogError) as e:
                out.warn(f"  WARNING: Could not update issue {issue_ref} title: {e}")

    return True


def _update_item_description(item: BacklogItem, description: str, output: Output | None = None) -> bool:
    """Update the backend-owned item description. Provider-only, no GitHub sync.

    Returns:
        True if updated, False if no backend reference on item.
    """
    out = output or Output()
    reference = item.reference
    if not reference:
        return False
    update_item_metadata(reference, {"description": description}, output=out)
    return True


def _apply_plan_to_item(item: BacklogItem, plan: str, repo: str = "", output: Output | None = None) -> bool:
    """Apply plan update through GitHub and the configured backend.

    Posts a plan comment on the linked GitHub Issue before updating the backend-owned record.
    If GitHub is unavailable, the backend update still succeeds.

    Returns:
        True if updated, False otherwise.
    """
    out = output or Output()
    reference = item.reference
    if not reference:
        return False
    update_item_metadata(reference, {"metadata": {"plan": plan}}, output=out)

    # GH-first: post plan reference as a comment on the linked issue
    issue_ref = item.issue
    if issue_ref:
        if get_config().backend.issue_id_type == "string":
            # String-ID backend (e.g. beads): issue ref is a nanoid, not a GitHub number.
            # Local plan metadata was already updated above; no GitHub sync needed.
            return True
        repository = try_get_github(repo)
        if repository is not None:
            try:
                num = parse_issue_number(issue_ref)
                if num is None:
                    msg = f"Expected numeric GitHub issue ref, got {issue_ref!r}"
                    raise ValueError(msg)
                owner, repo_name = repository.full_name.split("/", 1)
                issue_node = _fetch_issue_graphql(repository, owner, repo_name, num)
                _add_comment_graphql(repository, issue_node["id"], f"**Plan**: {plan}")
                out.info(f"  Plan comment posted to issue {issue_ref}")
            except (GithubException, BacklogError) as e:
                out.warn(f"  WARNING: Could not post plan to issue {issue_ref}: {e}")

    return True


def _resolve_groomed_content(
    section: str | None, content: str | None, groomed_content: str | None, groomed_file: str | None
) -> tuple[str, str | None]:
    """Resolve groomed content from section/content, groomed_content, or groomed_file.

    Returns:
        Tuple of (content_string, section_name_or_None).

    Raises:
        ValidationError: If no content source is provided. stdin is not supported in MCP/agent context.
    """
    if section is not None and content is not None:
        return content, section
    if groomed_content is not None:
        return groomed_content, None
    if groomed_file:
        return Path(groomed_file).read_text(encoding="utf-8"), None
    msg = "No groomed content provided — supply section+content, groomed_content, or groomed_file"
    raise ValidationError(msg)


def _extract_subsection_body(body: str, section_name: str) -> str:
    """Extract the content of a ### subsection under ## Groomed.

    Returns:
        Subsection body text, or empty string if not found.
    """
    groomed_re = re.compile(r"## Groomed\s*\([^)]*\)\s*\n([\s\S]*?)(?=\n## |\Z)", re.MULTILINE)
    groomed_match = groomed_re.search(body)
    if not groomed_match:
        return ""
    groomed_body = groomed_match.group(1)
    sub_re = re.compile(
        rf"### {re.escape(section_name.strip())}[^\n]*\n([\s\S]*?)(?=\n### |\n## |\Z)", re.IGNORECASE | re.MULTILINE
    )
    sub_match = sub_re.search(groomed_body)
    if not sub_match:
        return ""
    return sub_match.group(1).strip()


def _apply_groomed_entries(
    section: Section,
    groomed_content: str,
    *,
    append: bool,
    replace_section: bool,
    reason: str | None,
    entry_id: str | None,
    added_date: str,
) -> None:
    """Mutate a Section's entry list according to the requested grooming operation.

    Args:
        section: Section whose entries are updated in place.
        groomed_content: Content for the new or updated entry.
        append: Always append without matching by id.
        replace_section: Strike all existing entries and append new content.
            Requires ``reason``.
        reason: Strike reason; required when ``replace_section`` is ``True``.
        entry_id: Id of an existing entry to update in place.
        added_date: ISO date string used as id prefix for legacy seeding.

    Raises:
        ValueError: When ``replace_section`` is ``True`` but ``reason`` is empty.
    """
    if append:
        section.entries.append(Entry(id=now_iso(), content=groomed_content))
        return
    if replace_section:
        if not reason:
            msg = "reason is required when replace_section=True"
            raise ValueError(msg)
        struck_at = now_iso()
        for entry in section.entries:
            if not entry.struck:
                entry.struck = True
                entry.struck_at = struck_at
                entry.struck_reason = reason
        section.entries.append(Entry(id=now_iso(), content=groomed_content))
        return
    if entry_id:
        for entry in section.entries:
            if entry.id == entry_id:
                entry.content = groomed_content
                return
        section.entries.append(Entry(id=entry_id, content=groomed_content))
        return
    # Default: append only when content is non-empty and not already present.
    # Identical content in any existing unstruck entry is treated as idempotent.
    if groomed_content.strip() and not any(e.content == groomed_content and not e.struck for e in section.entries):
        section.entries.append(Entry(id=now_iso(), content=groomed_content))


def _normalize_section_key(name: str) -> str:
    """Return the canonical snake_case storage key for a section name.

    Resolves display names (e.g. ``"RT-ICA"``) and aliases (e.g. ``"rt-ica"``) to
    the snake_case key used in ``SECTION_HEADING`` (e.g. ``"rt_ica"``).  Unknown
    and custom section names are returned unchanged so they pass through as-is.

    Lookup order:
    1. ``SECTION_HEADING_ALIAS`` keyed by ``name.lower()`` — catches hyphened aliases.
    2. Reverse scan of ``SECTION_HEADING`` for a matching display value — catches
       display names stored verbatim (e.g. ``"RT-ICA"`` → ``"rt_ica"``).
    3. Return *name* unchanged when no match is found.

    Args:
        name: Section name as provided by the caller (e.g. ``"RT-ICA"`` or ``"rt_ica"``).

    Returns:
        Canonical snake_case key (e.g. ``"rt_ica"``), or *name* unchanged for unknown sections.
    """
    alias_key = SECTION_HEADING_ALIAS.get(name.lower())
    if alias_key is not None:
        return alias_key
    for snake_key, display in SECTION_HEADING.items():
        if display == name:
            return snake_key
    return name


def _write_groomed_to_item(
    reference: str,
    groomed_content: str,
    section_name: str | None = None,
    *,
    entry_id: str | None = None,
    replace_section: bool = False,
    reason: str | None = None,
    added_date: str = "0000-00-00",
    append: bool = False,
) -> None:
    """Write groomed content into a backend-owned work item.

    Loads the item by opaque reference, updates the relevant section, sets the
    groomed date on metadata, and persists it through the configured backend.

    Args:
        reference: Opaque stable work-item reference.
        groomed_content: The text to write into the section.
        section_name: Named section to update.  When ``None`` the top-level
            ``groomed`` section (stored as ``GroomedData``) is updated.
        entry_id: Optional ID used to locate an existing entry for update.
        replace_section: When ``True``, strike all existing entries and add
            the new content as a replacement.  Requires ``reason``.
        reason: Strike reason; required when ``replace_section`` is ``True``.
        added_date: ISO date used as the entry id when migrating legacy text.
        append: When ``True``, always append a new entry rather than updating
            by id.
    """
    item = _work_item(reference)
    today_str = today()
    item.metadata.groomed = today_str

    if section_name is None:
        existing = item.sections.get("groomed")
        groomed_data = existing if isinstance(existing, GroomedData) else GroomedData(date=today_str)
        groomed_data.date = today_str
        groomed_data.subsections["content"] = groomed_content.strip()
        item.sections["groomed"] = groomed_data
    else:
        section_key = _normalize_section_key(section_name)
        existing_section = item.sections.get(section_key)
        section = existing_section if isinstance(existing_section, Section) else Section()
        _apply_groomed_entries(
            section,
            groomed_content,
            append=append,
            replace_section=replace_section,
            reason=reason,
            entry_id=entry_id,
            added_date=added_date,
        )
        item.sections[section_key] = section

    get_config().backend.put_work_item(item)


def _write_groomed_to_reference(
    reference: str,
    groomed_content: str,
    section_name: str | None = None,
    output: Output | None = None,
    *,
    entry_id: str | None = None,
    replace_section: bool = False,
    reason: str | None = None,
    added_date: str = "0000-00-00",
    append: bool = False,
) -> None:
    """Merge groomed content into a backend-owned work item.

    Args:
        reference: Opaque stable work-item reference.
        groomed_content: Content to merge into the item.
        section_name: Named section to update; when ``None`` the top-level
            ``groomed`` section is replaced.
        output: Optional output collector (unused; kept for API compatibility).
        entry_id: Optional ID used to locate an existing entry for update.
        replace_section: Strike existing entries and replace when ``True``.
        reason: Strike reason; required when ``replace_section`` is ``True``.
        added_date: ISO date for legacy entry migration.
        append: When ``True``, always append a new entry rather than updating
            by id.
    """
    _write_groomed_to_item(
        reference,
        groomed_content,
        section_name,
        entry_id=entry_id,
        replace_section=replace_section,
        reason=reason,
        added_date=added_date,
        append=append,
    )


_AC_CHECKBOX_RE = re.compile(r"^- \[[ xX]\]", re.MULTILINE)
_AC_HEADER_RE = re.compile(r"^#{2,3}\s+Acceptance", re.MULTILINE | re.IGNORECASE)
_AC_OVERLAP_MSG = (
    "Description contains AC-like content (checkboxes or Acceptance header found). "
    "Verify the Acceptance Criteria section does not duplicate the description."
)


def _check_ac_overlap(item: BacklogItem, output: Output) -> None:
    """Warn if item description contains checkbox or Acceptance-header patterns.

    Advisory only — does not block the write.

    Args:
        item: BacklogItem whose description will be inspected.
        output: Output aggregator to receive the warning.
    """
    body = item.description or ""
    if _AC_CHECKBOX_RE.search(body) or _AC_HEADER_RE.search(body):
        output.warn(_AC_OVERLAP_MSG)


def _reconcile_groomed_item(item: BacklogItem, output: Output) -> None:
    backend = get_config().backend
    if not item.issue or not isinstance(backend, SyncProvider):
        return
    try:
        result = backend.reconcile(ReconcileRequest(scope=ReconcileScope.TARGETED, references=[item.issue]))
    except BackendUnavailableError:
        output.info(f"Queued {item.issue} for provider reconciliation.")
        return
    output.info(
        f"Reconciled {item.issue}: {result.provider_patches} provider patch(es), "
        f"{result.pending_mutations} pending mutation(s), {result.failures} failure(s)."
    )


def _handle_update_groomed(
    item: BacklogItem,
    groomed_content_val: str,
    section_name: str | None,
    repo: str,
    output: Output | None = None,
    *,
    entry_id: str | None = None,
    replace_section: bool = False,
    reason: str | None = None,
    append: bool = False,
) -> None:
    """Handle groomed content through the configured backend and its sync capability."""
    out = output or Output()
    added_date = item.added if hasattr(item, "added") and item.added else "0000-00-00"

    if section_name == "Acceptance Criteria":
        _check_ac_overlap(item, out)

    _write_groomed_to_reference(
        item.reference,
        groomed_content_val,
        section_name,
        output=out,
        entry_id=entry_id,
        replace_section=replace_section,
        reason=reason,
        added_date=added_date,
        append=append,
    )
    out.info(f"Updated {item.reference} with groomed content")
    _reconcile_groomed_item(item, out)


def _handle_batch_groomed(
    item: BacklogItem, sections: dict[str, str], repo: str, output: Output | None = None
) -> list[str]:
    """Write multiple groomed sections, then reconcile the linked item once.

    Args:
        item: BacklogItem with a stable backend reference.
        sections: Mapping of section name to raw content (entry-block wrapping applied automatically).
        repo: GitHub repo slug (e.g. "owner/repo").
        output: Optional Output aggregator.

    Returns:
        List of section names that were written locally.

    Raises:
        BacklogError: If item has no file_path.
    """
    out = output or Output()
    if not item.reference:
        msg = "Item has no backend reference"
        raise BacklogError(msg)
    added_date = item.added if hasattr(item, "added") and item.added else "0000-00-00"

    # Phase 1: Local writes — load once, apply all sections in memory, save once.
    # Loading once avoids the legacy-MD-parser-on-YAML-content failure that occurs
    # when a YAML write targets a .md filepath and a subsequent backend read on
    # that same path incorrectly re-parses it as Markdown, losing prior sections.
    written: list[str] = []
    batch_item = _work_item(item.reference)
    today_str = today()
    batch_item.metadata.groomed = today_str
    for section_name, content in sections.items():
        section_key = _normalize_section_key(section_name)
        existing_section = batch_item.sections.get(section_key)
        section = existing_section if isinstance(existing_section, Section) else Section()
        _apply_groomed_entries(
            section, content, append=False, replace_section=False, reason=None, entry_id=None, added_date=added_date
        )
        batch_item.sections[section_key] = section
        written.append(section_key)
    get_config().backend.put_work_item(batch_item)
    out.info(f"Updated {item.reference} with {len(written)} groomed section(s)")

    if "Acceptance Criteria" in sections:
        _check_ac_overlap(item, out)

    _reconcile_groomed_item(batch_item, out)

    return written


def _pull_if_issue_selector(selector: str, repo: str, output: Output | None = None) -> None:
    """Fetch a GitHub issue into the provider-backed record when selector resolves to an issue number.

    Calls pull_single_issue when parse_issue_selector returns a number. No-op otherwise.

    Args:
        selector: Backlog selector string (title, #N, bare number, or URL).
        repo: GitHub repo in owner/repo format.
        output: Optional Output collector.
    """
    issue_num = parse_issue_selector(selector)
    if issue_num:
        pull_single_issue(int(issue_num), output=output)


# ---------------------------------------------------------------------------
# Pull helpers
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Public API: ADD  (private helpers)
# ---------------------------------------------------------------------------


def _validate_add_item_priority(priority: str) -> None:
    """Raise ValidationError if priority is not an accepted value for a new item.

    Accepts the canonical set (``VALID_NEW_ITEM_PRIORITIES``) plus any
    case-insensitive ``idea*`` variant, matching the convenience normalisation
    ``BacklogItemMetadata._validate_priority`` applies when the value is later
    written into the item's YAML frontmatter.

    Args:
        priority: Raw priority value supplied by the caller.

    Raises:
        ValidationError: If priority is not a recognized value.
    """
    if priority in VALID_NEW_ITEM_PRIORITIES or priority.lower().startswith("idea"):
        return
    msg = f"Invalid priority: {priority!r}. Valid priorities: {', '.join(VALID_NEW_ITEM_PRIORITIES)} (or an 'Idea*' variant)."
    raise ValidationError(msg)


def _validate_add_item_type(type_: str) -> None:
    """Raise ValidationError if type_ is not a recognized item type or alias.

    Args:
        type_: Raw item type value supplied by the caller.

    Raises:
        ValidationError: If type_ is not a recognized value or alias.
    """
    if type_ in VALID_ITEM_TYPES or type_.lower() in ITEM_TYPE_ALIASES:
        return
    msg = (
        f"Invalid type: {type_!r}. Valid types: {', '.join(VALID_ITEM_TYPES)} "
        f"(aliases: {', '.join(ITEM_TYPE_ALIASES)})."
    )
    raise ValidationError(msg)


def _check_for_duplicates(title: str, force: bool) -> None:
    """Raise DuplicateItemError if a fuzzy duplicate exists and force is False.

    Args:
        title: Title of the new item.
        force: When True, skip the check entirely.

    Raises:
        DuplicateItemError: If one or more similar titles are found.
    """
    if force:
        return
    existing_items = get_config().backend.list_work_items()
    duplicates = find_fuzzy_duplicates(title, existing_items)
    if not duplicates:
        return
    raise DuplicateItemError(duplicates)


def _resolve_reference(priority: str, slug: str) -> str:
    base = f"{priority.lower()}-{slug}"
    reference = base
    existing_references = {item.reference for item in get_config().backend.list_work_items()}
    idx = 0
    while reference in existing_references:
        idx += 1
        reference = f"{base}-{idx}"
    return reference


def _try_create_github_issue(item_data: BacklogItem, repo: str, out: Output) -> int | None:
    """Attempt to create a GitHub issue for item_data; return issue number or None.

    Args:
        item_data: Populated BacklogItem (file_path may be empty at this stage).
        repo: Repository slug (owner/name).
        out: Output collector for warnings.

    Returns:
        Issue number on success, None when GitHub is unavailable or creation fails.
    """
    repository = try_get_github(repo)
    if repository is None:
        out.warn("  WARNING: GitHub unavailable — creating local-only item")
        return None
    try:
        return create_issue_for_item(repository, item_data, dry_run=False, output=out)
    except (GithubException, BacklogError) as e:
        out.warn(f"  WARNING: Issue creation failed: {e}")
        return None


def _try_create_backend_issue_ref(item_data: BacklogItem, repo: str, out: Output) -> str:
    """Create a backend issue and return the issue ref string, or empty string on failure.

    Dispatches to the appropriate backend-native creation path:

    - String-ID backends (beads): calls ``create_beads_issue_for_item`` on the
      backend, returns the nanoid (e.g. ``"bd-a3f8"``).
    - Integer-ID backends (GitHub, sqlite, memory): calls
      ``_try_create_github_issue``, formats the returned number as ``"#N"``.

    The return value is always a ``str``: non-empty on success, empty string
    when the backend is unavailable or creation fails.

    Args:
        item_data: Populated BacklogItem (file_path may be empty at this stage).
        repo: Repository slug (owner/name) — used by integer-ID backends.
        out: Output collector for warnings.

    Returns:
        Issue ref string (e.g. ``"#42"`` or ``"bd-a3f8"``), or ``""`` on failure.
    """
    backend = get_config().backend
    if backend.issue_id_type == "string":
        from backlog_core.backends.beads_backend import BeadsBackend  # ruff: ignore[import-outside-top-level]

        if isinstance(backend, BeadsBackend):
            nanoid = backend.create_beads_issue_for_item(item_data, output=out)
            return nanoid or ""
        # Unknown string-ID backend — log and fall through to local-only.
        out.warn("  WARNING: String-ID backend does not support create_beads_issue_for_item — creating local-only item")
        return ""
    # Integer-ID backend path (GitHub, sqlite, memory).
    issue_num = _try_create_github_issue(item_data, repo, out)
    return f"#{issue_num}" if issue_num else ""


def _build_item_body(research_first: str, files: str, suggested_location: str) -> str:
    """Build the markdown body appended below the frontmatter.

    Args:
        research_first: Optional research-first note.
        files: Optional file references.
        suggested_location: Optional suggested location note.

    Returns:
        Markdown string (empty when all inputs are empty).
    """
    parts: list[str] = []
    if research_first:
        parts.append(f"**Research first**: {research_first}")
    if files:
        parts.append(f"**Files**: {files}")
    if suggested_location:
        parts.append(f"**Suggested location**: {suggested_location}")
    return "\n".join(parts) + "\n" if parts else ""


# ---------------------------------------------------------------------------
# Public API: ADD
# ---------------------------------------------------------------------------


def add_item(
    title: str,
    description: str,
    priority: str,
    source: str = "Not specified",
    type_: str = "Feature",
    research_first: str = "",
    files: str = "",
    suggested_location: str = "",
    force: bool = False,
    repo: str = "",
    output: Output | None = None,
) -> dict[str, str | int | bool | list[str]]:
    """Add an item through the configured backend and optionally create its native issue.

    Dispatches issue creation to the active backend:

    - Integer-ID backends (GitHub, sqlite, memory): creates an issue and
      stores the ref as ``"#N"``.
    - String-ID backends (beads): calls ``bd create`` and stores the returned
      nanoid (e.g. ``"bd-a3f8"``).

    Returns:
        Dict with title, priority, logical reference, compatibility ``file_path``, and optionally item_ref.

    Raises:
        ValidationError: If priority or type_ is not a recognized value. No
            item is stored and no backend issue is created when raised.
    """
    _validate_add_item_priority(priority)
    _validate_add_item_type(type_)

    out = output or Output()

    _check_for_duplicates(title, force)

    today_str = today()
    slug = title_to_slug(title)
    # Backend-first: try to create a backend issue BEFORE storing the backend record.
    # _try_create_backend_issue_ref returns the issue ref string ready to store,
    # or an empty string when the backend is unavailable or creation fails.
    item_data = BacklogItem(
        title=title,
        description=description,
        source=source,
        added=today_str,
        priority=priority,
        item_type=type_,
        research_first=research_first,
        files=files,
        suggested_location=suggested_location,
    )
    issue_ref = _try_create_backend_issue_ref(item_data, repo, out)
    item_reference = issue_ref or _resolve_reference(priority, slug)

    # Build and persist the backend-owned work item
    item_to_write = BacklogItem(
        title=title,
        description=description,
        source=source,
        added=today_str,
        priority=priority,
        item_type=type_,
        status="open",
        issue=issue_ref,
        reference=item_reference,
        research_first=research_first,
        files=files,
        suggested_location=suggested_location,
    )
    if issue_ref:
        item_to_write.metadata.last_synced = now_iso()
    get_config().backend.put_work_item(item_to_write)

    out.info(f"Backlog item created.\n  Title: {title}\n  Priority: {priority}\n  Reference: {item_reference}")
    if issue_ref:
        out.info(f"  Issue: {issue_ref}")
    out.info(f"Next steps: /groom-backlog-item {title}  /work-backlog-item {title}")

    result: dict[str, str | int | bool | list[str]] = {
        "title": title,
        "priority": priority,
        "reference": item_reference,
        "file_path": item_reference,
    }
    if issue_ref:
        result["item_ref"] = issue_ref
    return {**result, **out.to_dict()}


# ---------------------------------------------------------------------------
# Public API: LIST
# ---------------------------------------------------------------------------


def refresh_local_cache_from_github(
    repo: str = "",
    label: str | None = None,
    output: Output | None = None,
    full_refresh: bool = False,
    progress_callback: Callable[[int, int | None], None] | None = None,
) -> dict[str, int | list[str]]:
    """Reconcile provider items through the configured backend.

    Args:
        repo: Provider repository slug retained for wrapper compatibility.
        label: Optional label name to restrict the fetch.
        output: Optional ``Output`` accumulator for messages.
        full_refresh: Request an initial provider snapshot instead of an
            incremental snapshot.
        progress_callback: Optional callable invoked after each issue is
            reconciled. Receives ``(items_done, items_total)``.

    Returns:
        Dict with count of refreshed (open) issues and count of reconciled
        (closed) issues.
    """
    out = output or Output()
    backend = get_config().backend
    if not isinstance(backend, SyncProvider):
        out.info("Active backend does not support reconciliation.")
        return {"refreshed": 0, "reconciled": 0, **out.to_dict()}
    scope = ReconcileScope.INITIAL if full_refresh else ReconcileScope.INCREMENTAL
    references = (
        []
        if label and scope in {ReconcileScope.INITIAL, ReconcileScope.INCREMENTAL}
        else [item.metadata.issue for item in items_with_issues(get_config().backend.list_work_items())]
    )
    result = backend.reconcile(ReconcileRequest(scope=scope, label=label or "", references=references))
    if progress_callback is not None:
        progress_callback(result.fetched_items, result.fetched_items)
    out.info(
        f"Reconciled {result.fetched_items} provider item(s): {result.local_updates} local updates, "
        f"{result.provider_patches} patches, {result.no_ops} no-ops, {result.failures} failures."
    )
    return {"refreshed": result.local_updates, "reconciled": result.deleted_provider_items, **out.to_dict()}


def _item_derived_status(item: BacklogItem, status_map: dict[int, IssueStatus]) -> str:
    """Return the effective status string for an item.

    For items with a numeric GitHub issue reference, looks up the live status
    from *status_map*.  For items with a non-integer issue reference (e.g. a
    beads nanoid ``"bd-a3f8"``) or no issue at all, falls back to the locally
    cached ``item.status`` field.  This prevents beads and other string-ID
    backends from always returning ``"needs-grooming"`` when the status map is
    empty (ADR-002).

    Returns:
        Status string — either the GitHub label value from *status_map* or the
        local ``item.status`` value, defaulting to ``"needs-grooming"`` when
        neither is available.
    """
    num = parse_issue_number(item.issue)
    if num is not None:
        info = status_map.get(num)
        return info.status if info is not None else "needs-grooming"
    # Non-integer issue ref (beads nanoid) or no issue — use backend-owned status.
    return item.status or "needs-grooming"


def _filter_open_items(
    open_items: list[BacklogItem],
    section: str | None,
    title: str | None,
    status: str | None,
    status_map: dict[int, IssueStatus],
    type_: str | None = None,
    topic: str | None = None,
) -> list[BacklogItem]:
    """Apply section, title, status, type, and topic filters to open_items.

    type_ performs a case-insensitive exact match against metadata.type.
    Items missing metadata.type are excluded when type_ filter is active.

    topic performs a case-insensitive substring match against metadata.topic.
    Items missing metadata.topic are excluded when topic filter is active.

    Filters compose with AND logic.

    Returns:
        Filtered list of BacklogItem objects matching all supplied criteria.
    """
    if section:
        section_upper = section.upper()
        open_items = [it for it in open_items if it.section and it.section.upper() == section_upper]
    if title:
        title_lower = title.lower()
        open_items = [it for it in open_items if title_lower in it.title.lower()]
    if status:
        open_items = [it for it in open_items if _item_derived_status(it, status_map) == status]
    if type_:
        type_lower = type_.lower()
        open_items = [it for it in open_items if it.type_ and it.type_.lower() == type_lower]
    if topic:
        topic_lower = topic.lower()
        open_items = [it for it in open_items if it.topic and topic_lower in it.topic.lower()]
    return open_items


_TERMINAL_STATUSES: frozenset[str] = frozenset({"done", "resolved", "closed"})


def _filter_closed_items(items: list[BacklogItem], include_closed: bool) -> list[BacklogItem]:
    """Filter out items whose local status is a terminal state.

    Terminal states are ``done``, ``resolved``, and ``closed``.

    Args:
        items: Parsed BacklogItem objects.
        include_closed: When ``True``, return all items unfiltered.

    Returns:
        Filtered list excluding terminal-status items, or the original list
        when ``include_closed`` is ``True``.
    """
    if include_closed:
        return items
    return [it for it in items if it.status not in _TERMINAL_STATUSES]


def _build_item_search_body(item: BacklogItem) -> str:
    """Return all searchable text content of a backlog item as a single string.

    Concatenates the item description with every non-struck Section entry
    content and every GroomedData subsection value, separated by spaces.
    This string is stored in the ``body`` field of list entries so that
    full-text search covers the complete item content.

    Args:
        item: The BacklogItem whose sections to render.

    Returns:
        Space-joined string of all content fragments.
    """
    parts: list[str] = []
    if item.description:
        parts.append(item.description)
    for sec in item.sections.values():
        if isinstance(sec, Section):
            parts.extend(e.content for e in sec.entries if not e.struck and e.content)
        elif isinstance(sec, GroomedData):
            parts.extend(v for v in sec.subsections.values() if v)
    return " ".join(parts)


def _build_list_entry(item: BacklogItem, status_map: dict[int, IssueStatus]) -> dict[str, str | bool]:
    """Build the result dict for a single backlog item.

    Returns:
        Dict with section, title, issue, plan, type, topic, body, state,
        status, milestone, and optional file_path and groomed fields.
        The ``body`` field contains the full searchable text (description
        plus all section entry content) for use by the search filter.
    """
    entry: dict[str, str | bool] = {
        "section": item.section,
        "title": item.title,
        "issue": item.issue,
        "plan": item.plan,
        "type": item.type_,
        "topic": item.topic,
        "description": item.description,
        "body": _build_item_search_body(item),
    }
    if item.reference:
        entry["file_path"] = item.reference
    if item.groomed:
        entry["groomed"] = item.groomed
    if item.issue:
        num = parse_issue_number(item.issue)
        if num is not None:
            info = status_map.get(num)
            entry["status"] = info.status if info is not None else ""
            entry["milestone"] = info.milestone if info is not None else ""
        else:
            # Non-integer issue ref (e.g. beads nanoid "bd-a3f8"): status_map
            # cannot be keyed by int, so use the locally cached status field.
            # Milestone is not tracked locally for string-ID backends.
            entry["status"] = item.status or ""
            entry["milestone"] = ""
    elif item.status:
        # No issue reference at all (e.g. beads item never linked to a backend
        # issue).  Expose the locally cached status so consumers and filters
        # can see the real state rather than finding no ``status`` key.
        entry["status"] = item.status
    return entry


def list_items(
    from_github: bool = False,
    label: str | None = None,
    section: str | None = None,
    status: str | None = None,
    title: str | None = None,
    type_: str | None = None,
    topic: str | None = None,
    include_closed: bool = False,
    repo: str = "",
    output: Output | None = None,
    filter_by_key: dict[str, str] | None = None,
) -> dict[str, int | list[str] | list[dict[str, str | bool]]]:
    """List backlog items. Default reads provider-backed record only. Use from_github=True to refresh first.

    Args:
        from_github: Refresh provider-backed record from GitHub Issues before listing.
        label: Filter by GitHub label (applied during refresh).
        section: Filter by priority section — P0, P1, P2, or Ideas (case-insensitive).
        status: Filter by status value e.g. 'needs-grooming', 'status:in-progress'.
        title: Filter items whose title contains this substring (case-insensitive).
        type_: Filter by metadata.type — case-insensitive exact match (e.g. 'Bug', 'Feature').
            Items missing metadata.type are excluded when this filter is active.
        topic: Filter by metadata.topic — case-insensitive substring match.
            Items missing metadata.topic are excluded when this filter is active.
        include_closed: When True, include items with terminal status (done, resolved, closed).
        repo: GitHub repo in owner/repo format.
        output: Optional Output collector.
        filter_by_key: Generic key=value filter applied AFTER type/topic/status
            filtering, on the result item dicts. Each ``key=value`` pair matches
            items where the item's value for ``key`` equals ``value`` (string
            comparison). All pairs compose with AND logic. A key the item does
            not carry returns no match (a no-op, not an error). Existing
            type/topic/status filters are unaffected.

    Returns:
        Dict with items list (each item a dict with section, title, issue, plan, type, topic,
        file_path, groomed, status, and milestone fields for items with a GitHub issue).
    """
    out = output or Output()
    if from_github:
        refresh_local_cache_from_github(repo, label, output=out)
    items = get_config().backend.list_work_items()
    # Start with non-skipped items that have a section. The skip flag may be set
    # for reasons other than terminal status (e.g. malformed entries), so we
    # always exclude skip=True items regardless of include_closed. The
    # _filter_closed_items call below then decides whether terminal-status items
    # are included based on include_closed.
    open_items = [it for it in items if not it.skip and it.section]
    open_items = _filter_closed_items(open_items, include_closed)
    # Skip the batch fetch for backends that do not support it (e.g. beads,
    # Linear).  Those backends raise NotImplementedError from
    # batch_fetch_statuses because their issue IDs are strings with no integer
    # representation (BacklogBackend.supports_batch_status_fetch == False).
    # The backend-owned status field is authoritative for such backends — pass an
    # empty map.  _item_derived_status and _build_list_entry both fall back to
    # item.status when the map is empty.
    if get_config().backend.supports_batch_status_fetch:
        status_map = batch_fetch_statuses(open_items, repo)
    else:
        status_map: dict[int, IssueStatus] = {}
    open_items = _filter_open_items(open_items, section, title, status, status_map, type_=type_, topic=topic)
    result_items = [_build_list_entry(it, status_map) for it in open_items]
    if filter_by_key:
        result_items = [it for it in result_items if all(str(it.get(k)) == v for k, v in filter_by_key.items())]
    return {"items": result_items, "count": len(result_items), **out.to_dict()}


# ---------------------------------------------------------------------------
# Public API: FOLLOWUP — link a follow-up backlog item to its origin
# ---------------------------------------------------------------------------


def link_followup(selector: str, followup_to: str, output: Output | None = None) -> dict[str, str | bool | list[str]]:
    """Link a backlog item to its originating plan or task via ``followup_to``.

    Records the logical ID of the origin (e.g. ``"P1"``, ``"P1/T3"``) on the
    item's ``metadata.followup_to`` field and persists it to YAML frontmatter.

    Args:
        selector: Item selector — title substring, issue ref, or file path
            (forwarded to :func:`find_item`).
        followup_to: Logical ID of the originating plan or task.  Use the
            ``P{N}`` / ``P{N}/T{N}`` address form (or a slug).  Empty string
            clears the link.
        output: Optional :class:`Output` collector.

    Returns:
        Dict with ``title``, ``followup_to``, and output messages/warnings.

    Raises:
        ItemNotFoundError: When *selector* does not match any backlog item.
    """
    out = output or Output()
    item = find_item(get_config().backend.list_work_items(), selector)
    if not item:
        raise ItemNotFoundError(selector)
    reference = item.reference
    if not reference:
        msg = f"Item {selector!r} has no file_path — cannot persist followup_to"
        raise BacklogError(msg)
    update_item_metadata(reference, {"metadata": {"followup_to": followup_to}}, output=out)
    out.info(f"  Linked follow-up: {item.title} -> {followup_to or '(cleared)'}")
    return {"title": item.title, "followup_to": followup_to, **out.to_dict()}


def list_followups(followup_to: str, output: Output | None = None) -> dict[str, int | list[dict[str, str]] | list[str]]:
    """List backlog items linked as follow-ups to the given origin.

    Scans all local backlog items and returns those whose
    ``metadata.followup_to`` exactly matches *followup_to* (case-sensitive).

    Args:
        followup_to: Logical ID of the originating plan or task
            (e.g. ``"P1"``, ``"P1/T3"``).
        output: Optional :class:`Output` collector.

    Returns:
        Dict with ``items`` (list of dicts with ``title``, ``section``,
        ``issue``, ``followup_to``), ``count``, and output messages.
    """
    out = output or Output()
    items = get_config().backend.list_work_items()
    matches = [it for it in items if not it.skip and it.metadata.followup_to == followup_to]
    result_items = [
        {"title": it.title, "section": it.section, "issue": it.issue, "followup_to": it.metadata.followup_to}
        for it in matches
    ]
    return {"items": result_items, "count": len(result_items), **out.to_dict()}


# ---------------------------------------------------------------------------
# Public API: VIEW — helpers
# ---------------------------------------------------------------------------


_ENTRY_FILTER_KEYWORDS: frozenset[str] = frozenset({"all", "struck", "last", "first"})


def _merge_section_entries(existing: _SectionMetadata, new_entries: list[SectionEntryDict]) -> _SectionMetadata:
    """Merge *new_entries* into *existing* section metadata dict.

    Returns:
        Updated section metadata dict.
    """
    all_entries: list[SectionEntryDict] = list(existing["entries"]) + new_entries
    active_count = sum(1 for e in all_entries if not e["struck"])
    struck_count = sum(1 for e in all_entries if e["struck"])
    return _SectionMetadata(num_entries=active_count, num_struck=struck_count, entries=all_entries)


def _section_display_title(key: str, groomed_date: str = "") -> str:
    """Return the human-readable title for a section key.

    Delegates to the active backend's :meth:`section_display_title` method,
    which in turn delegates to :func:`~.rendering.section_display_title`.

    Args:
        key: Section storage key (e.g. ``"fact_check"``, ``"unknown__story"``).
        groomed_date: Optional date string from a ``GroomedData`` section, used
            to append the date to the ``"groomed"`` title.

    Returns:
        Display title string (e.g. ``"Fact-Check"``, ``"Story"``).
    """
    return get_config().backend.section_display_title(key, groomed_date)


def _build_sections_index_from_body(body: str) -> str:
    r"""Build a ``## Sections`` index block from a raw body string.

    Produces the same format as :func:`_render_section_index` but derives
    section data from the live body string rather than the backend-owned structured record.
    Used when *result.body* is populated from GitHub so that live data is
    preferred over the provider-backed record, maintaining cache coherence under concurrent
    groom writes.

    Returns empty string when *body* is empty or contains no ``### `` headers.

    Args:
        body: Full issue/item body text.

    Returns:
        Index block string ending with ``"\\n"`` or ``""`` when no sections.
    """
    if not body:
        return ""
    sections = _build_sections_compact(body)
    if not sections:
        return ""
    lines: list[str] = ["## Sections"]
    for idx, sec in enumerate(sections):
        name = str(sec.get("name", ""))
        count = int(sec.get("num_entries", 0))
        lines.append(f"[{idx}] {name} ({count} entries)")
    return "\n".join(lines) + "\n"


def _render_section_index(item: BacklogItem) -> str:
    r"""Render a ``## Sections`` index block listing all sections with counts.

    Each line has the form ``[N] Title (M entries)`` where N is the zero-based
    index and M is the active entry count.  For :class:`~.models.GroomedData`
    the count reflects the number of subsections.

    Returns empty string when *item.sections* is empty.

    Args:
        item: BacklogItem whose sections to index.

    Returns:
        Index block string ending with ``"\\n"`` or ``""`` when no sections.
    """
    if not item.sections:
        return ""
    lines: list[str] = ["## Sections"]
    for idx, (key, sec_data) in enumerate(item.sections.items()):
        groomed_date = sec_data.date if isinstance(sec_data, GroomedData) else ""
        title = _section_display_title(key, groomed_date)
        if isinstance(sec_data, GroomedData):
            count = len(sec_data.subsections)
            lines.append(f"[{idx}] {title} ({count} subsections)")
        elif isinstance(sec_data, Section):
            active = sum(1 for e in sec_data.entries if not e.struck)
            lines.append(f"[{idx}] {title} ({active} entries)")
        else:
            lines.append(f"[{idx}] {title}")
    return "\n".join(lines) + "\n"


def _resolve_section_indices(candidates: list[str], section: str) -> list[int]:
    """Resolve a *section* filter expression to ordered candidate indices.

    Shared by the YAML structured-sections path (:func:`_filter_sections`) and
    the raw-GitHub-body path (:func:`_apply_body_section_filter`) so both honour
    the identical set of section forms advertised by the ``backlog_view`` tool.

    The *section* parameter supports four forms, evaluated in this order:

    - ``"2"`` -- single numeric index (zero-based, negatives Python-style).
    - ``"0,2,4"`` -- comma-separated numeric indices.
    - ``"/regex/"`` -- regex pattern delimited by ``/`` (case-insensitive),
      matched with :func:`re.Pattern.search` against each candidate string.
    - Any other string -- case-insensitive substring match against each
      candidate string.

    Args:
        candidates: Ordered list of section-name strings to match against
            (display titles for backend-owned structured items, raw header text for bodies).
        section: Filter expression.

    Addressability fallback (issue #2495, M1): the numeric/comma/regex forms are
    tried first, but when the chosen form resolves to an *empty* set of in-range
    indices, this function falls back to case-insensitive substring matching
    before reporting no match.  This keeps a candidate literally named like an
    index (``"2"``) or like a regex (``"/foo/"``) reachable -- otherwise the
    leading numeric/regex interpretation would silently consume the expression,
    miss, and make that candidate permanently unaddressable (a No-Invented-Limits
    addressability loss).  Only when BOTH the index/regex interpretation AND the
    substring interpretation resolve nothing is the result empty.

    Returns:
        Ordered, de-duplicated list of matching indices into *candidates*.  An
        empty list means no candidate matched under *either* the index/regex
        interpretation or the substring fallback; callers decide whether an
        empty result is a filter miss.
    """
    if not candidates:
        return []

    stripped = section.strip()
    if not stripped:
        return []

    def _substring_indices() -> list[int]:
        lower_filter = stripped.lower()
        return [i for i, name in enumerate(candidates) if lower_filter in name.lower()]

    # --- comma-separated or single numeric index ---
    index_parts = [p.strip() for p in stripped.split(",")]
    numeric_parts = [p for p in index_parts if p]
    if numeric_parts and all(p.lstrip("-").isdigit() for p in numeric_parts):
        n = len(candidates)
        # Normalise negative indices (Python-style: -1 = last); drop out-of-range.
        resolved = {(int(p) % n) for p in numeric_parts if -n <= int(p) < n}
        # Fallback: an out-of-range / unresolved index expression may instead be
        # the literal name of a candidate (e.g. a header named "## 2").  Try the
        # substring interpretation before declaring a miss (M1, #2495).
        return sorted(resolved) if resolved else _substring_indices()

    # --- /regex/ pattern ---
    if stripped.startswith("/") and stripped.endswith("/") and len(stripped) > 1:
        try:
            compiled = re.compile(stripped[1:-1], re.IGNORECASE)
        except re.error:
            # A malformed pattern (e.g. ``/[/``) reaches this path for raw GitHub
            # bodies, where the delimited expression is untrusted caller input.
            # ``re.error`` is the only exception ``re.compile`` is documented to
            # raise for an invalid pattern; catch it narrowly and degrade
            # gracefully instead of crashing ``backlog_view`` (#2495).  Treat the
            # delimited text as a literal substring so a candidate literally named
            # like the expression stays reachable; ``_substring_indices`` returns
            # ``[]`` when nothing matches, which the caller reports as a
            # section_filter_miss.
            return _substring_indices()
        regex_matches = [i for i, name in enumerate(candidates) if compiled.search(name)]
        # Fallback: a candidate literally named like the delimited expression
        # ("/foo/") stays reachable when the regex interpretation matches nothing.
        return regex_matches or _substring_indices()

    # --- substring match ---
    return _substring_indices()


def _filter_sections(item: BacklogItem, section: str) -> dict[str, Section | GroomedData]:
    """Return a filtered subset of *item.sections* matching *section*.

    Delegates form detection to :func:`_resolve_section_indices`, matching the
    same numeric / comma / regex / substring forms as the raw-body filter path.
    Regex and substring forms match against each section's *display title*.

    Args:
        item: BacklogItem whose sections to filter.
        section: Filter expression.

    Returns:
        Ordered dict of matching ``{key: sec_data}`` pairs.  Empty dict when
        no sections match.
    """
    if not item.sections:
        return {}

    items = list(item.sections.items())
    candidates = [_section_display_title(k, sec.date if isinstance(sec, GroomedData) else "") for k, sec in items]
    return {items[i][0]: items[i][1] for i in _resolve_section_indices(candidates, section)}


def render_sections_as_body(item: BacklogItem, section: str | None = None) -> str:
    r"""Render a YAML BacklogItem's structured sections into a markdown body string.

    Prepends a ``## Sections`` index block (unless *section* filter is active
    or *item.sections* is empty).  Renders ``## {title}\\n\\n{content}`` for
    each section.  Returns ``""`` when *item.sections* is empty.

    Args:
        item: The BacklogItem whose sections to render.
        section: Optional filter expression forwarded to :func:`_filter_sections`.
            When ``None`` all sections are rendered (with index).

    Returns:
        Markdown string representation of sections, or ``""`` if none exist.
    """
    if not item.sections:
        return ""

    sections_to_render = _filter_sections(item, section) if section is not None else dict(item.sections)

    if not sections_to_render:
        return ""

    parts: list[str] = []
    # Include the full section index only when rendering all sections
    if section is None:
        index_block = _render_section_index(item)
        if index_block:
            parts.append(index_block.rstrip("\n"))

    for key, sec_data in sections_to_render.items():
        if isinstance(sec_data, GroomedData):
            parts.append(get_config().backend.render_groomed_section(sec_data))
        elif isinstance(sec_data, Section):
            title = _section_display_title(key)
            content = "\n".join(e.content for e in sec_data.entries if e.content)
            parts.append(f"## {title}\n\n{content}")

    return "\n\n".join(parts) + "\n\n" if parts else ""


def _build_sections_from_yaml_item(item: BacklogItem) -> dict[str, SectionEntryMetadata | GroomedSectionMetadata]:
    """Build sections metadata directly from a YAML BacklogItem's structured sections.

    Used when the item has no raw markdown body (i.e. it was created as a ``.yaml``
    file) but its ``sections`` field carries structured ``Section`` objects.

    Args:
        item: The BacklogItem whose sections to convert.

    Returns:
        Mapping of section name to entry metadata.  ``Section`` entries follow the
        :class:`SectionEntryMetadata` shape.  ``GroomedData`` entries follow the
        :class:`GroomedSectionMetadata` shape (``"type": "groomed"`` discriminator).
    """
    result: dict[str, SectionEntryMetadata | GroomedSectionMetadata] = {}
    for sec_name, sec_data in item.sections.items():
        if isinstance(sec_data, GroomedData):
            result[sec_name] = GroomedSectionMetadata(
                type="groomed", date=sec_data.date, subsections=sec_data.subsections
            )
        elif isinstance(sec_data, Section):
            entries = sec_data.entries
            entry_dicts: list[SectionEntryDict] = [
                SectionEntryDict(id=e.id, struck=e.struck, content=e.content) for e in entries
            ]
            active_count = sum(1 for e in entries if not e.struck)
            struck_count = sum(1 for e in entries if e.struck)
            result[sec_name] = _SectionMetadata(num_entries=active_count, num_struck=struck_count, entries=entry_dicts)
    return result


def _build_sections_metadata(
    body: str, show: str | int | None, since: str | None, section: str | None = None
) -> dict[str, SectionEntryMetadata | GroomedSectionMetadata]:
    """Extract ``### ``- or ``## ``-delimited sections from *body* into a metadata dict.

    Args:
        body: Full issue/item body text.
        show: Controls both section and entry filtering.
              A string not in ``{"all", "struck", "last", "first"}`` filters to
              the named section (case-insensitive).  An int or one of those
              keywords is forwarded to ``parse_entries`` for entry-level filtering.
              ``None`` includes all sections with all entries.
        since: If set, filter entries to those on or after this date.
        section: Explicit section-name filter.  When provided it takes precedence
                 over any section-name filter derived from *show*.

    Returns:
        Mapping of section name to entry metadata.
    """
    section_headers = list(_SECTION_BOUNDARY_RE.finditer(body))

    # Determine whether show is a section-name filter or an entry-level filter.
    # The explicit ``section`` parameter takes precedence over a section name derived from ``show``.
    section_name_filter: str | None = section
    entry_show: str | int | None = "all"
    if section_name_filter is None:
        if isinstance(show, str) and show not in _ENTRY_FILTER_KEYWORDS:
            section_name_filter = show
        elif show is not None:
            entry_show = show

    sections: dict[str, SectionEntryMetadata | GroomedSectionMetadata] = {}
    for i, hdr in enumerate(section_headers):
        sec_name = hdr.group(1).strip()
        start = hdr.end()
        end = section_headers[i + 1].start() if i + 1 < len(section_headers) else len(body)
        sec_body = body[start:end]
        if section_name_filter is not None and sec_name.lower() != section_name_filter.lower():
            continue
        entries = parse_entries(sec_body, show=entry_show, since=since)
        entry_dicts: list[SectionEntryDict] = [
            SectionEntryDict(id=e.id, struck=e.struck, content=e.content) for e in entries
        ]
        if sec_name in sections:
            # Invariant: _build_sections_metadata only inserts _SectionMetadata (SectionEntryMetadata)
            # values, never GroomedSectionMetadata, so the duplicate-section merge path is always
            # entry-block.  Enforce this at runtime instead of relying on a silent cast().
            existing = sections[sec_name]
            if not _is_section_entry_metadata(existing):
                msg = (
                    f"_build_sections_metadata invariant violated: expected SectionEntryMetadata "
                    f"for section {sec_name!r} but found {type(existing).__name__}"
                )
                raise TypeError(msg)
            sections[sec_name] = _merge_section_entries(existing, entry_dicts)
        else:
            active_count = sum(1 for e in entries if not e.struck)
            struck_count = sum(1 for e in entries if e.struck)
            sections[sec_name] = _SectionMetadata(
                num_entries=active_count, num_struck=struck_count, entries=entry_dicts
            )
    return sections


def _build_sections_compact(body: str) -> list[dict[str, str | int]]:
    """Extract section names and entry counts without parsing entry content.

    Returns a lightweight section inventory suitable for compact-mode responses.
    Unlike ``_build_sections_metadata``, this function does not apply section or
    entry filters — it always returns all sections with their active and struck
    entry counts.

    Uses ``_SECTION_BOUNDARY_RE`` (``^#{2,3} (.+?)$``) for boundary detection,
    matching the same rule as ``_build_sections_metadata`` so both functions
    agree on section structure for the same body.

    Args:
        body: Full issue/item body text.

    Returns:
        List of dicts, each with ``name`` (str), ``num_entries`` (int active),
        and ``num_struck`` (int struck).
    """
    section_headers = list(_SECTION_BOUNDARY_RE.finditer(body))

    result: list[dict[str, str | int]] = []
    for i, hdr in enumerate(section_headers):
        sec_name = hdr.group(1).strip()
        start = hdr.end()
        end = section_headers[i + 1].start() if i + 1 < len(section_headers) else len(body)
        sec_body = body[start:end]
        entries = parse_entries(sec_body, show="all")
        active_count = sum(1 for e in entries if not e.struck)
        struck_count = sum(1 for e in entries if e.struck)
        result.append({"name": sec_name, "num_entries": active_count, "num_struck": struck_count})
    return result


def _entry_owning_headers(body: str) -> list[str | None]:
    """Map each entry block in *body* to the ``## ``/``### `` header that owns it.

    Returns one element per :data:`ENTRY_RE` match in document order; the value is
    the full source header LINE (e.g. ``## Log`` or ``### Detail``) of the nearest
    preceding section header, or ``None`` when an entry precedes the first header
    (a headerless preamble entry).  The full line (not just the name) is kept so the
    paged body reproduces the original header level.

    The result aligns positionally with :func:`parse_entries` (which iterates the
    same ``ENTRY_RE`` matches in the same order), so the i-th owning header
    describes the i-th parsed entry.  Used by :func:`_paginate_body_result` to
    re-attach the owning header to each paged entry, keeping the paginated body
    self-describing so the section-metadata rebuild stays in sync with the page
    (#2495 finding #5).

    Args:
        body: Full (unpaginated) body text containing entry blocks.

    Returns:
        List of owning header lines (or ``None``) aligned with the entry order
        produced by :func:`parse_entries`.
    """
    entry_spans = [(m.start(), m.end()) for m in ENTRY_RE.finditer(body)]
    # A ``## ``/``### `` line INSIDE an entry block's content is part of that
    # entry's text, not a real section boundary — exclude it so a later entry is
    # not mis-attributed to a header embedded in a prior entry (#2495 C4).
    headers = [
        hdr
        for hdr in _SECTION_BOUNDARY_RE.finditer(body)
        if not any(start <= hdr.start() < end for start, end in entry_spans)
    ]
    owners: list[str | None] = []
    for entry_start, _entry_end in entry_spans:
        owner: str | None = None
        for hdr in headers:
            if hdr.start() <= entry_start:
                # Reproduce the source header line verbatim (its ``## ``/``### `` marker
                # and text) so a paged subsection keeps the level it had.
                owner = hdr.group(0).strip()
            else:
                break
        owners.append(owner)
    return owners


def _render_paged_entry_body(entries: list[Entry], owners: list[str | None]) -> str:
    """Render *entries* grouped under their owning ``## ``/``### `` headers.

    Consecutive entries sharing an owning header are emitted once under that
    header, so the paginated body keeps the section structure that
    :func:`_render_entry_raw` alone discards.  Entries with a ``None`` owner
    (headerless preamble) are emitted without a header line.

    Args:
        entries: The paged (sliced) entries to render, in document order.
        owners: Owning header lines aligned positionally with *entries*.

    Returns:
        The rendered body with section headers re-attached to their entries.
    """
    blocks: list[str] = []
    last_owner: str | None = None
    first = True
    for entry, owner in zip(entries, owners, strict=True):
        if first or owner != last_owner:
            if owner is not None:
                # ``owner`` is the full source header line (e.g. ``## Log`` or
                # ``### Detail``), reproduced verbatim to preserve the header level.
                blocks.append(owner)
            last_owner = owner
            first = False
        blocks.append(_render_entry_raw(entry))
    return "\n\n".join(blocks)


def _paginate_body_result(result: ViewItemResult, body: str, offset: int, limit: int) -> None:
    """Apply offset/limit pagination to the ``body`` field of *result* in-place.

    Paginates by entry blocks when the body contains timestamped entry blocks
    (``<div><sub>…</sub>…</div>``). Falls back to line-based pagination for
    plain-text bodies that contain no entry blocks.

    For the entry-block path the owning ``## ``/``### `` header of each paged
    entry is re-attached to the rendered page (#2495 finding #5).  Without it the
    rendered page is a bare run of ``<div><sub>…</sub></div>`` blocks with no
    header, so the downstream ``_build_sections_metadata`` rebuild parses a
    headerless page and produces ``{}`` — desyncing the section metadata from a
    body that does in fact belong to a named section.

    Args:
        result: Mutable ViewItemResult whose ``body`` field will be replaced.
        body: Original (unpaginated) body text.
        offset: Number of leading entry blocks (or lines) to skip.
        limit: Maximum entry blocks (or lines) to keep (0 = unlimited).
    """
    has_entry_blocks = bool(ENTRY_RE.search(body))
    if has_entry_blocks:
        # Entry-block aware pagination.  Owners are captured from the ORIGINAL body
        # (before the slice) so each paged entry can be rendered under the header it
        # belongs to, keeping the page self-describing for the metadata rebuild.
        entries = parse_entries(body, show="all")
        owners = _entry_owning_headers(body)
        total = len(entries)
        start = max(0, offset)
        end = start + limit if limit > 0 else len(entries)
        sliced = entries[start:end]
        sliced_owners = owners[start:end]
        result.body = _render_paged_entry_body(sliced, sliced_owners)
        # Use the clamped ``start`` (not raw ``offset``) so a negative offset
        # — which clamps to 0 and returns every entry — does not report a bogus
        # remaining count. Offset past the end yields an empty body with no
        # truncation flag (intended contract; see test_paginate_body.py).
        remaining = total - start - len(sliced)
        if remaining > 0:
            result.body_truncated = True
            result.body_remaining_entries = remaining
            result.body_total_entries = total
    else:
        # Fallback: line-based pagination for plain-text bodies with no entry blocks
        lines = body.splitlines()
        total = len(lines)
        start = max(0, offset)
        if start > 0:
            lines = lines[start:]
        if limit > 0:
            lines = lines[:limit]
        result.body = "\n".join(lines)
        remaining = total - start - len(lines)
        if remaining > 0:
            result.body_truncated = True
            result.body_remaining_lines = remaining
            result.body_total_lines = total


def _populate_yaml_item_content(result: ViewItemResult, item: BacklogItem, section: str | None) -> None:
    """Populate *result* with body and sections for a backend-owned structured item (full-content path).

    backend-owned structured items have structured ``sections`` but no raw body string.  This helper
    renders the body from the structured sections and populates ``result.body``
    and ``result.sections``.  When *section* is provided the output is filtered.

    Args:
        result: Mutable ViewItemResult to update in-place.
        item: YAML BacklogItem with structured sections.
        section: Optional section filter expression; ``None`` renders all sections.
    """
    if section is not None:
        filtered = _filter_sections(item, section)
        # Build a temporary item with only the filtered sections for rendering
        filtered_item = BacklogItem(title=item.title, sections=filtered)
        result.body = render_sections_as_body(filtered_item)
        result.sections = _build_sections_from_yaml_item(filtered_item)
    else:
        result.body = render_sections_as_body(item)
        result.sections = _build_sections_from_yaml_item(item)


def _int_field(sec: _SectionMetadata | GroomedSectionMetadata, key: str) -> int:
    """Return an integer field from a section metadata dict, defaulting to 0.

    Args:
        sec: Section metadata dict — either a :class:`SectionEntryMetadata` or
            :class:`GroomedSectionMetadata` instance.
        key: Dict key to retrieve.

    Returns:
        Integer value of the field, or 0 if absent or non-integer.
    """
    if not isinstance(sec, dict):
        return 0
    val = sec.get(key, 0)
    return val if isinstance(val, int) else 0


def _compact_entry_count(sec: _SectionMetadata | GroomedSectionMetadata) -> int:
    """Return the entry/subsection count for a section metadata dict.

    For groomed sections (``{"type": "groomed", "subsections": {...}}``), returns
    the subsection count.  For regular sections, returns ``num_entries``.
    """
    if not isinstance(sec, dict):
        return 0
    if sec.get("type") == "groomed":
        subs = sec.get("subsections")
        return len(subs) if isinstance(subs, dict) else 0
    entries = sec.get("num_entries")
    return int(entries) if isinstance(entries, int) else 0


def _populate_yaml_item_compact(result: ViewItemResult, item: BacklogItem) -> None:
    """Populate *result* with sections_metadata for a backend-owned structured item (compact path).

    Args:
        result: Mutable ViewItemResult to update in-place.
        item: YAML BacklogItem with structured sections.
    """
    yaml_sections = _build_sections_from_yaml_item(item)
    result.sections_metadata = [
        _models.SectionMeta(name=name, num_entries=_compact_entry_count(sec), num_struck=_int_field(sec, "num_struck"))
        for name, sec in yaml_sections.items()
    ]


# ---------------------------------------------------------------------------
# Public API: VIEW — helpers
# ---------------------------------------------------------------------------

_SECTION_BOUNDARY_RE = re.compile(r"^#{2,3} (.+?)$", re.MULTILINE)


def _slice_body_by_header_indices(body: str, headers: list[re.Match[str]], indices: list[int]) -> str:
    """Concatenate the *body* slices for the given *header* *indices* in order.

    The single shared body-slicing implementation (issue #2495, findings #8/#10):
    both the singular ``section=`` resolver (:func:`_apply_body_section_filter`)
    and the plural ``sections=[...]`` resolver (:func:`narrow_body_to_named_sections`)
    delegate the header-find -> index -> slice-join mechanics here.  Only the
    *matching contract* (how an index list is derived from a filter expression)
    differs between the two callers; the slicing geometry is identical and lives
    once.

    Each slice runs from its header's start to the next header's start (or end of
    *body* for the final header), so the header line and its body travel together.

    Args:
        body: Full issue body text.
        headers: Ordered ``## ``/``### `` header matches from
            :data:`_SECTION_BOUNDARY_RE` over *body*.
        indices: Indices into *headers* to keep, already in document order.

    Returns:
        The concatenated slices for *indices* (empty string when *indices* is
        empty).
    """
    return "".join(
        body[headers[i].start() : (headers[i + 1].start() if i + 1 < len(headers) else len(body))] for i in indices
    )


def _apply_body_section_filter(result: ViewItemResult, body: str, section: str) -> str:
    """Narrow *body* and *result.body* to the requested section(s).

    Resolves *section* against the ordered list of ``## ``/``### `` headers using
    :func:`_resolve_section_indices`, so the same numeric index (``"4"``),
    comma-separated indices (``"0,2"``), regex (``"/impact.*/"``), and
    substring/name forms advertised by the ``backlog_view`` tool all work on raw
    GitHub bodies — not only the name form.  The matched header slices are
    concatenated in document order via the shared
    :func:`_slice_body_by_header_indices`.  When no form resolves to a header,
    ``result.section_filter_miss`` is set and the body is left unchanged.

    Matching contract: the *singular* ``section=`` form (substring / numeric index
    / comma list / regex) — distinct from the plural ``sections=[...]`` exact
    case-insensitive contract in :func:`narrow_body_to_named_sections`.  Both
    contracts are documented on the ``backlog_view`` tool and preserved as-is;
    only the slicing mechanics are shared (#2495 findings #8/#10).

    Args:
        result: ViewItemResult to update in-place.
        body: Full issue body text.
        section: Section filter expression (index, comma list, regex, or name).

    Returns:
        The (possibly narrowed) body slice.
    """
    headers = list(_SECTION_BOUNDARY_RE.finditer(body))
    names = [hdr.group(1).strip() for hdr in headers]
    matched = _resolve_section_indices(names, section)
    if matched:
        body = _slice_body_by_header_indices(body, headers, matched)
    else:
        result.section_filter_miss = True
        result.section_filter_valid_names = names
    result.body = body
    return body


def narrow_body_to_named_sections(body: str, names: list[str]) -> tuple[str, bool]:
    """Return the slices of *body* whose ``## ``/``### `` headers match *names*.

    Used to keep the ``body`` field self-consistent with a ``sections=[...]``
    filter: only the slices for the requested section names (exact,
    case-insensitive — matching the ``sections=`` parameter contract) are kept,
    in document order.

    Reports whether any header matched (issue #2495, m1).  Returning the match
    flag alongside the (possibly unchanged) body lets the caller distinguish
    "names were wrong" from "item too big" instead of silently returning the
    full body — see ``.claude/rules/silent-failure-prevention.md`` (a transform
    must report what it changed).

    Args:
        body: Full issue body text.
        names: Exact section names to keep (case-insensitive).

    Returns:
        A ``(narrowed_body, matched)`` tuple.  ``matched`` is ``True`` when at
        least one ``## ``/``### `` header matched a requested name (and the body
        is the concatenated matching slices in document order); ``False`` when
        no header matched, in which case *body* is returned unchanged so the
        caller can surface the no-match signal without losing content.
    """
    # Case-fold with ``.casefold()`` (not ``.lower()``) so the plural
    # ``sections=[...]`` body arm uses the one Unicode-correct case-fold rule shared
    # with the structured-dict arm (``_filter_view_sections``) and the metadata arm
    # (#2495 minor).  No behaviour change for ASCII names.
    wanted = {n.casefold() for n in names}
    headers = list(_SECTION_BOUNDARY_RE.finditer(body))
    matched = [i for i, hdr in enumerate(headers) if hdr.group(1).strip().casefold() in wanted]
    if not matched:
        return body, False
    # Exact case-insensitive name matching above is the plural ``sections=[...]``
    # contract; only the slice-join mechanics are shared with the singular
    # ``section=`` path (#2495 findings #8/#10).
    return _slice_body_by_header_indices(body, headers, matched), True


def _assemble_view_compact(
    result: ViewItemResult, item: BacklogItem | None, body: str, section: str | None = None
) -> None:
    """Populate *result* for summary (non-content) view mode.

    Sets ``sections_metadata`` and ``sections_index`` without retaining the full
    body.  Delegates to the GitHub-body path when *body* is non-empty, otherwise
    falls back to the backend-owned structured item.

    When *section* is provided, ``sections_metadata`` is narrowed to only the
    matching section (case-insensitive name match).  ``sections_index`` is
    omitted when a section filter is active, mirroring the ``include_content=True``
    path which also omits the index when section is set.

    Args:
        result: ViewItemResult to update in-place.
        item: Local BacklogItem for YAML fallback, or ``None``.
        body: Raw body text (may be empty string).
        section: Optional section-name filter.  When provided, only the matching
            section's metadata is returned.
    """
    result.body = ""
    result.sections = {}
    if body:
        all_sections = _build_sections_compact(body)
        if section is not None:
            names = [str(s.get("name", "")) for s in all_sections]
            matched_indices = _resolve_section_indices(names, section)
            if not matched_indices:
                result.section_filter_miss = True
                result.section_filter_valid_names = names
                all_sections = []
            else:
                all_sections = [all_sections[i] for i in matched_indices]
        result.sections_metadata = [
            _models.SectionMeta(
                name=str(s.get("name", "")),
                num_entries=int(s.get("num_entries", 0)),
                num_struck=int(s.get("num_struck", 0)),
            )
            for s in all_sections
        ]
        if section is None:
            index = _build_sections_index_from_body(body)
            if index:
                result.sections_index = index
    elif item and item.sections:
        _populate_yaml_item_compact(result, item)
        if section is None:
            index = _render_section_index(item)
            if index:
                result.sections_index = index


def _sections_from_body_or_yaml(
    body: str, item: BacklogItem | None, show: str | int | None, since: str | None
) -> dict[str, SectionEntryMetadata | GroomedSectionMetadata]:
    """Return section metadata preferring body-parsed IDs, falling back to YAML.

    Priority order:
    1. Body has entry-block wrappers (``<div><sub>timestamp</sub>…</div>``) —
       ``_build_sections_metadata`` extracts real entry IDs from the blocks.
    2. Body has ``##``/``###`` section headers but no entry blocks:
       a. If the backend-owned structured item's section names cover every header in the body,
          prefer YAML — it carries real persisted entry IDs.  Zero-timestamp
          IDs produced by ``_build_sections_metadata`` on a plain-text body
          would corrupt ``since``-based filtering and discard stored IDs.
       b. Otherwise (body headers differ from YAML sections, or no backend-owned structured item),
          parse the body directly — the body is the authoritative source for
          which sections exist when the backend-owned structured item is absent or stale.
    3. No body headers — YAML fallback (``_build_sections_from_yaml_item``).
    4. Neither source available — return ``{}``.

    The subset check in step 2a resolves the tension between two requirements:
    (a) GitHub-enriched bodies must not corrupt stored entry IDs by silently
    replacing them with zero-timestamp fallbacks; and (b) plain-text bodies
    whose headers differ from the backend-owned structured item (e.g. a paginated slice that lands
    on a section not in the backend-owned structured item, or no backend-owned structured item at all) must still
    produce correct ``result.sections`` from the live body content.

    Args:
        body: The (possibly paginated) body string to inspect.
        item: Local backend-owned structured item whose structured sections carry real entry IDs.
            May be ``None`` when no backend-owned item is available.
        show: Entry display filter forwarded to ``_build_sections_metadata``.
        since: ISO date/datetime filter forwarded to ``_build_sections_metadata``.

    Returns:
        Section metadata mapping.  Empty dict when neither source is available.
    """
    if ENTRY_RE.search(body):
        return _build_sections_metadata(body, show, since, section=None)
    # Plain-text body with section headers but no entry blocks.
    if _SECTION_BOUNDARY_RE.search(body):
        if item and item.sections:
            body_header_names = {hdr.group(1).strip() for hdr in _SECTION_BOUNDARY_RE.finditer(body)}
            yaml_section_names = set(item.sections.keys())
            if body_header_names.issubset(yaml_section_names):
                # YAML covers all body headers — use it to preserve real entry IDs.
                return _build_sections_from_yaml_item(item)
        # Body headers not fully covered by YAML (or no backend-owned structured item) — body wins.
        return _build_sections_metadata(body, show, since, section=None)
    # Body has no section headers — YAML fallback.
    if item and item.sections:
        return _build_sections_from_yaml_item(item)
    return {}


def _assemble_view_content(
    result: ViewItemResult,
    item: BacklogItem | None,
    *,
    include_content: bool,
    section: str | None,
    show: str | int | None,
    since: str | None,
    offset: int,
    limit: int,
) -> None:
    """Populate *result* with body/sections for ``view_item``.

    Mutates *result* in place — sets ``body``, ``sections``, or
    ``sections_metadata`` depending on *include_content*.  Always sets
    ``sections_index`` when *include_content* is ``False`` and the item has
    structured sections, so callers can discover available sections without
    loading the full body.
    """
    body = result.body
    paginate = offset > 0 or limit > 0

    if include_content:
        # Display-only ``## Sections`` index for the ``section is None`` path.  It is
        # built from the full body but prepended to the body only AFTER pagination
        # (below).  It must never enter ``_paginate_body_result``: line-based
        # pagination would otherwise spend the page budget on the index lines and
        # displace the real content, and the metadata rebuild would then report a
        # spurious ``Sections`` key with no real section content (#2495 M1 —
        # regression introduced in d7abdee).
        #
        # The index is built ONLY for the NON-paged ``section is None`` path (#2495
        # Codex P2).  On a paged request (``offset``/``limit``) the index describes
        # the WHOLE un-paginated item — its size is unbounded and grows with the
        # heading count, so for an item with many headings the index alone can exceed
        # ``_VIEW_TOKEN_BUDGET``.  Prepending it to the budgeted page body would then
        # trip the over-budget gate (server.py) and replace the explicitly-requested
        # page with the compact directory — violating the contract that an
        # explicitly-narrowed request is delivered.  A paged caller asked for the
        # page, not the whole-item index; the page content plus the page-scoped
        # ``result.sections`` metadata are what is delivered, so the index is omitted
        # for paged responses (it remains available via the unbounded ``section is
        # None`` call and via ``summary=True``).
        pending_index = ""
        if body:
            if section is not None:
                # Resolve the section form once: narrow the body to the matched
                # section slices (numeric, comma, regex, substring, name -- not
                # just the exact-name form ``_build_sections_metadata`` recognises;
                # #2495 defect c).  On a genuine miss ``_apply_body_section_filter``
                # sets ``section_filter_miss`` and leaves the body unchanged.
                body = _apply_body_section_filter(result, body, section)
                if result.section_filter_miss:
                    # A miss must yield an EMPTY body and EMPTY sections, not the
                    # full unchanged body (#2495 defects #2/#3).  Returning the full
                    # body here would leak the whole item and (because it is still
                    # large) trip the over-budget gate, defeating the narrowing the
                    # caller asked for.  Empty body + empty sections is the single
                    # consistent "nothing matched" signal alongside
                    # ``section_filter_miss``; skip pagination and the metadata
                    # rebuild below entirely.
                    result.body = ""
                    result.sections = {}
                    return
                # Derive section metadata from the SAME narrowed body so the two
                # stay in sync for every resolved form.  Skip when pagination will
                # run: the pagination branch rebuilds the metadata from the
                # paginated slice, so building it here too would compute and discard
                # it (#2495 finding #9 — build the body-derived metadata at most
                # once, from the final body).
                if not paginate:
                    result.sections = _build_sections_metadata(body, show, since, section=None)
            # Build the section index from the FULL body so agents see it
            # regardless of body source, but DEFER prepending it until after
            # pagination (#2495 M1) so the index never consumes the page budget.
            # Prefer live body data over backend-owned structured record for cache coherence.
            # The index is display-only; metadata is built from ``body`` (without
            # it) so no spurious ``Sections`` key is produced.  Both the metadata
            # build and the index build are skipped under pagination: pagination
            # rebuilds the metadata from the paginated slice, and the whole-item
            # index is omitted from paged responses entirely (#2495 Codex P2 — an
            # unbounded index must not displace the explicitly-requested page via
            # the over-budget gate).
            elif not paginate:
                result.sections = _sections_from_body_or_yaml(body, item, show, since)
                pending_index = _build_sections_index_from_body(body)
        elif item and item.sections:
            # YAML fallback: ``_populate_yaml_item_content`` builds the richer
            # structured-section metadata via ``_build_sections_from_yaml_item``
            # (preserving struck counts and unknown-section shapes).  Do NOT
            # overwrite it with a body re-parse -- that loses information the YAML
            # path carries.  When pagination runs the metadata is re-bounded to the
            # paginated slice below (mirroring the pre-#2495 behaviour).
            _populate_yaml_item_content(result, item, section)
        # Pagination (when requested) re-bounds the body and its section metadata
        # to the paginated slice so a paged request cannot overflow the view budget
        # via an un-paged sections dump (#2495 defect a).  This is the single
        # metadata build for the paginated case (finding #9): the per-path builds
        # above are skipped when ``paginate`` is True.  Pagination runs on the RAW
        # body (no synthetic index prefix): the ``section is None`` index is
        # prepended afterwards so it never displaces real content and
        # ``result.sections`` reflects the real sections of the returned page
        # (#2495 M1).
        if paginate and result.body:
            _paginate_body_result(result, result.body, offset, limit)
            result.sections = _sections_from_body_or_yaml(result.body, item, show, since)
        # Prepend the deferred display-only ``## Sections`` index to the final,
        # post-pagination body in the NON-paged ``section is None`` path (#2495 M1).
        # ``pending_index`` is built only on that path (it is ``""`` whenever
        # ``paginate`` is True — #2495 Codex P2), so this prepend is a no-op for
        # paged responses: a paged caller receives the page without the unbounded
        # whole-item index that would otherwise trip the over-budget gate.
        if pending_index and result.body:
            result.body = pending_index + "\n" + result.body
    else:
        _assemble_view_compact(result, item, body, section=section)


# ---------------------------------------------------------------------------
# Public API: VIEW
# ---------------------------------------------------------------------------


def view_item(
    selector: str,
    repo: str = "",
    offset: int = 0,
    limit: int = 0,
    show: str | int | None = None,
    since: str | None = None,
    output: Output | None = None,
    include_content: bool = True,
    section: str | None = None,
) -> ViewItemResult:
    """View a backlog item or GitHub issue by URL, #N, bare number, or title.

    For string-ID backends (e.g. beads), ``selector`` also accepts a bare
    nanoid (e.g. ``"bd-a3f8"``). ``parse_issue_selector`` only recognizes
    numeric GitHub-style refs, so a nanoid that is not present in the local
    cache falls through to a direct ``view_enrich_from_github`` call gated on
    ``get_config().backend.issue_id_type == "string"`` — this lets
    :class:`~backlog_core.backends.beads_backend.BeadsBackend` resolve the
    item via ``bd show <id>`` even when it was never synced locally.

    Args:
        selector: Issue URL, #N, bare number, title substring, or (for
            string-ID backends) a bare nanoid such as ``"bd-a3f8"``.
        repo: GitHub repo in owner/repo format.
        offset: Skip N entry blocks from the start of the body (falls back to
            line-based skipping for plain-text bodies with no entry blocks).
        limit: Show at most N entry blocks (0 = all, no truncation); falls back
            to line-based limit for plain-text bodies with no entry blocks.
        show: Entry filter forwarded to parse_entries -- "all", "last", "first",
              "struck", positive int (first N active), negative int (last N active),
              or a section name string (case-insensitive section filter).
              MCP clients may send numeric values as strings; those are converted
              to int automatically.
        since: If set, filter entries to those on or after this date.
        output: Optional Output collector.
        include_content: When True (default), returns full body and section entries.
            When False, returns metadata and section inventory only (section names
            with entry counts, no body or entry content).
        section: Optional section name filter.  When the item has a raw body (GitHub
            items), narrows the body to the matching ``## `` or ``### `` header and
            sets ``result.section_filter_miss = True`` when no header matches.
            For backend-owned structured items with structured sections but no raw body, supports
            numeric index (``"2"``), comma-separated indices (``"0,2"``),
            regex (``"/impact.*/``), or substring match.

    Returns:
        ViewItemResult with item/issue details. When ``include_content=True``,
        ``body`` and ``sections`` are populated. When ``include_content=False``,
        ``body`` and ``sections`` are cleared and ``sections_metadata`` is set
        instead. When ``section`` is provided, ``body`` and ``sections`` reflect
        only the matched section(s).
    """
    out = output or Output()
    # Normalize blank/whitespace-only section filters to None so they behave as
    # an omitted filter (full content), not a no-match. strip() preserves real
    # values like "0". (PR #2496 Codex finding.)
    section = (section or "").strip() or None
    item = find_item(get_config().backend.list_work_items(), selector)
    issue_num = parse_issue_selector(selector)

    result: ViewItemResult = view_result_from_local_item(item) if item else ViewItemResult()

    if issue_num:
        enriched = view_enrich_from_github(result, issue_num, repo)
        if not enriched:
            if not item:
                raise ItemNotFoundError(selector)
            out.warnings.append("backend unreachable — sections_index reflects provider-backed record, may be stale")
        # Restore groomed date from local item — the enrichment path has no
        # access to backend-owned metadata, so preserve the date string.
        if item:
            result.groomed = item.metadata.groomed
    elif not item:
        if get_config().backend.issue_id_type == "string":
            enriched = view_enrich_from_github(result, selector.strip(), repo)
            if not enriched:
                raise ItemNotFoundError(selector)
        else:
            raise ItemNotFoundError(selector)

    # MCP clients send numeric show values as strings; convert before forwarding.
    parsed_show: str | int | None = show
    if isinstance(show, str):
        try:
            parsed_show = int(show)
        except ValueError:
            parsed_show = show

    _assemble_view_content(
        result,
        item,
        include_content=include_content,
        section=section,
        show=parsed_show,
        since=since,
        offset=offset,
        limit=limit,
    )

    result.messages = out.messages
    result.warnings = out.warnings
    result.errors = out.errors
    return result


# ---------------------------------------------------------------------------
# Public API: SYNC
# ---------------------------------------------------------------------------


def find_or_create_issue(
    item: BacklogItem,
    existing_issues: dict[str, int],
    repository: Repository,
    dry_run: bool,
    output: Output | None = None,
) -> int | None:
    """Check for existing issue by title; create only if no match found.

    Returns:
        Issue number (existing or newly created), or None for dry-run creates.
    """
    out = output or Output()
    title = item.title
    normalized = normalize_issue_title(title)
    if normalized in existing_issues:
        existing_num = existing_issues[normalized]
        out.info(f"  Linked #{existing_num}: {title[:60]} (existing issue found)")
        return existing_num
    if dry_run:
        out.info(f"  [dry-run] Would create: {title[:60]}")
        return None
    return create_issue_for_item(repository, item, dry_run=False, output=out)


def sync_create_missing_issues(
    items: list[BacklogItem],
    repo: str,
    dry_run: bool,
    output: Output | None = None,
    *,
    repository: Repository | None = None,
    existing_issues: dict[str, int] | None = None,
) -> dict[str, int | bool | list[str]]:
    """Pass 1 of sync: create GitHub issues for all items that lack them.

    Before creating any issues, fetches all open issues from GitHub and checks
    for title matches. If an existing open issue matches (after stripping
    conventional-commit prefixes), links to it instead of creating a duplicate.

    Args:
        items: Full backlog item list.
        repo: Repository in ``owner/repo`` format.  Ignored when ``repository``
            is provided.
        dry_run: When True, log actions without making changes.
        output: Optional Output collector for status/warning messages.
        repository: Optional pre-connected Repository object.  When provided,
            the ``get_github`` call is skipped (item 8 — single connection per
            ``sync_items`` pass).
        existing_issues: Optional pre-fetched ``{normalized_title: issue_number}``
            map.  When provided, the ``fetch_open_issues_by_title`` call is
            skipped (item 6 — single GraphQL fetch per ``sync_items`` pass).

    Returns:
        Dict with count of created/linked issues.
    """
    out = output or Output()
    needed = items_needing_issues(items)
    if not needed:
        out.info("No items need GitHub issues created.")
        return {"created": 0, **out.to_dict()}
    out.info(f"Found {len(needed)} item(s) without GitHub issues:")
    for it in needed:
        out.info(f"  - {it.title[:60]}")
    if dry_run:
        for it in needed:
            out.info(f"  [dry-run] Would create issue: {it.title[:60]}")
        return {"created": 0, "dry_run": True, **out.to_dict()}
    if repository is None:
        repository = get_github(repo)

    if existing_issues is None:
        # Dedup: fetch existing open issues to prevent duplicate creation.
        out.info("Fetching open issues for deduplication check...")
        existing_issues = fetch_open_issues_by_title(repository)
        out.info(f"  Found {len(existing_issues)} existing open issues.")

    created = 0
    for item in needed:
        issue_num = find_or_create_issue(item, existing_issues, repository, dry_run, output=out)
        if issue_num is None or dry_run:
            continue
        created += 1
        # Track newly created/linked issues to prevent intra-batch duplicates.
        new_normalized = normalize_issue_title(item.title)
        if new_normalized not in existing_issues:
            existing_issues[new_normalized] = issue_num
        # Update backend-owned metadata with issue number
        reference = item.reference
        if reference:
            update_item_metadata(reference, {"metadata": {"issue": f"#{issue_num}"}}, output=out)

    return {"created": created, **out.to_dict()}


def sync_items(
    repo: str = "", dry_run: bool = False, output: Output | None = None
) -> dict[str, int | bool | list[str]]:
    """Create GitHub issues for all items missing them, and push groomed content to existing issues.

    Establishes a single GitHub connection and performs a single GraphQL fetch
    for open issues, then threads both into the two sync passes to avoid
    redundant network round-trips.

    Returns:
        Dict with sync results.
    """
    out = output or Output()
    backend = get_config().backend
    if isinstance(backend, SyncProvider):
        create_result = sync_create_missing_issues(get_config().backend.list_work_items(), repo, dry_run, output=out)
        linked_items = items_with_issues(get_config().backend.list_work_items())
        references = list(dict.fromkeys(item.issue for item in linked_items))
        result = backend.reconcile(
            ReconcileRequest(scope=ReconcileScope.LINKED, references=references, dry_run=dry_run)
        )
        out.info(
            f"Reconciled linked items: {result.fetched_pages} pages, {result.fetched_items} items, "
            f"{result.local_updates} local updates, {result.provider_patches} patches, {result.no_ops} no-ops, "
            f"{result.conflicts} conflicts, {result.failures} failures."
        )
        return {
            "created": create_result.get("created", 0),
            "pushed": result.provider_patches,
            "dry_run": dry_run,
            **out.to_dict(),
        }

    out.info("Active backend does not support reconciliation.")
    return {"created": 0, "pushed": 0, "dry_run": dry_run, **out.to_dict()}


# ---------------------------------------------------------------------------
# Public API: CLOSE
# ---------------------------------------------------------------------------


def close_item(
    selector: str,
    reason: str,
    reference: str = "",
    comment: str = "",
    cleanup: bool = False,
    force: bool = False,
    repo: str = "",
    output: Output | None = None,
) -> dict[str, str | bool | list[str]]:
    """Dismiss an item without completion. Requires a categorized reason.

    Use for duplicates, out-of-scope items, superseded items, wontfix, or
    permanently blocked items. For completed work, use resolve_item() instead.

    Returns:
        Dict with closed item title and reason.
    """
    out = output or Output()
    reason = reason.strip().lower()
    if reason not in VALID_CLOSE_REASONS:
        msg = f"Invalid close reason: {reason!r}. Valid reasons: {', '.join(VALID_CLOSE_REASONS)}"
        raise ValidationError(msg)
    items = get_config().backend.list_work_items()
    item = find_item(items, selector)
    if not item:
        _pull_if_issue_selector(selector, repo, output=out)
        items = get_config().backend.list_work_items()
        item = find_item(items, selector)
    if not item:
        raise ItemNotFoundError(selector)
    issue_ref = item.issue
    if issue_ref and not force:
        issue_num_val = parse_issue_number(issue_ref)
        open_prs = check_open_prs_for_issue(issue_num_val, repo) if issue_num_val is not None else []
        if open_prs:
            out.warn(f"WARNING: Open PRs reference issue {issue_ref}:")
            for pr in open_prs:
                out.warn(f"  - PR #{pr.number}: {pr.title}")
                out.warn(f"    {pr.url}")
            out.warn(f"\nIssue {issue_ref} will auto-close when a PR merges with 'Fixes {issue_ref}'.")
            out.warn("Use force=True to close anyway.")
            msg = f"Open PRs reference issue {issue_ref}. Use force=True to close anyway."
            raise BacklogError(msg)

    today()

    reference = item.reference
    # Unreachable — see BacklogItem class docstring (models.py).
    if not reference:
        msg = "Item has no backend reference"
        raise BacklogError(msg)
    already_closed = item.status.lower() in {"closed", "done"}
    if already_closed:
        out.info("Item already closed.")
        return {"title": item.title, "already_closed": True, **out.to_dict()}

    update_item_metadata(reference, {"metadata": {"status": "closed", "close_reason": reason}}, output=out)

    out.info(f'Backlog item "{item.title}" closed ({reason}).')
    if issue_ref:
        close_github_issue(issue_ref, reason, reference=reference, comment=comment, repo=repo, output=out)
    if cleanup and issue_ref:
        out.info("Cleanup is managed by the configured backend.")

    return {"title": item.title, "closed": True, "reason": reason, **out.to_dict()}


# ---------------------------------------------------------------------------
# Public API: RESOLVE
# ---------------------------------------------------------------------------


def resolve_item(
    selector: str,
    summary: str,
    plan: str = "",
    method: str = "",
    notes: str = "",
    follow_ups: str = "",
    findings: str = "",
    cleanup: bool = False,
    force: bool = False,
    repo: str = "",
    output: Output | None = None,
) -> dict[str, str | bool | list[str]]:
    """Mark item DONE (completed) and close GitHub issue with evidence trail.

    Use when the work IS done. Creates a structured completion record
    (summary, method, notes, follow-ups, findings) as an audit trail.
    For dismissals (duplicate, out of scope, etc.), use close_item() instead.

    Returns:
        Dict with resolved item title and summary.
    """
    out = output or Output()
    if not summary.strip():
        msg = "summary is required (what was done)"
        raise ValidationError(msg)
    items = get_config().backend.list_work_items()
    item = find_item(items, selector)
    if not item:
        _pull_if_issue_selector(selector, repo, output=out)
        items = get_config().backend.list_work_items()
        item = find_item(items, selector)
    if not item:
        raise ItemNotFoundError(selector)
    issue_ref = item.issue
    if issue_ref and not force:
        issue_num_val = parse_issue_number(issue_ref)
        open_prs = check_open_prs_for_issue(issue_num_val, repo) if issue_num_val is not None else []
        if open_prs:
            out.warn(f"WARNING: Open PRs reference issue {issue_ref}:")
            for pr in open_prs:
                out.warn(f"  - PR #{pr.number}: {pr.title}")
                out.warn(f"    {pr.url}")
            out.warn("\nResolving will close the issue and orphan these PRs.")
            out.warn("Use force=True to resolve anyway.")
            msg = f"Open PRs reference issue {issue_ref}. Use force=True to resolve anyway."
            raise BacklogError(msg)

    today()

    reference = item.reference
    # Unreachable — see BacklogItem class docstring (models.py).
    if not reference:
        msg = "Item has no backend reference"
        raise BacklogError(msg)
    already_done = item.status.lower() in {"done", "resolved", "completed"}
    if already_done:
        out.info("Item already resolved.")
        return {"title": item.title, "already_resolved": True, **out.to_dict()}

    metadata: dict[str, object] = {"status": "done", "priority": "completed"}
    if plan:
        metadata["plan"] = plan
    update_item_metadata(reference, {"metadata": metadata}, output=out)

    out.info(f'Backlog item "{item.title}" resolved.')
    if issue_ref:
        resolve_github_issue(
            issue_ref,
            summary=summary,
            method=method,
            notes=notes,
            follow_ups=follow_ups,
            findings=findings,
            repo=repo,
            output=out,
        )
    if cleanup and issue_ref:
        out.info("Cleanup is managed by the configured backend.")

    return {"title": item.title, "resolved": True, "summary": summary, **out.to_dict()}


def _apply_non_in_progress_status(
    item: BacklogItem, status: str, repo: str, result: dict[str, str | int | bool | list[str]], output: Output
) -> None:
    """Handle every status value other than "in-progress" for _apply_issue_status_labels.

    Extracted to keep _apply_issue_status_labels' cyclomatic complexity within limit.
    Runs regardless of whether the item has a backend issue reference — the
    terminal-status and unrecognized-value rejections below are pure input
    validation that need no backend target; "blocked" reports a clear error
    instead of silently no-op'ing when there is genuinely nothing to write to.

    Args:
        item: Resolved BacklogItem.
        status: Status string to set (non-empty, not "in-progress").
        repo: GitHub repo slug (e.g. ``"owner/repo"``).
        result: Partial result dict mutated in place with ``"status"`` / ``"error"`` keys.
        output: Output aggregator for info/warning messages.
    """
    is_string_id_backend = get_config().backend.issue_id_type == "string"
    has_integer_issue = parse_issue_number(item.issue) is not None

    if status == "blocked":
        if is_string_id_backend:
            # item.reference self-heals to a title-hash placeholder at construction
            # (see BacklogItem's class docstring), so it is never empty here even
            # for a genuinely unissued item — reference_is_title_derived() is the
            # correct "no real backend reference yet" check instead of `not item.reference`.
            if not reference_is_title_derived(item):
                update_item_metadata(item.reference, {"metadata": {"status": "blocked"}}, output=output)
                result["status"] = "blocked"
            else:
                result["error"] = "Cannot set status='blocked': item has no backend reference"
        elif has_integer_issue:
            try:
                apply_status_blocked(item, repo, output=output)
            except GithubException as e:
                result["error"] = str(e)
                return
            result["status"] = "blocked"
        else:
            result["error"] = "Cannot set status='blocked': item has no issue reference"
    elif status in _TERMINAL_STATUSES:
        # done/resolved/closed are owned by resolve_item()/close_item(), which
        # record an evidence trail and actually close the backend issue.
        # Silently accepting them here would let an item look done locally
        # while the real issue stays open — surface a clear error instead.
        result["error"] = (
            f"status={status!r} must be set via 'backlog resolve' or 'backlog close', not 'backlog update'"
        )
    else:
        result["error"] = f"Unrecognized status value: {status!r}"


def _apply_issue_status_labels(
    item: BacklogItem,
    status: str | None,
    verified: bool,
    repo: str,
    result: dict[str, str | int | bool | list[str]],
    output: Output,
) -> None:
    """Apply status changes for the item.

    For items with a numeric integer issue reference, applies status labels via
    the backend (in-progress, verified).

    For backends whose ``issue_id_type`` is ``"string"`` — where ``item.issue``
    may be empty or hold an opaque string ID (e.g. a beads nanoid) — writes the
    status directly through the configured backend via :func:`update_item_metadata`.
    This prevents the status change from becoming a silent no-op on such backends
    (BUG-3).  The ``apply_status_in_progress`` backend call is still issued when
    ``item.issue`` is a string ID so the backend can claim the item (e.g.
    ``bd update --claim``).  When ``item.issue`` is empty the backend is
    responsible for resolving the item by title.

    This function checks ``BacklogBackend.issue_id_type`` rather than the
    concrete backend type, so future string-ID backends (e.g. Linear) inherit
    the correct behaviour automatically.

    Args:
        item: Resolved BacklogItem.
        status: Status string to set (e.g. ``"in-progress"``), or ``None``.
        verified: When ``True``, apply the verified status label.
        repo: GitHub repo slug (e.g. ``"owner/repo"``).
        result: Partial result dict mutated in place with ``"status"`` / ``"verified"`` / ``"error"`` keys.
        output: Output aggregator for info/warning messages.
    """
    has_integer_issue = parse_issue_number(item.issue) is not None
    is_string_id_backend = get_config().backend.issue_id_type == "string"
    no_backend_target = not item.issue and not is_string_id_backend

    if status == "in-progress":
        if no_backend_target:
            # No issue on an integer-ID backend — nothing to do.
            return
        if is_string_id_backend:
            # Backend call: claim the item (e.g. bd update <id-or-title> --claim).
            apply_status_in_progress(item, repo, output=output)
            # Local YAML update: list_items skips live batch-status fetch for
            # string-ID backends, so write status locally to keep the view current.
            if item.reference:
                update_item_metadata(item.reference, {"metadata": {"status": "in-progress"}}, output=output)
        elif has_integer_issue:
            apply_status_in_progress(item, repo, output=output)
        result["status"] = "in-progress"
    elif status:
        # Unlike "in-progress" above, these outcomes don't all require a
        # backend target — terminal-status/unrecognized-value rejection is
        # pure validation, so run it even when no_backend_target is True.
        _apply_non_in_progress_status(item, status, repo, result, output)
    elif no_backend_target:
        # No status change requested and nothing to write to: skip the
        # verified check below too, rather than reporting a no-op "verified".
        return

    if verified:
        if not has_integer_issue:
            # verified label requires a numeric issue ID — no-op for backends
            # that use string IDs or for items with no issue reference.
            result["verified"] = True
            return
        try:
            apply_status_verified(item, repo, output=output)
        except GithubException as e:
            result["error"] = str(e)
            return
        result["verified"] = True


# ---------------------------------------------------------------------------
# Public API: UPDATE
# ---------------------------------------------------------------------------


def _apply_groomed_update(
    item: BacklogItem,
    result: dict[str, str | int | bool | list[str]],
    groomed_file: str | None,
    groomed_content: str | None,
    section: str | None,
    content: str | None,
    repo: str,
    output: Output,
    *,
    entry_id: str | None,
    replace_section: bool,
    reason: str | None,
    append: bool,
    sections: dict[str, str] | None,
) -> dict[str, str | int | bool | list[str] | dict[str, str | int | bool]]:
    """Apply groomed content update (batch or single-section) and return result dict.

    Extracted from update_item to keep cyclomatic complexity within limit.

    Args:
        item: Resolved BacklogItem with a stable backend reference.
        result: Partial result dict already containing ``title`` key.
        groomed_file: Path to groomed content file (single-section path).
        groomed_content: Raw groomed content string (single-section path).
        section: Section name for single-section update.
        content: Content string for single-section update.
        repo: GitHub repo slug.
        output: Output aggregator (never None here).
        entry_id: Entry block ID for targeted replacement.
        replace_section: When True, replace the full section.
        reason: Reason string for entry-block operations.
        append: When True and section is set, append content.
        sections: Batch mapping of section name to raw content.

    Returns:
        Completed result dict with groomed_updated and optional sections_written.

    Raises:
        BacklogError: If item has no file_path.
        ValidationError: If resolved single-section content is empty.
    """
    # Unreachable — see BacklogItem class docstring (models.py).
    if not item.reference:
        msg = "Item has no backend reference"
        raise BacklogError(msg)

    if sections is not None:
        if sections:
            written = _handle_batch_groomed(item, sections, repo, output=output)
            return {**result, "sections_written": written, "groomed_updated": True, **output.to_dict()}
        return {**result, "sections_written": [], "groomed_updated": False, **output.to_dict()}

    groomed_content_val, section_name = _resolve_groomed_content(section, content, groomed_content, groomed_file)
    if not groomed_content_val.strip():
        msg = "No groomed content provided"
        raise ValidationError(msg)
    _handle_update_groomed(
        item,
        groomed_content_val,
        section_name,
        repo,
        output=output,
        entry_id=entry_id,
        replace_section=replace_section,
        reason=reason,
        append=append,
    )
    return {**result, "groomed_updated": True, **output.to_dict()}


def update_item(
    selector: str,
    plan: str | None = None,
    status: str | None = None,
    groomed_file: str | None = None,
    groomed_content: str | None = None,
    section: str | None = None,
    content: str | None = None,
    groomed: bool = False,
    title: str | None = None,
    description: str | None = None,
    repo: str = "",
    output: Output | None = None,
    *,
    entry_id: str | None = None,
    replace_section: bool = False,
    reason: str | None = None,
    verified: bool = False,
    append: bool = False,
    sections: dict[str, str] | None = None,
) -> dict[str, str | int | bool | list[str] | dict[str, str | int | bool]]:
    """Update item: add Plan, set status:in-progress, apply verified label, or write groomed content.

    Args:
        selector: Item selector (title, issue ref, or file path).
        plan: Plan string to apply to the item.
        status: Status string to set (e.g. "in-progress").
        groomed_file: Path to a file containing groomed content.
        groomed_content: Raw groomed content string.
        section: Section name for single-section update.
        content: Content for single-section update (requires section).
        groomed: When True with no other content args, mark item as groomed.
        title: New title to rename the item.
        description: New description string.
        repo: GitHub repo slug (e.g. "owner/repo").
        output: Optional Output aggregator.
        entry_id: Entry block ID for targeted replacement.
        replace_section: When True, replace the full section instead of appending.
        reason: Reason string for entry-block operations.
        verified: When True, apply the verified status label.
        append: When True and section is set, append rather than replace.
        sections: Mapping of section name to raw content for batch writes.
            Mutually exclusive with groomed_file, groomed_content, section/content.
            An empty dict is a no-op (returns success with sections_written=[]).

    Returns:
        Dict with update results. When sections is provided, includes
        ``sections_written: list[str]`` and ``groomed_updated: bool``.
    """
    out = output or Output()
    items = get_config().backend.list_work_items()
    item = find_item(items, selector)
    if not item:
        _pull_if_issue_selector(selector, repo, output=out)
        items = get_config().backend.list_work_items()
        item = find_item(items, selector)
    if not item:
        raise ItemNotFoundError(selector)

    result: dict[str, str | int | bool | list[str]] = {"title": item.title}

    if title:
        _rename_item_title(item, title, repo, output=out)
        result["renamed_to"] = title

    if description is not None:
        _update_item_description(item, description, output=out)
        result["description_updated"] = True

    has_groomed = groomed or groomed_file or groomed_content or (section and content) or (sections is not None)
    if has_groomed:
        return _apply_groomed_update(
            item,
            result,
            groomed_file=groomed_file,
            groomed_content=groomed_content,
            section=section,
            content=content,
            repo=repo,
            output=out,
            entry_id=entry_id,
            replace_section=replace_section,
            reason=reason,
            append=append,
            sections=sections,
        )

    if plan:
        _apply_plan_to_item(item, plan, repo, output=out)
        out.info(f"  Plan: {plan}")
        result["plan"] = plan

    if not item.issue and (not title or status or verified):
        issue_num = _create_issue_and_update_item(item, repo, output=out)
        if issue_num:
            out.info(f"  Issue: #{issue_num}")
            result["issue_num"] = issue_num

    _apply_issue_status_labels(item, status, verified, repo, result, out)

    changes = _extract_changes(result)
    return {**result, "changes": changes, **out.to_dict()}


# ---------------------------------------------------------------------------
# Public API: GROOM
# ---------------------------------------------------------------------------


def groom_item(
    selector: str,
    groomed_file: str | None = None,
    groomed_content: str | None = None,
    section: str | None = None,
    content: str | None = None,
    repo: str = "",
    output: Output | None = None,
    *,
    entry_id: str | None = None,
    replace_section: bool = False,
    reason: str | None = None,
    append: bool = False,
    sections: dict[str, str] | None = None,
    mark_groomed: bool = False,
) -> dict[str, str | int | bool | list[str] | dict[str, str | int | bool]]:
    """Write groomed content through the configured backend. Delegates to update_item.

    Args:
        selector: Item selector (title, issue ref, or file path).
        groomed_file: Path to a file containing groomed content.
        groomed_content: Raw groomed content string.
        section: Section name for single-section update.
        content: Content for single-section update (requires section).
        repo: GitHub repo slug (e.g. "owner/repo").
        output: Optional Output aggregator.
        entry_id: Entry block ID for targeted replacement.
        replace_section: When True, replace the full section instead of appending.
        reason: Reason string for entry-block operations.
        append: When True and section is set, append rather than replace.
        sections: Mapping of section name to raw content for batch writes.
            Mutually exclusive with groomed_file, groomed_content, section/content.
        mark_groomed: When True, advance item status to groomed after content is
            written: set local frontmatter status to 'groomed', remove
            status:needs-grooming label (idempotent), and add status:groomed label
            (created if absent). Default False preserves existing behavior.

    Returns:
        Dict with groom results.
    """
    out = output or Output()
    has_input = groomed_file or groomed_content or (section and content) or sections is not None
    items = get_config().backend.list_work_items()
    item = find_item(items, selector)
    if not item:
        _pull_if_issue_selector(selector, repo, output=out)
    if has_input:
        result = update_item(
            selector=selector,
            plan=None,
            status=None,
            groomed_file=groomed_file,
            groomed_content=groomed_content,
            section=section,
            content=content,
            groomed=True,
            repo=repo,
            output=out,
            entry_id=entry_id,
            replace_section=replace_section,
            reason=reason,
            append=append,
            sections=sections,
        )
    else:
        # No content to write — skip update_item to avoid stdin read in _resolve_groomed_content.
        # Proceed directly to mark_groomed handling below.
        result = {}
    if mark_groomed and "error" not in result:
        fresh_items = get_config().backend.list_work_items()
        fresh_item = find_item(fresh_items, selector)
        if not fresh_item:
            out.warn(f"  mark_groomed requested but item '{selector}' not found after re-parse — status not advanced")
            result["mark_groomed_skipped"] = True
            result["mark_groomed_skip_reason"] = f"Item '{selector}' not found in re-parsed backlog"
        else:
            if fresh_item.reference:
                update_item_metadata(fresh_item.reference, {"metadata": {"status": "groomed"}}, output=out)
                result["mark_groomed_applied"] = True
                out.info("  Status: groomed (local)")
            if fresh_item.issue:
                try:
                    apply_status_groomed(fresh_item, repo, output=out)
                except GithubException as e:
                    out.warn(f"  GitHub label update failed: {e}")
                    result["mark_groomed_label_error"] = str(e)
    return result


# ---------------------------------------------------------------------------
# Public API: STRIKE ENTRY
# ---------------------------------------------------------------------------


def strike_entry(
    selector: str, entry_id: str, reason: str, section: str | None = None, output: Output | None = None
) -> dict[str, str | int | bool | list[str]]:
    """Strike (retract) an entry block within a backlog item.

    Finds the entry by ``entry_id`` across all sections (or within a specific
    section if provided), wraps it in a collapsed ``<details>`` with the
    reason, writes the file back, and syncs to GitHub if an issue exists.

    Args:
        selector: Item title, slug, or issue reference.
        entry_id: Timestamp ID of the entry to strike.
        reason: Human-readable reason for striking.
        section: Optional section name to scope the search.
        output: Optional Output collector.

    Returns:
        Dict with strike results.

    Raises:
        ItemNotFoundError: If item cannot be found.
        ValueError: If entry_id not found in the item body.
    """
    out = output or Output()
    items = get_config().backend.list_work_items()
    item = find_item(items, selector)
    if not item:
        raise ItemNotFoundError(selector)
    # Unreachable — see BacklogItem class docstring (models.py).
    if not item.reference:
        msg = "Item has no backend reference"
        raise BacklogError(msg)

    struck_at = now_iso()
    found = False
    for section_name, section_data in item.sections.items():
        if not isinstance(section_data, Section) or (section and section_name.lower() != section.lower()):
            continue
        for entry in section_data.entries:
            if entry.id == entry_id:
                entry.struck = True
                entry.struck_at = struck_at
                entry.struck_reason = reason
                found = True
                break
        if found:
            break
    if not found:
        msg = f"Entry '{entry_id}' not found in item '{item.title}'"
        if section:
            msg += f" section '{section}'"
        raise ValueError(msg)

    backend = get_config().backend
    backend.put_work_item(item)
    out.info(f"Struck entry {entry_id} in {item.reference}")
    if item.issue and isinstance(backend, SyncProvider):
        backend.reconcile(ReconcileRequest(scope=ReconcileScope.TARGETED, references=[item.issue]))
        out.info(f"  Reconciled strike for {item.issue}")

    return {"title": item.title, "entry_id": entry_id, "struck": True, **out.to_dict()}


# ---------------------------------------------------------------------------
# Public API: NORMALIZE
# ---------------------------------------------------------------------------


def normalize_items(dry_run: bool = False, output: Output | None = None) -> dict[str, int | bool | list[str]]:
    """Normalize all work items through the configured backend.

    Returns:
        Dict with count of normalized items.
    """
    out = output or Output()
    items = get_config().backend.list_work_items()
    if not items:
        out.info("No backlog items found")
        return {"normalized": 0, **out.to_dict()}
    if not dry_run:
        for item in items:
            get_config().backend.put_work_item(item)
    updated = len(items)
    out.info(f"Normalized {updated} item(s)" + (" [dry-run]" if dry_run else ""))
    return {"normalized": updated, "dry_run": dry_run, **out.to_dict()}


# ---------------------------------------------------------------------------
# Helpers: issue field → metadata mapping
# ---------------------------------------------------------------------------


def _issue_fields_to_metadata(fields: IssueLocalFields) -> dict[str, str | list[str] | MilestoneInfo]:
    """Extract the GitHub-synced metadata fields from an IssueLocalFields instance.

    Returns:
        Dict suitable for merging into BacklogItemMetadata or passing as
        a nested ``"metadata"`` update dict to :func:`update_item_metadata`.
    """
    return {
        "updated_at": fields.updated_at,
        "assignees": fields.assignees,
        "labels": fields.labels,
        "milestone": fields.milestone,
        "milestone_info": fields.milestone_info,
    }


# ---------------------------------------------------------------------------
# Public API: PULL
# ---------------------------------------------------------------------------


def pull_single_issue(
    issue_num: int, output: Output | None = None, diff_mode: bool = False
) -> dict[str, str | list[str] | None]:
    """Reconcile one GitHub issue through the configured sync backend.

    If filepath is None, derives it from the issue title and priority.

    Args:
        issue_num: GitHub issue number to fetch.
        output: Optional Output collector for messages and warnings.
        diff_mode: When True, computes a unified diff of old vs new body content and
            includes it in the return dict under the ``"diff"`` key.

    Returns:
        Dict with ``"file_path"`` (Path or None on failure) and, when diff_mode is True
        and the file already existed, ``"diff"`` (unified diff string, may be empty if
        content was unchanged).
    """
    out = output or Output()
    backend = get_config().backend
    if not isinstance(backend, SyncProvider):
        out.info("Active backend does not support reconciliation.")
        return {"file_path": None, **out.to_dict()}
    reference = f"#{issue_num}"
    reconciliation = backend.reconcile(
        ReconcileRequest(scope=ReconcileScope.TARGETED, references=[reference], include_diff=diff_mode)
    )
    result: dict[str, str | list[str] | None] = {"file_path": reconciliation.file_paths.get(reference), **out.to_dict()}
    if diff_mode:
        result["diff"] = reconciliation.diffs.get(reference, "")
    return result


def pull_by_selector(
    selector: str, repo: str = "", output: Output | None = None, diff: bool = False
) -> dict[str, str | list[str] | None]:
    """Pull a single GitHub issue into the provider-backed record by selector.

    Supports issue number selectors (#N, bare number, URL) and title substrings.
    For issue number selectors, fetches directly from GitHub.
    For title substrings, finds the local item, reads its issue number,
    then fetches from GitHub.

    Args:
        selector: Issue number, URL, or title substring.
        repo: GitHub repository slug (owner/name).
        output: Optional Output collector for messages and warnings.
        diff: When True, computes a unified diff of old vs new body content and
            includes it in the return dict under the ``"diff"`` key.

    Returns:
        Dict with 'file_path' (local path written), output messages/warnings, and
        optionally 'diff' (unified diff string) when diff=True.

    Raises:
        ItemNotFoundError: If selector matches no item in the provider-backed record.
        BacklogError: If matched item has no linked GitHub issue.
    """
    out = output or Output()
    issue_num_str = parse_issue_selector(selector)
    if not issue_num_str:
        # Title substring: find item in provider-backed record then pull by its issue number
        items = get_config().backend.list_work_items()
        item = find_item(items, selector)
        if item is None:
            raise ItemNotFoundError(selector)

        issue_ref = item.issue
        if not issue_ref:
            msg = f"Item '{item.title}' has no linked GitHub issue. Use backlog_pull() for bulk pull."
            raise BacklogError(msg)

        issue_num_str = parse_issue_selector(issue_ref)
        if not issue_num_str:
            msg = f"Could not parse issue number from '{issue_ref}'"
            raise BacklogError(msg)

    reference = f"#{int(issue_num_str)}"
    backend = get_config().backend
    if isinstance(backend, SyncProvider):
        result = backend.reconcile(
            ReconcileRequest(scope=ReconcileScope.TARGETED, references=[reference], include_diff=diff)
        )
        out.info(
            f"Reconciled targeted item: {result.fetched_pages} pages, {result.fetched_items} items, "
            f"{result.local_updates} local updates, {result.provider_patches} patches, {result.no_ops} no-ops, "
            f"{result.conflicts} conflicts, {result.failures} failures."
        )
        ret: dict[str, str | list[str] | None] = {"file_path": result.file_paths.get(reference), **out.to_dict()}
        if diff and (changed_diff := result.diffs.get(reference)) is not None:
            ret["diff"] = changed_diff
        return ret

    out.info("Active backend does not support reconciliation.")
    return {"file_path": None, **out.to_dict()}


def pull_items(
    repo: str = "", dry_run: bool = False, force: bool = False, diff: bool = False, output: Output | None = None
) -> dict[str, int | bool | str | list[str]]:
    """Reconcile linked issue content through the configured sync backend.

    Also auto-migrates P0/P1 items that lack GitHub Issues by creating them.
    Merges by section — keeps longer version of each section.
    Skips items with no issue number (after migration).

    Returns:
        Dict with count of pulled items.
    """
    out = output or Output()
    items = get_config().backend.list_work_items()

    # Auto-migration: create missing GitHub Issues for P0/P1 items
    if any(it.section in {"P0", "P1"} and not it.skip and not it.issue for it in items):
        out.info(
            f"Auto-migrating {sum(it.section in {'P0', 'P1'} and not it.skip and not it.issue for it in items)} "
            "P0/P1 item(s) to GitHub Issues..."
        )
        sync_create_missing_issues(items, repo, dry_run, output=out)
        # Re-parse after migration to pick up updated issue numbers
        items = get_config().backend.list_work_items()

    candidates = [it for it in items if it.issue and not it.skip]

    if not candidates:
        out.info("No items with GitHub issue numbers found.")
        return {"pulled": 0, **out.to_dict()}

    backend = get_config().backend
    if isinstance(backend, SyncProvider):
        result = backend.reconcile(
            ReconcileRequest(
                scope=ReconcileScope.LINKED,
                references=list(dict.fromkeys(item.issue for item in candidates)),
                dry_run=dry_run,
                force=force,
                include_diff=diff,
            )
        )
        out.info(
            f"Reconciled linked items: {result.fetched_pages} pages, {result.fetched_items} items, "
            f"{result.local_updates} local updates, {result.provider_patches} patches, {result.no_ops} no-ops, "
            f"{result.conflicts} conflicts, {result.failures} failures."
        )
        if diff and result.diffs:
            return {
                "pulled": result.local_updates,
                "skipped": result.failures,
                "total": len(candidates),
                "dry_run": dry_run,
                "diff": "\n".join(result.diffs.values()),
                **out.to_dict(),
            }
        return {
            "pulled": result.local_updates,
            "skipped": result.failures,
            "total": len(candidates),
            "dry_run": dry_run,
            **out.to_dict(),
        }

    out.info("Active backend does not support reconciliation.")
    return {"pulled": 0, "skipped": 0, "total": len(candidates), "dry_run": dry_run, **out.to_dict()}


# ---------------------------------------------------------------------------
# Public API: SAM TASK OPERATIONS
# ---------------------------------------------------------------------------


def _sub_issues_to_task_dicts(sub_issues: list[IssueNode]) -> list[dict[str, object]]:
    """Convert a list of GraphQL IssueNode dicts to task dicts.

    Each dict contains ``issue_number``, ``issue_url``, ``title`` plus all
    ``SamTask`` fields parsed from the issue body's ``<!-- sam:task ... -->`` block.

    Args:
        sub_issues: List of IssueNode TypedDicts from ``get_config().backend.get_task_issues()``.

    Returns:
        List of task dicts with GitHub issue fields and SAM metadata merged.
    """
    tasks: list[dict[str, object]] = []
    for si in sub_issues:
        body = si["body"] or ""
        task_meta = parse_sam_task_metadata(body)
        task_dict: dict[str, object] = {"issue_number": si["number"], "issue_url": "", "title": si["title"]}
        if task_meta is not None:
            task_dict.update(task_meta.model_dump())
        tasks.append(task_dict)
    return tasks


def create_sam_task(
    parent_issue_number: int,
    task_id: str,
    feature: str,
    task_type: str,
    agent: str,
    priority: int,
    skills: list[str],
    dependencies: list[str],
    description: str,
    acceptance_criteria: list[str] | None = None,
    labels: list[str] | None = None,
    output: Output | None = None,
    repo: str = "",
) -> dict[str, str | int | list[str]]:
    """Create a GitHub issue for a SAM task and link it as a sub-issue of a parent story.

    Constructs a ``SamTask`` from scalar parameters, creates the GitHub issue, and
    links it as a sub-issue of the parent. Wraps ``backend.create_task_issue()``.

    Args:
        parent_issue_number: Issue number of the parent story (without ``#``).
        repo: Repository slug (``owner/name``). Defaults to ``DEFAULT_REPO``.
        task_id: Feature-scoped sequential ID, e.g. ``"T1"``, ``"T2"``.
        feature: Feature slug, e.g. ``"uv-skill-update"``.
        task_type: Execution category: ``"research"`` | ``"implement"`` | ``"review"`` | ``"fix"`` | ``"docs"``.
        agent: Agent name to execute the task.
        priority: Execution priority 1-5 (1 = highest).
        skills: Skill names the executing agent should load.
        dependencies: Feature-scoped task IDs this task depends on (e.g. ``["T1", "T2"]``).
        description: Short human-readable description of the task.
        acceptance_criteria: Optional list of acceptance criteria strings.
        labels: Optional list of label names to apply.
        output: Optional Output collector.

    Returns:
        Dict with ``issue_number``, ``title``, ``url``, and output messages.
        Includes ``warnings`` from sub-issue linking when applicable.

    Raises:
        GitHubUnavailableError: If GITHUB_TOKEN is not set.
    """
    out = output or Output()
    task = SamTask(
        task_id=task_id,
        feature=feature,
        task_type=task_type,
        agent=agent,
        priority=priority,
        skills=skills,
        dependencies=dependencies,
    )
    gh_repo = get_github(repo)
    issue = create_task_issue(gh_repo, parent_issue_number, task, description, acceptance_criteria, labels, output=out)
    if issue is None:
        return {"issue_number": 0, "title": "", "url": "", **out.to_dict()}
    return {"issue_number": issue["number"], "title": issue["title"], "url": "", **out.to_dict()}


def get_sam_tasks(
    parent_issue_number: int | str, refresh_cache: bool = True, repo: str = "", output: Output | None = None
) -> _SamTaskLookupResult:
    """Return SAM tasks from plans owned by a backend work item.

    Args:
        parent_issue_number: Native parent work-item reference.
        refresh_cache: Retained for caller compatibility; providers own refresh policy.
        repo: Retained for caller compatibility; the configured backend owns location.
        output: Optional Output collector.

    Returns:
        SAM task rows plus explicit provider availability and freshness metadata.
    """
    out = output or Output()
    _ = refresh_cache, repo
    backend = get_config().backend
    if not isinstance(backend, ContentProvider):
        out.error("Active backend does not support SAM task content")
        return {
            "tasks": [],
            "count": 0,
            "parent_issue_number": parent_issue_number,
            "stale": False,
            "pending": False,
            "unavailable": True,
            "messages": out.messages,
            "warnings": out.warnings,
            "errors": out.errors,
        }

    parent = str(parent_issue_number)
    owner_references = {parent, f"#{parent}"} if isinstance(parent_issue_number, int) else {parent}
    for item in backend.list_work_items():
        if parent in {item.reference.lstrip("#"), item.issue.lstrip("#")}:
            owner_references.update(reference for reference in (item.reference, item.issue) if reference)

    records = {}
    try:
        for owner_reference in owner_references:
            offset = 0
            while True:
                page = backend.list_content(
                    ContentQuery(
                        kind=ContentKind.PLAN, owner_reference=owner_reference, offset=offset, limit=_SAM_PLAN_PAGE_SIZE
                    )
                )
                for record in page:
                    records[record.reference.name] = record
                if len(page) < _SAM_PLAN_PAGE_SIZE:
                    break
                offset += len(page)
    except ContentUnavailableError as exc:
        out.error(str(exc))
        return {
            "tasks": [],
            "count": 0,
            "parent_issue_number": parent_issue_number,
            "stale": False,
            "pending": False,
            "unavailable": True,
            "messages": out.messages,
            "warnings": out.warnings,
            "errors": out.errors,
        }

    tasks: list[_SamTaskRow] = []
    stale = any(record.stale for record in records.values())
    pending = any(record.pending for record in records.values())
    try:
        plans = [
            Plan.model_validate(parse_plan_content(record.content, record.reference.name))
            for record in records.values()
        ]
    except (ValueError, YAMLError) as exc:
        out.error(f"SAM task content is invalid: {exc}")
        return {
            "tasks": [],
            "count": 0,
            "parent_issue_number": parent_issue_number,
            "stale": stale,
            "pending": pending,
            "unavailable": True,
            "messages": out.messages,
            "warnings": out.warnings,
            "errors": out.errors,
        }
    for plan in plans:
        tasks.extend(
            {
                "task_id": task.id,
                "feature": plan.feature,
                "status": task.status,
                "agent": task.agent or "",
                "priority": int(task.priority),
                "skills": task.skills,
                "dependencies": task.dependencies,
                "issue_number": task.github_issue or 0,
                "issue_url": "",
                "title": task.title,
            }
            for task in plan.tasks
        )
    if stale:
        out.warn("SAM tasks were served from provider-owned stale content")
    return {
        "tasks": tasks,
        "count": len(tasks),
        "parent_issue_number": parent_issue_number,
        "stale": stale,
        "pending": pending,
        "unavailable": False,
        "messages": out.messages,
        "warnings": out.warnings,
        "errors": out.errors,
    }


def update_sam_task_status(
    issue_number: int, new_status: str, output: Output | None = None, repo: str = ""
) -> dict[str, bool | int | str | list[str]]:
    """Update the status field in the ``<!-- sam:task ... -->`` block of a task issue body.

    Wraps ``backend.update_task_status()``. Returns without error when the status
    is already the target value or no ``sam:task`` block is found.

    Args:
        issue_number: Task issue number (without ``#``).
        new_status: Target status string, e.g. ``"in-progress"`` or ``"complete"``.
        repo: Repository slug (``owner/name``). Defaults to ``DEFAULT_REPO``.
        output: Optional Output collector.

    Returns:
        Dict with ``updated`` (bool), ``issue_number``, ``new_status``, and output messages.

    Raises:
        GitHubUnavailableError: If GITHUB_TOKEN is not set.
    """
    out = output or Output()
    gh_repo = get_github(repo)
    updated = update_task_status(gh_repo, issue_number, new_status, output=out)
    return {"updated": updated, "issue_number": issue_number, "new_status": new_status, **out.to_dict()}


def _extract_feature_slug(tasks: list[dict[str, object]]) -> str:
    """Return the first non-empty feature slug found in a list of task dicts."""
    for t in tasks:
        slug = t.get("feature", "")
        if isinstance(slug, str) and slug:
            return slug
    return ""


def _build_task_status_map(tasks: list[dict[str, object]]) -> dict[str, str]:
    """Return a ``{task_id: status}`` mapping for feature-scoped task IDs."""
    return {
        str(tid): str(t.get("status", "not-started"))
        for t in tasks
        if isinstance((tid := t.get("task_id", "")), str) and tid
    }


def _is_sam_task_ready(task: dict[str, object], status_by_id: dict[str, str]) -> bool:
    """Return True when a task is not-started and all feature-scoped deps are successful."""
    if str(task.get("status", "not-started")) != "not-started":
        return False
    deps_raw = task.get("dependencies", [])
    for dep in list(deps_raw) if isinstance(deps_raw, list) else []:
        dep_str = str(dep).strip()
        if dep_str.startswith("#"):  # cross-feature ref — always satisfied
            continue
        if status_by_id.get(dep_str, "not-started") not in _SAM_SUCCESSFUL_STATUSES:
            return False
    return True


def get_ready_sam_tasks(
    parent_issue_number: int, repo: str = "", output: Output | None = None
) -> dict[str, str | list[dict[str, object]] | int | list[str]]:
    """Return SAM tasks that are ready to execute (not-started with all deps satisfied).

    A task is ready when its status is ``"not-started"`` and all dependencies
    have a successful status (``"complete"`` or ``"deferred"``). Cross-feature ``#N`` dependencies
    (GitHub issue references) are treated as always-satisfied.

    Args:
        parent_issue_number: Issue number of the parent story (without ``#``).
        repo: Repository slug (``owner/name``). Defaults to ``DEFAULT_REPO``.
        output: Optional Output collector.

    Returns:
        Dict with ``feature`` (slug), ``ready_tasks`` (list), ``count``, and output messages.
        Each ready task dict contains: ``id``, ``name``, ``agent``, ``skills``, ``issue_number``.
    """
    out = output or Output()
    tasks_result = get_sam_tasks(parent_issue_number, refresh_cache=True, repo=repo, output=out)
    tasks_raw = tasks_result.get("tasks", [])
    tasks = (
        [{str(key): value for key, value in task.items()} for task in tasks_raw if isinstance(task, dict)]
        if isinstance(tasks_raw, list)
        else []
    )
    feature_slug = _extract_feature_slug(tasks)
    status_by_id = _build_task_status_map(tasks)
    ready: list[dict[str, object]] = [
        {
            "id": t.get("task_id", ""),
            "name": t.get("title", ""),
            "agent": t.get("agent", ""),
            "skills": t.get("skills", []),
            "issue_number": t.get("issue_number", 0),
        }
        for t in tasks
        if _is_sam_task_ready(t, status_by_id)
    ]
    return {"feature": feature_slug, "ready_tasks": ready, "count": len(ready), **out.to_dict()}


# ---------------------------------------------------------------------------
# Labels (read-only)
# ---------------------------------------------------------------------------


def list_labels(repo: str = "", limit: int = 100, output: Output | None = None) -> dict[str, object]:
    """Return repository labels up to ``limit``.

    Read-only. Label mutations are owned by ``state_handler.apply_github_transition()``.

    Args:
        repo: Repository slug (``owner/name``). Defaults to ``DEFAULT_REPO``.
        limit: Maximum number of labels to return. Defaults to 100.
        output: Optional Output collector.

    Returns:
        Dict with ``labels`` (list of dicts with ``name``, ``color``, ``description``),
        ``count`` (int), and output messages/warnings.

    Raises:
        GitHubUnavailableError: If GITHUB_TOKEN is not set or GitHub is unreachable.
    """
    out = output or Output()
    repository = get_github(repo)
    labels: list[dict[str, str]] = []
    for label in repository.get_labels():
        if len(labels) >= limit:
            break
        labels.append({"name": label.name, "color": label.color, "description": label.description or ""})
    return {"labels": labels, "count": len(labels), **out.to_dict()}


# ---------------------------------------------------------------------------
# Pull requests (read-only)
# ---------------------------------------------------------------------------


def list_merged_prs(
    repo: str = "", search: str | None = None, limit: int = 20, output: Output | None = None
) -> dict[str, list[dict[str, str | int]] | int | list[str]]:
    """Return merged pull requests, optionally filtered by a search query.

    Fetches closed PRs from GitHub and retains only those where
    ``merged_at`` is set (i.e. actually merged, not just closed).  When
    ``search`` is provided the PR title and body are scanned for the
    substring (case-insensitive).

    Args:
        repo: Repository slug (``owner/name``). Defaults to ``DEFAULT_REPO``.
        search: Optional substring to filter by (checked against title and
            body, case-insensitive).  Useful for finding PRs related to a
            specific issue number (e.g. ``"#42"``) or keyword.
        limit: Maximum number of PRs to return. Defaults to 20.
        output: Optional Output collector.

    Returns:
        Dict with ``pull_requests`` (list of dicts with ``number``,
        ``title``, ``merged_at``, ``author``, ``url``, ``head_branch``),
        ``count`` (int), and output messages/warnings.

    Raises:
        GitHubUnavailableError: If GITHUB_TOKEN is not set or GitHub is
            unreachable.
        BacklogError: On GitHub API errors.
    """
    out = output or Output()
    try:
        repository = get_github(repo)
        prs: list[dict[str, str | int]] = []
        needle = search.casefold() if search else None
        for pr in repository.get_pulls(state="closed", sort="updated", direction="desc"):
            if len(prs) >= limit:
                break
            if pr.merged_at is None:
                continue
            if needle is not None:
                title_match = needle in (pr.title or "").casefold()
                body_match = needle in (pr.body or "").casefold()
                if not title_match and not body_match:
                    continue
            prs.append({
                "number": pr.number,
                "title": pr.title or "",
                "merged_at": pr.merged_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "author": pr.user.login if pr.user else "",
                "url": pr.html_url or "",
                "head_branch": pr.head.ref if pr.head else "",
            })
    except GithubException as e:
        msg = f"GitHub API error fetching pull requests: {e}"
        raise BacklogError(msg) from e
    return {"pull_requests": prs, "count": len(prs), **out.to_dict()}


# ---------------------------------------------------------------------------
# Milestones
# ---------------------------------------------------------------------------


def list_milestones(
    repo: str = "", state: str = "open", output: Output | None = None
) -> dict[str, list[dict[str, object]] | int | list[str]]:
    """Return repository milestones filtered by state.

    Args:
        repo: Repository slug (``owner/name``). Defaults to ``DEFAULT_REPO``.
        state: Filter by milestone state: ``"open"``, ``"closed"``, or ``"all"``.
            Defaults to ``"open"``.
        output: Optional Output collector.

    Returns:
        Dict with ``milestones`` (list of dicts with ``number``, ``title``,
        ``state``, ``description``, ``due_on``, ``open_issues``,
        ``closed_issues``), ``count`` (int), and output messages/warnings.

    Raises:
        GitHubUnavailableError: If GITHUB_TOKEN is not set or GitHub is unreachable.
        ValidationError: If ``state`` is not one of ``open``, ``closed``, ``all``.
    """
    out = output or Output()
    valid_states = {"open", "closed", "all"}
    if state not in valid_states:
        msg = f"state must be one of {sorted(valid_states)!r}, got {state!r}"
        raise ValidationError(msg)
    repository = get_github(repo)
    owner, repo_name = repository.full_name.split("/", 1)
    state_map = {"open": ["OPEN"], "closed": ["CLOSED"], "all": ["OPEN", "CLOSED"]}
    ms_nodes = _fetch_milestones_graphql(repository, owner, repo_name, states=state_map[state])
    milestones: list[dict[str, object]] = [
        {
            "number": ms["number"],
            "title": ms["title"],
            "state": ms["state"].lower(),
            "description": ms["description"] or "",
            "due_on": ms["dueOn"],
            "open_issues": ms["openIssueCount"],
            "closed_issues": ms["closedIssueCount"],
        }
        for ms in ms_nodes
    ]
    return {"milestones": milestones, "count": len(milestones), **out.to_dict()}


def get_soonest_milestone(repo: str = "", output: Output | None = None) -> dict[str, object]:
    """Return the open milestone with the earliest due date.

    Milestones without a due date are excluded from consideration.
    If all open milestones lack a due date, the first one by GitHub's
    default ordering is returned with a warning.

    Args:
        repo: Repository slug (``owner/name``). Defaults to ``DEFAULT_REPO``.
        output: Optional Output collector.

    Returns:
        Dict with ``milestone`` (dict or None) containing ``number``, ``title``,
        ``state``, ``description``, ``due_on``, ``open_issues``,
        ``closed_issues``, and output messages/warnings.
        ``milestone`` is ``None`` when no open milestones exist.

    Raises:
        GitHubUnavailableError: If GITHUB_TOKEN is not set or GitHub is unreachable.
    """
    out = output or Output()
    repository = get_github(repo)
    owner, repo_name = repository.full_name.split("/", 1)
    all_open = _fetch_milestones_graphql(repository, owner, repo_name, states=["OPEN"])
    if not all_open:
        return {"milestone": None, **out.to_dict()}

    with_due = [ms for ms in all_open if ms["dueOn"] is not None]
    if with_due:
        soonest = min(with_due, key=operator.itemgetter("dueOn"))
    else:
        out.warn("No open milestones have a due date; returning first by default ordering")
        soonest = all_open[0]

    return {
        "milestone": {
            "number": soonest["number"],
            "title": soonest["title"],
            "state": soonest["state"].lower(),
            "description": soonest["description"] or "",
            "due_on": soonest["dueOn"],
            "open_issues": soonest["openIssueCount"],
            "closed_issues": soonest["closedIssueCount"],
        },
        **out.to_dict(),
    }


def create_milestone(
    repo: str = "", title: str = "", description: str = "", due_on: str | None = None, output: Output | None = None
) -> dict[str, object]:
    """Create a new milestone on the repository.

    Args:
        repo: Repository slug (``owner/name``). Defaults to ``DEFAULT_REPO``.
        title: Milestone title. Must be non-empty.
        description: Optional milestone description.
        due_on: Optional due date as ISO 8601 string (e.g. ``"2026-06-30"`` or
            ``"2026-06-30T00:00:00Z"``). Parsed to a ``datetime`` before
            passing to PyGithub.
        output: Optional Output collector.

    Returns:
        Dict with ``milestone`` containing ``number``, ``title``, ``state``,
        ``description``, ``due_on``, ``open_issues``, ``closed_issues``,
        and output messages/warnings.

    Raises:
        GitHubUnavailableError: If GITHUB_TOKEN is not set or GitHub is unreachable.
        ValidationError: If ``title`` is empty or ``due_on`` cannot be parsed.
    """
    out = output or Output()
    if not title.strip():
        msg = "title must be non-empty"
        raise ValidationError(msg)

    due_on_dt: datetime | None = None
    if due_on is not None:
        for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                due_on_dt = datetime.strptime(due_on, fmt).replace(tzinfo=UTC)
                break
            except ValueError:
                continue
        else:
            msg = f"due_on must be ISO 8601 (e.g. '2026-06-30' or '2026-06-30T00:00:00Z'), got {due_on!r}"
            raise ValidationError(msg)

    repository = get_github(repo)
    ms = repository.create_milestone(
        title=title.strip(),
        state="open",
        description=description or GithubObject.NotSet,
        due_on=due_on_dt if due_on_dt is not None else GithubObject.NotSet,
    )
    out.info(f"Created milestone #{ms.number}: {ms.title}")
    return {
        "milestone": {
            "number": ms.number,
            "title": ms.title,
            "state": ms.state,
            "description": ms.description or "",
            "due_on": ms.due_on.strftime("%Y-%m-%dT%H:%M:%SZ") if ms.due_on else None,
            "open_issues": ms.open_issues,
            "closed_issues": ms.closed_issues,
        },
        **out.to_dict(),
    }


# ---------------------------------------------------------------------------
# Issues (ancillary listing + commenting)
# ---------------------------------------------------------------------------

_VALID_ISSUE_STATES: frozenset[str] = frozenset({"open", "closed", "all"})


def _resolve_milestone_number(gh_repo: Repository, milestone: str | None, out: Output) -> int | None:
    """Resolve milestone title to its number via GraphQL.

    Returns:
        Milestone number if found, None otherwise.
    """
    if not milestone:
        return None
    owner, repo_name = gh_repo.full_name.split("/", 1)
    ms_nodes = _fetch_milestones_graphql(gh_repo, owner, repo_name, states=["OPEN", "CLOSED"])
    for ms in ms_nodes:
        if ms["title"] == milestone:
            return ms["number"]
    out.warn(f"  WARNING: milestone '{milestone}' not found — returning unfiltered results")
    return None


def _resolve_label_names(labels: str | None) -> list[str] | None:
    """Parse comma-separated label names string into a list.

    Returns:
        List of label name strings, or None when no labels given.
    """
    if not labels:
        return None
    names = [n.strip() for n in labels.split(",") if n.strip()]
    return names or None


def _collect_issues(
    gh_repo: Repository, state: str, label_names: list[str] | None, milestone_number: int | None, limit: int
) -> list[dict[str, object]]:
    """Fetch issues via GraphQL and return serialized dicts up to limit.

    Returns:
        List of issue dicts with number, title, state, labels, assignees,
        milestone, created_at, and updated_at fields.
    """
    owner, repo_name = gh_repo.full_name.split("/", 1)
    if state == "all":
        open_nodes = sync_issues_graphql(
            gh_repo, owner, repo_name, state="OPEN", labels=label_names, milestone_number=milestone_number
        )
        closed_nodes = sync_issues_graphql(
            gh_repo, owner, repo_name, state="CLOSED", labels=label_names, milestone_number=milestone_number
        )
        issue_nodes = open_nodes + closed_nodes
    else:
        graphql_state = "OPEN" if state == "open" else "CLOSED"
        issue_nodes = sync_issues_graphql(
            gh_repo, owner, repo_name, state=graphql_state, labels=label_names, milestone_number=milestone_number
        )

    issue_list: list[dict[str, object]] = []
    for issue_node in issue_nodes:
        issue_list.append({
            "number": issue_node["number"],
            "title": issue_node["title"],
            "state": issue_node["state"].lower(),
            "labels": [lbl["name"] for lbl in issue_node.get("labels", [])],
            "assignees": [a["login"] for a in issue_node.get("assignees", [])],
            "milestone": ((ms := issue_node.get("milestone")) and ms["title"]) or None,
            "created_at": issue_node.get("createdAt") or "",
            "updated_at": issue_node.get("updatedAt") or "",
        })
        if len(issue_list) >= limit:
            break
    return issue_list


def list_issues(
    repo: str = "",
    milestone: str | None = None,
    labels: str | None = None,
    state: str = "open",
    limit: int = 30,
    output: Output | None = None,
) -> dict[str, list[dict[str, object]] | int | list[str]]:
    """List GitHub issues with optional milestone, label, and state filters.

    Args:
        repo: Repository slug (``owner/name``). Defaults to ``DEFAULT_REPO``.
        milestone: Filter by milestone title. Warns and returns unfiltered
            when the title is not found.
        labels: Comma-separated label names to filter by. Labels that do not
            exist in the repository are skipped with a warning.
        state: Issue state filter — ``"open"``, ``"closed"``, or ``"all"``.
        limit: Maximum number of issues to return. Defaults to 30.
        output: Optional Output collector.

    Returns:
        Dict with ``issues`` (list of dicts), ``count`` (int), and output
        messages/warnings.

    Raises:
        ValidationError: If ``state`` is not one of the valid values.
        GitHubUnavailableError: If GITHUB_TOKEN is not set or GitHub is unreachable.
        BacklogError: On GitHub API errors.
    """
    out = output or Output()
    if state not in _VALID_ISSUE_STATES:
        msg = f"Invalid state {state!r}: must be one of {sorted(_VALID_ISSUE_STATES)}"
        raise ValidationError(msg)
    try:
        gh_repo = get_github(repo)
        milestone_number = _resolve_milestone_number(gh_repo, milestone, out)
        label_names = _resolve_label_names(labels)
        issue_list = _collect_issues(gh_repo, state, label_names, milestone_number, limit)
    except (GithubException, BacklogError) as e:
        msg = f"GitHub API error fetching issues: {e}"
        raise BacklogError(msg) from e
    return {"issues": issue_list, "count": len(issue_list), **out.to_dict()}


def comment_issue(
    repo: str = "", issue_number: int = 0, body: str = "", output: Output | None = None
) -> dict[str, str | int | list[str]]:
    """Add a comment to a GitHub issue.

    Args:
        repo: Repository slug (``owner/name``). Defaults to ``DEFAULT_REPO``.
        issue_number: GitHub issue number (without ``#``). Must be positive.
        body: Comment body in Markdown. Must not be empty.
        output: Optional Output collector.

    Returns:
        Dict with ``issue_number`` (int), ``comment_id`` (int),
        ``comment_url`` (str), and output messages/warnings.

    Raises:
        ValidationError: If ``issue_number`` is not positive or ``body`` is empty.
        GitHubUnavailableError: If GITHUB_TOKEN is not set or GitHub is unreachable.
        BacklogError: On GitHub API errors.
    """
    out = output or Output()
    if issue_number <= 0:
        msg = "issue_number must be a positive integer"
        raise ValidationError(msg)
    if not body.strip():
        msg = "body must not be empty"
        raise ValidationError(msg)
    try:
        gh_repo = get_github(repo)
        owner, repo_name = gh_repo.full_name.split("/", 1)
        issue_node = _fetch_issue_graphql(gh_repo, owner, repo_name, issue_number)
        comment_node_id = _add_comment_graphql(gh_repo, issue_node["id"], body)
        out.info(f"  Comment added to issue #{issue_number}")
    except (GithubException, BacklogError) as e:
        msg = f"GitHub API error adding comment: {e}"
        raise BacklogError(msg) from e
    return {"issue_number": issue_number, "comment_id": comment_node_id, "comment_url": "", **out.to_dict()}


_COMMENT_PREVIEW_LENGTH = 200


def list_comments(
    repo: str = "", issue_number: int = 0, limit: int = 20, offset: int = 0, output: Output | None = None
) -> ListCommentsResult:
    """List comments on a GitHub issue.

    Args:
        repo: Repository slug (``owner/name``). Defaults to ``DEFAULT_REPO``.
        issue_number: GitHub issue number (without ``#``). Must be positive.
        limit: Maximum number of comments to return. Defaults to 20.
        offset: Number of comments to skip before returning results. Defaults to 0.
        output: Optional Output collector.

    Returns:
        Dict with:
          - ``comments``: list of ``{id, author, created_at, updated_at, preview}``
          - ``count``: total comments in the result window
          - ``has_more``: True if more comments exist beyond the current window
          - ``messages``, ``warnings``, ``errors``: output lists

    Raises:
        ValidationError: If ``issue_number`` is not positive.
        GitHubUnavailableError: If GITHUB_TOKEN is not set or GitHub is unreachable.
        BacklogError: On GitHub API errors.
    """
    out = output or Output()
    if issue_number <= 0:
        msg = "issue_number must be a positive integer"
        raise ValidationError(msg)
    try:
        gh_repo = get_github(repo)
        owner, repo_name = gh_repo.full_name.split("/", 1)
        all_comments = _fetch_issue_comments_graphql(gh_repo, owner, repo_name, issue_number)
    except (GithubException, BacklogError) as e:
        msg = f"GitHub API error fetching comments: {e}"
        raise BacklogError(msg) from e

    window = all_comments[offset : offset + limit]
    has_more = len(all_comments) > offset + limit
    comment_list = [
        {
            "id": c["id"],
            "author": c["author"],
            "created_at": c["created_at"],
            "updated_at": c["updated_at"],
            "preview": c["body"][:_COMMENT_PREVIEW_LENGTH],
        }
        for c in window
    ]
    out_d = out.to_dict()
    return {
        "comments": comment_list,
        "count": len(comment_list),
        "has_more": has_more,
        "messages": out_d["messages"],
        "warnings": out_d["warnings"],
        "errors": out_d["errors"],
    }


def read_comment(
    repo: str = "", issue_number: int = 0, comment_id: int = 0, output: Output | None = None
) -> dict[str, str | list[str]]:
    """Read a single comment's full body from a GitHub issue.

    ``comment_id`` is the integer REST comment database ID as returned by the
    GitHub REST API (e.g., the ``id`` field from ``GET /repos/{owner}/{repo}/
    issues/comments``).  The ``id`` values returned by ``list_comments`` are
    GraphQL node IDs (strings like ``IC_kwDO...``) and cannot be used here
    directly — use a REST comment ID instead.  This function resolves the node
    ID automatically via PyGithub before fetching the full body via GraphQL.

    Args:
        repo: Repository slug (``owner/name``). Defaults to ``DEFAULT_REPO``.
        issue_number: GitHub issue number (without ``#``). Must be positive.
        comment_id: REST comment database ID (positive integer). Obtained from
            ``list_comments`` by looking up the comment in the issue's comment
            list, or from the GitHub REST API directly.
        output: Optional Output collector.

    Returns:
        Dict with:
          - ``id``: GraphQL node ID string
          - ``author``: login of the comment author
          - ``created_at``: ISO 8601 timestamp
          - ``updated_at``: ISO 8601 timestamp
          - ``body``: full Markdown content — no truncation
          - ``messages``, ``warnings``, ``errors``: output lists

    Raises:
        ValidationError: If ``issue_number`` or ``comment_id`` is not positive.
        GitHubUnavailableError: If GITHUB_TOKEN is not set or GitHub is unreachable.
        BacklogError: On GitHub API errors or if the comment is not found.
    """
    out = output or Output()
    if issue_number <= 0:
        msg = "issue_number must be a positive integer"
        raise ValidationError(msg)
    if comment_id <= 0:
        msg = "comment_id must be a positive integer"
        raise ValidationError(msg)
    try:
        gh_repo = get_github(repo)
        # Resolve the REST integer comment ID to a GraphQL node ID.
        pygithub_issue = gh_repo.get_issue(issue_number)
        pygithub_comment = pygithub_issue.get_comment(comment_id)
        node_id: str = str(pygithub_comment.node_id)
        comment = _fetch_comment_by_id_graphql(gh_repo, node_id)
    except (GithubException, BacklogError) as e:
        msg = f"GitHub API error reading comment: {e}"
        raise BacklogError(msg) from e
    return {
        "id": comment["id"],
        "author": comment["author"],
        "created_at": comment["created_at"],
        "updated_at": comment["updated_at"],
        "body": comment["body"],
        **out.to_dict(),
    }


# ---------------------------------------------------------------------------
# Projects V2 (GraphQL) — TypedDicts for response shapes
# ---------------------------------------------------------------------------


class _ProjectsV2Node(TypedDict):
    id: str
    number: int
    title: str
    url: str
    closed: bool
    shortDescription: NotRequired[str | None]


class _ProjectsV2Data(TypedDict):
    nodes: list[_ProjectsV2Node | None]
    totalCount: int


class _RepositoryOwner(TypedDict):
    projectsV2: _ProjectsV2Data


class _ProjectsV2QueryData(TypedDict):
    repositoryOwner: _RepositoryOwner | None


class _CreatedProjectV2(TypedDict):
    id: str
    number: int
    title: str
    url: str


class _CreateProjectV2Result(TypedDict):
    projectV2: _CreatedProjectV2


class _CreateProjectV2MutationData(TypedDict):
    createProjectV2: _CreateProjectV2Result


class _OwnerIdNode(TypedDict):
    id: str


class _OwnerIdQueryData(TypedDict):
    repositoryOwner: _OwnerIdNode | None


def _parse_projects_v2_node(item: dict[str, object]) -> _ProjectsV2Node:
    """Parse a single raw projectsV2 node dict into a typed _ProjectsV2Node.

    Returns:
        A _ProjectsV2Node with all fields populated; missing or wrongly-typed
        fields fall back to safe defaults.
    """
    node_id = item.get("id")
    node_number = item.get("number")
    node_title = item.get("title")
    node_url = item.get("url")
    node_closed = item.get("closed")
    node_short_desc = item.get("shortDescription")
    return _ProjectsV2Node(
        id=node_id if isinstance(node_id, str) else "",
        number=node_number if isinstance(node_number, int) else 0,
        title=node_title if isinstance(node_title, str) else "",
        url=node_url if isinstance(node_url, str) else "",
        closed=node_closed if isinstance(node_closed, bool) else False,
        shortDescription=node_short_desc if isinstance(node_short_desc, str) else None,
    )


def _parse_projects_v2_data(owner_dict: dict[str, object]) -> _ProjectsV2Data:
    """Parse the projectsV2 sub-dict from a repositoryOwner dict.

    Args:
        owner_dict: The repositoryOwner dict from a projectsV2 GraphQL response.

    Returns:
        A _ProjectsV2Data with nodes and totalCount populated from the dict.
    """
    pv2_val = owner_dict.get("projectsV2")
    pv2_dict: dict[str, object] = {str(k): v for k, v in pv2_val.items()} if isinstance(pv2_val, dict) else {}
    nodes_val = pv2_dict.get("nodes")
    nodes_list: list[object] = list(nodes_val) if isinstance(nodes_val, list) else []
    total_val = pv2_dict.get("totalCount")
    total: int = total_val if isinstance(total_val, int) else 0
    parsed_nodes: list[_ProjectsV2Node | None] = [
        _parse_projects_v2_node({str(k): v for k, v in item.items()}) if isinstance(item, dict) else None
        for item in nodes_list
    ]
    return _ProjectsV2Data(nodes=parsed_nodes, totalCount=total)


def _parse_projects_v2_response(raw: dict[str, object]) -> _ProjectsV2QueryData:
    """Safely construct a typed _ProjectsV2QueryData from a raw GraphQL response dict.

    Args:
        raw: The top-level dict returned by _graphql_request for a projectsV2 query.

    Returns:
        A _ProjectsV2QueryData with all required fields populated; missing or
        wrongly-typed fields from the raw response fall back to safe defaults.
    """
    owner_val = raw.get("repositoryOwner")
    if not isinstance(owner_val, dict):
        return _ProjectsV2QueryData(repositoryOwner=None)
    owner_dict: dict[str, object] = {str(k): v for k, v in owner_val.items()}
    owner: _RepositoryOwner = _RepositoryOwner(projectsV2=_parse_projects_v2_data(owner_dict))
    return _ProjectsV2QueryData(repositoryOwner=owner)


# ---------------------------------------------------------------------------
# Projects V2 (GraphQL)
# ---------------------------------------------------------------------------


def list_projects(
    repo: str = "", owner: str | None = None, limit: int = 20, output: Output | None = None
) -> dict[str, list[dict[str, object]] | int | list[str]]:
    """List Projects V2 for the repository owner via GraphQL.

    Args:
        repo: Repository slug (``owner/name``). Used to resolve owner when
            ``owner`` is ``None``.
        owner: GitHub owner login (org or user). Defaults to repo owner.
        limit: Maximum number of projects to return. Defaults to 20.
        output: Optional Output collector.

    Returns:
        Dict with ``projects`` (list of dicts with ``id``, ``title``,
        ``number``, ``url``, ``closed``, ``short_description``), ``count``
        (int), and output messages/warnings.

    Raises:
        GitHubUnavailableError: If GITHUB_TOKEN is not set or GitHub is unreachable.
        BacklogError: On GraphQL errors or unexpected response structure.
    """
    out = output or Output()
    gh_repo = get_github(repo)
    resolved_owner = owner or gh_repo.owner.login
    query, variables = _projects_v2_list_query(resolved_owner, limit)
    raw_data = _graphql_request(gh_repo, query, variables)
    query_data: _ProjectsV2QueryData = _parse_projects_v2_response(raw_data)
    owner_node: _RepositoryOwner | None = query_data["repositoryOwner"]
    nodes: list[_ProjectsV2Node | None] = owner_node["projectsV2"]["nodes"] if owner_node is not None else []
    projects: list[dict[str, object]] = []
    for node in nodes:
        if node is None:
            continue
        projects.append({
            "id": node["id"],
            "title": node["title"],
            "number": node["number"],
            "url": node["url"],
            "closed": node["closed"],
            "short_description": node.get("shortDescription") or "",
        })
    return {"projects": projects, "count": len(projects), **out.to_dict()}


def _resolve_owner_node_id(gh_repo: Repository, resolved_owner: str) -> str:
    """Resolve a GitHub owner login to its GraphQL node ID.

    Args:
        gh_repo: Authenticated PyGitHub Repository object.
        resolved_owner: GitHub owner login (org or user).

    Returns:
        The GraphQL node ID string for the owner.

    Raises:
        BacklogError: If the owner is not found via GraphQL.
    """
    id_query = "query GetOwnerId($owner: String!) { repositoryOwner(login: $owner) { id } }"
    id_raw = _graphql_request(gh_repo, id_query, {"owner": resolved_owner})
    owner_id_val = id_raw.get("repositoryOwner")
    if not owner_id_val or not isinstance(owner_id_val, dict):
        msg = f"Owner '{resolved_owner}' not found via GraphQL"
        raise BacklogError(msg)
    owner_id_dict: dict[str, object] = {str(k): v for k, v in owner_id_val.items()}
    owner_id_query_data: _OwnerIdQueryData = _OwnerIdQueryData(
        repositoryOwner=_OwnerIdNode(id=str(owner_id_dict.get("id", "")))
    )
    owner_id_node = owner_id_query_data["repositoryOwner"]
    if owner_id_node is None:
        msg = f"Owner '{resolved_owner}' not found via GraphQL"
        raise BacklogError(msg)
    return owner_id_node["id"]


def _create_project_v2_node(gh_repo: Repository, owner_id: str, title: str) -> _CreatedProjectV2:
    """Run the createProjectV2 mutation and return the typed project node.

    Args:
        gh_repo: Authenticated PyGitHub Repository object.
        owner_id: GraphQL node ID of the owner (org or user).
        title: Project title.

    Returns:
        A _CreatedProjectV2 typed dict with id, number, title, and url.

    Raises:
        BacklogError: If the GraphQL response is missing expected fields.
    """
    mutation, variables = _projects_v2_create_mutation(owner_id, title)
    create_raw = _graphql_request(gh_repo, mutation, variables)
    create_pv2_val = create_raw.get("createProjectV2")
    if not create_pv2_val or not isinstance(create_pv2_val, dict):
        msg = f"Unexpected GraphQL response for createProjectV2: {create_raw!r}"
        raise BacklogError(msg)
    create_pv2_dict: dict[str, object] = {str(k): v for k, v in create_pv2_val.items()}
    project_node_val = create_pv2_dict.get("projectV2")
    if not project_node_val or not isinstance(project_node_val, dict):
        msg = f"Unexpected GraphQL response for createProjectV2: {create_raw!r}"
        raise BacklogError(msg)
    project_node_dict: dict[str, object] = {str(k): v for k, v in project_node_val.items()}
    pn_number = project_node_dict.get("number")
    created_pv2: _CreatedProjectV2 = _CreatedProjectV2(
        id=str(project_node_dict.get("id", "")),
        number=pn_number if isinstance(pn_number, int) else 0,
        title=str(project_node_dict.get("title", "")),
        url=str(project_node_dict.get("url", "")),
    )
    return _CreateProjectV2MutationData(createProjectV2=_CreateProjectV2Result(projectV2=created_pv2))[
        "createProjectV2"
    ]["projectV2"]


def create_project(
    repo: str = "", title: str = "", owner: str | None = None, output: Output | None = None
) -> dict[str, str | int | list[str]]:
    """Create a Projects V2 project under the repository owner via GraphQL.

    Resolves the owner's GraphQL node ID first, then runs the
    ``createProjectV2`` mutation.

    Args:
        repo: Repository slug (``owner/name``). Used to resolve owner when
            ``owner`` is ``None``.
        title: Project title. Must not be empty.
        owner: GitHub owner login. Defaults to repo owner.
        output: Optional Output collector.

    Returns:
        Dict with ``project_id`` (str), ``title`` (str), ``url`` (str),
        ``number`` (int), and output messages/warnings.

    Raises:
        ValidationError: If ``title`` is empty.
        GitHubUnavailableError: If GITHUB_TOKEN is not set or GitHub is unreachable.
        BacklogError: On GraphQL errors or unexpected response structure.
    """
    out = output or Output()
    if not title.strip():
        msg = "title must not be empty"
        raise ValidationError(msg)
    gh_repo = get_github(repo)
    resolved_owner = owner or gh_repo.owner.login
    owner_id = _resolve_owner_node_id(gh_repo, resolved_owner)
    project_node = _create_project_v2_node(gh_repo, owner_id, title)
    out.info(f"  Created project '{project_node['title']}' (#{project_node['number']})")
    return {
        "project_id": project_node["id"],
        "title": project_node["title"],
        "url": project_node["url"],
        "number": project_node["number"],
        **out.to_dict(),
    }


# ---------------------------------------------------------------------------
# Impact Radius conflict analysis (pure — no GitHub calls)
# ---------------------------------------------------------------------------


class _UnionFind:
    """Path-compressed union-find with union-by-rank (disjoint set union) for integer indices."""

    def __init__(self, n: int) -> None:
        self._parent = list(range(n))
        self._rank = [0] * n

    def find(self, x: int) -> int:
        """Return canonical root of x with path compression."""
        while self._parent[x] != x:
            self._parent[x] = self._parent[self._parent[x]]
            x = self._parent[x]
        return x

    def union(self, x: int, y: int) -> None:
        """Merge the sets containing x and y using union-by-rank."""
        rx, ry = self.find(x), self.find(y)
        if rx == ry:
            return
        if self._rank[rx] < self._rank[ry]:
            rx, ry = ry, rx
        self._parent[ry] = rx
        if self._rank[rx] == self._rank[ry]:
            self._rank[rx] += 1


def _parse_impact_radius_paths(impact_radius: str) -> set[str]:
    """Extract normalised file paths from an Impact Radius markdown body.

    Args:
        impact_radius: Raw markdown section body (may contain bullet markers,
            blank lines, or section headers).

    Returns:
        Set of stripped file-path strings. Empty set when the body is blank
        or contains only headers/whitespace.
    """
    paths: set[str] = set()
    for raw_line in impact_radius.splitlines():
        # Strip bullet markers (-, *) and surrounding whitespace
        line = raw_line.strip().lstrip("-*").strip()
        # Discard empty lines and pure markdown headers
        if not line or line.startswith("#"):
            continue
        paths.add(line)
    return paths


def _collect_items_with_paths(items: list[ImpactRadiusItem]) -> tuple[list[str], list[set[str]]]:
    """Filter items to those with a non-empty impact_radius and parse their paths.

    Args:
        items: Raw item dicts.

    Returns:
        Tuple of (titles, path_sets) for items that have parsable paths.
    """
    titles: list[str] = []
    path_sets: list[set[str]] = []
    for item in items:
        radius_raw = item.get("impact_radius", "")
        if not isinstance(radius_raw, str) or not radius_raw.strip():
            continue
        paths = _parse_impact_radius_paths(radius_raw)
        if not paths:
            continue
        titles.append(str(item.get("title", "")))
        path_sets.append(paths)
    return titles, path_sets


def _build_conflict_groups(titles: list[str], path_sets: list[set[str]]) -> list[ConflictGroup]:
    """Run union-find over path_sets and return ConflictGroup models.

    Args:
        titles: Item title per index (parallel to path_sets).
        path_sets: Parsed file-path sets per index.

    Returns:
        List of ConflictGroup models for connected components with two or more
        members.
    """
    n = len(titles)
    uf = _UnionFind(n)

    # Union pairs sharing at least one file path
    for i in range(n):
        for j in range(i + 1, n):
            if path_sets[i] & path_sets[j]:
                uf.union(i, j)

    # Collect connected components
    components: dict[int, list[int]] = defaultdict(list)
    for i in range(n):
        components[uf.find(i)].append(i)

    # Gather shared paths per group root
    group_shared: dict[int, set[str]] = defaultdict(set)
    for i in range(n):
        for j in range(i + 1, n):
            overlap = path_sets[i] & path_sets[j]
            if overlap and uf.find(i) == uf.find(j):
                group_shared[uf.find(i)].update(overlap)

    # Build ConflictGroup models in stable order
    conflict_groups: list[ConflictGroup] = []
    group_id = 1
    for root in sorted(components):
        members = components[root]
        if len(members) < MIN_CONFLICT_GROUP_SIZE:
            continue
        member_titles = sorted(titles[i] for i in members)
        shared = group_shared.get(root, set())
        reason = "Shared files: " + ", ".join(sorted(shared))
        conflict_groups.append(ConflictGroup(group_id=group_id, reason=reason, items=member_titles))
        group_id += 1

    return conflict_groups


class ImpactRadiusItem(TypedDict, total=False):
    """Typed structure for items passed to :func:`analyze_impact_radius_conflicts`.

    Attributes:
        title: Item title used in ConflictGroup.items list.
        issue: GitHub issue number (present but unused in conflict output).
        impact_radius: Markdown section body containing file paths, one per
            line, optionally prefixed with bullet markers (``-`` / ``*``).
            Items without this key, or with an empty/whitespace-only value,
            are excluded from conflict analysis.
    """

    title: str
    issue: int
    impact_radius: str


def analyze_impact_radius_conflicts(items: list[ImpactRadiusItem]) -> list[ConflictGroup]:
    """Compute conflict groups from Impact Radius file-path overlap.

    Each item dict must contain:

    - ``"title"`` (str): item title used in ConflictGroup.items list.
    - ``"issue"`` (int): issue number (unused in output but validates input).
    - ``"impact_radius"`` (str): markdown section body containing file paths,
      one per line, optionally with bullet markers (``-`` / ``*``).

    Two items form a conflict group when they share any file path (exact
    string match after stripping whitespace and bullet markers).

    Items with no ``impact_radius`` key or an empty value are excluded from
    conflict analysis — they conflict with nothing.

    When three or more items overlap pairwise, they are merged into a
    single conflict group using union-find.  Example: if A overlaps B and
    B overlaps C but A and C share no paths, all three are in one group.

    Args:
        items: Pre-fetched backlog item dicts with Impact Radius content.
            Makes no GitHub calls.

    Returns:
        List of :class:`~dispatch_schema.core.models.ConflictGroup` models,
        one per connected component with two or more members.  Items with no
        file overlap are not included.  Returns an empty list when no
        conflicts are found.
    """
    titles, path_sets = _collect_items_with_paths(items)
    if len(titles) < MIN_CONFLICT_GROUP_SIZE:
        return []
    return _build_conflict_groups(titles, path_sets)
