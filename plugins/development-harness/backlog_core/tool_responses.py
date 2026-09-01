"""Shared Pydantic response models for the ``backlog_core`` MCP tool boundary.

FastMCP derives each tool's advertised ``outputSchema`` from the function's
return-type annotation via ``pydantic.TypeAdapter(...).json_schema()``. A bare
``dict[str, object]`` erases to an unconstrained object schema, so MCP clients
cannot see what fields a tool actually returns. Every ``@mcp.tool`` function
must return a flat Pydantic model shape instead -- never a ``Union`` of
models, which FastMCP's schema introspection does not recognise and silently
wraps the result (``x-fastmcp-wrap-result``), a wire-protocol change.

Most tools build a response model and return
``response.model_dump(exclude_none=True)`` (a plain dict), not the model
instance itself -- ``convert_result()`` serialises either identically, and
returning a dict keeps existing runtime assertions (e.g.
``"error" not in response``) unchanged when a field is conditionally absent.
The exception is a tool with no ``exclude_none=True`` at its call site (every
field unconditionally present, nothing to drop) -- see ``sync_status``/
``sync_now`` below -- where returning the model instance directly is
wire-identical and keeps the declared return type accurate for in-process
callers too.

FastMCP enforces a tool's advertised ``outputSchema`` at call time (verified
empirically, not just documented): a returned payload missing a property the
schema lists under ``required`` fails the call with "Output validation
error: 'x' is a required property" -- this is a hard runtime error, not a
lint-only concern. So for any tool whose except-arm reports a shaped error
without the full success payload (e.g. a ``BacklogError`` catch, or a "not
found" branch), every field the success arm doesn't unconditionally supply
must be declared ``X | None = None`` (moving it out of the schema's
``required`` list) rather than left required -- see
:class:`ArtifactRegisterResponse` for the pattern. Build both arms with the
normal validating constructor; the optional fields simply default to
``None`` and get dropped by ``exclude_none=True`` on the error arm.

This module is intentionally separate from ``models.py`` (1800+ lines of
domain models): these types exist only to shape the MCP wire boundary.
"""

from __future__ import annotations

from typing import Literal

from dispatch_schema import ConflictGroup
from pydantic import BaseModel

from .models import DispatchSpawnSummary, DispatchWaveSummary, Output, RegisterResult

__all__ = [
    "AccumulatedUsage",
    "ArtifactEntryOut",
    "ArtifactReadResponse",
    "ArtifactRegisterResponse",
    "ArtifactsListResponse",
    "BacklogAddResponse",
    "BacklogAssignItemToMilestoneResponse",
    "BacklogCloseResponse",
    "BacklogCommentIssueResponse",
    "BacklogCreateMilestoneResponse",
    "BacklogCreateProjectResponse",
    "BacklogCreateSamTaskResponse",
    "BacklogGetReadySamTasksResponse",
    "BacklogGetSoonestMilestoneResponse",
    "BacklogGroomResponse",
    "BacklogLinkFollowupResponse",
    "BacklogListCommentsResponse",
    "BacklogListFollowupsResponse",
    "BacklogListIssuesResponse",
    "BacklogListLabelsResponse",
    "BacklogListMergedPrsResponse",
    "BacklogListMilestonesResponse",
    "BacklogListProjectsResponse",
    "BacklogListResponse",
    "BacklogNormalizeResponse",
    "BacklogPullResponse",
    "BacklogReadCommentResponse",
    "BacklogResolveResponse",
    "BacklogStrikeEntryResponse",
    "BacklogSyncResponse",
    "BacklogUpdateResponse",
    "BacklogUpdateSamTaskStatusResponse",
    "CommentEntry",
    "DispatchConflictsResponse",
    "DispatchCreatePlanResponse",
    "DispatchItemStatusResponse",
    "DispatchReadResponse",
    "DispatchSpawnResponse",
    "DispatchStaleCheckResponse",
    "DispatchValidateResponse",
    "DispatchWaveStartResponse",
    "DispatchWaveStatusResponse",
    "FallibleToolResponse",
    "FollowupItem",
    "IssueEntry",
    "LabelEntry",
    "MergedPullRequestEntry",
    "Milestone",
    "MilestoneEchoError",
    "ProjectEntry",
    "SamTaskLookupResult",
    "SamTaskRow",
    "SyncNowResponse",
    "SyncStatusResponse",
    "ToolResponse",
    "WaveEchoError",
]


class ToolResponse(Output):
    """Base for MCP tool responses. Inherits messages/warnings/errors from Output."""


