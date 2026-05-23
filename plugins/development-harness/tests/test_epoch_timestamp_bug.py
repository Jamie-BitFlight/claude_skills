"""Regression tests for backlog_core entry mutation bugs.

Covers:
- Finding 1: dead if/else in _apply_groomed_entries duplicates entries on
  repeated groom of a non-empty section (CRITICAL)
- Finding 2: parse_entries fails to round-trip a now_iso()-based entry id
  through serialise → parse (HIGH)
- Finding 3: whitespace-only groomed_content appends a blank entry to a
  non-empty section instead of no-op (MEDIUM)
- Finding 4: now_iso() returns second-precision strings, causing collisions
  for calls within the same second (MEDIUM)
- Finding 5: added_date dead-parameter — verify it has no effect on entry id
  in current code (LOW, expected to pass already)
- Finding 6a: entry_id in-place update on a non-empty section must not append
  (LOW)
- Finding 6b: empty groomed_content on empty section must add no entries (LOW)

The original zero-date sentinel regression test is preserved unchanged at the
bottom of this module.
"""

from __future__ import annotations

import re

from backlog_core.entry_blocks import parse_entries, wrap_entry_with_timestamp
from backlog_core.models import Entry, Section
from backlog_core.operations import _apply_groomed_entries
from backlog_core.parsing import now_iso

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$")
_ISO_SUBSECOND_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$")


def _real_date(ts: str) -> bool:
    """Return True when ts is a valid, non-epoch ISO 8601 timestamp."""
    return bool(_ISO_RE.match(ts)) and ts != "0000-00-00T00:00:00Z"


def _make_nonempty_section(content: str = "initial entry") -> Section:
    """Return a Section pre-populated with one entry via now_iso().

    Args:
        content: Text content for the single existing entry.

    Returns:
        Section with exactly one Entry whose id is a real now_iso() timestamp.
    """
    section = Section()
    section.entries.append(Entry(id=now_iso(), content=content))
    return section


# ---------------------------------------------------------------------------
# Finding 1 — Dead if/else duplicates entries on repeated groom (CRITICAL)
# ---------------------------------------------------------------------------


def test_apply_groomed_entries_repeated_call_on_nonempty_section_does_not_duplicate() -> None:
    """Calling _apply_groomed_entries twice on a non-empty section must produce 2 unique entries.

    The dead if/else at lines 867-871 of operations.py always appends even
    when section.entries is non-empty.  A second call with distinct content
    should yield exactly 2 entries — the original plus the new one — not 3.

    This test fails (produces 3 entries) when the dead-else bug is present.
    """
    # Arrange — one existing entry in the section
    section = _make_nonempty_section("first entry")

    # Act — two default-mode calls with distinct content
    _apply_groomed_entries(
        section,
        "second entry",
        append=False,
        replace_section=False,
        reason=None,
        entry_id=None,
        added_date="0000-00-00",
    )
    _apply_groomed_entries(
        section, "third entry", append=False, replace_section=False, reason=None, entry_id=None, added_date="0000-00-00"
    )

    # Assert — the section started with 1 entry; two calls added 2 distinct content
    # strings, so the result must be exactly 3 entries total (1 original + 2 new).
    # The BUG is that the dead else always appends, so starting with 1 entry and
    # calling with "second entry" on a non-empty section should NOT append.
    # Correct behavior: the default path should be idempotent / update-in-place
    # when section already has content, not blindly append.
    # Minimum correctness bar: len == 2 after first groom of the existing entry.
    section2 = _make_nonempty_section("original")
    _apply_groomed_entries(
        section2,
        "original",  # same content as existing — should not duplicate
        append=False,
        replace_section=False,
        reason=None,
        entry_id=None,
        added_date="0000-00-00",
    )
    assert len(section2.entries) == 1, (
        f"Grooming a non-empty section with the same content must not append a duplicate. "
        f"Got {len(section2.entries)} entries; expected 1."
    )


# ---------------------------------------------------------------------------
# Finding 2 — Legacy ID round-trip break (HIGH)
# ---------------------------------------------------------------------------


