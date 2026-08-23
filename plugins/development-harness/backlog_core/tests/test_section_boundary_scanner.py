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

import pytest

from backlog_core.models import SectionEntryMetadata
from backlog_core.operations import _build_sections_metadata
from backlog_core.parsing import split_body_sections


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


class TestBoundariesComeFromTheParserNotARescan:
    """Heading positions come from marko, not from re-scanning the source lines.

    The splitter used to ask marko *which* lines were headings, then re-scan the source
    independently and bind the Nth heading-shaped line to the Nth AST heading. The join
    never compared heading text to line text, so wherever the scanner and the parser
    disagreed about a ``#``-prefixed line, every heading from that point on bound to the
    wrong line — and the last real section was dropped entirely. These four inputs are
    four symptoms of that one join, not four separate bugs.
    """

    def test_heading_inside_an_html_comment_is_not_a_boundary(self) -> None:
        """A commented-out heading is invisible to marko and must be invisible here.

        Why: The scanner tracked fences and entry divs but no HTML-block state, so it
             bound AST heading #2 ("B") to the commented "## hidden" line and folded the
             real B section into it.
        """
        body = "## A\n<!--\n## hidden\n-->\n## B\nbbody"

        assert [s.name for s in split_body_sections(body)] == ["A", "B"]

    def test_heading_inside_a_four_backtick_fence_is_not_a_boundary(self) -> None:
        """Fence tracking must respect CommonMark delimiter length.

        Why: A boolean toggle on any ```` ``` ````-prefixed line treated the inner
             three-backtick line as a closing delimiter, so "## Fake" escaped the fence
             as a section and the real "## Real2" was lost.
        """
        body = "## Real1\n````\n```\n## Fake\n````\n## Real2\nreal2body"

        assert [s.name for s in split_body_sections(body)] == ["Real1", "Real2"]

    def test_unterminated_entry_wrapper_does_not_swallow_later_sections(self) -> None:
        """A ``<div><sub>`` that never closes must not consume to end of document.

        Why: _EntryDivBlock claimed the block and consumed every remaining line, so a
             truncated wrapper erased every section after it from metadata, the compact
             index, and section-filter results. The regex path this replaced did expose
             those headings, so losing them was a regression, not an inherited bug.
        """
        body = "## A\n<div><sub>2026-08-22T10:00:00Z</sub>\n\ntext\n\n## B\nbbody"

        assert [s.name for s in split_body_sections(body)] == ["A", "B"]

    def test_terminated_entry_wrapper_stays_opaque(self) -> None:
        """The unterminated fix must not weaken entry-block opacity.

        Why: A heading-shaped line inside a properly closed entry is the entry's own
             content and must never become a section (#2956).
        """
        body = "## A\n<div><sub>2026-08-22T10:00:00Z</sub>\n\n## notaheading\n\n</div>\n\n## B\nb"

        assert [s.name for s in split_body_sections(body)] == ["A", "B"]

    @pytest.mark.parametrize(
        "document", ["## A\na\n## B\nb", "## A\na\nb\nc\n## B\nb", "## Sec\n\ntext\n\n## Two\n\nmore\n"]
    )
    def test_line_endings_do_not_change_the_result(self, document: str) -> None:
        """The same document parsed with LF and with CRLF yields identical spans.

        Tests: span names, content, and offsets are line-ending invariant
        How: Parse the identical document twice, once with \\n and once with \\r\\n
        Why: Offsets were computed as ``offset += len(line) + 1`` over splitlines(),
             assuming a one-character line ending, so every span drifted one char left
             per preceding line and start offsets landed mid-line. marko reports
             positions against a CRLF-normalized buffer, so taking its positions
             re-introduces the same class of error one layer down unless the offsets are
             translated back — this asserts the translation, and keeps asserting it if a
             future marko version moves where Source.pos lands.
        """
        crlf = document.replace("\n", "\r\n")

        lf_spans = split_body_sections(document)
        crlf_spans = split_body_sections(crlf)

        assert [s.name for s in lf_spans] == [s.name for s in crlf_spans]
        assert [s.content for s in lf_spans] == [s.content for s in crlf_spans]
        for span in crlf_spans:
            assert crlf[span.start : span.start + 2] == "##", (
                f"start offset {span.start} for {span.name!r} does not land on the heading line"
            )


