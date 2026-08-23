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
from backlog_core.models import EntryNotFoundError, Section
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

    def test_wrapper_with_a_non_timestamp_id_is_wrapped_normally(self) -> None:
        """An entry-shaped block whose ID is not a timestamp is not adopted as an entry.

        Tests: The already-wrapped guard requires a well-formed entry ID
        How: Submit an HTML example documenting the entry format, with a label ID
        Why: Adopting it would persist "example-id" as the entry ID; a later
             ``since=`` read then raises in _parse_entry_timestamp — the same crash
             the zero-date fix below closes, reintroduced through the guard itself
        """
        documented_example = "<div><sub>example-id</sub>\n\nthis is what an entry looks like\n</div>"

        result = wrap_entry(documented_example)

        assert result != documented_example
        assert result.startswith("<div><sub>")
        assert documented_example in result

    def test_non_timestamp_id_does_not_break_the_since_filter(self) -> None:
        """Wrapping a documented example keeps the section filterable by ``since``."""
        documented_example = "<div><sub>example-id</sub>\n\nexample body\n</div>"

        wrapped = wrap_entry(documented_example)

        assert parse_entries(wrapped, since="2026-01-01", added_date="2026-08-22") != []

    def test_dedup_suffixed_id_is_still_recognised(self) -> None:
        """``_resolve_duplicate_ids`` appends ``-N``; such an ID is still a real entry.

        Why: Tightening the guard must not reject IDs the codebase itself produces.
        """
        suffixed = "<div><sub>2026-08-22T14:58:39Z-1</sub>\n\nsecond entry that day\n</div>"

        assert wrap_entry(suffixed) == suffixed

    def test_zero_date_id_is_still_recognised(self) -> None:
        """The zero-date fallback ID is a real (if unknown-timestamp) entry ID."""
        legacy = "<div><sub>0000-00-00T00:00:00Z</sub>\n\nlegacy unwrapped seed\n</div>"

        assert wrap_entry(legacy) == legacy

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


class TestUnknownTimestampSurvivesSinceFilter:
    """An entry whose write time is unknown must never be silently withheld by ``since``."""

    def test_since_filter_does_not_raise_on_zero_date_entries(self) -> None:
        """A section of legacy unwrapped content is filterable by ``since``.

        Tests: parse_entries(since=...) against the zero-date fallback ID
        How: Parse unwrapped content with added_date="0000-00-00" and a real cutoff
        Why: This previously raised "ValueError: year 0 is out of range", making ``since``
             unusable on any item whose entries lack real timestamps (#3153)
        """
        result = parse_entries("legacy unwrapped content", since="2026-01-01", added_date="0000-00-00")

        assert len(result) == 1

    def test_unknown_timestamp_entry_is_returned_not_dropped(self) -> None:
        """``since`` returns an unknown-timestamp entry rather than excluding it.

        Tests: parse_entries(since=...) keeps zero-date entries
        How: Compare an unfiltered read against a filtered read of the same content
        Why: docs/unified-section-layer-brief.md forbids substituting an epoch sentinel for a
             missing timestamp. Mapping it to datetime.min did that, and every ``since=`` read
             then dropped the entry — leaving a stateless agent unable to tell "nothing
             changed" from "content exists whose age I cannot determine". On #3152 that
             withheld roughly 22KB across 5 of 16 entries while reporting success.
        """
        no_filter = parse_entries("legacy unwrapped content", added_date="0000-00-00")
        filtered = parse_entries("legacy unwrapped content", since="2020-01-01", added_date="0000-00-00")

        assert len(no_filter) == 1
        assert len(filtered) == 1
        assert filtered[0].content == no_filter[0].content

    def test_unknown_timestamp_is_visible_to_the_caller_in_the_entry_id(self) -> None:
        """The returned entry carries the sentinel ID, so the caller can see the age is unknown.

        Why: Including the entry is only useful if the caller can tell it apart from one that
             genuinely postdates the cutoff. The ``since`` parameter description on
             ``backlog_view`` documents this exact ID as "may or may not be new".
        """
        filtered = parse_entries("legacy unwrapped content", since="2020-01-01", added_date="0000-00-00")

        assert filtered[0].id.startswith("0000-00-00")

    def test_real_timestamps_are_still_filtered(self) -> None:
        """The include-unknown rule is scoped to unknown timestamps — real ones still filter."""
        body = "<div><sub>2026-01-05T00:00:00Z</sub>old</div>\n\n<div><sub>2026-08-22T00:00:00Z</sub>new</div>"

        filtered = parse_entries(body, since="2026-06-01")

        assert [e.content for e in filtered] == ["new"]

    def test_unknown_timestamp_reports_unavailable_not_a_sentinel_datetime(self) -> None:
        """``_parse_entry_timestamp`` reports the timestamp as unavailable, not as year zero."""
        assert _parse_entry_timestamp("0000-00-00T00:00:00Z") is None
        assert _parse_entry_timestamp("2026-08-22T00:00:00Z") == datetime(2026, 8, 22, tzinfo=UTC)

    def test_genuinely_malformed_id_still_raises(self) -> None:
        """The fix is scoped to the zero-date sentinel — other bad IDs remain loud."""
        with pytest.raises(ValueError, match="does not contain a valid ISO timestamp prefix"):
            _parse_entry_timestamp("not-a-timestamp")

    def test_empty_id_still_raises(self) -> None:
        """The empty ID produced by the old orphan-entry corruption is not silently accepted."""
        with pytest.raises(ValueError, match="does not contain a valid ISO timestamp prefix"):
            _parse_entry_timestamp("")


