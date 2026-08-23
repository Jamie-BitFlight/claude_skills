"""Tests for entry block operations — timestamped, addressable content within backlog sections."""

from __future__ import annotations

import pytest
from backlog_core.models import Entry


def test_entry_model_defaults():
    e = Entry(id="2026-03-10T22:18:04Z", content="Some content")
    assert e.id == "2026-03-10T22:18:04Z"
    assert e.content == "Some content"
    assert e.struck is False
    assert e.struck_reason == ""
    assert e.struck_at == ""


def test_entry_model_struck():
    e = Entry(
        id="2026-03-10T22:18:04Z",
        content="Old content",
        struck=True,
        struck_reason="outdated",
        struck_at="2026-03-11T09:00:00Z",
    )
    assert e.struck is True
    assert e.struck_reason == "outdated"


# ---------------------------------------------------------------------------
# Task 2: wrap_entry()
# ---------------------------------------------------------------------------
import re

from backlog_core.entry_blocks import wrap_entry


def test_wrap_entry_format():
    result = wrap_entry("Some **markdown** content.\n\n- item 1\n- item 2")
    assert result.startswith("<div><sub>")
    assert "</sub>" in result
    assert "Some **markdown** content." in result
    assert result.strip().endswith("</div>")
    match = re.search(r"<sub>([^<]+)</sub>", result)
    assert match is not None
    ts = match.group(1)
    assert ts.endswith("Z")
    assert "T" in ts


def test_wrap_entry_preserves_content_exactly():
    content = "Line 1\n\n```python\ncode here\n```\n\nLine 3"
    result = wrap_entry(content)
    assert content in result


# ---------------------------------------------------------------------------
# Task 3: parse_entries()
# ---------------------------------------------------------------------------
from backlog_core.entry_blocks import parse_entries


def test_parse_single_active_entry():
    body = "<div><sub>2026-03-10T22:18:04Z</sub>\n\nSome content.\n</div>"
    entries = parse_entries(body)
    assert len(entries) == 1
    assert entries[0].id == "2026-03-10T22:18:04Z"
    assert entries[0].content == "Some content."
    assert entries[0].struck is False


def test_parse_multiple_entries():
    body = (
        "<div><sub>2026-03-10T08:00:00Z</sub>\n\nFirst.\n</div>\n\n"
        "<div><sub>2026-03-10T14:00:00Z</sub>\n\nSecond.\n</div>"
    )
    entries = parse_entries(body)
    assert len(entries) == 2
    assert entries[0].id == "2026-03-10T08:00:00Z"
    assert entries[1].id == "2026-03-10T14:00:00Z"


def test_parse_struck_entry():
    body = (
        "<div><sub>2026-03-10T08:00:00Z</sub>\n"
        "<details><summary>struck: 2026-03-11T09:00:00Z — outdated info</summary>\n\n"
        "Old content.\n</details>\n</div>"
    )
    entries = parse_entries(body)
    assert len(entries) == 1
    assert entries[0].struck is True
    assert entries[0].struck_reason == "outdated info"
    assert entries[0].struck_at == "2026-03-11T09:00:00Z"


def test_parse_duplicate_timestamps_get_suffixes():
    body = (
        "<div><sub>2026-03-10T08:00:00Z</sub>\n\nFirst.\n</div>\n\n"
        "<div><sub>2026-03-10T08:00:00Z</sub>\n\nSecond.\n</div>"
    )
    entries = parse_entries(body)
    assert len(entries) == 2
    assert entries[0].id == "2026-03-10T08:00:00Z-0"
    assert entries[1].id == "2026-03-10T08:00:00Z-1"


def test_parse_legacy_content_no_divs():
    body = "Plain text without any entry blocks.\n\nMore text."
    entries = parse_entries(body, added_date="2026-01-15")
    assert len(entries) == 1
    assert entries[0].id == "2026-01-15T00:00:00Z"
    assert "Plain text without any entry blocks." in entries[0].content