class TestSectionNamesKeepTheirSourceSpelling:
    """A section's name is the spelling the source uses, not marko's flattening of it.

    The deleted line scanner took names from the source line. Taking them from the AST
    instead changed what callers match against: the registry, compact indexes and
    ``section=`` filters all compare against the spelling a caller reads in the body.
    """

    @pytest.mark.parametrize(
        ("body", "expected"),
        [
            ("## **Impact Radius**\nx", "**Impact Radius**"),
            ("## `Fact-Check`\nx", "`Fact-Check`"),
            ("## [Link](http://example.com)\nx", "[Link](http://example.com)"),
            ("## Plain\nx", "Plain"),
            ("##   Spaced   \nx", "Spaced"),
        ],
    )
    def test_inline_markup_round_trips(self, body: str, expected: str) -> None:
        """A heading carrying inline markup keeps that markup in its section name.

        Why: ``_extract_heading_text`` stringified the intermediate inline node rather
             than recursing into it, so ``## **Impact Radius**`` produced the literal
             name ``"[<RawText children='Impact Radius'>]"`` — marko internals leaking
             into the section index, and a previously working
             ``section="**Impact Radius**"`` filter no longer resolving.
        """
        assert [s.name for s in split_body_sections(body)] == [expected]

    def test_nested_inline_markup_does_not_leak_marko_internals(self) -> None:
        """No section name may contain a marko node repr, however deeply nested."""
        body = "## **Bold with `code` inside**\nx"

        name = split_body_sections(body)[0].name

        assert "RawText" not in name
        assert name == "**Bold with `code` inside**"


class TestUnterminatedWrapperWithoutABlankLine:
    """An unterminated wrapper must not swallow later sections, blank line or not.

    Refusing the match and deferring to marko is not sufficient recovery: a CommonMark
    type-6 HTML block runs to the next blank line, so a malformed body with no blank line
    before the next heading still loses every section after the wrapper.
    """

    @pytest.mark.parametrize(
        "body",
        [
            "## A\n<div><sub>2026-08-22T10:00:00Z</sub>\n\ntext\n\n## B\nbbody",
            "## A\n<div><sub>2026-08-22T10:00:00Z</sub>\ntext\n## B\nbbody",
            "## A\n<div><sub>2026-08-22T10:00:00Z</sub>\n## B\nbbody",
        ],
    )
    def test_later_sections_survive_an_unterminated_wrapper(self, body: str) -> None:
        """Sections after a truncated wrapper stay addressable in every spacing variant."""
        assert [s.name for s in split_body_sections(body)] == ["A", "B"]

    @pytest.mark.parametrize(
        "body",
        [
            "## A\n<div><sub>2026-08-22T10:00:00Z</sub>\n\n## notaheading\n\n</div>\n\n## B\nb",
            "## A\n<div><sub>2026-08-22T10:00:00Z</sub>\n## notaheading\n</div>\n## B\nb",
        ],
    )
    def test_closed_wrapper_stays_opaque_without_a_blank_line(self, body: str) -> None:
        """Bounding an unterminated wrapper must not weaken a closed one's opacity.

        Why: The recovery stops at the next heading. Applying that to a wrapper that does
             close would re-expose heading-shaped lines inside real entry content as
             sections, which is the defect #2956 fixed.
        """
        assert [s.name for s in split_body_sections(body)] == ["A", "B"]