class FallibleToolResponse(ToolResponse):
    """Base for tool responses whose except-BacklogError arm returns a shaped error."""

    error: str | None = None
    """Error message set when the operation failed; ``None`` on success."""


# Mixes in RegisterResult's domain fields rather than redeclaring them, so
# the wire shape and the domain result computed by artifact_register's
# _run() closure cannot drift apart. Its BacklogError arm never has a
# RegisterResult to report, so those four fields are widened to optional
# here (dropped by exclude_none=True on that arm) without touching
# RegisterResult itself, which stays required for every other caller.
# Docstring kept to one line -- see BacklogListResponse's design note on
# the total outputSchema token budget.
class ArtifactRegisterResponse(RegisterResult, FallibleToolResponse):
    """Response for ``artifact_register``."""

    registered: bool | None = None
    artifact_count: int | None = None
    action: Literal["added", "updated"] | None = None
    content_stored: bool | None = None


class Milestone(BaseModel):
    """A single milestone as returned by milestone-listing MCP tools."""

    number: int
    """Milestone number."""

    title: str
    """Milestone title."""

    state: str
    """Milestone state, e.g. ``open`` or ``closed``."""

    description: str
    """Milestone description."""

    due_on: str | None = None
    """ISO 8601 due date, or ``None`` when unset."""

    open_issues: int
    """Count of open issues attached to this milestone."""

    closed_issues: int
    """Count of closed issues attached to this milestone."""


# Mirrors backlog_core.models.ArtifactEntry's model_dump(mode="json") shape --
# string fields correspond to that model's enum fields (ArtifactType,
# ArtifactStatus) serialised to their string values.
class ArtifactEntryOut(BaseModel):
    """One artifact manifest entry, as returned by artifact-listing MCP tools."""

    artifact_type: str
    artifact_id: str
    status: str
    created_at: str
    agent: str
    content_revision: str
    storage_tier: Literal["local", "remote"]


# Shared by artifact_list and artifact_get. Both have a BacklogError arm
# (artifact_get also treats "type not found"/"id not found" as BacklogError,
# per its docstring) that returns only error plus the Output triad, so
# artifacts/count are widened to optional.
class ArtifactsListResponse(FallibleToolResponse):
    """Response for ``artifact_list``/``artifact_get``."""

    artifacts: list[ArtifactEntryOut] | None = None
    """Registered artifact entries matching the request. Absent on the error arm."""

    count: int | None = None
    """Total number of artifacts returned; ``0`` alongside an empty ``artifacts``. Absent on the error arm."""


# Mirrors ArtifactContent's model_dump(mode="json") shape. Its
# BacklogError arm (raised for "type not found" and "id not found") never
# has content to report, so every field is widened to optional.
class ArtifactReadResponse(FallibleToolResponse):
    """Response for ``artifact_read``."""

    artifact_type: str | None = None
    """Category of the returned artifact."""

    path: str | None = None
    """Repo-relative path (or logical artifact id) that was read."""

    content: str | None = None
    """Raw artifact content."""

    status: str | None = None
    """Lifecycle state of the artifact."""


# Its BacklogError arm never has an operations.add_item result to report,
# so every field is widened to optional.
class BacklogAddResponse(FallibleToolResponse):
    """Response for ``backlog_add``."""

    title: str | None = None
    """Item title as stored."""

    priority: str | None = None
    """Priority level applied to the item."""

    reference: str | None = None
    """Logical reference for the created item."""

    file_path: str | None = None
    """Compatibility alias for ``reference`` -- for display only."""

    item_ref: str | None = None
    """Backend issue ref, or ``""`` when creation failed or was skipped."""


class BacklogAssignItemToMilestoneResponse(FallibleToolResponse):
    """Response for ``backlog_assign_item_to_milestone``."""

    issue_number: int | None = None
    """Issue number that was assigned. Absent only on the ``BacklogError`` arm."""

    milestone_number: int | None = None
    """Milestone number the issue was assigned to. Absent only on the ``BacklogError`` arm."""


# operations.close_item has two distinct success shapes: an already-closed
# early return (title, already_closed) and a normal close (title, closed,
# reason). Both are optional here besides title because the BacklogError
# arm supplies neither.
class BacklogCloseResponse(FallibleToolResponse):
    """Response for ``backlog_close``."""

    title: str | None = None
    """Title of the item that was closed (or already closed)."""

    closed: bool | None = None
    """``True`` when this call performed the close."""

    already_closed: bool | None = None
    """``True`` when the item was already closed before this call."""

    reason: str | None = None
    """Close reason, present only on the normal (non-already-closed) path."""


