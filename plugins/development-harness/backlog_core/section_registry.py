"""Canonical section-name registry — the single source of truth for backlog section keys.

Backlog items use two independent naming layers, each governed by its own
enum + alias map + case-insensitive resolver in this module:

- **Sections** (``BacklogItem.sections`` keys): a canonical ``snake_case`` storage
  key (e.g. ``"fact_check"``) paired with a display heading (e.g. ``"Fact-Check"``).
- **Subsections** (``GroomedData.subsections`` keys): the display text itself is
  the storage key (e.g. ``"Priority"`` — there is no separate snake_case form).

Both the write path (``operations._normalize_section_key``,
``github_sync._parse_groomed_section``) and the read path
(``rendering.normalize_unknown_sections``) resolve names through the functions
here, so a name is registered once and behaves identically everywhere it is
read or written.

Dependency direction (must remain acyclic):
    section_registry <- everything else

This module imports nothing from the rest of ``backlog_core`` — it is a leaf,
even more foundational than ``models.py`` — so any module may import from it
without risking a cycle.

How to add a new canonical section
-----------------------------------
1. Append a member to :class:`SectionKey` — the value is the ``snake_case``
   storage key (e.g. ``PROGRESS_NOTES = "progress_notes"``).
2. Add a matching ``(SectionKey.PROGRESS_NOTES, "Progress Notes")`` entry to
   :data:`_SECTION_DISPLAY` — the display heading rendered in GitHub markdown.
3. If a deprecated or historic alternate spelling exists for the name (e.g. an
   agent doc previously wrote ``"Progress notes"`` or ``"Progress-Notes"``),
   add ``"progress notes": SectionKey.PROGRESS_NOTES.value`` to
   :data:`SECTION_NAME_ALIASES` (lowercased key -> canonical value). Aliases
   are historic-spelling recovery only — never the primary registration.

How to add a new canonical subsection (``GroomedData.subsections``)
---------------------------------------------------------------------
1. Append a member to :class:`SubsectionKey` — the value IS the display text
   used verbatim as the storage key (e.g. ``RISKS = "Risks"``).
2. If a deprecated or historic alternate spelling exists, add it to
   :data:`SUBSECTION_NAME_ALIASES` the same way as section aliases.

See ``backlog_core/ARCHITECTURE.md`` "Module: section_registry.py" for the
incident (#2956, #2970) this registry exists to prevent: agents independently
hardcoding section-name strings with no shared source of truth, silently
accumulating unregistered ``unknown__`` keys.
"""

from __future__ import annotations

from enum import StrEnum

__all__ = [
    "SECTION_HEADING",
    "SECTION_NAME_ALIASES",
    "SUBSECTION_KEY_ORDER",
    "SUBSECTION_NAME_ALIASES",
    "SectionKey",
    "SubsectionKey",
    "resolve_section_name",
    "resolve_subsection_name",
]


class SectionKey(StrEnum):
    """Canonical ``snake_case`` storage keys for ``BacklogItem.sections``.

    Append new members here when registering a new section — see the module
    docstring's "How to add a new canonical section" steps.
    """

    FACT_CHECK = "fact_check"
    RT_ICA = "rt_ica"
    ISSUE_CLASSIFICATION = "issue_classification"
    FILES = "files"
    RESOURCES = "resources"
    IMPACT = "impact"
    IMPACT_RADIUS = "impact_radius"
    DEPENDENCIES = "dependencies"
    PRIORITY = "priority"
    BENEFITS = "benefits"
    RESEARCH = "research"
    DESIGN_INTENT_ALIGNMENT = "design_intent_alignment"
    ACCEPTANCE_CRITERIA = "acceptance_criteria"
    EXPECTED_BEHAVIOR = "expected_behavior"
    EFFORT = "effort"
    REPRODUCIBILITY = "reproducibility"
    STORY = "story"
    CONTEXT = "context"
    WORKING_REGISTER = "working_register"
    SUGGESTED_LOCATION = "suggested_location"
    CONCERNS = "concerns"
    DIVERGENCE_NOTES = "divergence_notes"
    EXECUTION_RESULTS = "execution_results"
    GROOMING_NOTES = "grooming_notes"
    ROOT_CAUSE_ANALYSIS = "root_cause_analysis"
    SCOPE = "scope"
    DESIRED_STRUCTURE = "desired_structure"
    OUTPUT_EVIDENCE = "output_evidence"