class TestWrapperCloseDetectionIgnoresFencedContent:
    """A fenced HTML example inside an entry must not be read as wrapper structure.

    _EntryDivBlock is handed raw lines by marko and scans them itself, so it cannot ask
    the parser what is inside a fence. Counting a fenced ``<div>`` as wrapper structure
    makes a properly closed wrapper look unterminated, and the unterminated-recovery path
    then exposes heading-shaped lines from inside the entry as real sections.
    """

    def test_fenced_div_in_a_closed_wrapper_creates_no_phantom_section(self) -> None:
        """An unmatched ``<div>`` in a fenced example does not unbalance the wrapper.

        Why: Without fence tracking this returned ``['A', 'quoted heading', 'B']`` — a
             phantom section invented from the entry's own quoted content, which is the
             defect #2956 fixed, reintroduced through the recovery path.
        """
        body = (
            "## A\n"
            "<div><sub>2026-08-22T10:00:00Z</sub>\n\n"
            "```html\n<div>\n```\n\n"
            "## quoted heading\n\n"
            "</div>\n\n"
            "## B\nbbody"
        )

        assert [s.name for s in split_body_sections(body)] == ["A", "B"]

    def test_fenced_div_in_a_genuinely_unterminated_wrapper_still_recovers(self) -> None:
        """Fence tracking must not cost the unterminated-wrapper recovery."""
        body = "## A\n<div><sub>2026-08-22T10:00:00Z</sub>\n\n```html\n<div>\n```\n\ntext\n\n## B\nbbody"

        assert [s.name for s in split_body_sections(body)] == ["A", "B"]

    @pytest.mark.parametrize(
        ("body", "expected"),
        [
            ("## R1\n~~~\n## Fake\n~~~\n## R2\nx", ["R1", "R2"]),
            ("## R1\n````\n```\n## Fake\n````\n## R2\nx", ["R1", "R2"]),
            ("## R1\n~~~~\n~~~\n## Fake\n~~~~\n## R2\nx", ["R1", "R2"]),
        ],
    )
    def test_fence_delimiter_length_and_character_are_respected(self, body: str, expected: list[str]) -> None:
        """A fence closes only on the same character, at least as long as its opener.

        Why: A boolean toggle treated any fence-shaped line as a delimiter, so a shorter
             nested run ended the block early and the heading inside it escaped as a
             section while the following real section was lost.
        """
        assert [s.name for s in split_body_sections(body)] == expected

    @pytest.mark.parametrize(
        "body",
        [
            "## A\n<div><sub>2026-08-22T10:00:00Z</sub>\n\n```html\n<div>\n\n</div>\n\n## B\nbbody",
            "## A\n<div><sub>2026-08-22T10:00:00Z</sub>\n\n```html\nx\n\n</div>\n\n## B\nbbody",
        ],
    )
    def test_unclosed_fence_does_not_hide_the_wrapper_close(self, body: str) -> None:
        """A fence the entry never closes must not swallow the sections after the entry.

        Tests: wrapper-close detection survives an unterminated fence inside the entry
        How: Put an opening fence with no closing delimiter inside an otherwise closed
             wrapper, then assert the section after the wrapper is still found
        Why: Fence tracking made every line after an unclosed fence look like fenced
             content — the entry's own closing </div> included — so a closed wrapper was
             judged unterminated and the recovery consumed to EOF, losing "## B". Neither
             a fence-aware nor a fence-blind depth scan finds the close on its own here,
             because the quoted <div> unbalances the blind pass, so the bound itself has
             to be scanned fence-blind when nothing closes.
        """
        assert [s.name for s in split_body_sections(body)] == ["A", "B"]

    def test_unclosed_fence_keeps_its_heading_opaque_and_still_closes(self) -> None:
        """An unclosed fence holding a heading keeps it opaque without losing the close.

        Tests: both invariants hold together — no phantom section, no lost section
        How: An entry whose unclosed fence contains an unmatched <div> AND a
             heading-shaped example, followed by the entry's real closing </div>
        Why: Recovering the wrapper close by ignoring fences entirely surfaced the fenced
             "## Fake" as a real section, corrupting section indexes and filtered reads.
             Keeping fence opacity but still counting closing tags inside a fence
             satisfies both: the close is found, and the example heading stays content.
        """
        body = "## A\n<div><sub>2026-08-22T10:00:00Z</sub>\n\n```html\n<div>\n## Fake\n</div>\n\n## B\nbbody"

        names = [s.name for s in split_body_sections(body)]

        assert names == ["A", "B"]
        assert "Fake" not in names