def test_parse_show_last():
    body = (
        "<div><sub>2026-03-10T08:00:00Z</sub>\n\nFirst.\n</div>\n\n"
        "<div><sub>2026-03-10T14:00:00Z</sub>\n\nSecond.\n</div>\n\n"
        "<div><sub>2026-03-10T20:00:00Z</sub>\n\nThird.\n</div>"
    )
    entries = parse_entries(body, show="last")
    assert len(entries) == 1
    assert entries[0].content == "Third."


def test_parse_show_first():
    body = (
        "<div><sub>2026-03-10T08:00:00Z</sub>\n\nFirst.\n</div>\n\n"
        "<div><sub>2026-03-10T14:00:00Z</sub>\n\nSecond.\n</div>"
    )
    entries = parse_entries(body, show="first")
    assert len(entries) == 1
    assert entries[0].content == "First."


def test_parse_show_positive_int():
    body = (
        "<div><sub>2026-03-10T08:00:00Z</sub>\n\nA.\n</div>\n\n"
        "<div><sub>2026-03-10T09:00:00Z</sub>\n\nB.\n</div>\n\n"
        "<div><sub>2026-03-10T10:00:00Z</sub>\n\nC.\n</div>"
    )
    entries = parse_entries(body, show=2)
    assert len(entries) == 2
    assert entries[0].content == "A."
    assert entries[1].content == "B."


def test_parse_show_negative_int():
    body = (
        "<div><sub>2026-03-10T08:00:00Z</sub>\n\nA.\n</div>\n\n"
        "<div><sub>2026-03-10T09:00:00Z</sub>\n\nB.\n</div>\n\n"
        "<div><sub>2026-03-10T10:00:00Z</sub>\n\nC.\n</div>"
    )
    entries = parse_entries(body, show=-2)
    assert len(entries) == 2
    assert entries[0].content == "B."
    assert entries[1].content == "C."


def test_parse_show_struck():
    body = (
        "<div><sub>2026-03-10T08:00:00Z</sub>\n\nActive.\n</div>\n\n"
        "<div><sub>2026-03-10T09:00:00Z</sub>\n"
        "<details><summary>struck: 2026-03-11T09:00:00Z — wrong</summary>\n\n"
        "Struck content.\n</details>\n</div>"
    )
    entries = parse_entries(body, show="struck")
    assert len(entries) == 1
    assert entries[0].struck is True


def test_parse_since_filter():
    body = (
        "<div><sub>2026-03-08T08:00:00Z</sub>\n\nOld.\n</div>\n\n<div><sub>2026-03-10T14:00:00Z</sub>\n\nNew.\n</div>"
    )
    entries = parse_entries(body, since="2026-03-10")
    assert len(entries) == 1
    assert entries[0].content == "New."


def test_parse_since_with_show_combined():
    body = (
        "<div><sub>2026-03-08T08:00:00Z</sub>\n\nOld.\n</div>\n\n"
        "<div><sub>2026-03-10T10:00:00Z</sub>\n\nA.\n</div>\n\n"
        "<div><sub>2026-03-10T14:00:00Z</sub>\n\nB.\n</div>\n\n"
        "<div><sub>2026-03-10T20:00:00Z</sub>\n\nC.\n</div>"
    )
    entries = parse_entries(body, show=-2, since="2026-03-10")
    assert len(entries) == 2
    assert entries[0].content == "B."
    assert entries[1].content == "C."


# ---------------------------------------------------------------------------
# Task 4: strike_entry()
# ---------------------------------------------------------------------------
from backlog_core.entry_blocks import strike_entry


def test_strike_entry_wraps_content():
    entry_raw = "<div><sub>2026-03-10T22:18:04Z</sub>\n\nOriginal content.\n</div>"
    result = strike_entry(entry_raw, "based on training data")
    assert "<sub>2026-03-10T22:18:04Z</sub>" in result
    assert "<details>" in result
    assert "struck:" in result
    assert "based on training data" in result
    assert "Original content." in result
    assert result.strip().startswith("<div>")
    assert result.strip().endswith("</div>")