class BacklogCommentIssueResponse(FallibleToolResponse):
    """Response for ``backlog_comment_issue``."""

    issue_number: int | None = None
    """GitHub issue number the comment was added to."""

    comment_id: str | None = None
    """GraphQL node ID of the newly created comment -- not a REST integer ID."""

    comment_url: str | None = None
    """Always ``""`` -- the backend does not resolve a comment URL."""


class BacklogCreateMilestoneResponse(FallibleToolResponse):
    """Response for ``backlog_create_milestone``."""

    milestone: Milestone | None = None
    """The created milestone. Absent only on the ``BacklogError`` arm."""


class BacklogCreateProjectResponse(FallibleToolResponse):
    """Response for ``backlog_create_project``."""

    project_id: str | None = None
    """GraphQL node ID of the created Projects V2 project."""

    title: str | None = None
    """Project title."""

    url: str | None = None
    """Project URL."""

    number: int | None = None
    """Project number."""


class BacklogCreateSamTaskResponse(FallibleToolResponse):
    """Response for ``backlog_create_sam_task``."""

    issue_number: int | None = None
    """Created sub-issue number, or ``0`` when issue creation failed."""

    title: str | None = None
    """Task issue title, or ``""`` when issue creation failed."""

    url: str | None = None
    """Always ``""`` -- the backend does not resolve an issue URL."""


# ready_tasks entries are built via untyped .get() lookups in
# operations.get_ready_sam_tasks -- kept as dict[str, object] rather than a
# nested model per this module's token-budget policy (see
# DispatchWaveStatusResponse's design note).
class BacklogGetReadySamTasksResponse(FallibleToolResponse):
    """Response for ``backlog_get_ready_sam_tasks``."""

    feature: str | None = None
    """Feature slug the ready tasks belong to."""

    ready_tasks: list[dict[str, object]] | None = None
    """Ready task dicts, each with id, name, agent, skills, issue_number. Absent on the error arm."""

    count: int | None = None
    """Number of ready tasks returned."""


class BacklogGetSoonestMilestoneResponse(FallibleToolResponse):
    """Response for ``backlog_get_soonest_milestone``."""

    milestone: Milestone | None = None
    """Soonest-due open milestone, or ``None`` when no open milestones exist."""


# title/groomed_updated are absent when operations.groom_item is called with no
# content to write (section/content/groomed_file/groomed_content/sections all
# omitted) and returns {} before any mark_groomed handling runs -- so both are
# optional. The tool's inline pre-flight validation error (sections passed
# together with the single-section args) returns only error, with no Output
# triad; that still validates because messages/warnings/errors default to [].
class BacklogGroomResponse(FallibleToolResponse):
    """Response for ``backlog_groom``."""

    title: str | None = None
    """Groomed item's title."""

    groomed_updated: bool | None = None
    """``True`` when groomed content was written."""

    sections_written: list[str] | None = None
    """Section names written, present only for batch (``sections=``) writes."""

    mark_groomed_skipped: bool | None = None
    """``True`` when ``mark_groomed=True`` but the post-write re-lookup failed."""

    mark_groomed_skip_reason: str | None = None
    """Explains why the status advance was skipped."""

    mark_groomed_applied: bool | None = None
    """``True`` when the local groomed status was applied."""

    mark_groomed_label_error: str | None = None
    """GitHub label update error, present only when that step failed."""


# Pydantic counterpart of backlog_core.operations._SamTaskRow for the MCP
# wire boundary; operations.py keeps using its own TypedDict internally.
class SamTaskRow(BaseModel):
    """One SAM task row as returned by SAM-task-listing MCP tools."""

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


# Pydantic counterpart of backlog_core.operations._SamTaskLookupResult for the
# MCP wire boundary; operations.py keeps using its own TypedDict internally.
# The tool wraps operations.get_sam_tasks in a BacklogError arm that reports
# only error plus the Output triad, so every other field is widened to
# optional even though operations.get_sam_tasks itself always returns the
# full shape.
class SamTaskLookupResult(FallibleToolResponse):
    """Response for ``backlog_get_sam_tasks``."""

    tasks: list[SamTaskRow] | None = None
    """Matching SAM task rows. Absent on the error arm."""

    count: int | None = None
    """Number of tasks returned."""

    parent_issue_number: int | str | None = None
    """Parent issue number, or a placeholder string when unavailable."""

    stale: bool | None = None
    """True when the cached task data is known to be out of date."""

    pending: bool | None = None
    """True when a sync is pending and results may be incomplete."""

    unavailable: bool | None = None
    """True when the backend could not be reached at all."""


