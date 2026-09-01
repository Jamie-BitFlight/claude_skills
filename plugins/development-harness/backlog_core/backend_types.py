"""Backend-agnostic contracts for backlog implementations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, Protocol, TypedDict, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import datetime

    from github.Repository import Repository

    from .models import (
        BackendStatus,
        BacklogItem,
        BranchInfo,
        ContentQuery,
        ContentRecord,
        ContentRef,
        ContentWrite,
        GroomedData,
        IssueLocalFields,
        IssueStatus,
        MergeResult,
        Output,
        PullRequestRef,
        ReconcileRequest,
        ReconcileResult,
        SamTask,
        ViewItemResult,
    )


class LabelNode(TypedDict):
    """Label node from GraphQL response."""

    id: str
    name: str


class MilestoneNode(TypedDict):
    """Milestone node nested inside an IssueNode.

    ``state`` is a backend-neutral open/closed flag, not a GitHub-only value
    set — every backend collapses its own milestone lifecycle onto these two
    values at the backend boundary.
    """

    id: str
    number: int
    title: str
    dueOn: str | None
    state: Literal["OPEN", "CLOSED"]


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
# Layered protocol subsets (T-P6-PROTOCOL)
#
# The surface is partitioned into ``WorkItemBackend`` (generic, mandatory),
# ``GitHubExtras`` (GitHub/GraphQL-only, optional), and ``BranchBackend``
# (Git branch operations, optional).  A non-GitHub backend implements only
# ``WorkItemBackend`` plus any optional protocol it opts into, satisfying
# PURPOSE.md:74-75 ("Adding a provider must change only provider
# implementation, registration, and configuration").
#
# The monolithic ``BacklogBackend`` Protocol that previously bundled all 46
# methods has been removed; call sites use ``WorkItemBackend`` (and
# ``GitHubExtras`` / ``BranchBackend`` where appropriate).
# ---------------------------------------------------------------------------


@runtime_checkable
class WorkItemBackend(Protocol):
    """Generic work-item surface every backend must implement.

    Methods take and return logical objects (or existing types tolerated as
    generic during migration).  No ``PyGithub.Repository`` parameter, no
    GraphQL-only primitives, no GitHub issue-number return type on the generic
    create path.  ``IssueNode`` remains the return type of
    ``_fetch_issue_graphql`` on ``GitHubExtras``; the generic surface uses
    ``BacklogItem`` / ``IssueLocalFields`` which are already backend-neutral.

    Capability flags (read by ``operations.py`` to avoid ``isinstance``):

    - ``supports_batch_status_fetch`` — batch status fetch implemented.
    - ``supports_batch_issue_update`` — batch GraphQL update implemented.
    - ``issue_id_type`` — integer vs string issue IDs.
    - ``supports_branches`` — whether ``BranchBackend`` is implemented.
    - ``supports_github_extras`` — whether ``GitHubExtras`` is implemented; gate via ``require_github_extras()`` (see ``GitHubExtras``'s docstring for why ``isinstance`` alone is insufficient).
    - ``supports_milestones`` — whether the milestone create/list/assign
      methods below are genuinely implemented; gate via
      ``require_milestone_support()`` in ``_capability_gates.py``. Unlike
      ``supports_branches``/``supports_github_extras`` this is not a
      separate optional Protocol — the methods live directly on
      ``WorkItemBackend`` and every backend must define them (raising
      ``NotImplementedError`` and setting the flag ``False`` is the
      documented escape hatch for a backend whose native ID type cannot
      satisfy the ``int`` signature below — see ``BeadsBackend``'s ADR-002).
    """

    supports_batch_status_fetch: bool
    supports_batch_issue_update: bool
    issue_id_type: Literal["integer", "string"]
    supports_branches: bool
    supports_github_extras: bool
    supports_milestones: bool

    def list_work_items(self) -> list[BacklogItem]: ...
    def get_work_item(self, reference: str) -> BacklogItem: ...
    def put_work_item(self, item: BacklogItem) -> None: ...

    # Repository access (generic subset)
    def try_get_github(self, repo: str = "") -> Repository | None: ...
    def probe_backend_status(self, repo: str = "") -> BackendStatus: ...

    # Issue CRUD (generic subset)
    def create_issue_for_item(
        self, repo: Repository, item: BacklogItem, dry_run: bool = False, output: Output | None = None
    ) -> int | None: ...
    def close_github_issue(
        self,
        issue_ref: str,
        reason: str,
        *,
        reference: str = "",
        comment: str = "",
        repo: str = "",
        output: Output | None = None,
    ) -> None: ...
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
    ) -> None: ...
    def fetch_open_issues_by_title(self, repo: Repository) -> dict[str, int]: ...
    def fetch_github_issue_body(
        self, repo_obj: Repository, issue_num: int, output: Output | None = None
    ) -> str | None: ...
    def check_open_prs_for_issue(self, issue_num: int, repo: str = "") -> list[PullRequestRef]: ...
    def batch_fetch_statuses(self, items: list[BacklogItem], repo: str = "") -> dict[int, IssueStatus]: ...
    def fetch_item_status(self, item: BacklogItem, repo: str = "", output: Output | None = None) -> str: ...
    def view_enrich_from_github(self, result: ViewItemResult, issue_num: str, repo: str = "") -> bool: ...
    def issue_to_local_fields(self, issue: IssueNode) -> IssueLocalFields: ...

    # Status mutations (generic — BeadsBackend really implements these)
    def apply_status_in_progress(self, item: BacklogItem, repo: str = "", output: Output | None = None) -> None: ...
    def apply_status_verified(self, item: BacklogItem, repo: str = "", output: Output | None = None) -> None: ...
    def apply_status_groomed(self, item: BacklogItem, repo: str = "", output: Output | None = None) -> None: ...
    def apply_status_blocked(self, item: BacklogItem, repo: str = "", output: Output | None = None) -> None: ...

    # Sync / serialisation (generic)
    def render_issue_body(self, item: BacklogItem, original_body: str | None = None) -> str: ...
    def parse_issue_body(self, body: str, existing: BacklogItem | None = None) -> BacklogItem: ...
    def merge_item(self, local: BacklogItem, remote: BacklogItem) -> BacklogItem: ...
    def unknown_key_to_heading(self, key: str) -> str: ...
    @property
    def section_heading(self) -> dict[str, str]: ...
    def render_groomed_section(self, groomed: GroomedData) -> str: ...
    def section_display_title(self, key: str, groomed_date: str = "") -> str: ...

    # Milestones (generic — gate via require_milestone_support())
    def list_milestones(self, states: list[str] | None = None, repo: str = "") -> list[MilestoneFullNode]: ...
    def create_milestone(
        self, title: str, description: str = "", due_on: datetime | None = None, repo: str = ""
    ) -> MilestoneFullNode: ...
    def assign_item_to_milestone(self, issue_number: int, milestone_number: int, repo: str = "") -> None: ...


@runtime_checkable
class SyncProvider(Protocol):
    """Optional one-method reconciliation capability for remote backends."""

    def reconcile(self, request: ReconcileRequest) -> ReconcileResult: ...


@runtime_checkable
class ContentProvider(Protocol):
    """Optional logical plan and artifact content capability."""

    def list_content(self, query: ContentQuery) -> list[ContentRecord]: ...
    def get_content(self, reference: ContentRef) -> ContentRecord: ...
    def put_content(self, request: ContentWrite) -> ContentRecord: ...


@runtime_checkable
class GitHubExtras(Protocol):
    """GitHub-specific surface only ``GitHubBackend`` implements.

    Backends that are not GitHub-backed are NOT required to implement this
    protocol. ``GitHubExtras`` is ``runtime_checkable``, which means
    ``isinstance(backend, GitHubExtras)`` checks attribute *names* only —
    ``SQLiteBackend`` and ``InMemoryBackend`` implement all of these methods
    as local simulations and therefore satisfy ``isinstance`` structurally,
    even though neither can return a real ``Repository``.

    Callers MUST gate on the ``supports_github_extras`` capability flag
    first — via ``require_github_extras()`` in ``_capability_gates.py`` —
    and treat ``isinstance(backend, GitHubExtras)`` only as a secondary
    assertion after that flag check passes. Gating on ``isinstance`` alone
    is a defect: it lets non-GitHub backends pass the gate and reach a
    bare ``RuntimeError`` stub instead of a typed
    ``UnsupportedBackendCapabilityError``.
    """

    # Repository access (GitHub-only)
    def get_github(self, repo: str = "", timeout: int = 15) -> Repository: ...

    # GraphQL utilities
    def _graphql_request(
        self, repo: Repository, query: str, variables: dict[str, object] | None = None
    ) -> dict[str, Any]: ...
    def _resolve_labels_graphql(
        self, repo: Repository, repo_owner: str, repo_name: str, label_names: list[str]
    ) -> list[str]: ...

    # Issue CRUD (GraphQL fetch/update)
    def _fetch_issue_graphql(self, repo: Repository, owner: str, repo_name: str, issue_number: int) -> IssueNode: ...
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
    ) -> list[IssueNode]: ...
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
    ) -> None: ...
    def _update_issues_graphql_batch(self, repo: Repository, updates: list[tuple[str, str]]) -> None: ...
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
    ) -> list[IssueNode]: ...

    # Issue comments (GraphQL)
    def _add_comment_graphql(self, repo: Repository, issue_node_id: str, body: str) -> str: ...
    def _fetch_issue_comments_graphql(
        self, repo: Repository, owner: str, repo_name: str, issue_number: int
    ) -> list[IssueCommentNode]: ...
    def _fetch_comment_by_id_graphql(self, repo: Repository, comment_node_id: str) -> IssueCommentNode: ...
    def _update_issue_comment_graphql(self, repo: Repository, comment_node_id: str, body: str) -> None: ...

    # Status sync to GitHub (GitHub-only — the local YAML path is generic)
    def sync_groomed_to_github_issue(
        self,
        repo_obj: Repository,
        issue_num: int,
        groomed_content: str,
        section_name: str | None = None,
        output: Output | None = None,
    ) -> bool: ...

    # Milestones / projects (GitHub-only)
    def _fetch_milestones_graphql(
        self, repo: Repository, owner: str, repo_name: str, states: list[str] | None = None
    ) -> list[MilestoneFullNode]: ...
    def _projects_v2_list_query(self, owner: str, limit: int = 20) -> tuple[str, dict[str, object]]: ...
    def _projects_v2_create_mutation(self, owner_id: str, title: str) -> tuple[str, dict[str, object]]: ...

    # Task issues (GitHub sub-issue bridge)
    def create_task_issue(
        self,
        repo: Repository,
        parent_issue_number: int,
        task: SamTask,
        description: str = "",
        acceptance_criteria: list[str] | None = None,
        labels: list[str] | None = None,
        output: Output | None = None,
    ) -> IssueNode | None: ...
    def get_task_issues(
        self, repo: Repository, parent_issue_number: int, output: Output | None = None
    ) -> list[IssueNode]: ...
    def update_task_status(
        self, repo: Repository, issue_number: int, new_status: str, output: Output | None = None
    ) -> bool: ...


@runtime_checkable
class BranchBackend(Protocol):
    """Optional Git branch-operation surface.

    Backends that do not support Git branch operations set
    ``supports_branches = False`` and are NOT required to implement this
    protocol. ``BranchBackend`` is ``runtime_checkable``, which means
    ``isinstance(backend, BranchBackend)`` checks attribute names only, so
    callers MUST gate on the ``supports_branches`` flag first — via
    ``require_branch_support()`` in ``_capability_gates.py`` — and must not
    rely on catching :exc:`RuntimeError` from a stub; the gate raises
    ``UnsupportedBackendCapabilityError`` instead.
    """

    def create_integration_branch(
        self,
        milestone_number: int,
        slug: str,
        *,
        base_branch: str = "main",
        repo: str = "",
        output: Output | None = None,
    ) -> BranchInfo: ...
    def get_integration_branch_status(
        self, branch_name: str, *, repo: str = "", output: Output | None = None
    ) -> BranchInfo | None: ...
    def merge_integration_branch(
        self, head_branch: str, base_branch: str, commit_message: str, *, repo: str = "", output: Output | None = None
    ) -> MergeResult: ...
    def delete_integration_branch(self, branch_name: str, *, repo: str = "", output: Output | None = None) -> bool: ...
    def list_integration_branches(self, *, repo: str = "", output: Output | None = None) -> list[BranchInfo]: ...


@dataclass
class BacklogConfig:
    """Container for the active backend instance.

    This dataclass replaces direct imports from gh_client, github_sync, and
    github_branches.  Pass a BacklogConfig to operations and server functions
    so they can work against any conforming backend.

    Attributes:
        backend: The active ``WorkItemBackend`` implementation.
    """

    backend: WorkItemBackend