def test_strike_entry_roundtrips_through_parser():
    entry_raw = "<div><sub>2026-03-10T22:18:04Z</sub>\n\nOriginal content.\n</div>"
    struck = strike_entry(entry_raw, "wrong info")
    entries = parse_entries(struck)
    assert len(entries) == 1
    assert entries[0].struck is True
    assert entries[0].struck_reason == "wrong info"
    assert "Original content." in entries[0].content


# ---------------------------------------------------------------------------
# Task 5: rewrite_section()
# ---------------------------------------------------------------------------
from backlog_core.entry_blocks import rewrite_section


def test_rewrite_append_to_empty():
    result = rewrite_section(existing_body="", new_content="First entry.", added_date="2026-01-01")
    entries = parse_entries(result)
    assert len(entries) == 1
    assert entries[0].content == "First entry."


def test_rewrite_append_to_existing():
    existing = "<div><sub>2026-03-10T08:00:00Z</sub>\n\nFirst.\n</div>"
    result = rewrite_section(existing_body=existing, new_content="Second entry.", added_date="2026-01-01")
    entries = parse_entries(result)
    assert len(entries) == 2
    assert entries[1].content == "Second entry."


def test_rewrite_append_to_legacy():
    result = rewrite_section(
        existing_body="Legacy plain text content.", new_content="New entry.", added_date="2026-01-15"
    )
    entries = parse_entries(result)
    assert len(entries) == 2
    assert entries[0].id == "2026-01-15T00:00:00Z"
    assert "Legacy plain text content." in entries[0].content
    assert entries[1].content == "New entry."


def test_rewrite_overwrite_by_entry_id():
    existing = (
        "<div><sub>2026-03-10T08:00:00Z</sub>\n\nOld.\n</div>\n\n<div><sub>2026-03-10T14:00:00Z</sub>\n\nKeep.\n</div>"
    )
    result = rewrite_section(
        existing_body=existing, new_content="Replaced.", entry_id="2026-03-10T08:00:00Z", added_date="2026-01-01"
    )
    entries = parse_entries(result)
    assert len(entries) == 2
    assert entries[0].content == "Replaced."
    assert entries[1].content == "Keep."


def test_rewrite_replace_section():
    existing = (
        "<div><sub>2026-03-10T08:00:00Z</sub>\n\nOld 1.\n</div>\n\n"
        "<div><sub>2026-03-10T14:00:00Z</sub>\n\nOld 2.\n</div>"
    )
    result = rewrite_section(
        existing_body=existing,
        new_content="Fresh start.",
        replace=True,
        reason="section rewritten during grooming",
        added_date="2026-01-01",
    )
    entries = parse_entries(result, show="all")
    active = [e for e in entries if not e.struck]
    struck = [e for e in entries if e.struck]
    assert len(active) == 1
    assert active[0].content == "Fresh start."
    assert len(struck) == 2


# ---------------------------------------------------------------------------
# Task 6: generate_diff()
# ---------------------------------------------------------------------------
from backlog_core.entry_blocks import generate_diff


def test_diff_identical():
    body = "<div><sub>2026-03-10T08:00:00Z</sub>\n\nSame.\n</div>"
    diff = generate_diff(local=body, remote=body)
    assert "- " not in diff
    assert "+ " not in diff
    assert "Same." in diff


def test_diff_remote_has_new_entry():
    local = "<div><sub>2026-03-10T08:00:00Z</sub>\n\nLocal.\n</div>"
    remote = (
        "<div><sub>2026-03-10T08:00:00Z</sub>\n\nLocal.\n</div>\n\n"
        "<div><sub>2026-03-10T14:00:00Z</sub>\n\nNew remote.\n</div>"
    )
    diff = generate_diff(local=local, remote=remote)
    assert "+ <div><sub>2026-03-10T14:00:00Z</sub>" in diff


def test_diff_local_only_entry():
    local = (
        "<div><sub>2026-03-10T08:00:00Z</sub>\n\nCommon.\n</div>\n\n"
        "<div><sub>2026-03-10T14:00:00Z</sub>\n\nLocal only.\n</div>"
    )
    remote = "<div><sub>2026-03-10T08:00:00Z</sub>\n\nCommon.\n</div>"
    diff = generate_diff(local=local, remote=remote)
    assert "- <div><sub>2026-03-10T14:00:00Z</sub>" in diff


