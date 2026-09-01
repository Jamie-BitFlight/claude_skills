"""Shared Pydantic response models for the ``backlog_core`` MCP tool boundary.

FastMCP derives each tool's advertised ``outputSchema`` from the function's
return-type annotation via ``pydantic.TypeAdapter(...).json_schema()``. A bare
``dict[str, object]`` erases to an unconstrained object schema, so MCP clients
cannot see what fields a tool actually returns. Every ``@mcp.tool`` function
must return a flat Pydantic model shape instead -- never a ``Union`` of
models, which FastMCP's schema introspection does not recognise and silently
wraps the result (``x-fastmcp-wrap-result``), a wire-protocol change.

Tools build a response model and return ``response.model_dump(exclude_none=True)``
(a plain dict), not the model instance itself -- ``convert_result()`` serialises
either identically, and returning a dict keeps existing runtime assertions
(e.g. ``"error" not in response``) unchanged.

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

from pydantic import BaseModel, Field

from .models import DispatchSpawnSummary, DispatchWaveSummary, Output, RegisterResult

__all__ = [
    "ArtifactReadResponse",
    "ArtifactRegisterResponse",
    "ArtifactsListResponse",
    "BacklogAddResponse",
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
    "DispatchSpawnResponse",
    "DispatchWaveStatusResponse",
    "FallibleToolResponse",
    "Milestone",
    "SamTaskLookupResult",
    "ToolResponse",
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

    due_on: str | None
    """ISO 8601 due date, or ``None`` when unset."""

    open_issues: int
    """Count of open issues attached to this milestone."""

    closed_issues: int
    """Count of closed issues attached to this milestone."""


# Shared by artifact_list and artifact_get. Both have a BacklogError arm
# (artifact_get also treats "type not found"/"id not found" as BacklogError,
# per its docstring) that returns only error plus the Output triad, so
# artifacts/count are widened to optional. ``artifacts`` was originally a
# ``list[ArtifactEntryOut]`` nested model (artifact_type, artifact_id,
# status, created_at, agent, content_revision, storage_tier) mirroring
# ``backlog_core.models.ArtifactEntry``'s ``model_dump(mode="json")`` shape;
# inlined twice (once per tool sharing this response model), it alone put
# artifact_list/artifact_get at 298 tokens each and blocked the total
# outputSchema budget (see :class:`~backlog_core.tool_responses.BacklogListResponse`'s
# design note for the full total-budget context) -- flattened to
# ``dict[str, object]`` per this module's token-budget policy.
class ArtifactsListResponse(FallibleToolResponse):
    """Response for ``artifact_list``/``artifact_get``."""

    artifacts: list[dict[str, object]] = Field(default_factory=list)
    """Registered artifact entries matching the request."""

    count: int = 0
    """Total number of artifacts returned; ``0`` alongside an empty ``artifacts``."""


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


# ``milestone`` was a nested :class:`Milestone` model; flattened to
# ``dict[str, object]`` per this module's token-budget policy -- see
# :class:`~backlog_core.tool_responses.BacklogListResponse`'s design note.
class BacklogCreateMilestoneResponse(FallibleToolResponse):
    """Response for ``backlog_create_milestone``."""

    milestone: dict[str, object] | None = None
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

    ready_tasks: list[dict[str, object]] = Field(default_factory=list)
    """Ready task dicts, each with id, name, agent, skills, issue_number."""

    count: int | None = None
    """Number of ready tasks returned."""


# ``milestone`` flattened to ``dict[str, object]`` -- see
# :class:`BacklogCreateMilestoneResponse`'s design note.
class BacklogGetSoonestMilestoneResponse(FallibleToolResponse):
    """Response for ``backlog_get_soonest_milestone``."""

    milestone: dict[str, object] | None = None
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


# Pydantic counterpart of backlog_core.operations._SamTaskLookupResult for the
# MCP wire boundary; operations.py keeps using its own TypedDict internally.
# The tool wraps operations.get_sam_tasks in a BacklogError arm that reports
# only error plus the Output triad, so every other field is widened to
# optional even though operations.get_sam_tasks itself always returns the
# full shape. ``tasks`` is kept as ``dict[str, object]`` rather than a nested
# per-row model (task_id, feature, status, agent, priority, skills,
# dependencies, issue_number, issue_url, title) -- inlining that row shape
# here blew the single-tool schema token budget (see
# :class:`DispatchWaveStatusResponse`'s design note for the same tradeoff).
class SamTaskLookupResult(FallibleToolResponse):
    """Response for ``backlog_get_sam_tasks``."""

    tasks: list[dict[str, object]] = Field(default_factory=list)
    """Matching SAM task rows (task_id, feature, status, agent, priority,
    skills, dependencies, issue_number, issue_url, title)."""

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
# within the single-tool schema token budget. ``accumulated_usage`` (a
# TODO placeholder, always zero -- see the tool's docstring) is left off
# this model entirely and merged into the response dict after
# ``model_dump()`` for the same budget reason; it isn't schema-advertised.
class DispatchWaveStatusResponse(DispatchWaveSummary, FallibleToolResponse):
    """Response for ``dispatch_wave_status``."""

    status: str | None = None
    total_items: int | None = None
    pending: int | None = None
    in_progress: int | None = None
    complete: int | None = None
    failed: int | None = None
    skipped: int | None = None
    items: list[dict[str, object]] = Field(default_factory=list)


# See DispatchWaveStatusResponse's design notes above.
class DispatchSpawnResponse(DispatchSpawnSummary, FallibleToolResponse):
    """Response for ``dispatch_spawn``."""

    waves_executed: int | None = None
    total_items: int | None = None
    completed: int | None = None
    failed: int | None = None
    skipped: int | None = None
    elapsed_seconds: float | None = None
    per_wave: list[dict[str, object]] = Field(default_factory=list)


# Its BacklogError arm (item not found, or found item lacking a
# persistable reference) never has a title/followup_to pair to report, so
# both are widened to optional.
class BacklogLinkFollowupResponse(FallibleToolResponse):
    """Response for ``backlog_link_followup``."""

    title: str | None = None
    """Title of the item that was linked."""

    followup_to: str | None = None
    """Logical ID recorded on the item, or ``""`` when the link was cleared."""


# ``items`` is kept as ``dict[str, object]`` rather than a nested per-row
# model (title, section, issue, followup_to) -- see the total-schema-budget
# design note on :class:`BacklogListResponse` below for why every
# list-of-dict field across this batch of tools follows the same tradeoff.
class BacklogListFollowupsResponse(FallibleToolResponse):
    """Response for ``backlog_list_followups``."""

    items: list[dict[str, object]] = Field(default_factory=list)
    """Backlog items (title, section, issue, followup_to) matching the requested origin."""

    count: int = 0
    """Number of items returned; ``0`` alongside an empty ``items``."""


# backlog_list has two disjoint success shapes selected by count_only: the
# full shape (items/count/available_fields/pagination/backend, optionally
# sync_state/next_call/match_pages) and a minimal {count, sync_state?}
# shape that skips items/available_fields/pagination/backend/next_call/
# match_pages entirely -- so every field but the Output triad is optional.
# The BacklogError arm reports only error/backend plus the Output triad.
# ``items`` stays ``dict[str, object]`` (never a model) because the
# caller-supplied ``fields=`` parameter projects an arbitrary per-call key
# subset via ``_apply_fields_projection`` in server.py -- genuinely dynamic.
# ``pagination``/``backend``/``sync_state``/``match_pages`` are all
# fixed-shape but kept as plain dicts rather than nested models -- even
# with only ``backend`` (mirroring models.BackendStatus) expanded as a
# $ref, that one field's inlined class + enum docstrings alone put this
# tool's schema at 694 tokens, well over the 400-token single-tool budget.
# The same tradeoff -- ``list[dict[str, object]]`` instead of a nested
# per-row model -- is applied to every other list-of-dict field across this
# batch of 13 tools (backlog_list_comments/issues/labels/merged_prs/
# milestones/projects, backlog_list_followups): typing all of them as
# small Pydantic models pushed the *total* outputSchema token count across
# all 43 registered tools to 7954, over the 6000-token total budget in
# ``test_output_schemas_stay_within_token_budget`` even though every
# individual tool stayed under its own 400-token cap. Flattening trades
# away nested-field documentation in the schema for staying in budget;
# callers still get the field names via each source function's docstring
# (operations.list_items/list_comments/list_issues/list_labels/
# list_merged_prs/list_milestones/list_projects/list_followups,
# _probe_backend_status, _build_sync_state_block, _paginate_match_items
# in server.py).
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


# ``comments`` stays ``dict[str, object]`` (id, author, created_at,
# updated_at, preview) -- see :class:`BacklogListResponse`'s design note.
class BacklogListCommentsResponse(FallibleToolResponse):
    """Response for ``backlog_list_comments``."""

    comments: list[dict[str, object]] = Field(default_factory=list)
    """Comments in the requested window."""

    count: int = 0
    """Number of comments in this response window; ``0`` alongside an empty ``comments``."""

    has_more: bool = False
    """``True`` when comments exist beyond the current window."""


# ``issues`` stays ``dict[str, object]`` (number, title, state, labels,
# assignees, milestone, created_at, updated_at) -- see
# :class:`BacklogListResponse`'s design note.
class BacklogListIssuesResponse(FallibleToolResponse):
    """Response for ``backlog_list_issues``."""

    issues: list[dict[str, object]] = Field(default_factory=list)
    """Matching GitHub issues."""

    count: int = 0
    """Number of issues returned; ``0`` alongside an empty ``issues``."""


# ``labels`` stays ``dict[str, object]`` (name, color, description) -- see
# :class:`BacklogListResponse`'s design note.
class BacklogListLabelsResponse(FallibleToolResponse):
    """Response for ``backlog_list_labels``."""

    labels: list[dict[str, object]] = Field(default_factory=list)
    """Repository labels, up to the requested limit."""

    count: int = 0
    """Number of labels returned; ``0`` alongside an empty ``labels``."""


# ``pull_requests`` stays ``dict[str, object]`` (number, title, merged_at,
# author, url, head_branch) -- see :class:`BacklogListResponse`'s design note.
class BacklogListMergedPrsResponse(FallibleToolResponse):
    """Response for ``backlog_list_merged_prs``."""

    pull_requests: list[dict[str, object]] = Field(default_factory=list)
    """Merged pull requests matching the request."""

    count: int = 0
    """Number of pull requests returned; ``0`` alongside an empty ``pull_requests``."""


# ``milestones`` stays ``dict[str, object]`` -- see
# :class:`BacklogListResponse`'s design note. :class:`Milestone` (kept as a
# documented reusable shape above) is no longer referenced by any response
# model: :class:`BacklogCreateMilestoneResponse` and
# :class:`BacklogGetSoonestMilestoneResponse` also flattened their single
# ``milestone`` field to ``dict[str, object]`` for the same total-budget
# reason.
class BacklogListMilestonesResponse(FallibleToolResponse):
    """Response for ``backlog_list_milestones``."""

    milestones: list[dict[str, object]] = Field(default_factory=list)
    """Repository milestones matching the requested state filter."""

    count: int = 0
    """Number of milestones returned; ``0`` alongside an empty ``milestones``."""


# ``projects`` stays ``dict[str, object]`` (id, title, number, url, closed,
# short_description) -- see :class:`BacklogListResponse`'s design note.
class BacklogListProjectsResponse(FallibleToolResponse):
    """Response for ``backlog_list_projects``."""

    projects: list[dict[str, object]] = Field(default_factory=list)
    """Projects V2 projects for the resolved owner."""

    count: int = 0
    """Number of projects returned; ``0`` alongside an empty ``projects``."""


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