class AccumulatedUsage(BaseModel):
    """Token/cost usage accumulated across a wave's dispatch events.

    TODO: not yet wired to stored dispatch state -- always zero. See
    ``dispatch_wave_status``'s docstring.
    """

    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    estimated_cost_usd: float = 0.0
    events_with_usage: int = 0


# Design notes for DispatchWaveStatusResponse and DispatchSpawnResponse below:
# each mixes in its domain model (DispatchWaveSummary / DispatchSpawnSummary)
# rather than redeclaring its fields; kept as wire-only subclasses so the
# extra fields here don't leak into the CLI's unmodified reuse of the same
# domain models (dh_core.operations, and DispatchSpawnSummary.per_wave).
# Every field besides milestone/(wave_num)/error/the Output triad is
# widened to optional, per this module's docstring, because each tool's
# error arm never has the full summary to report. ``items``/``per_wave``
# are further widened to plain dicts rather than full nested models
# (``DispatchItemRecord`` alone is a 13-field SQLite row mirror) to stay
# within the single-tool schema token budget.
class DispatchWaveStatusResponse(DispatchWaveSummary, FallibleToolResponse):
    """Response for ``dispatch_wave_status``."""

    status: str | None = None
    total_items: int | None = None
    pending: int | None = None
    in_progress: int | None = None
    complete: int | None = None
    failed: int | None = None
    skipped: int | None = None
    started_at: str | None = None
    completed_at: str | None = None
    items: list[dict[str, object]] | None = None
    accumulated_usage: AccumulatedUsage | None = None


# See DispatchWaveStatusResponse's design notes above.
class DispatchSpawnResponse(DispatchSpawnSummary, FallibleToolResponse):
    """Response for ``dispatch_spawn``."""

    waves_executed: int | None = None
    total_items: int | None = None
    completed: int | None = None
    failed: int | None = None
    skipped: int | None = None
    elapsed_seconds: float | None = None
    per_wave: list[dict[str, object]] | None = None


# Its BacklogError arm (item not found, or found item lacking a
# persistable reference) never has a title/followup_to pair to report, so
# both are widened to optional.
class BacklogLinkFollowupResponse(FallibleToolResponse):
    """Response for ``backlog_link_followup``."""

    title: str | None = None
    """Title of the item that was linked."""

    followup_to: str | None = None
    """Logical ID recorded on the item, or ``""`` when the link was cleared."""


class FollowupItem(BaseModel):
    """One backlog item linked as a follow-up to another item or plan."""

    title: str
    section: str
    issue: str
    followup_to: str


class BacklogListFollowupsResponse(FallibleToolResponse):
    """Response for ``backlog_list_followups``."""

    items: list[FollowupItem] | None = None
    """Backlog items matching the requested origin. Absent on the error arm."""

    count: int | None = None
    """Number of items returned; ``0`` alongside an empty ``items``. Absent on the error arm."""


# backlog_list has two disjoint success shapes selected by count_only: the
# full shape (items/count/available_fields/pagination/backend, optionally
# sync_state/next_call/match_pages) and a minimal {count, sync_state?}
# shape that skips items/available_fields/pagination/backend/next_call/
# match_pages entirely -- so every field but the Output triad is optional.
# The BacklogError arm reports only error/backend plus the Output triad.
# ``items`` stays ``dict[str, object]`` (never a model) because the
# caller-supplied ``fields=`` parameter projects an arbitrary per-call key
# subset via ``_apply_fields_projection`` in server.py -- genuinely dynamic,
# not a budget tradeoff. ``pagination``/``backend``/``sync_state``/
# ``match_pages`` stay plain dicts too: this is already the most complex
# tool in the server (a full expansion of just ``backend`` alone, mirroring
# models.BackendStatus's enum, put this tool's schema at 694 tokens on its
# own) -- callers get the field names via operations.list_items's docstring
# and _probe_backend_status/_build_sync_state_block/_paginate_match_items
# in server.py.
class BacklogListResponse(FallibleToolResponse):
    """Response for ``backlog_list``."""

    items: list[dict[str, object]] | None = None
    """Matching item dicts, projected to ``fields=`` when given."""

    count: int | None = None
    """Number of items in this response."""

    available_fields: list[str] | None = None
    """Field names selectable via ``fields=``."""

    pagination: dict[str, object] | None = None
    """offset/limit/total/has_more for the current page."""

    backend: dict[str, object] | None = None
    """Configured backend's reachability and item-count status."""

    sync_state: dict[str, object] | None = None
    """Background-sync status, present only when the sync is not IDLE."""

    next_call: str | None = None
    """Suggested follow-up call, present only when ``has_more`` is true."""

    match_pages: dict[str, object] | None = None
    """Match token-pagination metadata, present only when ``match_context=True``."""


