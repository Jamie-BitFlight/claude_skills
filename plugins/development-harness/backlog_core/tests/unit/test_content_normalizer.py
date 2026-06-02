"""Tests for ItemContentNormalizer.normalize() — TDD, authored before T12 implementation.

These tests intentionally fail at collection (ModuleNotFoundError) until T12
creates ``backlog_core/content_normalizer.py``. That is the correct TDD state.

Behavioral contract pinned by this file:

1. **Order from [N] lines**: normalize() returns sections ordered by the ``[N] Title``
   lines found in the body's ``## Sections`` block (prepended by view_item()) or
   the ``sections_index`` field (summary path) — NOT by ``dict.keys()`` iteration.
2. **Empty sections included**: A section with 0 entries appears as
   ``NormalizedSection(entries=[])`` — ordinal position is not compressed.
3. **Un-gated content produces non-empty list**: The full un-gated result for a large
   item (#2515) normalizes to a non-empty list, guarding against the gated-path trap.
4. **Ordinals match position**: ``NormalizedSection.index`` equals its 0-based position
   in the returned list.

Implementation note for T12
---------------------------
In the full-content ``view_item()`` path (``include_content=True``), the
``ViewItemResult.sections_index`` FIELD is empty (``""``). The ``[N] Title``
canonical ordering appears in the body, prepended as a ``## Sections`` block
(``operations.py`` line ~3229: ``result.body = pending_index + "\\n" + result.body``).
The ``sections_index`` field is only populated by the summary path
(``include_content=False``). The normalizer must derive order from whichever source
is present — body ``## Sections`` block when field is empty, field when body is empty.
See DN-1 in this plan task for the design-refinement record.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# Intentionally fails at collection until T12 creates this module.
from backlog_core.content_normalizer import ItemContentNormalizer, NormalizedEntry, NormalizedSection
from backlog_core.models import GroomedSectionMetadata, SectionEntryDict, SectionEntryMetadata, ViewItemResult

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _body_sections_block(order: list[tuple[str, int]]) -> str:
    """Build the ``## Sections`` index block that ``view_item()`` prepends to body.

    Args:
        order: ``(section_title, num_entries)`` pairs in canonical order.

    Returns:
        String ``"## Sections\\n[0] Title (N entries)\\n..."`` ending with ``\\n``.
    """
    lines = ["## Sections"]
    for idx, (title, count) in enumerate(order):
        lines.append(f"[{idx}] {title} ({count} entries)")
    return "\n".join(lines) + "\n"


def _entry_dict(content: str, entry_id: str = "test-id") -> SectionEntryDict:
    """Create a minimal SectionEntryDict for test fixtures."""
    return SectionEntryDict(id=entry_id, struck=False, content=content)


def _section(contents: list[str]) -> SectionEntryMetadata | GroomedSectionMetadata:
    """Build a SectionEntryMetadata with the given entry contents."""
    entries: list[SectionEntryDict] = [_entry_dict(c, f"e{i}") for i, c in enumerate(contents)]
    return SectionEntryMetadata(num_entries=len(entries), num_struck=0, entries=entries)


def _load_fixture(name: str) -> dict[str, object]:
    """Load a regenerated JSON fixture from tests/fixtures/."""
    path = FIXTURES_DIR / name
    return json.loads(path.read_text(encoding="utf-8"))  # type: ignore[return-value]


def _fixture_sections(data: dict[str, object]) -> dict[str, dict[str, object]]:
    """Extract and narrow the ``sections`` dict from fixture data.

    JSON fixtures arrive as ``dict[str, object]``; ty cannot narrow the value
    type after a plain ``isinstance(v, dict)`` guard because the key type of
    ``dict[Unknown, Unknown]`` resolves to ``Never``.  This boundary helper
    performs the narrowing explicitly, returning a properly-typed dict that
    downstream test code can subscript and call ``.get()`` on without type errors.
    """
    raw = data.get("sections")
    if not isinstance(raw, dict):
        return {}
    result: dict[str, dict[str, object]] = {}
    for k, v in raw.items():
        if isinstance(k, str) and isinstance(v, dict):
            result[k] = {str(fk): fv for fk, fv in v.items()}
    return result


def _extract_body_section_order(body: str) -> list[str]:
    """Parse the ``## Sections`` block at the start of body, return ordered titles.

    Handles section titles that contain ``(`` (e.g. ``Groomed (2026-06-01)``).
    """
    titles: list[str] = []
    for line in body.split("\n"):
        if not (line.startswith("[") and "] " in line):
            continue
        after_bracket = line[line.index("] ") + 2 :]
        # Format: "Title (N entries)" — rsplit on last " (" to handle "(date)" in title.
        title = after_bracket.rsplit(" (", 1)[0]
        titles.append(title)
    return titles


# ---------------------------------------------------------------------------
# TC-N1: Order derives from [N] listing, not dict.keys()
# ---------------------------------------------------------------------------


class TestNormalizerOrderFromSectionsIndex:
    """normalize() order matches [N] lines — never dict.keys() insertion order."""

    def test_body_sections_block_order_overrides_dict_keys(self) -> None:
        """When body ## Sections lists sections in a different order than dict.keys(),
        normalize() MUST follow the ## Sections block.

        This is the authoritative test for the canonical-order invariant
        (architect spec §4.2.1): "sections ORDER is always derived from
        sections_index [N] lines, not from dict.keys() iteration."

        Input shape: full-content view_item() path where sections_index field is
        empty and order lives in the prepended body ## Sections block.
        """
        # Dict keys: Alpha → Beta → Gamma (insertion order)
        # Body ## Sections block: Gamma [0], Alpha [1], Beta [2]  (reversed)
        # normalize() MUST return Gamma, Alpha, Beta.
        sections: dict[str, SectionEntryMetadata | GroomedSectionMetadata] = {
            "Alpha": _section(["alpha content"]),
            "Beta": _section(["beta 1", "beta 2"]),
            "Gamma": _section(["gamma content"]),
        }
        body = _body_sections_block([("Gamma", 1), ("Alpha", 1), ("Beta", 2)])

        normalized = ItemContentNormalizer().normalize(ViewItemResult(sections=sections, body=body, sections_index=""))

        assert len(normalized) == 3, f"Expected 3 sections; got {len(normalized)}."
        assert normalized[0].title == "Gamma", (
            f"[0]=Gamma must be first; got {normalized[0].title!r}. "
            "Order MUST follow ## Sections block, not dict.keys()."
        )
        assert normalized[1].title == "Alpha", f"[1]=Alpha must be second; got {normalized[1].title!r}."
        assert normalized[2].title == "Beta", f"[2]=Beta must be third; got {normalized[2].title!r}."

    def test_sections_index_field_order_overrides_dict_keys(self) -> None:
        """When sections_index FIELD is populated (summary path), its [N] ordering governs.

        This tests the alternative input shape: body is empty, sections_index field
        carries the canonical ordering (produced by view_item(include_content=False)).
        """
        sections: dict[str, SectionEntryMetadata | GroomedSectionMetadata] = {
            "Alpha": _section(["a"]),
            "Beta": _section(["b"]),
            "Gamma": _section(["g"]),
        }
        # sections_index field has Gamma first
        si_field = _body_sections_block([("Gamma", 1), ("Alpha", 1), ("Beta", 1)])

        normalized = ItemContentNormalizer().normalize(
            ViewItemResult(sections=sections, sections_index=si_field, body="")
        )

        assert len(normalized) == 3
        assert normalized[0].title == "Gamma", (
            f"sections_index field [0]=Gamma must be first; got {normalized[0].title!r}."
        )
        assert normalized[1].title == "Alpha"
        assert normalized[2].title == "Beta"

    def test_normalized_section_index_field_equals_position(self) -> None:
        """NormalizedSection.index must equal the section's 0-based list position."""
        sections: dict[str, SectionEntryMetadata | GroomedSectionMetadata] = {
            "A": _section(["a"]),
            "B": _section(["b"]),
            "C": _section(["c"]),
        }
        body = _body_sections_block([("A", 1), ("B", 1), ("C", 1)])

        normalized = ItemContentNormalizer().normalize(ViewItemResult(sections=sections, body=body, sections_index=""))

        for pos, section in enumerate(normalized):
            assert section.index == pos, (
                f"NormalizedSection.index must be {pos}; got {section.index} for {section.title!r}."
            )


# ---------------------------------------------------------------------------
# TC-N2: Empty sections (0 entries) appear with entries=[] and correct ordinal
# ---------------------------------------------------------------------------


class TestNormalizerEmptySection:
    """Empty sections appear in output — ordinal position is preserved, not skipped."""

    def test_zero_entry_section_included_with_empty_entries_list(self) -> None:
        """A section with 0 entries must appear as NormalizedSection with entries=[].

        Architect spec §4.2.1: "Empty sections (0 entries) are included as
        NormalizedSection with entries=[]. Their ordinal position is still counted."
        """
        sections: dict[str, SectionEntryMetadata | GroomedSectionMetadata] = {
            "Intro": _section(["intro content"]),
            "Groomed (2026-06-01)": _section([]),  # 0 entries — the empty section
            "Analysis": _section(["analysis content"]),
        }
        body = _body_sections_block([("Intro", 1), ("Groomed (2026-06-01)", 0), ("Analysis", 1)])

        normalized = ItemContentNormalizer().normalize(ViewItemResult(sections=sections, body=body, sections_index=""))

        assert len(normalized) == 3, f"All 3 sections (including empty Groomed) must appear; got {len(normalized)}."
        groomed = normalized[1]
        assert groomed.title == "Groomed (2026-06-01)", (
            f"Position 1 must be the empty Groomed section; got {groomed.title!r}."
        )
        assert groomed.entries == [], f"Groomed section must have entries=[]; got {groomed.entries!r}."
        assert groomed.index == 1, f"Empty section ordinal must be 1 (position preserved); got {groomed.index}."

    def test_sections_after_empty_section_have_correct_ordinal(self) -> None:
        """Sections after an empty section keep their correct ordinal — no gap compression."""
        sections: dict[str, SectionEntryMetadata | GroomedSectionMetadata] = {
            "A": _section(["a"]),
            "Empty": _section([]),
            "C": _section(["c"]),
        }
        body = _body_sections_block([("A", 1), ("Empty", 0), ("C", 1)])

        normalized = ItemContentNormalizer().normalize(ViewItemResult(sections=sections, body=body, sections_index=""))

        assert normalized[2].title == "C", f"Third section must be C; got {normalized[2].title!r}."
        assert normalized[2].index == 2, (
            f"C must have index=2 (no gap due to empty section at 1); got {normalized[2].index}."
        )


# ---------------------------------------------------------------------------
# TC-N3: NormalizedEntry structure — index and content fields
# ---------------------------------------------------------------------------


class TestNormalizedEntryStructure:
    """Each NormalizedEntry has index (0-based within section) and content fields."""

    def test_entries_have_correct_index_and_content(self) -> None:
        """NormalizedEntry.index is 0-based within its parent section; content is preserved."""
        sections: dict[str, SectionEntryMetadata | GroomedSectionMetadata] = {
            "Tasks": _section(["first task", "second task", "third task"])
        }
        body = _body_sections_block([("Tasks", 3)])

        normalized = ItemContentNormalizer().normalize(ViewItemResult(sections=sections, body=body, sections_index=""))

        assert len(normalized) == 1
        tasks_section = normalized[0]
        assert len(tasks_section.entries) == 3, f"Tasks section must have 3 entries; got {len(tasks_section.entries)}."
        for i, entry in enumerate(tasks_section.entries):
            assert isinstance(entry, NormalizedEntry), f"Entry {i} must be NormalizedEntry; got {type(entry).__name__}."
            assert entry.index == i, f"NormalizedEntry.index must be {i} (0-based within section); got {entry.index}."


# ---------------------------------------------------------------------------
# TC-N4: #2521 fixture — under-budget item with Groomed empty section
# ---------------------------------------------------------------------------


class TestNormalizerIssue2521Fixture:
    """Under-budget fixture #2521: all sections returned, Groomed appears with entries=[]."""

    @pytest.fixture(scope="class")
    def data_2521(self) -> dict[str, object]:
        return _load_fixture("issue-2521-full.json")

    def test_returns_one_section_per_fixture_section(self, data_2521: dict[str, object]) -> None:
        """normalize() on #2521 returns exactly as many sections as the fixture has."""
        sections = _fixture_sections(data_2521)
        expected = len(sections)

        result = ViewItemResult.model_validate(data_2521)
        normalized = ItemContentNormalizer().normalize(result)

        assert len(normalized) == expected, f"Expected {expected} sections from #2521 fixture; got {len(normalized)}."

    def test_order_matches_body_sections_block(self, data_2521: dict[str, object]) -> None:
        """Normalized section titles match the order in the body ## Sections block."""
        body = str(data_2521.get("body", ""))
        assert body.startswith("## Sections"), "Precondition: #2521 body must start with the ## Sections index block."
        expected_titles = _extract_body_section_order(body)
        assert expected_titles, "Precondition: extracted title list must be non-empty."

        result = ViewItemResult.model_validate(data_2521)
        normalized = ItemContentNormalizer().normalize(result)

        actual_titles = [s.title for s in normalized]
        assert actual_titles == expected_titles, (
            "Section title order must match the body ## Sections block.\n"
            f"Expected: {expected_titles}\n"
            f"Got:      {actual_titles}"
        )

    def test_groomed_section_has_empty_entries(self, data_2521: dict[str, object]) -> None:
        """The Groomed (2026-06-01) section in #2521 appears in output with entries=[]."""
        groomed_title = "Groomed (2026-06-01)"
        sections = _fixture_sections(data_2521)
        assert groomed_title in sections, f"Precondition: fixture must contain {groomed_title!r}."
        meta = sections[groomed_title]
        assert meta.get("num_entries") == 0, (
            f"Precondition: Groomed section must have num_entries=0; got {meta.get('num_entries')}."
        )

        result = ViewItemResult.model_validate(data_2521)
        normalized = ItemContentNormalizer().normalize(result)

        groomed_hits = [s for s in normalized if s.title == groomed_title]
        assert len(groomed_hits) == 1, f"Exactly one {groomed_title!r} must appear; got {len(groomed_hits)}."
        assert groomed_hits[0].entries == [], (
            f"Empty Groomed section must have entries=[]; got {groomed_hits[0].entries!r}."
        )


# ---------------------------------------------------------------------------
# TC-N5: #2515 fixture — over-budget un-gated result, guards gated-path trap
# ---------------------------------------------------------------------------


class TestNormalizerIssue2515Fixture:
    """Large fixture #2515: full un-gated result normalizes to complete section list.

    The 'gated-path trap': the gated backlog_view path returns body='', sections={}
    for over-budget items.  A normalizer that relied on the gated path would return
    an empty list.  The handler calls view_item() directly (un-gated) to get full
    content.  These tests verify the normalizer handles the un-gated full result.
    """

    @pytest.fixture(scope="class")
    def data_2515(self) -> dict[str, object]:
        return _load_fixture("issue-2515-full.json")

    @pytest.fixture(scope="class")
    def normalized_2515(self, data_2515: dict[str, object]) -> list[NormalizedSection]:
        result = ViewItemResult.model_validate(data_2515)
        return ItemContentNormalizer().normalize(result)

    def test_returns_non_empty_list(self, normalized_2515: list[NormalizedSection]) -> None:
        """normalize() on full un-gated #2515 content must return at least one section.

        An empty return would indicate the gated-path trap: receiving body='',
        sections={} and returning nothing.
        """
        assert len(normalized_2515) > 0, (
            "normalize() on full un-gated #2515 must not return an empty list. "
            "An empty result means the normalizer received the gated-path shape."
        )

    def test_all_sections_present(self, data_2515: dict[str, object], normalized_2515: list[NormalizedSection]) -> None:
        """normalize() returns at least as many sections as unique names in the fixture dict.

        The body ## Sections block may list duplicate section names (e.g. two
        "Acceptance Criteria" lines).  The normalizer emits one NormalizedSection
        per [N] line, so len(result) >= len(sections-dict).  The exact order and
        count are pinned by test_order_matches_body_sections_block.
        """
        sections = _fixture_sections(data_2515)
        expected = len(sections)
        assert expected > 0, "Precondition: #2515 must have sections."

        assert len(normalized_2515) >= expected, (
            f"At least {expected} sections from #2515 must appear; got {len(normalized_2515)}."
        )

    def test_all_elements_are_normalized_sections(self, normalized_2515: list[NormalizedSection]) -> None:
        """Every element is a properly-typed NormalizedSection with correct field types."""
        for i, section in enumerate(normalized_2515):
            assert isinstance(section, NormalizedSection), (
                f"Item {i} must be NormalizedSection; got {type(section).__name__}."
            )
            assert isinstance(section.index, int), (
                f"section.index at position {i} must be int; got {type(section.index).__name__}."
            )
            assert isinstance(section.title, str), (
                f"section.title at position {i} must be str; got {type(section.title).__name__}."
            )
            assert isinstance(section.entries, list), (
                f"section.entries at position {i} must be list; got {type(section.entries).__name__}."
            )
            for j, entry in enumerate(section.entries):
                assert isinstance(entry, NormalizedEntry), (
                    f"Section {section.title!r} entry {j} must be NormalizedEntry; got {type(entry).__name__}."
                )

    def test_empty_sections_in_2515_have_no_entries(
        self, data_2515: dict[str, object], normalized_2515: list[NormalizedSection]
    ) -> None:
        """Empty sections in #2515 (e.g. Groomed, Research) appear with entries=[]."""
        sections = _fixture_sections(data_2515)
        empty_titles = [title for title, meta in sections.items() if meta.get("num_entries") == 0]
        assert len(empty_titles) > 0, "Precondition: #2515 must contain at least one section with 0 entries."

        normalized_by_title = {s.title: s for s in normalized_2515}
        for title in empty_titles:
            assert title in normalized_by_title, f"Empty section {title!r} must appear in normalized output."
            section = normalized_by_title[title]
            assert section.entries == [], (
                f"Section {title!r} has 0 entries in fixture; "
                f"normalize() must return entries=[]; got {section.entries!r}."
            )

    def test_order_matches_body_sections_block(
        self, data_2515: dict[str, object], normalized_2515: list[NormalizedSection]
    ) -> None:
        """Normalized section order matches the ## Sections block in the #2515 body."""
        body = str(data_2515.get("body", ""))
        assert body.startswith("## Sections"), "Precondition: #2515 body must start with the ## Sections block."
        expected_titles = _extract_body_section_order(body)
        assert expected_titles, "Precondition: ## Sections block must list sections."

        actual_titles = [s.title for s in normalized_2515]
        assert actual_titles == expected_titles, (
            "Section title order must match ## Sections block from #2515 body.\n"
            f"Expected: {expected_titles}\n"
            f"Got:      {actual_titles}"
        )