def test_diff_content_differs():
    local = "<div><sub>2026-03-10T08:00:00Z</sub>\n\nShort.\n</div>"
    remote = "<div><sub>2026-03-10T08:00:00Z</sub>\n\nLonger content here.\n</div>"
    diff = generate_diff(local=local, remote=remote)
    assert "- <div><sub>2026-03-10T08:00:00Z</sub>" in diff
    assert "+ <div><sub>2026-03-10T08:00:00Z</sub>" in diff


# ---------------------------------------------------------------------------
# Task 7: _render_entry_raw() — unified entry renderer
# ---------------------------------------------------------------------------
from backlog_core.entry_blocks import _render_entry_raw


def test_render_entry_raw_active_format():
    """Active entry uses double newline between id and content."""
    e = Entry(id="2026-03-10T22:18:04Z", content="Active content.")
    result = _render_entry_raw(e)
    assert result == "<div><sub>2026-03-10T22:18:04Z</sub>\n\nActive content.\n</div>"


def test_render_entry_raw_struck_uses_double_newline():
    """Struck entry wraps content in details block with double newline before inner block.

    Regression: github_sync._render_entry used a single newline (\\n{inner}\\n),
    which caused merge operations to see false differences. The unified function
    must use double newline (\\n\\n{inner}\\n) consistent with active entry format.
    """
    e = Entry(
        id="2026-03-10T22:18:04Z",
        content="Old content.",
        struck=True,
        struck_reason="outdated",
        struck_at="2026-03-11T09:00:00Z",
    )
    result = _render_entry_raw(e)
    expected_inner = "<details><summary>struck: 2026-03-11T09:00:00Z — outdated</summary>\n\nOld content.\n</details>"
    expected = f"<div><sub>2026-03-10T22:18:04Z</sub>\n\n{expected_inner}\n</div>"
    assert result == expected
    # Explicitly verify the double-newline before the inner block is present
    assert "<sub>2026-03-10T22:18:04Z</sub>\n\n<details>" in result
    # Verify the old single-newline variant is NOT present
    assert "<sub>2026-03-10T22:18:04Z</sub>\n<details>" not in result


def test_render_entry_raw_struck_roundtrips_through_parser():
    """Rendered struck entry must parse back to the same Entry."""
    e = Entry(
        id="2026-03-10T22:18:04Z",
        content="Some content.",
        struck=True,
        struck_reason="wrong info",
        struck_at="2026-03-11T09:00:00Z",
    )
    rendered = _render_entry_raw(e)
    entries = parse_entries(rendered, show="all")
    assert len(entries) == 1
    assert entries[0].struck is True
    assert entries[0].struck_reason == "wrong info"
    assert entries[0].struck_at == "2026-03-11T09:00:00Z"
    assert "Some content." in entries[0].content


# ---------------------------------------------------------------------------
# Edge-case tests
# ---------------------------------------------------------------------------


def test_strike_entry_invalid_input():
    with pytest.raises(ValueError, match="Cannot strike"):
        strike_entry("not a valid entry block", "reason")


def test_rewrite_replace_without_reason_raises():
    with pytest.raises(ValueError, match="reason is required"):
        rewrite_section(existing_body="some body", new_content="new", replace=True)


def test_rewrite_overwrite_duplicate_suffixed_entry_id():
    existing = (
        "<div><sub>2026-03-10T08:00:00Z</sub>\n\nFirst.\n</div>\n\n"
        "<div><sub>2026-03-10T08:00:00Z</sub>\n\nSecond.\n</div>"
    )
    result = rewrite_section(
        existing_body=existing,
        new_content="Replaced second.",
        entry_id="2026-03-10T08:00:00Z-1",
        added_date="2026-01-01",
    )
    entries = parse_entries(result)
    assert len(entries) == 2
    assert entries[0].content == "First."
    assert entries[1].content == "Replaced second."


def test_parse_entries_empty_string():
    entries = parse_entries("")
    assert entries == []