class CommentEntry(BaseModel):
    """One issue comment, truncated to a preview."""

    id: str
    author: str
    created_at: str
    updated_at: str
    preview: str


class BacklogListCommentsResponse(FallibleToolResponse):
    """Response for ``backlog_list_comments``."""

    comments: list[CommentEntry] | None = None
    """Comments in the requested window. Absent on the error arm."""

    count: int | None = None
    """Number of comments in this response window; ``0`` alongside an empty ``comments``. Absent on the error arm."""

    has_more: bool | None = None
    """``True`` when comments exist beyond the current window. Absent on the error arm."""


class IssueEntry(BaseModel):
    """One GitHub issue summary."""

    number: int
    title: str
    state: str
    labels: list[str]
    assignees: list[str]
    milestone: str | None = None
    created_at: str
    updated_at: str


class BacklogListIssuesResponse(FallibleToolResponse):
    """Response for ``backlog_list_issues``."""

    issues: list[IssueEntry] | None = None
    """Matching GitHub issues. Absent on the error arm."""

    count: int | None = None
    """Number of issues returned; ``0`` alongside an empty ``issues``. Absent on the error arm."""


class LabelEntry(BaseModel):
    """One repository label."""

    name: str
    color: str
    description: str


class BacklogListLabelsResponse(FallibleToolResponse):
    """Response for ``backlog_list_labels``."""

    labels: list[LabelEntry] | None = None
    """Repository labels, up to the requested limit. Absent on the error arm."""

    count: int | None = None
    """Number of labels returned; ``0`` alongside an empty ``labels``. Absent on the error arm."""


class MergedPullRequestEntry(BaseModel):
    """One merged pull request."""

    number: int
    title: str
    merged_at: str
    author: str
    url: str
    head_branch: str


class BacklogListMergedPrsResponse(FallibleToolResponse):
    """Response for ``backlog_list_merged_prs``."""

    pull_requests: list[MergedPullRequestEntry] | None = None
    """Merged pull requests matching the request. Absent on the error arm."""

    count: int | None = None
    """Number of pull requests returned; ``0`` alongside an empty ``pull_requests``. Absent on the error arm."""


class BacklogListMilestonesResponse(FallibleToolResponse):
    """Response for ``backlog_list_milestones``."""

    milestones: list[Milestone] | None = None
    """Repository milestones matching the requested state filter. Absent on the error arm."""

    count: int | None = None
    """Number of milestones returned; ``0`` alongside an empty ``milestones``. Absent on the error arm."""


class ProjectEntry(BaseModel):
    """One Projects V2 project."""

    id: str
    title: str
    number: int
    url: str
    closed: bool
    short_description: str


class BacklogListProjectsResponse(FallibleToolResponse):
    """Response for ``backlog_list_projects``."""

    projects: list[ProjectEntry] | None = None
    """Projects V2 projects for the resolved owner. Absent on the error arm."""

    count: int | None = None
    """Number of projects returned; ``0`` alongside an empty ``projects``. Absent on the error arm."""


# dry_run is absent on the no-items early return (only normalized: 0 is
# reported), so it is widened to optional alongside normalized itself for
# the BacklogError arm.
class BacklogNormalizeResponse(FallibleToolResponse):
    """Response for ``backlog_normalize``."""

    normalized: int | None = None
    """Count of items normalized (or that would be, when ``dry_run=True``)."""

    dry_run: bool | None = None
    """``True`` when this was a preview run; absent when no items exist."""


# backlog_pull has two disjoint success shapes selected by whether `selector`
# is given: a single-item pull (file_path, optional diff) or a bulk pull
# (pulled, optional skipped/total/dry_run/diff -- skipped/total/dry_run are
# absent on the no-candidates early return, which reports only `pulled: 0`).
# One flat model with every field beyond the Output triad optional covers
# both paths plus the BacklogError arm.
class BacklogPullResponse(FallibleToolResponse):
    """Response for ``backlog_pull``."""

    file_path: str | None = None
    """Local path written, present only on the single-selector path."""

    pulled: int | None = None
    """Count of items pulled, present only on the bulk (no-selector) path."""

    skipped: int | None = None
    """Count of items that failed to reconcile, on the bulk path."""

    total: int | None = None
    """Total candidate items considered, on the bulk path."""

    dry_run: bool | None = None
    """``True`` when this was a preview run, on the bulk path."""

    diff: str | None = None
    """Unified diff of local vs remote changes, present only when ``diff=True``."""