# Ordered (key, display heading) pairs — order is the canonical render order
# used by github_sync.render_issue_body's entry-bearing-sections loop.
_SECTION_DISPLAY: tuple[tuple[SectionKey, str], ...] = (
    (SectionKey.FACT_CHECK, "Fact-Check"),
    (SectionKey.RT_ICA, "RT-ICA"),
    (SectionKey.ISSUE_CLASSIFICATION, "Issue Classification"),
    (SectionKey.FILES, "Files"),
    (SectionKey.RESOURCES, "Resources"),
    (SectionKey.IMPACT, "Impact"),
    (SectionKey.IMPACT_RADIUS, "Impact Radius"),
    (SectionKey.DEPENDENCIES, "Dependencies"),
    (SectionKey.PRIORITY, "Priority"),
    (SectionKey.BENEFITS, "Benefits"),
    (SectionKey.RESEARCH, "Research"),
    (SectionKey.DESIGN_INTENT_ALIGNMENT, "Design Intent Alignment"),
    (SectionKey.ACCEPTANCE_CRITERIA, "Acceptance Criteria"),
    (SectionKey.EXPECTED_BEHAVIOR, "Expected Behavior"),
    (SectionKey.EFFORT, "Effort"),
    (SectionKey.REPRODUCIBILITY, "Reproducibility"),
    (SectionKey.STORY, "Story"),
    (SectionKey.CONTEXT, "Context"),
    (SectionKey.WORKING_REGISTER, "Working Register"),
    (SectionKey.SUGGESTED_LOCATION, "Suggested Location"),
    (SectionKey.CONCERNS, "Concerns"),
    (SectionKey.DIVERGENCE_NOTES, "Divergence Notes"),
    (SectionKey.EXECUTION_RESULTS, "Execution Results"),
    (SectionKey.GROOMING_NOTES, "Grooming Notes"),
    (SectionKey.ROOT_CAUSE_ANALYSIS, "Root-Cause Analysis"),
    (SectionKey.SCOPE, "Scope"),
    (SectionKey.DESIRED_STRUCTURE, "Desired Structure"),
    (SectionKey.OUTPUT_EVIDENCE, "Output / Evidence"),
)

# Section key (plain str, never the enum instance — this dict is iterated to
# build BacklogItem.sections dict keys, which Pydantic/ruamel.yaml must see as
# ordinary str, not a StrEnum subclass) -> markdown heading text.
SECTION_HEADING: dict[str, str] = {str(key): display for key, display in _SECTION_DISPLAY}

# Deprecated/historic alternate spellings -> canonical SectionKey value (plain str).
# Kept as a map DISTINCT from SECTION_HEADING (never merged into it): this is
# recovery for names a caller might still supply, not a second registration
# surface. Keys are matched case-insensitively (callers lowercase before
# lookup) — do not add mixed-case keys here, they will never match.
SECTION_NAME_ALIASES: dict[str, str] = {
    "fact-check": SectionKey.FACT_CHECK.value,
    "facts check": SectionKey.FACT_CHECK.value,
    "fact checker": SectionKey.FACT_CHECK.value,
    "rt-ica": SectionKey.RT_ICA.value,
    "issue-classification": SectionKey.ISSUE_CLASSIFICATION.value,
}


