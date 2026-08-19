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

from .models import Entry, GroomedData, Section
from .section_registry import SECTION_HEADING, SUBSECTION_KEY_ORDER, resolve_section_name, resolve_subsection_name

__all__ = [
    "GROOMED_SUBSECTION_ORDER",
    "SECTION_HEADING",
    "heading_to_unknown_key",
    "merge_entries",
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


def merge_entries(local_entries: list[Entry], remote_entries: list[Entry]) -> list[Entry]:
    """Merge two entry lists into a single chronologically-ordered list.

    Merge rules (applied per entry id):
    - struck state wins over active for the same id
    - when both have the same struck state, longer content wins
    - entries unique to either side are always preserved
    - result is sorted chronologically by id

    Shared by :func:`github_sync.merge_item` (local vs. remote reconciliation)
    and :func:`normalize_unknown_sections` (folding an ``unknown__{key}`` and
    ``{key}`` pair within the same item) — one merge policy for "two entry
    lists that may both contain the same id", not a bespoke first-seen-wins
    rule per caller that could silently drop a struck or longer-content copy.

    Args:
        local_entries: Entries from one side (e.g. the local BacklogItem).
        remote_entries: Entries from the other side (e.g. the remote/GitHub
            BacklogItem, or a second key folding onto the same target).

    Returns:
        Merged list of Entry objects ordered by id (ascending).
    """
    local_by_id: dict[str, Entry] = {e.id: e for e in local_entries}
    remote_by_id: dict[str, Entry] = {e.id: e for e in remote_entries}

    merged: dict[str, Entry] = {}
    for eid in set(local_by_id) | set(remote_by_id):
        local_e = local_by_id.get(eid)
        remote_e = remote_by_id.get(eid)

        if local_e is None and remote_e is not None:
            merged[eid] = remote_e
        elif remote_e is None and local_e is not None:
            merged[eid] = local_e
        elif local_e is not None and remote_e is not None:
            if local_e.struck and not remote_e.struck:
                # struck wins over active
                merged[eid] = local_e
            elif remote_e.struck and not local_e.struck:
                merged[eid] = remote_e
            else:
                # same struck state — longer content wins; local wins on tie
                merged[eid] = local_e if len(local_e.content) >= len(remote_e.content) else remote_e

    return [merged[eid] for eid in sorted(merged)]


def normalize_unknown_sections(sections: dict[str, Section | GroomedData]) -> dict[str, Section | GroomedData]:
    """Fold non-canonical section keys into their registered counterpart.

    A local YAML cache written before a name was registered in
    :data:`SECTION_HEADING` stores it verbatim — either ``unknown__{key}``
    (e.g. ``unknown__story``, produced by the current write/parse boundary) or
    a bare, non-canonical key such as ``"Working Register"`` (produced by an
    older write path that returned an unresolved caller-supplied name
    unchanged instead of prefixing it — see #2956's write-path trace). Once
    that name becomes canonical, a freshly parsed GitHub body or a fresh write
    produces the same logical section under the plain registered key
    (``working_register``) instead — two different dict keys for one heading,
    which survive :func:`github_sync.merge_item`'s key-union merge and render
    as a duplicated ``## Working Register`` heading, with the newer key's
    entries silently lost on the next GitHub-body reparse (last-heading-wins
    in :func:`github_sync.extract_sections`) — #2956's live data-loss defect.
    Resolving *any* non-canonical key against the current registry at load
    time — before reconciliation ever sees the item — makes both sides
    collide on one key, whether the stale key carries the ``unknown__``
    prefix or not.

    A key already present in :data:`SECTION_HEADING` is left alone — it is
    already canonical, and re-resolving it is a no-op at best.

    When both a non-canonical key and its canonical counterpart are present
    in the same ``sections`` dict (e.g. a manually edited cache file, or a
    stale bare key alongside a fresh canonical write), their entries are
    merged through :func:`merge_entries` — the same struck-wins /
    longer-content-wins-per-id rule :func:`github_sync.merge_item` applies to
    local/remote reconciliation — rather than a bespoke first-seen-wins dedup
    that would silently drop a struck or longer-content copy sharing an id
    with the other key's entry. The canonical key's entries are always passed
    as :func:`merge_entries`' first (tie-break-winning) argument, regardless
    of which key ``sections`` happens to iterate first — the dict's key order
    is an incidental artifact of the caller (YAML load order, dict-literal
    order in a test), not a documented local/remote distinction, so the
    exact-tie winner must not depend on it (#3015 Copilot review finding).

    Recovery is routed through :func:`~.section_registry.resolve_section_name`
    — the same alias-aware resolver the write boundary
    (``operations._normalize_section_key``) and the GitHub-parse boundary
    (``github_sync.parse_issue_body``) both use — rather than a bespoke
    display-title-only comparison, so a legacy key whose reconstructed
    heading matches a registered *alias* (e.g. ``"unknown__facts_check"`` ->
    alias ``"facts check"`` -> canonical ``fact_check``), not only an exact
    :data:`SECTION_HEADING` display title, still folds.

    Two forms of the stored key are tried, in order: the raw key itself, with
    any ``unknown__`` prefix stripped (a no-op for a bare non-canonical key;
    already ``snake_case`` for keys produced by the current,
    punctuation-sanitizing :func:`heading_to_unknown_key`), then the
    reconstructed display heading (:func:`unknown_key_to_heading` output,
    also a no-op-safe title-case pass for a bare key already in that form) —
    the fallback that still supports older, more heavily punctuation-bearing
    ``unknown__`` keys (e.g. ``"unknown__output_/_evidence"``, whose raw
    stripped form never matches a ``SectionKey`` value but whose
    reconstructed title ``"Output / Evidence"`` does).

    A key that resolves to nothing (e.g. ``"Description"``, which
    ``github_sync.parse_issue_body`` special-cases as ``item.description``
    rather than a section, so it can never be a registered ``SectionKey``) is
    left unchanged — it is orphan data outside this function's recovery
    scope, not a bug this fold can fix.

    Args:
        sections: Raw ``BacklogItem.sections`` mapping as loaded from storage.

    Returns:
        A new mapping with legacy non-canonical keys folded into their
        now-canonical counterparts. Keys that are already canonical, or whose
        name is still unresolvable, are returned unchanged.
    """
    normalized: dict[str, Section | GroomedData] = {}
    # Tracks, per target key, whether the Section entries currently stored in
    # `normalized` include the canonical key's own entries — so a canonical
    # key encountered *after* its legacy counterpart still wins
    # merge_entries' tie-break, instead of losing simply because it folded
    # into `normalized[target]` second.
    canonical_owns: dict[str, bool] = {}
    for key, value in sections.items():
        target = key
        is_canonical_key = key in SECTION_HEADING
        if not is_canonical_key and isinstance(value, Section):
            stripped = key.removeprefix("unknown__")
            canonical = resolve_section_name(stripped) or resolve_section_name(unknown_key_to_heading(key))
            if canonical is not None:
                target = canonical
        existing = normalized.get(target)
        if isinstance(existing, Section) and isinstance(value, Section):
            existing_is_canonical = canonical_owns.get(target, False)
            if is_canonical_key and not existing_is_canonical:
                # `value` carries the canonical key's own entries but was
                # reached second — swap argument order so it is still the
                # tie-break-winning ("local") side of merge_entries.
                merged_entries = merge_entries(value.entries, existing.entries)
            else:
                merged_entries = merge_entries(existing.entries, value.entries)
            normalized[target] = Section(entries=merged_entries)
            canonical_owns[target] = existing_is_canonical or is_canonical_key
        elif isinstance(value, GroomedData):
            normalized[target] = GroomedData(
                date=value.date, subsections=normalize_groomed_subsections(value.subsections)
            )
        else:
            normalized[target] = value
            if isinstance(value, Section):
                canonical_owns[target] = is_canonical_key
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
    string value per key, not an entry list). On an exact length tie, the
    first-seen (canonical dict-iteration-order) value wins — matching
    :func:`github_sync._merge_groomed`'s strict ``>`` comparison, where the
    already-present ``local`` value is kept unless the incoming value is
    *strictly* longer, not merely as long.

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
        normalized[target] = content if len(content) > len(existing) else existing
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
