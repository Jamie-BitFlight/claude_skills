"""General-purpose section round-trip data-integrity tests.

Narrowly-scoped regression tests for specific historical bugs already exist
elsewhere (``test_section_name_registry_drift.py``,
``test_backlog_groom_sections.py``, ``test_batch_section_writes.py``). This
suite is not scoped to any one bug — it exercises the round-trip contract for
ANY section name through the real write path (``operations.groom_item``) and
real read path (``operations.view_item``), plus the ``yaml_io``
``unknown__`` promotion mechanism (``rendering.normalize_unknown_sections``),
so it can catch anything the narrower tests don't.

Suite A: write -> read -> write -> read through the operations layer, for
canonical section names (read live from ``rendering.SECTION_HEADING``),
novel names never seen in this repo, and a Title-Case collision pair.

Suite B: ``unknown__{name}`` promotion round-trip through ``yaml_io.save_item``
/ ``yaml_io.load_item`` for both a now-registered name and a name that stays
unregistered.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import backlog_core.operations as ops
import pytest
from backlog_core import rendering, yaml_io
from backlog_core.models import BacklogItem, BacklogItemMetadata, Entry, GroomedData, Output, Section
from backlog_core.operations import view_item
from backlog_core.parsing import find_item, now_iso

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture

# ---------------------------------------------------------------------------
# Suite A: general round-trip integrity, any key
# ---------------------------------------------------------------------------

# (a) Every canonical display name currently registered — read live so this
# suite tracks rendering.SECTION_HEADING instead of a copy that can drift.
_CANONICAL_NAMES = sorted(rendering.SECTION_HEADING.values())

# (b) Names never seen anywhere in this repo — proves the mechanism doesn't
# special-case known names.
_NOVEL_NAMES = ["Zorbnak Analysis", "Quux Metrics", "Section 47"]

_ALL_NAMES = _CANONICAL_NAMES + _NOVEL_NAMES


def _mock_no_github(mocker: MockerFixture) -> None:
    mocker.patch("backlog_core.operations.view_enrich_from_github", return_value=False)
    mocker.patch("backlog_core.operations.try_get_github", return_value=None)


@pytest.mark.parametrize("name", _ALL_NAMES)
def test_round_trip_fresh_write_no_loss_no_duplication(name: str, mocker: MockerFixture) -> None:
    """write -> read -> write -> read preserves all content under one stable key.

    Tests: operations.groom_item (write) + operations.view_item (read) round trip
    How: Write one entry via groom_item, read, write a second entry via groom_item
         with the same section name, read again. Assert both entries are present,
         nothing is duplicated, and the section key used is identical both times.
    Why: The general round-trip contract must hold for ANY section name, not just
         the specific names covered by narrowly-scoped bug regression tests.
    """
    _mock_no_github(mocker)
    out = Output()
    title = f"RT Fresh {name}"
    ops.add_item(title=title, priority="P1", description="Test", output=out)

    ops.groom_item(selector=title, section=name, content="Entry one.", output=out)
    result1 = view_item(selector=title, output=out)
    keys1 = set(result1.sections)
    assert len(keys1) == 1, f"Expected exactly one section key after first write, got {keys1}"
    key1 = next(iter(keys1))
    section1 = result1.sections[key1]
    assert ops._is_section_entry_metadata(section1)
    assert [e["content"] for e in section1["entries"]] == ["Entry one."]

    ops.groom_item(selector=title, section=name, content="Entry two.", output=out)
    result2 = view_item(selector=title, output=out)
    keys2 = set(result2.sections)
    assert keys2 == keys1, f"Section key changed between writes: {keys1} -> {keys2}"
    section2 = result2.sections[key1]
    assert ops._is_section_entry_metadata(section2)
    contents2 = {e["content"] for e in section2["entries"]}
    assert contents2 == {"Entry one.", "Entry two."}, f"Expected both entries present, got {contents2}"


@pytest.mark.parametrize("name", _ALL_NAMES)
def test_round_trip_existing_prior_content_no_loss_no_duplication(name: str, mocker: MockerFixture) -> None:
    """Writing into a section that already has content preserves the existing entry.

    Tests: operations.groom_item append path against a pre-seeded backend record
    How: Seed the backend directly with one existing entry under the key
         operations._normalize_section_key(name) computes for this name (the real
         normalizer, not a re-derived guess), then groom_item a second entry using
         the caller-supplied display name; assert both entries survive under one key.
    Why: The "existing keys" case is exactly where a write-path/parse-path key
         mismatch would silently duplicate or orphan content (#2956's bug class) —
         this independently verifies _normalize_section_key agrees with itself
         across a seed-then-append sequence.
    """
    _mock_no_github(mocker)
    out = Output()
    title = f"RT Existing {name}"
    ops.add_item(title=title, priority="P1", description="Test", output=out)

    from backlog_core.backend_protocol import get_config

    key = ops._normalize_section_key(name)
    item = find_item(get_config().backend.list_work_items(), title)
    assert item is not None
    item.sections[key] = Section(entries=[Entry(id=now_iso(), content="Pre-existing entry.")])
    get_config().backend.put_work_item(item)

    ops.groom_item(selector=title, section=name, content="New entry.", output=out)
    result = view_item(selector=title, output=out)
    keys = set(result.sections)
    assert len(keys) == 1, f"Expected exactly one section key, got {keys}"
    section = result.sections[next(iter(keys))]
    assert ops._is_section_entry_metadata(section)
    contents = {e["content"] for e in section["entries"]}
    assert contents == {"Pre-existing entry.", "New entry."}, f"Expected both entries present, got {contents}"


def test_title_case_collision_writes_merge_into_one_section(mocker: MockerFixture) -> None:
    """Case-variant section names collide onto one storage key (#2971 regression guard).

    Tests: operations._normalize_section_key case-insensitive collision handling
    How: groom_item with section="Notes", then section="notes" (differing only by
         case). Assert both entries land in ONE section, not two.
    Why: Before #2971's key-normalization unification, differently-cased calls
         into the same logical section could diverge into separate unknown__
         keys, silently orphaning content under a key no reader would look at.
         Reuses the exact "Notes" vs "notes" scenario #2971 fixed.

         Asserts on the RAW backend-stored keys, not just view_item's output:
         view_item's YAML-fallback path (_build_sections_from_yaml_item) merges
         entries by display title, which can mask a storage-key divergence that
         still leaves two distinct keys persisted (confirmed by falsification —
         reverting heading_to_unknown_key's case-folding produced two raw keys,
         'unknown__Notes' and 'unknown__notes', while view_item's display-merged
         output still showed only one section, silently hiding the regression).
    """
    _mock_no_github(mocker)
    out = Output()
    title = "RT Collision Item"
    ops.add_item(title=title, priority="P1", description="Test", output=out)

    ops.groom_item(selector=title, section="Notes", content="Upper case write.", output=out)
    ops.groom_item(selector=title, section="notes", content="Lower case write.", output=out)

    from backlog_core.backend_protocol import get_config

    item = find_item(get_config().backend.list_work_items(), title)
    assert item is not None
    raw_matching_keys = [k for k in item.sections if k.lower() in {"notes", "unknown__notes"}]
    assert len(raw_matching_keys) == 1, (
        f"Expected exactly one raw storage key for 'Notes'/'notes', got {list(item.sections)}"
    )
    raw_section = item.sections[raw_matching_keys[0]]
    assert isinstance(raw_section, Section)
    raw_contents = {e.content for e in raw_section.entries}
    assert raw_contents == {"Upper case write.", "Lower case write."}

    result = view_item(selector=title, output=out)
    matching_keys = [k for k in result.sections if k.lower() == "notes"]
    assert len(matching_keys) == 1, f"Expected exactly one 'notes'-like key, got {list(result.sections)}"
    section = result.sections[matching_keys[0]]
    assert ops._is_section_entry_metadata(section)
    contents = {e["content"] for e in section["entries"]}
    assert contents == {"Upper case write.", "Lower case write."}


# ---------------------------------------------------------------------------
# Suite B: unknown__ promotion round-trip (yaml_io.normalize_unknown_sections)
# ---------------------------------------------------------------------------


def _make_item(sections: dict[str, Section | GroomedData]) -> BacklogItem:
    return BacklogItem(
        title="Legacy Cache Item",
        description="Test item",
        metadata=BacklogItemMetadata(source="test", added="2026-01-01", priority="P1", status="open"),
        sections=sections,
    )


def test_unknown_prefix_folds_into_canonical_key_on_load(tmp_path: Path) -> None:
    """A legacy unknown__{name} key for a now-registered name folds to the plain key.

    Tests: yaml_io.load_item -> rendering.normalize_unknown_sections
    How: Construct a BacklogItem with sections={"unknown__story": ...} ("story"
         is registered in SECTION_HEADING), save via yaml_io.save_item, load back
         via yaml_io.load_item. Assert the loaded item has "story" (not
         "unknown__story") with the original entry intact.
    Why: A cache file written before a section name was registered stores it
         legacy-prefixed; normalize_unknown_sections is the mechanism that heals
         it on next load without a migration script.
    """
    assert "story" in rendering.SECTION_HEADING, "test fixture assumes 'story' is a registered canonical section"
    path = tmp_path / "legacy.yaml"
    item = _make_item({
        "unknown__story": Section(entries=[Entry(id="2026-01-01T00:00:00Z", content="Legacy content.")])
    })
    yaml_io.save_item(item, path)

    loaded = yaml_io.load_item(path)

    assert "unknown__story" not in loaded.sections, "Legacy unknown__ key must not survive a load once registered"
    assert "story" in loaded.sections
    story = loaded.sections["story"]
    assert isinstance(story, Section)
    assert [e.content for e in story.entries] == ["Legacy content."]


def test_unknown_prefix_promoted_key_survives_further_write_and_read(tmp_path: Path) -> None:
    """After promotion, the canonical key behaves as a normal section across further writes.

    Tests: yaml_io normalize-then-append-then-reload round trip
    How: Load a legacy unknown__story item (promotes to "story" on load), append
         a new entry directly to the promoted Section, save, reload. Assert no
         unknown__ remnant and both the legacy and new entries are present.
    Why: Promotion must not be a one-shot cosmetic rename that a later write can
         silently un-promote or duplicate — content from both the legacy entry
         and the new write must both survive, not one clobbering the other.
    """
    path = tmp_path / "legacy.yaml"
    item = _make_item({
        "unknown__story": Section(entries=[Entry(id="2026-01-01T00:00:00Z", content="Legacy content.")])
    })
    yaml_io.save_item(item, path)

    loaded = yaml_io.load_item(path)
    story = loaded.sections["story"]
    assert isinstance(story, Section)
    story.entries.append(Entry(id="2026-01-02T00:00:00Z", content="New content."))
    yaml_io.save_item(loaded, path)

    reloaded = yaml_io.load_item(path)
    assert "unknown__story" not in reloaded.sections
    assert "story" in reloaded.sections
    reloaded_story = reloaded.sections["story"]
    assert isinstance(reloaded_story, Section)
    contents = {e.content for e in reloaded_story.entries}
    assert contents == {"Legacy content.", "New content."}


def test_unknown_prefix_unregistered_name_stays_prefixed_across_cycles(tmp_path: Path) -> None:
    """An unregistered unknown__ name stays consistently prefixed across repeated cycles.

    Tests: yaml_io normalize round trip for a name NOT in SECTION_HEADING
    How: Round-trip save/load three times for "unknown__zorbnak_analysis" (never
         registered), appending a new entry each cycle. Assert the key never
         changes spelling and no content is lost across the cycles.
    Why: Falsification target for "no flip-flopping" — an unregistered name must
         not oscillate between different unknown__ spellings, and normalizing
         an unrecognised key must not crash or drop content.
    """
    assert "zorbnak_analysis" not in rendering.SECTION_HEADING, "test fixture name must stay unregistered"
    path = tmp_path / "legacy.yaml"
    item = _make_item({"unknown__zorbnak_analysis": Section(entries=[Entry(id="2026-01-01T00:00:00Z", content="A.")])})
    yaml_io.save_item(item, path)

    for cycle_num, cycle_content in enumerate(("B.", "C."), start=2):
        loaded = yaml_io.load_item(path)
        assert set(loaded.sections) == {"unknown__zorbnak_analysis"}, (
            f"Key spelling changed across cycles: {list(loaded.sections)}"
        )
        section = loaded.sections["unknown__zorbnak_analysis"]
        assert isinstance(section, Section)
        section.entries.append(Entry(id=f"2026-01-0{cycle_num}T00:00:00Z", content=cycle_content))
        yaml_io.save_item(loaded, path)

    final = yaml_io.load_item(path)
    assert set(final.sections) == {"unknown__zorbnak_analysis"}
    final_section = final.sections["unknown__zorbnak_analysis"]
    assert isinstance(final_section, Section)
    contents = {e.content for e in final_section.entries}
    assert contents == {"A.", "B.", "C."}