class SubsectionKey(StrEnum):
    """Canonical display-text keys for ``GroomedData.subsections``.

    Unlike :class:`SectionKey`, the enum value IS the storage key verbatim
    (subsections have no separate snake_case form) — append new members here
    per the module docstring's "How to add a new canonical subsection" steps.
    """

    CONTENT = "content"
    """Whole-body groomed content, written by ``operations._write_groomed_to_item``
    when its ``section_name`` argument is ``None`` — not produced by any ``###``
    Markdown heading, so it is registered here rather than in a producer template."""
    RT_ICA_ASSESSMENT = "RT-ICA Assessment"
    ARTIFACT_CLASSIFICATION = "Artifact Classification"
    REPRODUCIBILITY = "Reproducibility"
    OUTPUT_EVIDENCE = "Output / Evidence"
    PRIORITY = "Priority"
    IMPACT = "Impact"
    SCOPE = "Scope"
    BENEFITS = "Benefits"
    EXPECTED_BEHAVIOR = "Expected Behavior"
    DESIRED_STRUCTURE = "Desired Structure"
    ACCEPTANCE_CRITERIA = "Acceptance Criteria"
    HUMAN_INPUT = "Human Input"
    QUESTIONS_FOR_HUMAN = "Questions for Human"
    RESOURCES = "Resources"
    RESEARCH = "Research"
    SKILLS = "Skills"
    AGENTS = "Agents"
    PRIOR_WORK = "Prior Work"
    FILES = "Files"
    DEPENDENCIES = "Dependencies"
    BLOCKERS = "Blockers"
    EFFORT = "Effort"
    DECISION = "Decision"


# Canonical render order for GroomedData subsections — derived from SubsectionKey
# declaration order so rendering.py and this module cannot drift apart.
SUBSECTION_KEY_ORDER: list[str] = [str(key) for key in SubsectionKey]

# Deprecated/historic alternate subsection spellings -> canonical SubsectionKey
# value (plain str), matched case-insensitively. Empty today — no historic
# alternate subsection spelling has been observed in this repo's evidence
# (unlike SECTION_NAME_ALIASES, seeded from #2956/#2970's grep of real corrupted
# cache data). Populate using the same pattern the moment one is found; leaving
# this empty is not a stub, the resolver below already applies it uniformly.
SUBSECTION_NAME_ALIASES: dict[str, str] = {}

_SECTION_HEADING_BY_LOWER: dict[str, str] = {v.lower(): k for k, v in SECTION_HEADING.items()}
_SUBSECTION_BY_LOWER: dict[str, str] = {str(key).lower(): str(key) for key in SubsectionKey}


def resolve_section_name(name: str) -> str | None:
    """Resolve a caller-supplied section name to its canonical storage key.

    Lookup order: :data:`SECTION_NAME_ALIASES` (exact historic spelling),
    then the canonical ``snake_case`` :class:`SectionKey` value itself
    (covers a caller supplying the storage key verbatim, e.g.
    ``"fact_check"``), then a case-insensitive match against
    :data:`SECTION_HEADING` display text (covers callers supplying the
    display heading verbatim, e.g. ``"RT-ICA"``).

    Args:
        name: Caller-supplied section name, already stripped of surrounding
            whitespace.

    Returns:
        The canonical ``snake_case`` storage key, or ``None`` when *name*
        matches neither the alias map nor a registered display heading.
    """
    lowered = name.lower()
    alias = SECTION_NAME_ALIASES.get(lowered)
    if alias is not None:
        return alias
    if lowered in SECTION_HEADING:
        # SECTION_HEADING's keys ARE the canonical SectionKey values (see the
        # dict comprehension above) — a caller supplying the storage key
        # itself (e.g. "fact_check") is already canonical, not merely a
        # display-heading match.
        return lowered
    return _SECTION_HEADING_BY_LOWER.get(lowered)


def resolve_subsection_name(name: str) -> str | None:
    """Resolve a caller-supplied subsection name to its canonical storage key.

    Mirrors :func:`resolve_section_name` one level deeper: lookup order is
    :data:`SUBSECTION_NAME_ALIASES` then a case-insensitive match against
    :class:`SubsectionKey` values.

    Args:
        name: Caller-supplied subsection name, already stripped of
            surrounding whitespace.

    Returns:
        The canonical subsection storage key (display text, e.g.
        ``"Priority"``), or ``None`` when *name* matches neither the alias
        map nor a registered subsection.
    """
    lowered = name.lower()
    alias = SUBSECTION_NAME_ALIASES.get(lowered)
    if alias is not None:
        return alias
    return _SUBSECTION_BY_LOWER.get(lowered)
