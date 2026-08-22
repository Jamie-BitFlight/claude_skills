"""Regression tests for the ``_build_sections_metadata`` boundary-scanner defect (#3157).

``_build_sections_metadata`` used to scan section boundaries with the naive
``_SECTION_BOUNDARY_RE`` line regex (``^#{2,3} (.+?)$``), which matches ANY
``##``/``###`` line anywhere in the body — including a heading-shaped line that
is legitimately part of an entry's own content inside a
``<div><sub>...</sub>...</div>`` entry block.  ``parsing.extract_sections``
already solved the same problem correctly by delegating to the marko-AST,
entry-block-aware ``_split_body_h2`` splitter.  ``_build_sections_metadata``
now routes through the same splitter (``parsing.split_body_sections``,
generalized to also match ``### ``) so the two functions cannot disagree.

Observed real-world impact: backlog item #3152's ``Fact-Check`` section stores
one entry whose content legitimately contains 27 literal ``## Claim ...``
headings (a fact-checker verdict quoting one claim per heading). The old regex
invented 27 spurious extra sections from that single entry, and
``view_item`` reported a wildly inflated section count with truncated
content — a read-path misreport, not data loss (the stored content was never
touched).
"""

from __future__ import annotations

from typing import cast

from backlog_core.models import SectionEntryMetadata
from backlog_core.operations import _build_sections_metadata


class TestEntryContentHeadingsAreNotSectionBoundaries:
    """A heading-shaped line inside an entry block's own content is not a section."""

    def test_two_h2_headings_inside_one_entry_yield_one_section(self) -> None:
        """Two ``## `` lines inside a single wrapped entry must not fragment the section.

        Tests: _build_sections_metadata's boundary detection against a body whose
               entry content legitimately quotes two ``## `` headings (mirrors #3152's
               Fact-Check section, which quotes 27 ``## Claim ...`` headings).
        How: Build a body with one ``## Fact-Check`` section containing a single
             entry block whose content has two internal ``## Claim`` lines, then
             assert exactly one top-level section is discovered.
        Why: The old ``_SECTION_BOUNDARY_RE`` naive line scan treated every ``## ``
             line as a real boundary regardless of nesting, inventing spurious
             sections from entry content and truncating the reported content.
        """
        body = (
            "## Fact-Check\n\n"
            "<div><sub>2026-08-22T10:00:00Z</sub>\n\n"
            "## Claim H: one\n"
            "text\n\n"
            "## Claim I: two\n"
            "text\n"
            "</div>\n\n"
            "## Context\n\n"
            "authored.\n"
        )

        sections = cast("dict[str, SectionEntryMetadata]", _build_sections_metadata(body, None, None))

        assert set(sections) == {"Fact-Check", "Context"}, (
            f"expected exactly 2 top-level sections, got {sorted(sections)}"
        )
        assert sections["Fact-Check"]["num_entries"] == 1, (
            f"the ## Claim lines inside the entry must not split it into extra entries; "
            f"got num_entries={sections['Fact-Check']['num_entries']}"
        )

    def test_two_h3_headings_inside_one_entry_yield_one_section(self) -> None:
        """The same guard applies to ``### `` headings quoted inside entry content.

        Tests: _build_sections_metadata's boundary detection with ``### `` (not ``## ``)
               heading-shaped lines embedded in an entry.
        How: Build a body with one ``### Detail`` section whose single entry quotes
             two internal ``### Sub`` lines, then assert exactly one section results.
        Why: ``_SECTION_BOUNDARY_RE`` matches ``#{2,3}`` — both heading levels shared
             the same naive-scan defect, so the fix must cover both, not just ``## ``.
        """
        body = "### Detail\n\n<div><sub>2026-08-22T10:00:00Z</sub>\n\n### Sub one\ntext\n\n### Sub two\ntext\n</div>\n"

        sections = cast("dict[str, SectionEntryMetadata]", _build_sections_metadata(body, None, None))

        assert set(sections) == {"Detail"}, f"expected exactly 1 section, got {sorted(sections)}"
        assert sections["Detail"]["num_entries"] == 1, (
            f"the ### Sub lines inside the entry must not split it into extra entries; "
            f"got num_entries={sections['Detail']['num_entries']}"
        )

    def test_genuinely_separate_sections_still_yield_two(self) -> None:
        """Two REAL top-level sections (not nested in an entry) must not be merged.

        Tests: The guard against entry-embedded headings must not over-correct and
               collapse genuinely distinct sections.
        How: Build a body with two ``## `` sections, each with its own entry block,
               neither containing internal heading-shaped lines.
        Why: A fix that always treats consecutive ``## `` lines as one section would
             pass the "two headings in one entry" test for the wrong reason.
        """
        body = (
            "## A\n\n"
            "<div><sub>2026-08-22T10:00:00Z</sub>\n\n"
            "text a\n"
            "</div>\n\n"
            "## B\n\n"
            "<div><sub>2026-08-22T11:00:00Z</sub>\n\n"
            "text b\n"
            "</div>\n"
        )

        sections = cast("dict[str, SectionEntryMetadata]", _build_sections_metadata(body, None, None))

        assert set(sections) == {"A", "B"}, f"expected exactly 2 sections, got {sorted(sections)}"
        assert sections["A"]["num_entries"] == 1
        assert sections["B"]["num_entries"] == 1

    def test_h3_delimited_section_is_still_discovered(self) -> None:
        """A genuine top-level ``### `` section (no ``## `` parent) is still found.

        Tests: Level-3 support survived generalizing the shared splitter to accept
               a level set instead of a single hard-coded level.
        How: Build a body containing only a ``### Detail`` section with no entries
             quoting internal headings, and assert it is discovered as a section.
        Why: The fix must preserve ``_SECTION_BOUNDARY_RE``'s original contract of
             matching BOTH ``## `` and ``### `` as top-level boundaries.
        """
        body = "### Detail\n\n<div><sub>2026-08-22T10:00:00Z</sub>\n\ncontent here\n</div>\n"

        sections = cast("dict[str, SectionEntryMetadata]", _build_sections_metadata(body, None, None))

        assert set(sections) == {"Detail"}, f"expected the ### section to be discovered, got {sorted(sections)}"

    def test_section_content_is_returned_complete_not_truncated(self) -> None:
        """Entry content spanning an internal heading-shaped line is not truncated.

        Tests: The fix does not just fix the section COUNT but also preserves the
               FULL content of the one true entry — nothing is cut off at the first
               internal ``## ``/``### `` line.
        How: Build a body whose single entry contains two internal ``## Claim``
             headings with distinguishable text after each, then assert both
             fragments of text are present in the parsed entry's content.
        Why: #3152's live report was that ``view_item`` returned TRUNCATED content
             for a section whose stored content was actually complete — the
             boundary scanner was fragmenting entry content mid-way, discarding the
             remainder into "extra sections" that were then themselves truncated
             by the response budget.
        """
        body = (
            "## Fact-Check\n\n"
            "<div><sub>2026-08-22T10:00:00Z</sub>\n\n"
            "## Claim H: one\n"
            "full text belonging to claim H\n\n"
            "## Claim I: two\n"
            "full text belonging to claim I\n"
            "</div>\n"
        )

        sections = cast("dict[str, SectionEntryMetadata]", _build_sections_metadata(body, None, None))

        assert sections["Fact-Check"]["num_entries"] == 1
        entry_content = sections["Fact-Check"]["entries"][0]["content"]
        assert "full text belonging to claim H" in entry_content
        assert "full text belonging to claim I" in entry_content