def test_parse_entries_invalid_show_raises():
    body = "<div><sub>2026-03-10T08:00:00Z</sub>\n\nContent.\n</div>"
    with pytest.raises(ValueError, match="Unrecognized show"):
        parse_entries(body, show="bogus")


def test_parse_since_with_deduplicated_suffixed_ids():
    body = (
        "<div><sub>2026-03-10T08:00:00Z</sub>\n\nFirst.\n</div>\n\n"
        "<div><sub>2026-03-10T08:00:00Z</sub>\n\nSecond.\n</div>"
    )
    entries = parse_entries(body, since="2026-03-10T08:00:00Z")
    assert len(entries) == 2
    assert entries[0].content == "First."
    assert entries[1].content == "Second."


# ---------------------------------------------------------------------------
# wrap_entry_with_timestamp()
# ---------------------------------------------------------------------------
from backlog_core.entry_blocks import wrap_entry_with_timestamp


def test_wrap_entry_with_timestamp():
    result = wrap_entry_with_timestamp("Some content.", "2026-01-15T00:00:00Z")
    assert result == "<div><sub>2026-01-15T00:00:00Z</sub>\n\nSome content.\n</div>"


# ---------------------------------------------------------------------------
# _resolve_duplicate_ids() and _deduplicate_timestamps() — shared dedup logic
# ---------------------------------------------------------------------------
from backlog_core.entry_blocks import _deduplicate_timestamps, _resolve_duplicate_ids


def test_resolve_duplicate_ids_suffixes_duplicates():
    """Duplicate IDs must be suffixed with -0, -1, etc."""
    entries = [
        Entry(id="2026-03-10T08:00:00Z", content="First."),
        Entry(id="2026-03-10T08:00:00Z", content="Second."),
        Entry(id="2026-03-10T08:00:00Z", content="Third."),
    ]
    _resolve_duplicate_ids(entries)
    assert entries[0].id == "2026-03-10T08:00:00Z-0"
    assert entries[1].id == "2026-03-10T08:00:00Z-1"
    assert entries[2].id == "2026-03-10T08:00:00Z-2"


def test_resolve_duplicate_ids_returns_modified_count():
    """Return value must equal the number of entries whose id was changed."""
    entries = [
        Entry(id="2026-03-10T08:00:00Z", content="First."),
        Entry(id="2026-03-10T08:00:00Z", content="Second."),
        Entry(id="2026-03-10T09:00:00Z", content="Unique."),
    ]
    count = _resolve_duplicate_ids(entries)
    assert count == 2


def test_resolve_duplicate_ids_no_duplicates_returns_zero():
    """When all IDs are unique, return 0 and leave entries unchanged."""
    entries = [Entry(id="2026-03-10T08:00:00Z", content="A."), Entry(id="2026-03-10T09:00:00Z", content="B.")]
    count = _resolve_duplicate_ids(entries)
    assert count == 0
    assert entries[0].id == "2026-03-10T08:00:00Z"
    assert entries[1].id == "2026-03-10T09:00:00Z"


def test_deduplicate_timestamps_returns_modified_count():
    """_deduplicate_timestamps must return count of modified IDs (not None)."""
    entries = [Entry(id="2026-03-10T08:00:00Z", content="First."), Entry(id="2026-03-10T08:00:00Z", content="Second.")]
    result = _deduplicate_timestamps(entries)
    assert result == 2
    assert entries[0].id == "2026-03-10T08:00:00Z-0"
    assert entries[1].id == "2026-03-10T08:00:00Z-1"


def test_deduplicate_timestamps_delegates_to_resolve_duplicate_ids():
    """_deduplicate_timestamps and _resolve_duplicate_ids must produce identical results."""
    entries_a = [
        Entry(id="2026-03-10T08:00:00Z", content="First."),
        Entry(id="2026-03-10T08:00:00Z", content="Second."),
        Entry(id="2026-03-10T09:00:00Z", content="Unique."),
    ]
    entries_b = [
        Entry(id="2026-03-10T08:00:00Z", content="First."),
        Entry(id="2026-03-10T08:00:00Z", content="Second."),
        Entry(id="2026-03-10T09:00:00Z", content="Unique."),
    ]
    count_a = _resolve_duplicate_ids(entries_a)
    count_b = _deduplicate_timestamps(entries_b)
    assert count_a == count_b
    assert [e.id for e in entries_a] == [e.id for e in entries_b]


