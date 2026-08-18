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

import re

from .models import GroomedData, Section
from .section_registry import SECTION_HEADING, SUBSECTION_KEY_ORDER, resolve_subsection_name

__all__ = [
    "GROOMED_SUBSECTION_ORDER",
    "SECTION_HEADING",
    "heading_to_unknown_key",
    "normalize_groomed_subsections",
    "normalize_unknown_sections",
    "render_groomed_section",
    "resolve_subsection_name",
    "section_display_title",
    "unknown_key_to_heading",
]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
#
# SECTION_HEADING is re-exported from section_registry — that module is the
# single canonical source of truth (SectionKey StrEnum + SECTION_NAME_ALIASES).
# See backlog_core/ARCHITECTURE.md "Module: section_registry.py" for the "how
# to add a section" template.

# Frozenset of the display values in SECTION_HEADING.
# Used by section_display_title to recognise display-name keys stored verbatim
# (e.g. "RT-ICA") that bypass the snake_case lookup but are already correct.
_SECTION_HEADING_VALUES: frozenset[str] = frozenset(SECTION_HEADING.values())

# Reverse lookup: lowercased display title -> canonical snake_case key.
# Used by normalize_unknown_sections to fold an unknown__ key into its
# now-canonical counterpart by comparing display titles rather than raw
# storage-key text, so a key produced under an older, less-sanitized
# heading_to_unknown_key() (e.g. "unknown__output_/_evidence") still folds
# once its title ("Output / Evidence") matches a registered entry.
_SECTION_HEADING_BY_LOWER_TITLE: dict[str, str] = {v.lower(): k for k, v in SECTION_HEADING.items()}

# Matches any run of characters that are not lowercase ASCII letters or
# digits, so heading_to_unknown_key() collapses ALL punctuation (spaces,
# slashes, etc.) to a single separator instead of only spaces.
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")

# Canonical render order for GroomedData subsections — re-exported from
# section_registry.SUBSECTION_KEY_ORDER (derived from the SubsectionKey enum)
# under its historic name so existing callers are unaffected.
GROOMED_SUBSECTION_ORDER: list[str] = SUBSECTION_KEY_ORDER

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
    collapsing every run of non-alphanumeric characters (spaces, slashes,
    punctuation) to a single underscore, then prepends the ``"unknown__"``
    prefix so unknown section keys never collide with :data:`SECTION_HEADING`
    keys (e.g. ``"fact_check"``). Sanitizing all punctuation — not just
    spaces — keeps the derivation stable for any future name containing a
    character like ``/`` (see #2979 follow-up: ``"Output / Evidence"``
    previously produced ``"unknown__output_/_evidence"``, a key that could
    never match a later-registered ``"output_evidence"`` SECTION_HEADING
    entry via plain string equality).

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
    normalised = _NON_ALNUM_RE.sub("_", heading_text.strip().lower()).strip("_")
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

    The fold matches by display title (:func:`unknown_key_to_heading` output),
    not by raw key-string equality — so a legacy ``unknown__`` key produced
    before :func:`heading_to_unknown_key` sanitized punctuation (e.g.
    ``"unknown__output_/_evidence"``, whose title is ``"Output / Evidence"``)
    still folds into a later-registered canonical key even though its raw
    text never matches the key sanitized writes now produce.

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
            canonical = _SECTION_HEADING_BY_LOWER_TITLE.get(unknown_key_to_heading(key).lower())
            if canonical is not None:
                target = canonical
        existing = normalized.get(target)
        if isinstance(existing, Section) and isinstance(value, Section):
            seen_ids = {e.id for e in existing.entries}
            merged_entries = [*existing.entries, *(e for e in value.entries if e.id not in seen_ids)]
            normalized[target] = Section(entries=merged_entries)
        elif isinstance(value, GroomedData):
            normalized[target] = GroomedData(
                date=value.date, subsections=normalize_groomed_subsections(value.subsections)
            )
        else:
            normalized[target] = value
    return normalized


def normalize_groomed_subsections(subsections: dict[str, str]) -> dict[str, str]:
    """Fold aliased or miscased subsection keys into their canonical spelling.

    Mirrors :func:`normalize_unknown_sections` one level deeper, applying the
    same registry-plus-alias-plus-fold pattern to ``GroomedData.subsections``
    via :func:`~.section_registry.resolve_subsection_name` instead of a
    bespoke, one-off comparison.

    When two keys fold onto the same canonical name (e.g. a legacy cache held
    both ``"priority"`` and ``"Priority"``), the longer content wins — the
    same per-key rule :func:`github_sync._merge_groomed` already uses to
    merge local and remote ``GroomedData``, reused here rather than inventing
    a second merge policy for what is the same kind of collision (single
    string value per key, not an entry list).

    Args:
        subsections: Raw ``GroomedData.subsections`` mapping as loaded from
            storage.

    Returns:
        A new mapping with resolvable keys folded to their canonical
        spelling. Keys that resolve_subsection_name does not recognise are
        returned unchanged — an unregistered subsection name is legitimate
        free text, not an error.
    """
    normalized: dict[str, str] = {}
    for key, content in subsections.items():
        target = resolve_subsection_name(key) or key
        existing = normalized.get(target, "")
        normalized[target] = content if len(content) >= len(existing) else existing
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