class TestFilterSemanticsPreserved:
    """``show``/``since``/``section`` filtering semantics must not change."""

    _BODY = (
        "## A\n\n"
        "<div><sub>2026-08-20T10:00:00Z</sub>\n\ntext a1\n</div>\n\n"
        "<div><sub>2026-08-22T10:00:00Z</sub>\n\ntext a2\n</div>\n\n"
        "## B\n\n"
        "<div><sub>2026-08-21T10:00:00Z</sub>\n\ntext b\n</div>\n"
    )

    def test_section_filter_narrows_to_one_named_section(self) -> None:
        """``section='A'`` returns only section A's metadata."""
        sections = cast(
            "dict[str, SectionEntryMetadata]", _build_sections_metadata(self._BODY, None, None, section="A")
        )

        assert set(sections) == {"A"}, f"expected only 'A', got {sorted(sections)}"
        assert sections["A"]["num_entries"] == 2

    def test_since_filter_excludes_earlier_entries(self) -> None:
        """``since`` excludes entries dated before the cutoff, per section."""
        sections = cast("dict[str, SectionEntryMetadata]", _build_sections_metadata(self._BODY, None, "2026-08-21"))

        assert sections["A"]["num_entries"] == 1, "the 08-20 entry in A must be excluded by since=08-21"
        assert sections["B"]["num_entries"] == 1, "the 08-21 entry in B is on the cutoff date and must be included"

    def test_show_last_returns_only_the_most_recent_entry_per_section(self) -> None:
        """``show='last'`` returns only the most recent entry in each section."""
        sections = cast("dict[str, SectionEntryMetadata]", _build_sections_metadata(self._BODY, "last", None))

        assert sections["A"]["num_entries"] == 1, "show='last' must narrow section A to its single most recent entry"
        entry_content = sections["A"]["entries"][0]["content"]
        assert "text a2" in entry_content, "show='last' must keep the most recent (08-22) entry, not the earliest"

    def test_show_as_section_name_string_filters_by_name(self) -> None:
        """A ``show`` value that is a plain section name (not a filter keyword) filters sections.

        Mirrors the pre-existing contract: a string ``show`` not in the entry-filter
        keyword set is treated as a section-name filter, exactly like passing the
        same value via the explicit ``section`` parameter.
        """
        sections = cast("dict[str, SectionEntryMetadata]", _build_sections_metadata(self._BODY, "B", None))

        assert set(sections) == {"B"}, f"show='B' must filter to only section 'B', got {sorted(sections)}"