def test_rewrite_by_entry_id_uses_same_dedup_logic_as_parse():
    """rewrite_section(entry_id=...) with duplicate timestamps must resolve
    IDs the same way parse_entries() does, so a suffixed ID from parse
    round-trips correctly through rewrite."""
    existing = (
        "<div><sub>2026-03-10T08:00:00Z</sub>\n\nFirst.\n</div>\n\n"
        "<div><sub>2026-03-10T08:00:00Z</sub>\n\nSecond.\n</div>\n\n"
        "<div><sub>2026-03-10T09:00:00Z</sub>\n\nThird.\n</div>"
    )
    # parse_entries assigns: -0, -1 to the two duplicates; third stays as-is
    parsed = parse_entries(existing)
    assert parsed[0].id == "2026-03-10T08:00:00Z-0"
    assert parsed[1].id == "2026-03-10T08:00:00Z-1"
    assert parsed[2].id == "2026-03-10T09:00:00Z"

    # rewrite targeting the second duplicate must use the same suffixed ID
    result = rewrite_section(
        existing_body=existing,
        new_content="Replaced second.",
        entry_id="2026-03-10T08:00:00Z-1",
        added_date="2026-01-01",
    )
    entries = parse_entries(result)
    assert len(entries) == 3
    assert entries[0].content == "First."
    assert entries[1].content == "Replaced second."
    assert entries[2].content == "Third."


# ---------------------------------------------------------------------------
# resolve_all_entry_ids() / resolve_entry_id() — global collision resolution
#
# A suffix generated for a raw duplicate ("T", "T" -> "T-0", "T-1") must not
# collide with any id already present verbatim elsewhere in the same list —
# not just with other members of the same duplicate group. Pre-#3183 code
# could persist exactly this shape: an unknown entry_id silently appended a
# new entry carrying that literal id, so a stored section can hold two
# entries sharing a base id (needing suffixing) plus a third, unrelated
# entry whose stored id equals what the suffix algorithm would generate.
# ---------------------------------------------------------------------------
from backlog_core.entry_blocks import resolve_all_entry_ids, resolve_entry_id
from backlog_core.models import EntryNotFoundError


def test_resolve_all_entry_ids_suffix_does_not_collide_with_pre_existing_id():
    """A generated ``-N`` suffix must not collide with a raw id that already
    exists verbatim elsewhere in the list, even though that id was never
    itself duplicated."""
    raw_ids = ["T", "T", "T-0"]
    resolved = resolve_all_entry_ids(raw_ids)
    assert len(resolved) == len(set(resolved)), f"collision in {resolved!r}"
    # The pre-existing "T-0" entry keeps its literal id; both duplicates of
    # "T" must be suffixed to something else entirely.
    assert resolved[2] == "T-0"
    assert resolved[0] != "T-0"
    assert resolved[1] != "T-0"


def test_resolve_entry_id_targets_the_pre_existing_entry_not_the_first_duplicate():
    """``resolve_entry_id`` must resolve "T-0" to the entry that was
    genuinely stored under that literal id (index 2), not silently return
    the first duplicate of "T" that happens to generate the same suffix."""
    raw_ids = ["T", "T", "T-0"]
    assert resolve_entry_id(raw_ids, "T-0") == 2


