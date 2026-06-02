"""Canonical type definitions for the MCP progressive disclosure contract.

This module is the single source of truth for all disclosure-related types.
Downstream tasks (T13-T16) import from here -- no other module redefines these types.

All response types are frozen dataclasses (not Pydantic models — they are internal
value objects or MCP response shapes, not ingress validators).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


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


@dataclass(frozen=True, slots=True)
class MapResponse:
    """Response for ``map=True`` calls.

    ``map_text`` is always < 2,000 tokens regardless of item size.
    """

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
    """Full formatted map — ordinal lines joined by newlines (≤ 2,000 tokens)."""

    over_budget: bool
    """``True`` when ``total_est_tokens`` exceeds the configured token budget."""


@dataclass(frozen=True, slots=True)
class NavigateResponse:
    """Response for ``navigate=ordinal`` without ``head``.

    When ``has_children`` is ``True`` the node has sub-heading children and
    ``child_map`` contains a formatted listing of their ordinals and titles.
    ``content`` is an empty string in that case — prose is accessed by
    navigating to individual child ordinals (ADR-7).

    When ``has_children`` is ``False`` the node is a leaf (or a code-only
    node) and ``content`` carries the full body text or raw fence body.
    ``child_map`` is ``None``.
    """

    ordinal: str
    """Echoed ordinal string (e.g. ``'4.0'``)."""

    title: str
    """Section or entry heading text."""

    content: str
    """Full section/entry content — may be large.

    Empty string (not ``None``) when ``has_children`` is ``True`` (ADR-7).
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

    Code-only nodes (prose + fences, no sub-headings) have ``has_children=False``
    (ADR-4).  When ``True``, callers should display ``child_map`` and navigate
    to a child ordinal rather than using ``content`` directly.
    """


@dataclass(frozen=True, slots=True)
class BoundedResponse:
    """Response for ``navigate=ordinal`` with ``head=N``.

    ``BoundedResponse`` is a value object — it carries no ``selector`` field.
    The ``next_call`` hint is assembled by ``BacklogViewDisclosureHandler._handle_extract()``
    where the selector is in scope.
    """

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


@dataclass(frozen=True, slots=True)
class BoundedContent:
    """Internal intermediate value produced by ``TokenBoundedExtractor``.

    Not returned to MCP callers — converted to ``BoundedResponse`` by the handler.
    """

    content: str
    total_tokens: int
    returned_tokens: int
    truncated: bool


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


class OrdinalNotFoundError(Exception):
    """Ordinal did not match any node in the document map.

    Attributes:
        requested: The ordinal string that was requested.
        valid_ordinals: Ordered list of all valid ordinals in the document.
    """

    def __init__(self, requested: str, valid_ordinals: list[str]) -> None:
        """Initialize with the missing ordinal and the full list of valid ordinals."""
        super().__init__(f"Ordinal {requested!r} not found. Valid ordinals: {valid_ordinals}")
        self.requested = requested
        self.valid_ordinals = valid_ordinals


__all__ = [
    "BoundedContent",
    "BoundedResponse",
    "DisclosureMode",
    "DisclosureParamError",
    "MapResponse",
    "NavigateResponse",
    "OrdinalNotFoundError",
]