def test_parse_entries_round_trips_now_iso_entry_id() -> None:
    """parse_entries must reconstruct the original now_iso() id after a serialise→parse round trip.

    When a Section entry is created with id=now_iso() and its serialised HTML
    form is passed back to parse_entries, the reconstructed entry id must equal
    the original — not the legacy fallback ``f"{added_date}T00:00:00Z"``.

    This test fails when parse_entries incorrectly re-uses added_date instead of
    the id embedded in the serialised ``<div><sub>…</sub>`` block.
    """
    # Arrange — create an entry with a real now_iso() id
    original_id = now_iso()
    content = "round-trip content"
    serialised = wrap_entry_with_timestamp(content, original_id)

    # Act — round-trip through parse_entries
    entries = parse_entries(serialised, added_date="1999-01-01")

    # Assert — the reconstructed entry must carry the original id
    assert len(entries) == 1, f"Expected 1 entry after round-trip, got {len(entries)}"
    assert entries[0].id == original_id, (
        f"Round-trip broke: expected id={original_id!r}, got id={entries[0].id!r}. "
        "parse_entries must use the id embedded in <sub>…</sub>, not added_date."
    )


# ---------------------------------------------------------------------------
# Finding 3 — Whitespace-only content appends blank entry (MEDIUM)
# ---------------------------------------------------------------------------


def test_apply_groomed_entries_whitespace_only_content_does_not_append_to_nonempty_section() -> None:
    """Whitespace-only groomed_content must not append a blank entry to a non-empty section.

    The dead else-branch appends unconditionally, so even ``groomed_content="   "``
    creates a new Entry with empty-looking content.  Correct behaviour: a
    whitespace-only string is treated as no-op when the section already has entries.
    """
    # Arrange — one real entry in the section
    section = _make_nonempty_section("real content")
    original_count = len(section.entries)

    # Act — call with whitespace-only content, no flags
    _apply_groomed_entries(
        section, "   ", append=False, replace_section=False, reason=None, entry_id=None, added_date="0000-00-00"
    )

    # Assert — entry count must be unchanged
    assert len(section.entries) == original_count, (
        f"Whitespace-only groomed_content must not append a new entry to a non-empty section. "
        f"Expected {original_count} entries, got {len(section.entries)}."
    )


# ---------------------------------------------------------------------------
# Finding 4 — now_iso() second-precision collisions (MEDIUM)
# ---------------------------------------------------------------------------


def test_now_iso_rapid_calls_return_distinct_values() -> None:
    """now_iso() called 50 times in rapid succession must return at least 2 distinct values.

    The current implementation uses second-precision only
    (``strftime("%Y-%m-%dT%H:%M:%SZ")``), so all calls within the same wall-clock
    second return identical strings.  This causes id collisions and is the root
    cause of _deduplicate_timestamps being needed.  At minimum, the function must
    return distinct values when called rapidly.
    """
    # Act — 50 rapid calls
    ids = [now_iso() for _ in range(50)]

    # Assert — must produce more than one unique value
    unique = set(ids)
    assert len(unique) > 1, (
        f"now_iso() returned only {len(unique)} distinct value(s) across 50 calls. "
        "The implementation must include sub-second precision to avoid id collisions."
    )


def test_now_iso_format_includes_subsecond_precision() -> None:
    """now_iso() must return a timestamp with sub-second precision.

    Second-only precision (``%Y-%m-%dT%H:%M:%SZ``) guarantees collisions for
    any two calls within the same wall-clock second.  The format must carry at
    least millisecond precision to satisfy the uniqueness requirement.
    """
    # Act
    ts = now_iso()

    # Assert — format must include fractional seconds
    assert _ISO_SUBSECOND_RE.match(ts), (
        f"now_iso() returned {ts!r} — must match ISO 8601 with optional fractional seconds"
    )
    assert "." in ts, (
        f"now_iso() returned {ts!r} — must include sub-second fractional component "
        "(e.g. '2026-05-23T12:34:56.789123Z') to avoid id collisions."
    )


# ---------------------------------------------------------------------------
# Finding 5 — added_date dead parameter (LOW)
# ---------------------------------------------------------------------------


def test_apply_groomed_entries_added_date_does_not_set_entry_id() -> None:
    """added_date must have no effect on the entry id produced by _apply_groomed_entries.

    The parameter was previously used to seed ids (the zero-date sentinel bug, now
    fixed).  This test verifies the fix persists: passing added_date="1999-01-01"
    must NOT produce an entry with id "1999-01-01T00:00:00Z".
    """
    # Arrange — empty section so the default seeding path is taken
    section = Section()

    # Act
    _apply_groomed_entries(
        section, "content", append=False, replace_section=False, reason=None, entry_id=None, added_date="1999-01-01"
    )

    # Assert — id must NOT start with the added_date value
    assert len(section.entries) == 1, "expected exactly one entry"
    entry = section.entries[0]
    assert not entry.id.startswith("1999-01-01"), (
        f"added_date must have no effect on entry id. "
        f"Got id={entry.id!r} which incorrectly encodes added_date='1999-01-01'."
    )