@pytest.mark.parametrize(
    "raw_ids",
    [
        pytest.param(["T", "T", "T-0"], id="reproduction-two-dupes-one-pre-existing-suffix"),
        pytest.param(["T-0", "T", "T"], id="pre-existing-suffix-appears-before-its-duplicates"),
        pytest.param(["A", "A", "A-1"], id="pre-existing-suffix-matches-the-second-duplicate-not-the-first"),
        pytest.param(["T", "T"], id="plain-duplicate-no-pre-existing-collision"),
        pytest.param(["S", "S", "S", "S-0", "S-2"], id="three-way-dupe-two-pre-existing-suffixes"),
        pytest.param(["T", "T", "T", "T", "T-0", "T-1", "T-2"], id="cascading-collision-skips-multiple-candidates"),
        pytest.param(["A", "A", "B", "B", "A-0", "B-1"], id="two-separate-duplicate-groups-each-colliding"),
    ],
)
def test_resolve_all_entry_ids_never_produces_duplicate_ids(raw_ids: list[str]) -> None:
    """For any input list of raw ids, every resolved id must be pairwise
    distinct -- the invariant the collision bug violated."""
    resolved = resolve_all_entry_ids(raw_ids)
    assert len(resolved) == len(set(resolved)), f"collision in {resolved!r}"


def test_resolve_entry_id_raises_for_id_matching_no_resolved_entry():
    """An id that matches neither a raw nor a resolved id must still raise,
    not silently resolve to an unrelated entry."""
    with pytest.raises(EntryNotFoundError):
        resolve_entry_id(["T", "T", "T-0"], "does-not-exist")


def test_parse_entries_body_parsed_path_shares_the_same_collision_fix():
    """``parse_entries`` -> ``_deduplicate_timestamps`` -> ``_resolve_duplicate_ids``
    is a second, independent caller of the shared collision-resolution
    function -- reachable from a raw section body rather than a stored id
    list, and unrelated to the structured-read caller. It must not collide
    either, since both callers route through the same implementation."""
    body = (
        "<div><sub>T</sub>\n\nFirst.\n</div>\n\n"
        "<div><sub>T</sub>\n\nSecond.\n</div>\n\n"
        "<div><sub>T-0</sub>\n\nThird.\n</div>"
    )
    ids = [e.id for e in parse_entries(body)]
    assert len(ids) == len(set(ids)), f"collision in {ids!r}"
    assert ids[2] == "T-0"


# hypothesis is a repository dev dependency (see pyproject.toml); a small,
# bounded alphabet of ids that includes both bases and their own suffixed
# forms is what actually stresses the collision path -- purely random
# strings would almost never generate an id that looks like another id's
# suffix.
from hypothesis import given, strategies as st

_COLLISION_PRONE_IDS = st.sampled_from(["T", "T-0", "T-1", "T-2", "A", "A-0", "A-1", "S", "S-0", "S-1", "S-2"])


@given(st.lists(_COLLISION_PRONE_IDS, min_size=0, max_size=8))
def test_resolve_all_entry_ids_property_ids_are_always_pairwise_distinct(raw_ids: list[str]) -> None:
    """Property: for any input list drawn from an alphabet designed to
    provoke base/suffix collisions, resolve_all_entry_ids must never return
    two equal ids."""
    resolved = resolve_all_entry_ids(raw_ids)
    assert len(resolved) == len(raw_ids)
    assert len(resolved) == len(set(resolved)), f"collision in {resolved!r} from input {raw_ids!r}"


# ---------------------------------------------------------------------------
# Residual extent-rule divergence — wrap_entry/strike_entry off ENTRY_RE onto
# find_entry_spans, the STRUCK_RE defect, the <div/> and case-insensitive tag
# grammar gaps. See .tmp/scratch/reports/20260823-entry-extent-residual.md.
# ---------------------------------------------------------------------------


def test_wrap_entry_nested_div_is_idempotent_across_resubmission():
    """A nested <div> inside an entry must not make ENTRY_RE-style truncation
    split the entry and grow a fresh junk entry on every resubmission."""
    content = 'Finding A.\n\n<div align="center">a nested figure</div>\n\nFinding B - the important part.'
    submit_1 = wrap_entry(content)
    submit_2 = wrap_entry(submit_1)
    submit_3 = wrap_entry(submit_2)
    assert submit_2 == submit_1
    assert submit_3 == submit_1
    entries = parse_entries(submit_3)
    assert len(entries) == 1
    assert "Finding B - the important part." in entries[0].content