class TestAlreadyWrappedGuardRejectsPartialInput:
    """The guard adopts input only when it is ENTIRELY complete, well-formed entry blocks.

    The guard previously matched any string starting with a valid wrapper and ending in
    ``</div>``, with a greedy ``.*`` between. ``parse_entries`` extracts only ``ENTRY_RE``
    matches, so everything outside those blocks reached the provider body, was absent from the
    parsed entries, and was gone after the next render (PR #3160 F4/F7, PR #3165 F7).
    """

    def test_prose_between_two_wrappers_is_not_adopted(self) -> None:
        """Interstitial prose between two entry blocks is not silently swallowed.

        Tests: wrap_entry rejects a wrapper-prose-wrapper sequence
        How: Submit two valid blocks with a bare NOTE line between them
        Why: Adopting it persisted NOTE into the body while parse_entries returned only the
             two blocks, so NOTE vanished on the next render
        """
        mixed = "<div><sub>2026-08-22T10:00:00Z</sub>one</div>\nNOTE\n<div><sub>2026-08-22T11:00:00Z</sub>two</div>"

        result = wrap_entry(mixed)

        assert result != mixed
        assert "NOTE" in result

    def test_interstitial_prose_survives_a_body_round_trip(self) -> None:
        """The rejected-and-wrapped form keeps the prose reachable through parse_entries."""
        mixed = "<div><sub>2026-08-22T10:00:00Z</sub>one</div>\nNOTE\n<div><sub>2026-08-22T11:00:00Z</sub>two</div>"

        entries = parse_entries(rewrite_section("", new_content=mixed, added_date="2026-08-22"))

        assert any("NOTE" in e.content for e in entries), "interstitial prose must not be lost"

    def test_trailing_non_entry_div_is_not_adopted(self) -> None:
        """A non-entry ``<div>`` after a valid block is content, not part of the entry sequence."""
        mixed = '<div><sub>2026-08-22T10:00:00Z</sub>one</div>\n<div class="note">keepme</div>'

        result = wrap_entry(mixed)

        assert result != mixed
        assert "keepme" in result

    def test_whitespace_between_wrappers_is_still_adopted(self) -> None:
        """The guard is not over-tight — blank lines between blocks are not content."""
        pair = "<div><sub>2026-08-22T10:00:00Z</sub>one</div>\n\n<div><sub>2026-08-22T11:00:00Z</sub>two</div>"

        assert wrap_entry(pair) == pair

    def test_calendar_impossible_timestamp_is_not_adopted(self) -> None:
        """A shape-valid but calendar-impossible ID is rejected before it can be persisted.

        Tests: The guard validates the ID semantically, not only structurally
        How: Submit a block whose month is 13
        Why: Adopting it persisted the ID, and the next ``since=`` read raised
             "ValueError: month must be in 1..12" — the exact crash the guard exists to
             prevent (PR #3165 F6)
        """
        impossible = "<div><sub>2026-13-01T00:00:00Z</sub>x</div>"

        assert wrap_entry(impossible) != impossible

    def test_calendar_impossible_timestamp_does_not_break_the_since_filter(self) -> None:
        """A section seeded with a calendar-impossible wrapper stays filterable by ``since``."""
        impossible = "<div><sub>2026-99-99T99:99:99Z</sub>x</div>"

        wrapped = wrap_entry(impossible)

        assert parse_entries(wrapped, since="2026-01-01") != []


