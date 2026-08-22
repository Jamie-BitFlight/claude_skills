"""Regression tests for entry-block wrapper nesting and the zero-date ``since`` crash.

Both defects were observed live while grooming #3152: two grooming agents submitted content
that already carried the ``<div><sub>...</sub>`` entry wrapper — the shape ``backlog_view``
renders when reading — and their writes returned success while losing content.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

import pytest

from backlog_core.entry_blocks import _parse_entry_timestamp, parse_entries, rewrite_section, wrap_entry
from backlog_core.models import Section
from backlog_core.parsing import parse_md_body_sections

_AGENT_SUBMITTED_PREWRAPPED = (
    "<div><sub>2026-08-22T14:58:39.771586Z</sub>\n\n"
    "verdict: VERIFIED\n"
    "claim: build_issue_body has one non-test caller\n"
    "evidence: repo-wide grep\n"
    "</div>"
)

_RAW_CONTENT = "verdict: VERIFIED\nclaim: something checkable\nevidence: source read"


class TestWrapEntryDoesNotNest:
    """wrap_entry must not wrap content that already carries an entry wrapper."""

    def test_prewrapped_content_is_returned_unchanged(self) -> None:
        """Submitting an already-wrapped entry does not produce a nested block.

        Tests: wrap_entry is idempotent for already-wrapped input
        How: Wrap a complete entry block and assert only one opening tag results
        Why: Two grooming agents echoed back the wrapper shown by backlog_view; the
             resulting nested block silently lost their content
        """
        result = wrap_entry(_AGENT_SUBMITTED_PREWRAPPED)

        assert result.count("<div><sub>") == 1
        assert result == _AGENT_SUBMITTED_PREWRAPPED

    def test_raw_content_is_still_wrapped(self) -> None:
        """Ordinary unwrapped content is wrapped exactly once — the guard is not over-broad."""
        result = wrap_entry(_RAW_CONTENT)

        assert result.count("<div><sub>") == 1
        assert _RAW_CONTENT in result
        assert result.endswith("</div>")

    def test_content_merely_mentioning_a_div_is_still_wrapped(self) -> None:
        """Prose that references a div but is not itself an entry block still gets wrapped.

        Why: The guard matches only a string that is entirely one or more entry blocks.
             Content discussing the wrapper must not be mistaken for the wrapper.
        """
        prose = "The parser emits <div><sub>ts</sub> when the section is unwrapped."

        result = wrap_entry(prose)

        assert result.count("<div><sub>") == 2
        assert prose in result


class TestPrewrappedContentSurvivesBodyRoundTrip:
    """A pre-wrapped submission must not lose content or emit a stray entry."""

    def test_no_orphan_entry_after_body_round_trip(self) -> None:
        """Round-tripping a pre-wrapped submission yields one entry, not an orphan closing tag.

        Tests: The full write -> render -> parse path the GitHub reconcile performs
        How: Write pre-wrapped content into a section, embed it in a body, parse the body back
        Why: Nesting previously produced a second entry whose entire content was "</div>" and
             whose ID was the empty string — corruption that reads as a real entry
        """
        section_body = rewrite_section("", new_content=_AGENT_SUBMITTED_PREWRAPPED, added_date="2026-08-22")
        full_body = f"## Fact-Check\n\n{section_body}\n\n## Context\n\nauthored context.\n"

        sections = parse_md_body_sections(full_body, added_date="2026-08-22")
        entries = cast("Section", sections["fact_check"]).entries

        assert len(entries) == 1
        assert all(e.id for e in entries), "an entry with an empty ID is corruption, not content"
        assert "</div>" not in entries[0].content

    def test_submitted_body_text_is_preserved(self) -> None:
        """The agent's actual verdict text survives the round-trip.

        Why: The observed failure returned success while persisting only the wrapper fragment.
        """
        section_body = rewrite_section("", new_content=_AGENT_SUBMITTED_PREWRAPPED, added_date="2026-08-22")
        full_body = f"## Fact-Check\n\n{section_body}\n"

        sections = parse_md_body_sections(full_body, added_date="2026-08-22")
        content = cast("Section", sections["fact_check"]).entries[0].content

        assert "verdict: VERIFIED" in content
        assert "build_issue_body has one non-test caller" in content
        assert "evidence: repo-wide grep" in content


class TestZeroDateSinceFilter:
    """The zero-date fallback ID must not crash the documented ``since`` filter."""

    def test_since_filter_does_not_raise_on_zero_date_entries(self) -> None:
        """A section of legacy unwrapped content is filterable by ``since``.

        Tests: parse_entries(since=...) against the zero-date fallback ID
        How: Parse unwrapped content with added_date="0000-00-00" and a real cutoff
        Why: This previously raised "ValueError: year 0 is out of range", making ``since``
             unusable on any item whose entries lack real timestamps (#3153)
        """
        result = parse_entries("legacy unwrapped content", since="2026-01-01", added_date="0000-00-00")

        assert result == []

    def test_zero_date_entry_is_excluded_not_included(self) -> None:
        """An entry with an unknown timestamp is not "at or after" a real cutoff."""
        no_filter = parse_entries("legacy unwrapped content", added_date="0000-00-00")
        filtered = parse_entries("legacy unwrapped content", since="2020-01-01", added_date="0000-00-00")

        assert len(no_filter) == 1
        assert filtered == []

    def test_zero_date_sorts_before_every_real_timestamp(self) -> None:
        """The unknown-timestamp sentinel maps to datetime.min, not to year zero."""
        assert _parse_entry_timestamp("0000-00-00T00:00:00Z") == datetime.min.replace(tzinfo=UTC)
        assert _parse_entry_timestamp("0000-00-00T00:00:00Z") < _parse_entry_timestamp("2026-08-22T00:00:00Z")

    def test_genuinely_malformed_id_still_raises(self) -> None:
        """The fix is scoped to the zero-date sentinel — other bad IDs remain loud."""
        with pytest.raises(ValueError, match="does not contain a valid ISO timestamp prefix"):
            _parse_entry_timestamp("not-a-timestamp")

    def test_empty_id_still_raises(self) -> None:
        """The empty ID produced by the old orphan-entry corruption is not silently accepted."""
        with pytest.raises(ValueError, match="does not contain a valid ISO timestamp prefix"):
            _parse_entry_timestamp("")