class BacklogReadCommentResponse(FallibleToolResponse):
    """Response for ``backlog_read_comment``."""

    id: str | None = None
    """GraphQL node ID of the comment."""

    author: str | None = None
    """Login of the comment author."""

    created_at: str | None = None
    """ISO 8601 creation timestamp."""

    updated_at: str | None = None
    """ISO 8601 last-update timestamp."""

    body: str | None = None
    """Full Markdown comment body -- no truncation."""


# operations.resolve_item has two distinct success shapes: an already-done
# early return (title, already_resolved) and a normal resolve (title,
# resolved, summary). Both are optional here besides title because the
# BacklogError arm supplies neither -- same pattern as BacklogCloseResponse.
class BacklogResolveResponse(FallibleToolResponse):
    """Response for ``backlog_resolve``."""

    title: str | None = None
    """Title of the item that was resolved (or already resolved)."""

    already_resolved: bool | None = None
    """``True`` when the item was already resolved before this call."""

    resolved: bool | None = None
    """``True`` when this call performed the resolve."""

    summary: str | None = None
    """Completion summary, present only on the normal (non-already-resolved) path."""


# operations.strike_entry's only failure paths raise (ItemNotFoundError,
# EntryNotFoundError, or the unreachable no-reference BacklogError), so the
# tool's BacklogError arm never has a title/entry_id/struck triple to
# report -- all three are widened to optional.
class BacklogStrikeEntryResponse(FallibleToolResponse):
    """Response for ``backlog_strike_entry``."""

    title: str | None = None
    """Title of the item the entry was struck in."""

    entry_id: str | None = None
    """ID of the struck entry, echoed back from the request."""

    struck: bool | None = None
    """``True`` when the entry was successfully struck."""


# operations.sync_items always returns created/pushed/dry_run on both its
# SyncProvider and non-SyncProvider paths, but the tool's BacklogError arm
# (raised only by the underlying GraphQL/reconcile call) reports just error
# plus the Output triad, so all three are widened to optional.
class BacklogSyncResponse(FallibleToolResponse):
    """Response for ``backlog_sync``."""

    created: int | None = None
    """Count of new GitHub issues created for previously unlinked items."""

    pushed: int | None = None
    """Count of items whose groomed content was pushed/reconciled to the backend."""

    dry_run: bool | None = None
    """``True`` when this was a preview run."""


# operations.update_item has two structurally disjoint success branches
# selected by whether groomed content is being written (see
# _apply_groomed_update vs. the plan/status/verified tail of update_item):
# the groomed branch never sets plan/issue_num/status/verified/changes, and
# the non-groomed branch never sets groomed_updated/sections_written. Both
# branches always start from {"title": item.title}, but the tool's
# BacklogError arm (item not found, or the unreachable no-reference error)
# reports only error plus the Output triad, so title is widened to optional
# too. ``error`` here also covers a *non-fatal* soft error that
# _apply_non_in_progress_status/_apply_issue_status_labels can set on an
# otherwise-successful non-groomed call (e.g. an unrecognized status value,
# or a GitHub label-apply failure) -- sharing FallibleToolResponse.error is
# correct because the two meanings are mutually exclusive in practice (a
# fatal BacklogError never reaches the point where the soft error is set)
# and both mean "something about this call didn't fully succeed". ``changes``
# stays ``dict[str, object]`` -- fixed key domain (renamed_to/description_
# updated/plan/status/issue_num) but heterogeneous value types (str | int |
# bool) make a nested model more trouble than it is worth for a summary dict.
class BacklogUpdateResponse(FallibleToolResponse):
    """Response for ``backlog_update``."""

    title: str | None = None
    """Title of the updated item."""

    renamed_to: str | None = None
    """New title, present only when ``title=`` was applied."""

    description_updated: bool | None = None
    """``True`` when ``description=`` was applied."""

    plan: str | None = None
    """Plan string applied, present only on the non-groomed path with ``plan=``."""

    issue_num: int | None = None
    """Newly created backend issue number, present only when one was auto-created."""

    status: str | None = None
    """Status value applied, present only on the non-groomed path with ``status=``."""

    verified: bool | None = None
    """``True`` when the verified label was applied (or would be a no-op)."""

    changes: dict[str, object] | None = None
    """Summary of applied field changes, present only on the non-groomed path."""

    groomed_updated: bool | None = None
    """``True`` when groomed content was written, present only on the groomed path."""

    sections_written: list[str] | None = None
    """Section names written, present only for batch (``sections=``) groomed writes."""


