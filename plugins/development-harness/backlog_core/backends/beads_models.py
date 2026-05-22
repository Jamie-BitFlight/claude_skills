"""Pydantic v2 boundary models for ``bd --json`` output validation.

This module defines Pydantic boundary models for every JSON shape produced
by the ``bd`` CLI.  All models use ``ConfigDict(strict=True, extra="ignore")``
so that:

- Unknown JSON fields are dropped silently, keeping models resilient to
  future ``bd`` schema additions.
- Strict mode rejects unexpected type coercions (e.g. ``int`` → ``str``),
  catching upstream schema drift early.
- Enum fields (``BeadsStatus``, ``BeadsIssueType``, ``BeadsPriority``) are
  individually annotated with ``Field(strict=False)`` so that the plain
  JSON string and integer values produced by ``bd`` are coerced to enum
  instances without loosening strictness for non-enum fields.

The :func:`parse_*` functions are the **only** public entry points for
consuming raw ``bd`` output.  Downstream code must not call
``BeadsIssueRaw.model_validate`` directly; routing through the parse
functions ensures a single place to add error enrichment when needed.

Boundary type chain
-------------------
``bd`` subprocess → :class:`BdRunner.run_json` returns :data:`JsonValue`
→ parse function validates → typed model instance

``BeadsId`` is a :func:`typing.NewType` for the type-checker; Pydantic
fields that hold beads IDs use ``Annotated[str, StringConstraints(pattern=...)]``
for runtime pattern enforcement.
"""

from __future__ import annotations

from enum import IntEnum, StrEnum
from typing import Annotated, Final, NewType

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, TypeAdapter

from backlog_core.backends.bd_runner import JsonValue

__all__ = [
    "BeadsCommentRaw",
    "BeadsDependencyRaw",
    # Types
    "BeadsId",
    # Raw models
    "BeadsIssueRaw",
    "BeadsIssueType",
    "BeadsLabelRaw",
    "BeadsPriority",
    # Enums
    "BeadsStatus",
    "parse_dependency_list",
    # Parse functions
    "parse_issue",
    "parse_issue_list",
    "parse_ready_list",
]

# ---------------------------------------------------------------------------
# Identity types
# ---------------------------------------------------------------------------

#: Regex pattern for beads nanoid-prefixed issue identifiers.
#: Format: ``<slug>-<nanoid>`` e.g. ``bd-a3f8``, ``my-project-XkP9.2``.
_BEADS_ID_PATTERN: Final[str] = r"^[a-z][a-z0-9_-]*-[A-Za-z0-9.]+$"

#: NewType alias for beads issue IDs.  Use this in function signatures and
#: data-model fields outside the boundary layer to express that a ``str`` is
#: specifically a validated beads ID.
BeadsId = NewType("BeadsId", str)

