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
    "ArtifactEntryOut",
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


class ArtifactRegisterResponse(RegisterResult, FallibleToolResponse):
    """Response shape returned by the ``artifact_register`` MCP tool.

    Mixes in :class:`~backlog_core.models.RegisterResult`'s domain fields
    rather than redeclaring them, so the wire shape and the domain result
    computed by ``artifact_register``'s ``_run()`` closure cannot drift
    apart. Its ``BacklogError`` arm never has a ``RegisterResult`` to
    report, so those four fields are widened to optional here (dropped by
    ``exclude_none=True`` on that arm) without touching ``RegisterResult``
    itself, which stays required for every other caller.
    """

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


# Mirrors backlog_core.models.ArtifactEntry's model_dump(mode="json") shape --
# string fields here correspond to that model's enum fields (ArtifactType,
# ArtifactStatus) serialised to their string values. Docstring kept short: this
# model is inlined (not $ref'd) into both artifact_list's and artifact_get's
# outputSchema, so its description is billed twice against the token budget.
class ArtifactEntryOut(BaseModel):
    """One artifact manifest entry, as returned by artifact-listing MCP tools."""

    artifact_type: str
    """Artifact category, e.g. ``architect`` or ``code-review``."""

    artifact_id: str
    """Logical identifier for the artifact."""

    status: str
    """Lifecycle state, e.g. ``current`` or ``superseded``."""

    created_at: str
    """ISO 8601 timestamp of when the artifact was registered."""

    agent: str
    """Name of the agent that produced the artifact."""

    content_revision: str
    """Content-addressed revision published with this manifest entry."""

    storage_tier: Literal["local", "remote"]
    """Storage tier for this artifact."""


# Shared by artifact_list and artifact_get. Both have a BacklogError arm
# (artifact_get also treats "type not found"/"id not found" as BacklogError,
# per its docstring) that returns only error plus the Output triad, so
# artifacts/count are widened to optional.
class ArtifactsListResponse(FallibleToolResponse):
    """Response shape for the ``artifact_list`` and ``artifact_get`` MCP tools."""

    artifacts: list[ArtifactEntryOut] | None = None
    """Registered artifact entries matching the request."""

    count: int | None = None
    """Total number of artifacts returned."""


class ArtifactReadResponse(FallibleToolResponse):
    """Response shape returned by the ``artifact_read`` MCP tool.

    Mirrors ``backlog_core.models.ArtifactContent``'s ``model_dump(mode="json")``
    shape. Its ``BacklogError`` arm (raised for "type not found" and "id not
    found", per the tool's docstring) never has content to report, so every
    field is widened to optional.
    """

    artifact_type: str | None = None
    """Category of the returned artifact."""

    path: str | None = None
    """Repo-relative path (or logical artifact id) that was read."""

    content: str | None = None
    """Raw artifact content."""

    status: str | None = None
    """Lifecycle state of the artifact."""


class BacklogAddResponse(FallibleToolResponse):
    """Response shape returned by the ``backlog_add`` MCP tool.

    Its ``BacklogError`` arm never has an ``operations.add_item`` result to
    report, so every field is widened to optional.
    """

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


class BacklogCloseResponse(FallibleToolResponse):
    """Response shape returned by the ``backlog_close`` MCP tool.

    ``operations.close_item`` has two distinct success shapes: an
    already-closed early return (``title``, ``already_closed``) and a normal
    close (``title``, ``closed``, ``reason``). Both are optional here besides
    ``title`` because the ``BacklogError`` arm supplies neither.
    """

    title: str | None = None
    """Title of the item that was closed (or already closed)."""

    closed: bool | None = None
    """``True`` when this call performed the close."""

    already_closed: bool | None = None
    """``True`` when the item was already closed before this call."""

    reason: str | None = None
    """Close reason, present only on the normal (non-already-closed) path."""


class BacklogCommentIssueResponse(FallibleToolResponse):
    """Response shape returned by the ``backlog_comment_issue`` MCP tool."""

    issue_number: int | None = None
    """GitHub issue number the comment was added to."""

    comment_id: str | None = None
    """GraphQL node ID of the newly created comment -- not a REST integer ID."""

    comment_url: str | None = None
    """Always ``""`` -- the backend does not resolve a comment URL."""


class BacklogCreateMilestoneResponse(FallibleToolResponse):
    """Response shape returned by the ``backlog_create_milestone`` MCP tool."""

    milestone: Milestone | None = None
    """The created milestone. Absent only on the ``BacklogError`` arm."""


class BacklogCreateProjectResponse(FallibleToolResponse):
    """Response shape returned by the ``backlog_create_project`` MCP tool."""

    project_id: str | None = None
    """GraphQL node ID of the created Projects V2 project."""

    title: str | None = None
    """Project title."""

    url: str | None = None
    """Project URL."""

    number: int | None = None
    """Project number."""


class BacklogCreateSamTaskResponse(FallibleToolResponse):
    """Response shape returned by the ``backlog_create_sam_task`` MCP tool."""

    issue_number: int | None = None
    """Created sub-issue number, or ``0`` when issue creation failed."""

    title: str | None = None
    """Task issue title, or ``""`` when issue creation failed."""

    url: str | None = None
    """Always ``""`` -- the backend does not resolve an issue URL."""


class BacklogGetReadySamTasksResponse(FallibleToolResponse):
    """Response shape returned by the ``backlog_get_ready_sam_tasks`` MCP tool.

    ``ready_tasks`` entries are built via untyped ``.get()`` lookups in
    ``operations.get_ready_sam_tasks`` -- kept as ``dict[str, object]`` rather
    than a nested model per this module's token-budget policy (see
    :class:`DispatchWaveStatusResponse`'s design note).
    """

    feature: str | None = None
    """Feature slug the ready tasks belong to."""

    ready_tasks: list[dict[str, object]] = Field(default_factory=list)
    """Ready task dicts, each with id, name, agent, skills, issue_number."""

    count: int | None = None
    """Number of ready tasks returned."""


class BacklogGetSoonestMilestoneResponse(FallibleToolResponse):
    """Response shape returned by the ``backlog_get_soonest_milestone`` MCP tool."""

    milestone: Milestone | None = None
    """Soonest-due open milestone, or ``None`` when no open milestones exist."""


# title/groomed_updated are absent when operations.groom_item is called with no
# content to write (section/content/groomed_file/groomed_content/sections all
# omitted) and returns {} before any mark_groomed handling runs -- so both are
# optional. The tool's inline pre-flight validation error (sections passed
# together with the single-section args) returns only error, with no Output
# triad; that still validates because messages/warnings/errors default to [].
class BacklogGroomResponse(FallibleToolResponse):
    """Response shape returned by the ``backlog_groom`` MCP tool."""

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
    """Response shape returned by the ``backlog_get_sam_tasks`` MCP tool."""

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
    """Response shape returned by the ``dispatch_wave_status`` MCP tool."""

    status: str | None = None
    total_items: int | None = None
    pending: int | None = None
    in_progress: int | None = None
    complete: int | None = None
    failed: int | None = None
    skipped: int | None = None
    items: list[dict[str, object]] = Field(default_factory=list)


class DispatchSpawnResponse(DispatchSpawnSummary, FallibleToolResponse):
    """Response shape returned by the ``dispatch_spawn`` MCP tool.

    See :class:`DispatchWaveStatusResponse`'s design notes.
    """

    waves_executed: int | None = None
    total_items: int | None = None
    completed: int | None = None
    failed: int | None = None
    skipped: int | None = None
    elapsed_seconds: float | None = None
    per_wave: list[dict[str, object]] = Field(default_factory=list)