class BacklogUpdateSamTaskStatusResponse(FallibleToolResponse):
    """Response for ``backlog_update_sam_task_status``."""

    updated: bool | None = None
    """``True`` when the status field was changed; ``False`` if it already matched."""

    issue_number: int | None = None
    """Task sub-issue number, echoed back from the request."""

    new_status: str | None = None
    """Status value that was applied, echoed back from the request."""


# Shared error-arm shape for dispatch_* tools keyed by a GitHub milestone
# number: dispatch_read, dispatch_validate, dispatch_stale_check, and
# dispatch_conflicts all return exactly {"error": ..., "milestone_number":
# ...} on every failure path, with no Output triad. milestone_number is
# required -- every success path echoes it back too.
class MilestoneEchoError(BaseModel):
    """Shared ``{error, milestone_number}`` error-arm field set for milestone-keyed dispatch tools."""

    milestone_number: int
    """GitHub milestone number, echoed back on both success and error."""

    error: str | None = None
    """Error message; ``None`` on success."""

    unsupported_capability: str | None = None
    """Missing capability flag name, set only on an ``UnsupportedBackendCapabilityError`` arm."""

    backend: str | None = None
    """Active backend's class name, set only on an ``UnsupportedBackendCapabilityError`` arm."""


# conflict_groups reuses dispatch_schema.core.models.ConflictGroup directly
# (rather than redeclaring an equivalent shape here) because
# operations.analyze_impact_radius_conflicts already returns that exact
# type -- model_dump() on it produces the group_id/reason/items dict the
# tool has always returned.
class DispatchConflictsResponse(MilestoneEchoError):
    """Response for ``dispatch_conflicts``."""

    conflict_groups: list[ConflictGroup] | None = None
    """Groups of items whose Impact Radii share a file path."""

    count: int | None = None
    """Number of conflict groups found."""


# dispatch_create_plan spreads Output (messages/warnings/errors/error via
# FallibleToolResponse) but then overwrites warnings/errors with
# validate_plan_integrity's result lists rather than Output's own -- same
# field names and list[str] type, so no redeclaration is needed, just this
# note. Three arms: success (all fields present, is_valid only when
# validate=True), a milestone-mismatch/write-failure error (error +
# milestone_number + Output triad), and an already-exists error (error +
# Output triad only, no milestone_number) -- so milestone_number is
# widened to optional alongside the plan-summary fields.
class DispatchCreatePlanResponse(FallibleToolResponse):
    """Response for ``dispatch_create_plan``."""

    milestone_number: int | None = None
    """GitHub milestone number, absent only on the already-exists error path."""

    wave_count: int | None = None
    """Number of waves in the stored plan."""

    item_count: int | None = None
    """Total items across all waves in the stored plan."""

    is_valid: bool | None = None
    """Structural validity of the plan; ``None`` when ``validate=False``."""


# Hand-rolled, not an Output spread -- messages/warnings/errors are literal
# lists on the success arm only. Both error arms (invalid status value, item
# not found) share the same {"error", "milestone", "issue"} shape, distinct
# from MilestoneEchoError's "milestone_number" key, so declared directly
# rather than via a shared base (no other tool reuses this exact pairing).
class DispatchItemStatusResponse(BaseModel):
    """Response for ``dispatch_item_status``."""

    milestone: int
    """GitHub milestone number, echoed back on both success and error."""

    issue: int
    """Issue number of the item, echoed back on both success and error."""

    wave_num: int | None = None
    """Wave number the item was found in."""

    status: str | None = None
    """Status that was recorded: complete, failed, or skipped."""

    messages: list[str] | None = None
    """Informational messages about the action taken."""

    warnings: list[str] | None = None
    """Always empty -- reserved for future use, present only on success."""

    errors: list[str] | None = None
    """Always empty -- reserved for future use, present only on success."""

    error: str | None = None
    """Error message; ``None`` on success."""


