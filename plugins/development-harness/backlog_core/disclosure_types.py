"""Canonical backlog response types for progressive Markdown disclosure.

This module is the single source of truth for all disclosure-related types.
Downstream tasks (T13-T16) import from here -- no other module redefines these types.

``MapResponse``/``NavigateResponse``/``BoundedResponse`` (the three MCP response
shapes ``BacklogViewDisclosureHandler`` returns) are frozen Pydantic ``BaseModel``
subclasses, per this repo's "structured data -> Pydantic, not dataclass/TypedDict" convention
(AGENTS.md), matching the ``ConfigDict(frozen=True)`` value-object pattern already
used in ``file_cache_state.py``. Internal navigation models belong to
``progressive_markdown``; this module owns only backlog response envelopes and
request-mode validation.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from .models import StatusSource


class DisclosureMode(StrEnum):
    """Operating mode resolved from disclosure parameters in a single MCP call."""

    PASSTHROUGH = "passthrough"
    """No disclosure parameters set — existing backlog_view behaviour unchanged."""

    MAP = "map"
    """``map=True`` — return flat ordinal dot-path map of item structure."""

    NAVIGATE = "navigate"
    """``navigate=ordinal`` without ``head`` — return full content at the ordinal."""

    EXTRACT = "extract"
    """``navigate=ordinal`` with ``head=N`` — return a token-bounded window."""


# ---------------------------------------------------------------------------
# Response types (produced by BacklogViewDisclosureHandler)
# ---------------------------------------------------------------------------


class MapResponse(BaseModel):
    """Response for ``map=True`` calls.

    ``map_text`` contains the complete formatted map. ``over_budget`` reports whether
    the represented content exceeds the navigation budget; it does not truncate or
    paginate the map.
    """

    model_config = ConfigDict(frozen=True)

    selector: str
    """Item selector echoed from the request (e.g. ``'#2515'``)."""

    total_sections: int
    """Count of top-level (level-1) sections in the document."""

    total_est_tokens: int
    """Sum of level-1 section token estimates only.

    Level-2 entry lines are excluded to prevent double-counting body text already
    included in the parent section token estimate.
    """

    map_text: str
    """Complete formatted map with ordinal lines joined by newlines."""

    over_budget: bool
    """``True`` when ``total_est_tokens`` exceeds the configured token budget."""

    struck_ordinals: list[str] = Field(default_factory=list)
    """Ordinals of every struck (retracted) entry or descendant in the map (#3187).

    Explicit field rather than requiring callers to parse ``[struck] `` markers
    out of ``map_text`` — the "No Invented Limits" data-completeness contract
    this project follows requires struck state to be addressable, not merely
    visible in formatted text."""

    status_source: StatusSource = "cache"
    """Provenance of the underlying ``operations.view_item()`` read's
    live-enrichment data (#3546, B5/B6). See :data:`~backlog_core.models.StatusSource`
    for the provenance meanings. Forwarded from that call's ``ViewItemResult`` so a
    disclosure-mode response never silently drops the signal a passthrough
    ``backlog_view`` call already carries (Codex review, PR #3577)."""

    unavailable_capabilities: list[str] = Field(default_factory=list)
    """Capabilities that could not be read live this call, e.g.
    ``["live_enrichment"]`` when ``status_source == "unavailable"``. Forwarded
    from the underlying ``ViewItemResult``; empty when nothing was degraded."""

    messages: list[str] = Field(default_factory=list)
    """Informational messages from the underlying ``operations.view_item()`` read,
    e.g. a reconcile summary. Forwarded from that call's ``Output`` collector so
    this disclosure mode does not silently drop them."""

    warnings: list[str] = Field(default_factory=list)
    """Degradation warnings from the underlying ``operations.view_item()`` read,
    e.g. "backend unreachable — sections_index reflects provider-backed record,
    may be stale". Forwarded from that call's ``Output`` collector so this
    disclosure mode does not silently drop them."""

    errors: list[str] = Field(default_factory=list)
    """Non-fatal error messages from the underlying ``operations.view_item()``
    read. Forwarded from that call's ``Output`` collector so this disclosure mode
    does not silently drop them."""


class NavigateResponse(BaseModel):
    """Response for ``navigate=ordinal`` without ``head``.

    When ``has_children`` is ``True`` the node has sub-heading children and
    ``child_map`` contains a formatted listing of their ordinals and titles.
    ``content`` is an empty string in that case — prose is accessed by
    navigating to individual child ordinals.

    When ``has_children`` is ``False`` the node is a leaf (or a code-only
    node) and ``content`` carries the full body text or raw fence body.
    ``child_map`` is ``None``.
    """

    model_config = ConfigDict(frozen=True)

    ordinal: str
    """Echoed ordinal string (e.g. ``'4.0'``)."""

    title: str
    """Section or entry heading text."""

    content: str
    """Full section/entry content — may be large.

    Empty string (not ``None``) when ``has_children`` is ``True``.
    """

    total_tokens: int
    """tiktoken ``cl100k_base`` count of ``content``."""

    truncated: bool
    """``False`` for navigate-without-head responses.

    May be ``True`` for EXTRACT-on-parent (navigate + head) when the
    ``child_map`` text exceeds the head token budget.
    """

    child_map: str | None = None
    """Formatted listing of direct sub-heading children when this node has
    sub-heading children; ``None`` for leaf nodes and code-block nodes."""

    has_children: bool = False
    """``True`` iff this node has sub-heading children (``SectionNode`` children).

    Code-only nodes (prose + fences, no sub-headings) have ``has_children=False``.
    When ``True``, callers should display ``child_map`` and navigate
    to a child ordinal rather than using ``content`` directly.
    """

    struck: bool = False
    """``True`` when the resolved ordinal addresses a struck (retracted) entry,
    or a descendant of one (#3187).  ``False`` for level-1 section aggregates,
    which have no single-entry identity."""

    entry_id: str = ""
    """Stable identifier of the owning entry; ``""`` when the resolved ordinal
    has no entry identity (level-1 sections)."""

    status_source: StatusSource = "cache"
    """Provenance of the underlying ``operations.view_item()`` read's
    live-enrichment data (#3546, B5/B6). See :data:`~backlog_core.models.StatusSource`
    for the provenance meanings. Forwarded from that call's ``ViewItemResult`` so a
    disclosure-mode response never silently drops the signal a passthrough
    ``backlog_view`` call already carries (Codex review, PR #3577)."""

    unavailable_capabilities: list[str] = Field(default_factory=list)
    """Capabilities that could not be read live this call, e.g.
    ``["live_enrichment"]`` when ``status_source == "unavailable"``. Forwarded
    from the underlying ``ViewItemResult``; empty when nothing was degraded."""

    messages: list[str] = Field(default_factory=list)
    """Informational messages from the underlying ``operations.view_item()`` read.
    Forwarded from that call's ``Output`` collector so this disclosure mode does
    not silently drop them."""

    warnings: list[str] = Field(default_factory=list)
    """Degradation warnings from the underlying ``operations.view_item()`` read,
    e.g. "backend unreachable — sections_index reflects provider-backed record,
    may be stale". Forwarded from that call's ``Output`` collector so this
    disclosure mode does not silently drop them."""

    errors: list[str] = Field(default_factory=list)
    """Non-fatal error messages from the underlying ``operations.view_item()``
    read. Forwarded from that call's ``Output`` collector so this disclosure mode
    does not silently drop them."""


class BoundedResponse(BaseModel):
    """Response for ``navigate=ordinal`` with ``head=N``.

    ``BoundedResponse`` is a value object — it carries no ``selector`` field.
    The ``next_call`` hint is assembled by ``BacklogViewDisclosureHandler._handle_extract()``
    where the selector is in scope.
    """

    model_config = ConfigDict(frozen=True)

    ordinal: str
    title: str

    content: str
    """First ``head_tokens`` tokens of the section/entry."""

    total_tokens: int
    """tiktoken count of FULL content before truncation."""

    returned_tokens: int
    """tiktoken count of ``content`` actually returned."""

    truncated: bool

    next_call: str | None
    """Continuation hint when ``truncated=True``, uses ``skip_tokens=`` parameter.

    ``None`` when ``truncated`` is ``False``.
    """

    struck: bool = False
    """``True`` when the resolved ordinal addresses a struck (retracted) entry,
    or a descendant of one (#3187).  Struck state is metadata, not content, so
    it survives token-bounded windowing even when ``content`` is truncated."""

    entry_id: str = ""
    """Stable identifier of the owning entry; ``""`` when the resolved ordinal
    has no entry identity (level-1 sections)."""

    status_source: StatusSource = "cache"
    """Provenance of the underlying ``operations.view_item()`` read's
    live-enrichment data (#3546, B5/B6). See :data:`~backlog_core.models.StatusSource`
    for the provenance meanings. Forwarded from that call's ``ViewItemResult`` so a
    disclosure-mode response never silently drops the signal a passthrough
    ``backlog_view`` call already carries (Codex review, PR #3577)."""

    unavailable_capabilities: list[str] = Field(default_factory=list)
    """Capabilities that could not be read live this call, e.g.
    ``["live_enrichment"]`` when ``status_source == "unavailable"``. Forwarded
    from the underlying ``ViewItemResult``; empty when nothing was degraded."""

    messages: list[str] = Field(default_factory=list)
    """Informational messages from the underlying ``operations.view_item()`` read.
    Forwarded from that call's ``Output`` collector so this disclosure mode does
    not silently drop them."""

    warnings: list[str] = Field(default_factory=list)
    """Degradation warnings from the underlying ``operations.view_item()`` read,
    e.g. "backend unreachable — sections_index reflects provider-backed record,
    may be stale". Forwarded from that call's ``Output`` collector so this
    disclosure mode does not silently drop them."""

    errors: list[str] = Field(default_factory=list)
    """Non-fatal error messages from the underlying ``operations.view_item()``
    read. Forwarded from that call's ``Output`` collector so this disclosure mode
    does not silently drop them."""


# ---------------------------------------------------------------------------
# Error types
# ---------------------------------------------------------------------------


class DisclosureParamError(Exception):
    """Invalid disclosure parameter combination.

    Attributes:
        message: Human-readable explanation.
        invalid_params: Mapping of parameter names to the provided values.
    """

    def __init__(self, message: str, invalid_params: dict[str, object]) -> None:
        """Initialize with a human-readable message and the offending parameters."""
        super().__init__(message)
        self.invalid_params = invalid_params


__all__ = ["BoundedResponse", "DisclosureMode", "DisclosureParamError", "MapResponse", "NavigateResponse"]