#: Annotated string type enforcing the beads ID pattern at Pydantic
#: validation time.  Used in model field annotations; the ``NewType``
#: above is for the type-checker only.
_BeadsIdField = Annotated[str, StringConstraints(pattern=_BEADS_ID_PATTERN)]


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class BeadsStatus(StrEnum):
    """Issue lifecycle status values returned by the ``bd`` CLI."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    HOOKED = "hooked"
    DEFERRED = "deferred"
    PINNED = "pinned"
    CLOSED = "closed"


class BeadsIssueType(StrEnum):
    """Issue type labels returned by the ``bd`` CLI."""

    TASK = "task"
    BUG = "bug"
    FEATURE = "feature"
    EPIC = "epic"
    CHORE = "chore"
    DECISION = "decision"
    MOLECULE = "molecule"
    GATE = "gate"
    EVENT = "event"
    MESSAGE = "message"
    MERGE_REQUEST = "merge-request"


class BeadsPriority(IntEnum):
    """Numeric priority levels (lower is more urgent)."""

    P0 = 0
    P1 = 1
    P2 = 2
    P3 = 3
    P4 = 4


# ---------------------------------------------------------------------------
# Raw boundary models
# ---------------------------------------------------------------------------


class BeadsIssueRaw(BaseModel):
    """Raw representation of a single issue from ``bd show <id> --json`` or ``bd list --json``.

    Detailed issue shape from the beads CLI JSON output.

    Attributes:
        id: Beads nanoid-prefixed identifier, e.g. ``bd-a3f8``.
        title: Short human-readable summary.
        status: Current lifecycle status.
        type: Issue classification.
        priority: Numeric priority (0 = critical, 4 = backlog).
        description: Long-form description body, may be absent.
        notes: Supplementary notes, may be absent.
        metadata: Arbitrary key-value metadata set via ``bd update --metadata``.
            Used by the artifact provider to store the ``dh.artifacts`` manifest.
            The ``bd`` CLI may represent dot-notation keys (``dh.artifacts``) as
            either a nested dict ``{"dh": {"artifacts": ...}}`` or a flat key
            ``{"dh.artifacts": ...}`` — both are accepted at parse time.
        assignee: Username of the assigned user, may be absent.
        created_at: ISO-8601 creation timestamp, may be absent.
        updated_at: ISO-8601 last-update timestamp, may be absent.
        closed_at: ISO-8601 closure timestamp, absent when issue is open.
    """

    model_config = ConfigDict(strict=True, extra="ignore")

    id: _BeadsIdField
    title: str
    status: Annotated[BeadsStatus, Field(strict=False)]
    type: Annotated[BeadsIssueType, Field(strict=False)]
    priority: Annotated[BeadsPriority, Field(strict=False)]
    description: str | None = None
    notes: str | None = None
    metadata: dict[str, object] | None = None
    labels: list[str] | None = None
    assignee: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    closed_at: str | None = None


class BeadsDependencyRaw(BaseModel):
    """Raw representation of a dependency entry from ``bd dep --json``.

    Attributes:
        id: Beads nanoid-prefixed identifier of the depended-on issue.
        title: Short summary, may be absent in compact list responses.
        status: Lifecycle status of the depended-on issue, may be absent.
    """

    model_config = ConfigDict(strict=True, extra="ignore")

    id: _BeadsIdField
    title: str | None = None
    status: Annotated[BeadsStatus, Field(strict=False)] | None = None


class BeadsCommentRaw(BaseModel):
    """Raw representation of a comment from ``bd comments <id> --json``.

    Attributes:
        id: Opaque comment identifier (not a beads nanoid; format varies).
        body: Comment text.
        author: Username of the comment author, may be absent.
        created_at: ISO-8601 creation timestamp, may be absent.
    """

    model_config = ConfigDict(strict=True, extra="ignore")

    id: str
    body: str
    author: str | None = None
    created_at: str | None = None


class BeadsLabelRaw(BaseModel):
    """Raw representation of a label from ``bd labels --json``.

    Attributes:
        name: Label name (e.g. ``status:open``, ``priority:2``).
        color: Hex colour string, may be absent.
        description: Human-readable description, may be absent.
    """

    model_config = ConfigDict(strict=True, extra="ignore")

    name: str
    color: str | None = None
    description: str | None = None


# ---------------------------------------------------------------------------
# TypeAdapter singletons (built once at module load; thread-safe after that)
# ---------------------------------------------------------------------------

_issue_adapter: TypeAdapter[BeadsIssueRaw] = TypeAdapter(BeadsIssueRaw)
_issue_list_adapter: TypeAdapter[list[BeadsIssueRaw]] = TypeAdapter(list[BeadsIssueRaw])
_dep_list_adapter: TypeAdapter[list[BeadsDependencyRaw]] = TypeAdapter(list[BeadsDependencyRaw])


# ---------------------------------------------------------------------------
# Parse functions — sole public entry points for bd JSON output
# ---------------------------------------------------------------------------


def parse_issue(data: JsonValue) -> BeadsIssueRaw:
    """Validate and return a single issue from raw ``bd --json`` output.

    Parameters
    ----------
    data:
        Parsed JSON value (typically the return value of
        :meth:`~bd_runner.BdRunner.run_json`).

    Returns:
    -------
    BeadsIssueRaw
        Validated issue model.

    Raises:
    ------
    pydantic.ValidationError
        When *data* does not conform to :class:`BeadsIssueRaw`.
    """
    return _issue_adapter.validate_python(data)


def parse_issue_list(data: JsonValue) -> list[BeadsIssueRaw]:
    """Validate and return a list of issues from raw ``bd list --json`` output.

    Parameters
    ----------
    data:
        Parsed JSON value, expected to be a JSON array of issue objects.

    Returns:
    -------
    list[BeadsIssueRaw]
        List of validated issue models.

    Raises:
    ------
    pydantic.ValidationError
        When *data* is not a list or any element fails validation.
    """
    return _issue_list_adapter.validate_python(data)


def parse_ready_list(data: JsonValue) -> list[BeadsIssueRaw]:
    """Validate and return a list of ready issues from ``bd ready --json``.

    ``bd ready`` returns the same JSON shape as ``bd list``.  This
    function is a dedicated entry point so callers can be explicit about
    the source command.

    Parameters
    ----------
    data:
        Parsed JSON value, expected to be a JSON array of issue objects.

    Returns:
    -------
    list[BeadsIssueRaw]
        List of validated issue models.

    Raises:
    ------
    pydantic.ValidationError
        When *data* is not a list or any element fails validation.
    """
    return _issue_list_adapter.validate_python(data)


def parse_dependency_list(data: JsonValue) -> list[BeadsDependencyRaw]:
    """Validate and return a dependency list from ``bd dep --json``.

    Parameters
    ----------
    data:
        Parsed JSON value, expected to be a JSON array of dependency objects.

    Returns:
    -------
    list[BeadsDependencyRaw]
        List of validated dependency models.

    Raises:
    ------
    pydantic.ValidationError
        When *data* is not a list or any element fails validation.
    """
    return _dep_list_adapter.validate_python(data)
