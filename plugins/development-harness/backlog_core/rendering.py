"""Backend-neutral rendering utilities for backlog sections.

This module extracts rendering logic from ``github_sync`` into a shared,
backend-agnostic location.  All three BacklogBackend implementations (GitHub,
SQLite, memory) import from here so that section rendering is identical across
backends.

Dependency direction (must remain acyclic):
    models <- rendering

Do not import from github_sync, operations, gh_client, or server.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .models import Section

if TYPE_CHECKING:
    from .models import GroomedData

__all__ = [
    "GROOMED_SUBSECTION_ORDER",
    "SECTION_HEADING",
    "heading_to_unknown_key",
    "normalize_unknown_sections",
    "render_groomed_section",
    "section_display_title",
    "unknown_key_to_heading",
]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Section key (used in BacklogItem.sections) -> markdown heading text.
#
# The first three entries (fact_check, rt_ica, issue_classification) need an
# explicit mapping because their correct display form cannot be derived by
# the generic unknown-section fallback (title-casing "rt_ica" produces "Rt
# Ica", not the acronym-cased "RT-ICA"; "fact_check" needs a hyphen, not a
# space). Every entry below this point DOES already round-trip correctly
# through the generic unknown__ fallback (#2956's write-path/parse-path fix
# makes that true for ANY section name, registered or not) — registering
# them here is a display-quality improvement only, not a correctness fix:
# it gives grooming's most commonly observed sections a clean canonical
# storage key (e.g. "files") instead of the "unknown__" prefix. Sourced from
# a full grep of the real corrupted local cache for #2953/#2955 (the
# ground-truth evidence for #2956) plus every literal `section=` value found
# across plugins/development-harness/agents/*.md and skill references
# (2026-08-18) — not a guessed or partial list.
SECTION_HEADING: dict[str, str] = {
    "fact_check": "Fact-Check",
    "rt_ica": "RT-ICA",
    "issue_classification": "Issue Classification",
    "files": "Files",
    "resources": "Resources",
    "impact": "Impact",
    "impact_radius": "Impact Radius",
    "dependencies": "Dependencies",
    "priority": "Priority",
    "benefits": "Benefits",
    "research": "Research",
    "design_intent_alignment": "Design Intent Alignment",
    "acceptance_criteria": "Acceptance Criteria",
    "expected_behavior": "Expected Behavior",
    "effort": "Effort",
    "reproducibility": "Reproducibility",
    "story": "Story",
    "context": "Context",
    "working_register": "Working Register",
    "suggested_location": "Suggested Location",
    "concerns": "Concerns",
    "divergence_notes": "Divergence Notes",
    "execution_results": "Execution Results",
    "grooming_notes": "Grooming Notes",
    "root_cause_analysis": "Root-Cause Analysis",
}

# Frozenset of the display values in SECTION_HEADING.
# Used by section_display_title to recognise display-name keys stored verbatim
# (e.g. "RT-ICA") that bypass the snake_case lookup but are already correct.
_SECTION_HEADING_VALUES: frozenset[str] = frozenset(SECTION_HEADING.values())

# Canonical render order for GroomedData subsections (heading text as stored)
GROOMED_SUBSECTION_ORDER: list[str] = [
    "Priority",
    "Impact",
    "Benefits",
    "Expected Behavior",
    "Desired Structure",
    "Acceptance Criteria",
    "Resources",
    "Dependencies",
    "Effort",
]

# ---------------------------------------------------------------------------
# Heading <-> key helpers
# ---------------------------------------------------------------------------


def unknown_key_to_heading(key: str) -> str:
    """Reconstruct a display heading from an unknown-section storage key.

    Reverses the ``unknown__`` prefixing: strips the prefix, replaces
    underscores with spaces, and title-cases the result.

    Args:
        key: Storage key such as ``"unknown__custom_analysis"``.

    Returns:
        Display heading such as ``"Custom Analysis"``.
    """
    stripped = key.removeprefix("unknown__")
    return stripped.replace("_", " ").title()


def heading_to_unknown_key(heading_text: str) -> str:
    """Convert an arbitrary section heading/name to its canonical storage key.

    Inverse of :func:`unknown_key_to_heading`. Normalises by lowercasing and
    replacing spaces with underscores, then prepends the ``"unknown__"``
    prefix so unknown section keys never collide with :data:`SECTION_HEADING`
    keys (e.g. ``"fact_check"``).

    This is the single normalisation used on both sides of the local-write /
    GitHub-parse boundary: :mod:`operations` calls it when storing a section
    under a caller-supplied display name, and :mod:`github_sync` calls it when
    parsing an unrecognised ``## Heading`` from an issue body. Keeping both
    call sites on one function is what makes the two round-trip to the same
    key — see ``ARCHITECTURE.md`` for the incident this closed.

    Strips leading/trailing whitespace before normalising, defensively —
    :mod:`github_sync`'s caller already strips its extracted heading text
    before calling this function, but a local write's caller-supplied name
    was not guaranteed to be pre-trimmed; a trailing space surviving into the
    key (``"unknown__files_"`` vs. ``"unknown__files"``) reproduces the exact
    write-path/parse-path key divergence this function exists to prevent.

    Args:
        heading_text: Raw heading or section display name.

    Returns:
        Storage key such as ``"unknown__custom_analysis"``.
    """
    normalised = heading_text.strip().lower().replace(" ", "_")
    return f"unknown__{normalised}"


def normalize_unknown_sections(sections: dict[str, Section | GroomedData]) -> dict[str, Section | GroomedData]:
    """Fold ``unknown__{key}`` entries into ``{key}`` when now canonical.

    A local YAML cache written before a name was registered in
    :data:`SECTION_HEADING` stores it as ``unknown__{key}`` (e.g.
    ``unknown__story``).  Once that name becomes canonical, a freshly parsed
    GitHub body produces the same logical section under the plain key
    (``story``) instead — two different dict keys for one heading, which
    survive :func:`github_sync.merge_item`'s key-union merge and render as a
    duplicated ``## Story`` heading (#2956 follow-up). Resolving legacy
    ``unknown__`` keys against the current registry at load time — before
    reconciliation ever sees the item — makes both sides collide on one key.

    When both ``unknown__{key}`` and ``{key}`` are present in the same
    ``sections`` dict (e.g. a manually edited cache file), their entries are
    concatenated, deduplicating by entry ``id``.

    Args:
        sections: Raw ``BacklogItem.sections`` mapping as loaded from storage.

    Returns:
        A new mapping with legacy ``unknown__{key}`` keys folded into their
        now-canonical counterparts. Keys that are not legacy, or whose
        ``unknown__`` name is still uncanonical, are returned unchanged.
    """
    normalized: dict[str, Section | GroomedData] = {}
    for key, value in sections.items():
        target = key
        if key.startswith("unknown__") and isinstance(value, Section):
            candidate = key.removeprefix("unknown__")
            if candidate in SECTION_HEADING:
                target = candidate
        existing = normalized.get(target)
        if isinstance(existing, Section) and isinstance(value, Section):
            seen_ids = {e.id for e in existing.entries}
            merged_entries = [*existing.entries, *(e for e in value.entries if e.id not in seen_ids)]
            normalized[target] = Section(entries=merged_entries)
        else:
            normalized[target] = value
    return normalized


# ---------------------------------------------------------------------------
# Rendering functions
# ---------------------------------------------------------------------------


def render_groomed_section(groomed: GroomedData) -> str:
    """Render a GroomedData as ``## Groomed ({date})`` with ``### subsection`` children.

    Subsections are emitted in canonical order defined by
    :data:`GROOMED_SUBSECTION_ORDER`.  Any keys not in the canonical list are
    appended alphabetically.

    Args:
        groomed: GroomedData to render.

    Returns:
        Rendered section string (no trailing newline).
    """
    parts: list[str] = [f"## Groomed ({groomed.date})"]
    ordered = [k for k in GROOMED_SUBSECTION_ORDER if k in groomed.subsections]
    extras = sorted(k for k in groomed.subsections if k not in GROOMED_SUBSECTION_ORDER)
    parts.extend(f"### {key}\n\n{groomed.subsections[key]}" for key in ordered + extras)
    return "\n\n".join(parts)


def section_display_title(key: str, groomed_date: str = "") -> str:
    """Return the human-readable title for a section key.

    Known keys are looked up in :data:`SECTION_HEADING`.  Unknown keys with
    the ``"unknown__"`` prefix are reconstructed via
    :func:`unknown_key_to_heading`.  The special ``"groomed"`` key returns
    ``"Groomed — {date}"`` when a date is provided.  All other keys are
    title-cased with underscores replaced by spaces.

    Args:
        key: Section storage key (e.g. ``"fact_check"``, ``"unknown__story"``).
        groomed_date: Optional date string from a ``GroomedData`` section, used
            to append the date to the ``"groomed"`` title.

    Returns:
        Display title string (e.g. ``"Fact-Check"``, ``"Story"``).
    """
    if key in SECTION_HEADING:
        return SECTION_HEADING[key]
    if key == "groomed":
        return f"Groomed \u2014 {groomed_date}" if groomed_date else "Groomed"
    if key.startswith("unknown__"):
        return unknown_key_to_heading(key)
    if key in _SECTION_HEADING_VALUES:
        return key
    return key.replace("_", " ").title()