def test_wrap_entry_fenced_example_preserves_fence_and_is_idempotent():
    """A fenced markdown example of the wrapper format must not be broken open
    by a naive ENTRY_RE scan that does not know about code fences."""
    content = "Why it matters.\n\n```\n<div><sub>2026-01-01T00:00:00Z</sub>\n\ninner\n</div>\n```"
    submit_1 = wrap_entry(content)
    submit_2 = wrap_entry(submit_1)
    submit_3 = wrap_entry(submit_2)
    assert submit_2 == submit_1
    assert submit_3 == submit_1
    entries = parse_entries(submit_3)
    assert len(entries) == 1
    assert "Why it matters." in entries[0].content
    assert "```\n<div><sub>2026-01-01T00:00:00Z</sub>\n\ninner\n</div>\n```" in entries[0].content


def test_wrap_entry_inline_code_is_idempotent_across_resubmission():
    """A literal `</div>` inside an inline code span must not be treated as
    the wrapper's real closing tag."""
    content = "See the closing tag `</div>` in the wrapper format.\n\nTrailing sentence."
    submit_1 = wrap_entry(content)
    submit_2 = wrap_entry(submit_1)
    submit_3 = wrap_entry(submit_2)
    assert submit_2 == submit_1
    assert submit_3 == submit_1
    entries = parse_entries(submit_3)
    assert len(entries) == 1
    assert "Trailing sentence." in entries[0].content


def test_parse_entries_struck_entry_with_nested_details_preserves_tail():
    """STRUCK_RE's non-greedy stop at the first </details> must not drop
    content that follows a nested <details> inside the struck block."""
    body = (
        "<div><sub>2026-03-03T00:00:00Z</sub>\n"
        "<details><summary>struck: 2026-08-23T04:00:00Z — superseded</summary>\n\n"
        "Notes.\n\n"
        "<details><summary>detail</summary>\ninner\n</details>\n\n"
        "Tail that matters.\n"
        "</details>\n"
        "</div>"
    )
    entries = parse_entries(body)
    assert len(entries) == 1
    assert entries[0].struck is True
    assert "Tail that matters." in entries[0].content


def test_parse_entries_prose_mentioning_struck_format_is_not_struck():
    """A struck marker that merely appears inside prose documenting the format
    (not at the start of the entry's content) must not be treated as struck."""
    body = (
        "<div><sub>2026-03-03T00:00:00Z</sub>\n\n"
        "A struck entry renders as:\n\n"
        "<details><summary>struck: TS — reason</summary>\n\n"
        "original\n"
        "</details>\n\n"
        "That is the format.\n"
        "</div>"
    )
    entries = parse_entries(body)
    assert len(entries) == 1
    assert entries[0].struck is False
    assert "A struck entry renders as:" in entries[0].content
    assert "That is the format." in entries[0].content


def test_find_entry_spans_self_closing_div_does_not_drop_entry():
    """A self-closing <div/> must not count as an opener that never closes —
    that drops the whole entry, not just its content."""
    body = (
        "<div><sub>2026-01-01T00:00:00Z</sub>\n\nA <div/> self-closing.\n</div>\n\n"
        "<div><sub>2026-01-02T00:00:00Z</sub>\n\nSecond entry.\n</div>"
    )
    entries = parse_entries(body)
    assert len(entries) == 2
    assert entries[0].id == "2026-01-01T00:00:00Z"
    assert "self-closing" in entries[0].content
    assert entries[1].content == "Second entry."


def test_find_entry_spans_case_differing_nested_div_does_not_drop_entry():
    """A nested div tag whose spelling differs in case between open and close
    (e.g. <div> ... </DIV>) must still balance and not drop the entry."""
    body = (
        "<div><sub>2026-01-01T00:00:00Z</sub>\n\n"
        'Finding.\n\n<div class="note">note</DIV>\n\nTail.\n'
        "</div>\n\n"
        "<div><sub>2026-01-02T00:00:00Z</sub>\n\nSecond entry.\n</div>"
    )
    entries = parse_entries(body)
    assert len(entries) == 2
    assert entries[0].id == "2026-01-01T00:00:00Z"
    assert "Tail." in entries[0].content
    assert entries[1].content == "Second entry."
