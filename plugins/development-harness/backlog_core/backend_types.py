"""Backend-agnostic contracts for backlog implementations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, Protocol, TypedDict, runtime_checkable

from pydantic import BaseModel, ConfigDict

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
        MergeResult,
        Output,
        ProviderSnapshot,
        PullRequestRef,
        ReconcileRequest,
        ReconcileResult,
        SamTask,
        StatusFetchResult,
        ViewEnrichmentResult,
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


class IssueCommentNode(BaseModel):
    """Comment node returned from issue comments listing query.

    ``id`` is GitHub's GraphQL node ID (``IC_kwDO...``). REST addresses the same
    comment by its numeric identifier instead, which GraphQL exposes as
    ``fullDatabaseId`` and is carried here as ``database_id``. Both are needed
    together: a node that arrives over GraphQL cannot otherwise be read or
    written over REST.

    ``fullDatabaseId`` (GitHub's ``BigInt`` scalar) is what the GraphQL
    queries select, not the sibling ``databaseId: Int`` field: real comment
    database IDs already exceed the signed 32-bit range ``Int`` caps out at,
    and GitHub serializes ``BigInt`` as a decimal string on the wire (a JSON
    integer is also tolerated) — see
    https://docs.github.com/en/graphql/reference/scalars#bigint. The parser
    that populates this field (``gh_client._parse_full_database_id``)
    normalizes both encodings to a Python ``int`` before construction.

    ``database_id`` is optional because only GitHub has one. The SQLite and
    memory backends address their comments by ``id`` alone, and supplying a
    number there would invent an identifier that resolves to nothing.

    A validated, immutable wire-data record — ``strict=True`` rejects a
    non-``int`` ``database_id`` (including ``bool``, which subclasses ``int``
    in Python and would otherwise coerce ``True`` into comment ``1``) instead
    of silently coercing it, matching ``WorkItemHead``/``WorkItemVersion`` in
    ``backends/_github_work_item_versions.py``.
    """

    model_config = ConfigDict(frozen=True, strict=True)

    id: str
    body: str
    url: str
    author: str
    created_at: str
    updated_at: str
    database_id: int | None = None


class AddedCommentNode(BaseModel):
    """Result of creating a comment via the ``addComment`` mutation.

    ``id`` is GitHub's GraphQL node ID for the newly created comment.
    ``database_id`` is the REST integer ID (the mutation's ``fullDatabaseId``
    selection, normalized the same way as ``IssueCommentNode.database_id`` --
    see that model's docstring for the ``BigInt`` wire encoding) that
    ``backlog_read_comment``'s ``comment_id`` requires. It achieves the same
    create/list/read identifier symmetry ``IssueCommentNode.database_id``
    already provides for the listing and single-comment paths.

    ``database_id`` is optional for the same reason as
    ``IssueCommentNode.database_id``: only GitHub-backed comments carry a
    REST integer ID -- the SQLite and in-memory backends invent no such
    value for a comment they created themselves.
    """

    model_config = ConfigDict(frozen=True, strict=True)

    id: str
    database_id: int | None = None


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
      satisfy the ``int`` signature below — see ``BeadsBackend``'s ADR-003).
    - ``supports_cached_listing`` — whether :meth:`list_work_items` reads a
      provider-private cache (``True``, GitHub only) rather than the
      backend's own authoritative storage directly (``False`` — sqlite,
      memory, beads). Read by ``operations.list_items`` (backlog #3546 task
      A4) to compute the ``from_cache`` provenance bit on every listing
      response — a cache-backed listing can lag the provider; a
      backend-owned one cannot. ``has_pending_writes()`` below is the
      companion fact and deliberately a separate bit (critique ALT-4,
      Firestore's ``fromCache``/``hasPendingWrites``): a fully-synced cache
      can still hold locally-queued mutations the provider has not
      acknowledged, and collapsing both facts into one boolean would report
      such a listing as unqualified-confident when a third of its rows are
      local-only.
    """

    supports_batch_status_fetch: bool
    supports_batch_issue_update: bool
    issue_id_type: Literal["integer", "string"]
    supports_branches: bool
    supports_github_extras: bool
    supports_milestones: bool
    supports_cached_listing: bool

    def list_work_items(self) -> list[BacklogItem]: ...
    def get_work_item(self, reference: str) -> BacklogItem: ...
    def put_work_item(self, item: BacklogItem) -> None: ...
    def has_pending_writes(self) -> bool:
        """Report whether the most recent listing includes locally-queued mutations.

        Every backend defines this directly (like the milestone methods
        above), always ``False`` for a backend that writes straight to its
        own authoritative storage with no separate offline queue (sqlite,
        memory, beads — see each backend's flags block). GitHub is the one
        backend where this can be ``True``: ``put_work_item`` durably queues
        an intent that ``list_work_items`` overlays onto the cached snapshot
        before the provider has acknowledged it (backlog #3546 task A4).
        """
        ...

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
    def batch_fetch_statuses(self, items: list[BacklogItem], repo: str = "") -> StatusFetchResult: ...
    def fetch_item_status(self, item: BacklogItem, repo: str = "", output: Output | None = None) -> str: ...
    def view_enrich_from_github(
        self, result: ViewItemResult, issue_num: str, repo: str = ""
    ) -> ViewEnrichmentResult: ...
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

    def reconcile(self, request: ReconcileRequest, *, snapshot: ProviderSnapshot | None = None) -> ReconcileResult: ...


@runtime_checkable
class SnapshotCheckpointProvider(Protocol):
    """Optional capability: report whether a cache has ever completed a sync.

    Deliberately a separate protocol rather than a second method on
    :class:`SyncProvider`: a backend can implement ``reconcile`` (to satisfy
    ``SyncProvider`` structurally, e.g. a test double whose ``reconcile`` is
    never meant to be invoked) without exposing checkpoint state at all.
    Folding this into ``SyncProvider`` would make every existing
    ``isinstance(x, SyncProvider)`` gate in this codebase (the
    never-synced-cache warning in ``operations.list_items`` among them) also
    require this method, silently changing their behaviour for any backend
    or test double that does not implement it. Callers that want the
    one-shot cold-cache read-through in ``operations.list_items`` gate on
    *both* protocols.
    """

    def has_synced_snapshot(self) -> bool: ...


@runtime_checkable
class SnapshotCompletenessProvider(Protocol):
    """Optional capability: report whether the last snapshot load skipped any file.

    Deliberately a separate protocol from :class:`SnapshotCheckpointProvider`,
    for the same reason that one is deliberately separate from
    :class:`SyncProvider` (see its docstring): folding ``has_skipped_snapshots``
    into ``SnapshotCheckpointProvider`` would require every existing
    ``isinstance(x, SnapshotCheckpointProvider)`` gate — including the
    read-through-once check in ``operations.list_items`` (backlog #3546 task
    A3) — to also implement this method, silently disabling that check for
    any backend or test double that does not.

    A warm ``snapshot_checkpoint`` only records that a reconcile ran, never
    that the item files it produced are still readable
    (``WorkItemSnapshotBatch.skipped``, backlog #3546 task A2): a cache whose
    files were truncated, restored from a partial backup, or otherwise made
    unreadable keeps its checkpoint but silently returns a partial snapshot
    set. ``operations.list_items`` (task A4) gates its fail-safe provenance
    check on *both* this protocol and ``SnapshotCheckpointProvider``
    independently, exactly as the docstring above prescribes for the
    checkpoint/sync pairing.
    """

    def has_skipped_snapshots(self) -> bool: ...


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
    def fetch_snapshot(self, request: ReconcileRequest) -> ProviderSnapshot: ...
    def pending_work_items(self, repo: str = "") -> list[BacklogItem]: ...

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
    def resolve_issue_body(self, repo: Repository, owner: str, repo_name: str, issue: IssueNode) -> str: ...

    # Issue comments (GraphQL)
    def _add_comment_graphql(self, repo: Repository, issue_node_id: str, body: str) -> AddedCommentNode: ...
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