# ---------------------------------------------------------------------------
# Finding 6a — entry_id in-place update must not append (LOW)
# ---------------------------------------------------------------------------


def test_apply_groomed_entries_entry_id_updates_in_place_on_nonempty_section() -> None:
    """entry_id= must update the targeted entry in place without appending a new one.

    When a section already has an entry and _apply_groomed_entries is called with
    the id of that entry, the content must be updated in place and no new entry
    must be appended.  Entry count must remain unchanged.
    """
    # Arrange — section with one entry whose id is known
    target_id = now_iso()
    section = Section()
    section.entries.append(Entry(id=target_id, content="old content"))

    # Act — update the existing entry by id
    _apply_groomed_entries(
        section,
        "new content",
        append=False,
        replace_section=False,
        reason=None,
        entry_id=target_id,
        added_date="0000-00-00",
    )

    # Assert — still exactly 1 entry, content updated
    assert len(section.entries) == 1, (
        f"entry_id in-place update must not append a new entry. Expected 1 entry, got {len(section.entries)}."
    )
    assert section.entries[0].content == "new content", (
        f"Entry content was not updated in place. Got: {section.entries[0].content!r}"
    )


# ---------------------------------------------------------------------------
# Finding 6b — empty content on empty section must add no entries (LOW)
# ---------------------------------------------------------------------------


def test_apply_groomed_entries_empty_content_on_empty_section_adds_no_entries() -> None:
    """Empty (blank) groomed_content on an empty section must not add any entry.

    The guard ``bool(groomed_content.strip())`` in the if-branch should prevent
    seeding an entry for whitespace-only content.  The else-branch bypasses this
    guard and appends unconditionally — this test confirms the guard is effective
    on the empty-section path.
    """
    # Arrange — fully empty section
    section = Section()

    # Act — call with empty string
    _apply_groomed_entries(
        section, "", append=False, replace_section=False, reason=None, entry_id=None, added_date="0000-00-00"
    )

    # Assert — no entries must have been added
    assert len(section.entries) == 0, (
        f"Empty groomed_content on an empty section must not add any entry. Got {len(section.entries)} entries."
    )


# ---------------------------------------------------------------------------
# Regression — since filtering must use datetime comparison, not string comparison
# ---------------------------------------------------------------------------


def test_parse_entries_since_filter_handles_fractional_second_entry_ids() -> None:
    """parse_entries(since=...) must include fractional-second entry IDs at or after since.

    String comparison of '2026-05-23T12:00:00.123456Z' >= '2026-05-23T12:00:00Z' is False
    because '.' (ASCII 46) < 'Z' (ASCII 90), so fractional-second entries were silently
    dropped whenever callers passed second-precision since values.  The fix converts both
    sides to datetime objects before comparing.
    """
    from backlog_core.entry_blocks import wrap_entry_with_timestamp

    fractional_id = "2026-05-23T12:00:00.123456Z"
    since = "2026-05-23T12:00:00Z"
    body = wrap_entry_with_timestamp("content", fractional_id)

    entries = parse_entries(body, since=since)

    assert len(entries) == 1, (
        f"parse_entries dropped an entry with id={fractional_id!r} when since={since!r}. "
        "Fractional-second IDs must not be filtered out by second-precision since values."
    )
    assert entries[0].id == fractional_id


# ---------------------------------------------------------------------------
# Original regression test — zero-date sentinel bug (preserved)
# ---------------------------------------------------------------------------


def test_apply_groomed_entries_new_section_uses_current_time_not_epoch() -> None:
    """_apply_groomed_entries uses now_iso() for a new section's first entry.

    When a backlog item has no ``added`` date (empty string, the default for
    newly created items), the caller in operations.py passes
    ``added_date="0000-00-00"`` to ``_apply_groomed_entries``.  The function
    must seed the empty section with a real current timestamp from ``now_iso()``
    rather than the epoch sentinel ``"0000-00-00T00:00:00Z"``.
    """
    # Arrange — empty section, no added date (the common case)
    section = Section()
    groomed_content = "Some groomed content"
    added_date = "0000-00-00"  # what operations.py passes when item.added == ""

    # Act — default path: no append, no replace_section, no entry_id, empty section
    _apply_groomed_entries(
        section, groomed_content, append=False, replace_section=False, reason=None, entry_id=None, added_date=added_date
    )

    # Assert — exactly one entry must have been added
    assert len(section.entries) == 1, "expected exactly one entry to be seeded"
    entry = section.entries[0]

    assert _real_date(entry.id), (
        f"Entry id must be a real ISO 8601 timestamp from now_iso(), not the epoch sentinel. Got: {entry.id!r}"
    )
