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
    "ArtifactRegisterResponse",
    "ArtifactsListResponse",
    "DispatchSpawnResponse",
    "DispatchWaveStatusResponse",
    "FallibleToolResponse",
    "Milestone",
    "SamTaskLookupResult",
    "SamTaskRow",
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


class ArtifactEntryOut(BaseModel):
    """One artifact manifest entry as returned by artifact-listing MCP tools.

    Mirrors ``backlog_core.models.ArtifactEntry``'s ``model_dump(mode="json")``
    shape -- string fields here correspond to that model's enum fields
    (``ArtifactType``, ``ArtifactStatus``) serialised to their string values.
    """

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


class ArtifactsListResponse(ToolResponse):
    """Response shape returned by the ``artifact_list`` MCP tool."""

    artifacts: list[ArtifactEntryOut]
    """Registered artifact entries for the requested issue."""

    count: int
    """Total number of artifacts returned."""


class SamTaskRow(BaseModel):
    """One SAM task row as returned by SAM-task-listing MCP tools.

    Pydantic counterpart of ``backlog_core.operations._SamTaskRow`` for the
    MCP wire boundary; ``operations.py`` keeps using its own TypedDict
    internally.
    """

    task_id: str
    """SAM task identifier."""

    feature: str
    """Feature slug the task belongs to."""

    status: str
    """Task status."""

    agent: str
    """Agent assigned to the task."""

    priority: int
    """Dispatch priority."""

    skills: list[str]
    """Skill names required by the task."""

    dependencies: list[str]
    """Task IDs this task depends on."""

    issue_number: int
    """Parent issue number."""

    issue_url: str
    """URL of the parent issue."""

    title: str
    """Task title."""


class SamTaskLookupResult(ToolResponse):
    """Response shape returned by SAM-task-lookup MCP tools.

    Pydantic counterpart of ``backlog_core.operations._SamTaskLookupResult``
    for the MCP wire boundary; ``operations.py`` keeps using its own
    TypedDict internally.
    """

    tasks: list[SamTaskRow]
    """Matching SAM task rows."""

    count: int
    """Number of tasks returned."""

    parent_issue_number: int | str
    """Parent issue number, or a placeholder string when unavailable."""

    stale: bool
    """True when the cached task data is known to be out of date."""

    pending: bool
    """True when a sync is pending and results may be incomplete."""

    unavailable: bool
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