class TestUnmatchedEntryIdIsLoud:
    """Targeting an entry that does not exist must be an error, not a silent no-op.

    ``entry_id`` is the only way to replace or strike one specific entry. Returning the
    section unchanged reported success while writing nothing, so a caller could not tell
    "replaced" from "did nothing". The collision case made this reachable without any caller
    mistake: entries sharing a stored ID are read back with a positional ``-N`` suffix, so the
    bare ID visible in the wire format matched nothing.
    """

    def test_unmatched_entry_id_raises(self) -> None:
        """A target that matches no entry raises instead of returning the body unchanged."""
        body = "<div><sub>2026-08-22T10:00:00Z</sub>alpha</div>"

        with pytest.raises(EntryNotFoundError, match="No entry with id"):
            rewrite_section(body, new_content="REPLACED", entry_id="2026-01-01T00:00:00Z")

    def test_error_names_the_available_ids(self) -> None:
        """The error states which IDs exist, so the caller can retry against a real one."""
        body = "<div><sub>2026-08-22T10:00:00Z</sub>alpha</div>"

        with pytest.raises(EntryNotFoundError) as excinfo:
            rewrite_section(body, new_content="REPLACED", entry_id="nope-2026-01-01T00:00:00Z")

        assert excinfo.value.available == ["2026-08-22T10:00:00Z"]
        assert "2026-08-22T10:00:00Z" in str(excinfo.value)

    def test_colliding_stored_ids_report_the_suffixed_forms(self) -> None:
        """The bare stored ID of a collided pair raises and names the forms that do target.

        Why: Two legacy entries in one section share the sentinel ID. Targeting the ID the
             wire format actually shows silently rewrote nothing; the caller had no way to
             learn that the '-0'/'-1' forms are what it must pass.
        """
        collided = "<div><sub>0000-00-00T00:00:00Z</sub>alpha</div>\n\n<div><sub>0000-00-00T00:00:00Z</sub>beta</div>"

        with pytest.raises(EntryNotFoundError) as excinfo:
            rewrite_section(collided, new_content="REPLACED", entry_id="0000-00-00T00:00:00Z")

        assert excinfo.value.available == ["0000-00-00T00:00:00Z-0", "0000-00-00T00:00:00Z-1"]

    def test_a_real_target_still_replaces(self) -> None:
        """The guard is not over-broad — a matching ID still replaces that entry only."""
        collided = "<div><sub>0000-00-00T00:00:00Z</sub>alpha</div>\n\n<div><sub>0000-00-00T00:00:00Z</sub>beta</div>"

        out = rewrite_section(collided, new_content="REPLACED", entry_id="0000-00-00T00:00:00Z-1")

        assert [e.content for e in parse_entries(out)] == ["alpha", "REPLACED"]

    def test_unmatched_target_on_legacy_content_raises(self) -> None:
        """Unwrapped legacy content reports its one synthetic ID rather than appending.

        Why: The legacy branch previously turned an unmatched targeted replace into a blind
             append, which is a different write than the one the caller asked for.
        """
        with pytest.raises(EntryNotFoundError) as excinfo:
            rewrite_section(
                "legacy prose", new_content="REPLACED", entry_id="2026-01-01T00:00:00Z", added_date="2026-08-22"
            )

        assert excinfo.value.available == ["2026-08-22T00:00:00Z"]