# plan is measured over the single-tool schema token budget (697 tokens vs
# the 600 cap) when nested as dispatch_schema.core.models.DispatchPlan --
# that model's five layers of Field(description=...) strings alone account
# for the overage. Falls back to dict[str, object] per this module's
# budget policy; callers get the field names from DispatchPlan's own
# docstrings and dispatch_read's docstring below.
class DispatchReadResponse(MilestoneEchoError):
    """Response for ``dispatch_read``."""

    plan: dict[str, object] | None = None
    """Full dispatch plan for the milestone (milestone/conflict_groups/waves/quality_gates)."""


class DispatchStaleCheckResponse(MilestoneEchoError):
    """Response for ``dispatch_stale_check``."""

    is_stale: bool | None = None
    """``True`` when the milestone's issues differ from the stored plan."""

    added_issues: list[int] | None = None
    """Issue numbers present in the milestone but absent from the plan."""

    removed_issues: list[int] | None = None
    """Issue numbers present in the plan but absent from the milestone."""

    message: str | None = None
    """Human-readable summary of the staleness state."""


class DispatchValidateResponse(MilestoneEchoError):
    """Response for ``dispatch_validate``."""

    is_valid: bool | None = None
    """``True`` when the plan passes every structural integrity check."""

    errors: list[str] | None = None
    """Fatal integrity violations found in the plan."""

    warnings: list[str] | None = None
    """Non-fatal issues found in the plan."""


# Shared error-arm shape for dispatch_wave_start: both its failure paths
# (malformed item entry, wave already exists) return exactly {"error": ...,
# "milestone": ..., "wave_num": ...}, with no Output triad.
class WaveEchoError(BaseModel):
    """Shared ``{error, milestone, wave_num}`` error-arm field set for wave-keyed dispatch tools."""

    milestone: int
    """GitHub milestone number, echoed back on both success and error."""

    wave_num: int
    """Wave number, echoed back on both success and error."""

    error: str | None = None
    """Error message; ``None`` on success."""


class DispatchWaveStartResponse(WaveEchoError):
    """Response for ``dispatch_wave_start``."""

    items_count: int | None = None
    """Number of items recorded for the wave."""

    status: str | None = None
    """Wave status after creation, e.g. ``"pending"``."""

    messages: list[str] | None = None
    """Informational messages about the action taken."""

    warnings: list[str] | None = None
    """Always empty -- reserved for future use, present only on success."""

    errors: list[str] | None = None
    """Always empty -- reserved for future use, present only on success."""


# Plain BaseModel, not Output/ToolResponse -- sync_status has no
# messages/warnings/errors triad, just SyncState.to_dict()'s 12 fields
# verbatim. Reused as-is for SyncNowResponse.sync_state below, since both
# report the identical snapshot shape. Unlike every other tool in this
# module, sync_status/sync_now return the model instance directly at the
# call site (no exclude_none=True, no model_dump()): every field here is
# unconditionally present in SyncState.to_dict() (some legitimately null)
# and neither tool has a BacklogError arm ever needing to hide a field, so
# there is nothing exclude_none=True would need to drop -- returning the
# instance is wire-identical to dumping one and keeps the declared return
# type accurate for in-process callers too.
class SyncStatusResponse(BaseModel):
    """Response for ``sync_status``; also nested as ``SyncNowResponse.sync_state``."""

    status: str
    """Sync lifecycle state: idle, running, offline, or error."""

    started_at: str | None = None
    """ISO 8601 UTC timestamp of current/last sync start."""

    completed_at: str | None = None
    """ISO 8601 UTC timestamp of last sync completion."""

    items_done: int
    """Issues written to cache in the current/last run."""

    items_total: int | None = None
    """Total issues expected; ``None`` when unknown."""

    last_error: str
    """Error message from last failed sync, or empty string."""

    last_success_at: str | None = None
    """ISO 8601 UTC timestamp of last successful sync."""

    retry_count: int
    """Consecutive failed attempts in the current cycle."""

    offline_reason: str
    """Why the server entered offline mode, or empty string."""

    percent: int | None = None
    """Completion percentage 0-100; ``None`` when total is unknown."""

    pending_mutations: int
    """Offline-queue depth as of the last completed sync."""

    rejected_mutations: int
    """Dead-lettered mutation count as of the last completed sync."""


# No Output spread and no BacklogError arm (sync_now never raises) -- all
# three return sites always populate triggered/sync_state/messages, so
# nothing here is optional.
class SyncNowResponse(BaseModel):
    """Response for ``sync_now``."""

    triggered: bool
    """``True`` if a new sync was started; ``False`` if one was already running."""

    sync_state: SyncStatusResponse
    """Current sync state snapshot."""

    messages: list[str]
    """Informational messages about the action taken."""
