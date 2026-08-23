"""End-to-end reproduction test for #3187 — struck state through progressive disclosure.

**TDD state (RED)**: This module pins the item's own reproduction verbatim, built
through the REAL production pipeline — ``entry_blocks.wrap_entry_with_timestamp`` →
``entry_blocks.strike_entry`` → ``entry_blocks.parse_entries`` → ``SectionEntryDict``
list → ``ViewItemResult`` → ``ItemContentNormalizer`` → ``OrdinalPathMapper`` →
``BacklogViewDisclosureHandler``. The only thing bypassed is the backend fetch
(``operations.view_item``, patched with a hand-built ``ViewItemResult``) — nothing
under test is mocked.

Bug being reproduced: the progressive-disclosure read path (``backlog_view`` with
``map=``/``navigate=``) silently dropped each entry's ``struck``/``id`` fields — a
retracted (struck) entry was indistinguishable from live content by the time it
reached a caller. Item #3187's own ``RT-ICA`` section is the canonical live
reproduction (see the solution design brief §2 for the captured baseline):

- ``16.0`` — RT-ICA Snapshot, ``struck: true``
- ``16.1`` — RT-ICA Final, live

This file rebuilds that exact shape synthetically (ordinal ``"0.0"``/``"0.1"``
instead of ``"16.0"``/``"16.1"`` — this is a fresh single-section document, not
item #3187 itself) so the test is self-contained and does not depend on live
backend state.

Until the fix lands, failures below are expected in one of two forms — both are
the RIGHT reason (feature not yet implemented downstream of ``NormalizedEntry``):

- ``AttributeError`` — accessing ``.struck``/``.entry_id``/``.struck_ordinals`` on
  types that do not carry those fields yet (``OrdinalEntry``, ``ResolvedUnit``,
  ``MapResponse``, ``NavigateResponse``, ``BoundedResponse``).
- ``AssertionError`` — the in-band ``[struck:{entry_id}]`` marker is absent from
  aggregate content because ``build_map()``'s section-content join does not emit
  it yet.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from backlog_core.content_normalizer import ItemContentNormalizer
from backlog_core.disclosure_handler import BacklogViewDisclosureHandler, DisclosureRequestParser
from backlog_core.disclosure_types import MapResponse
from backlog_core.entry_blocks import parse_entries, strike_entry, wrap_entry_with_timestamp
from backlog_core.models import Entry, SectionEntryDict, SectionEntryMetadata, ViewItemResult
from backlog_core.ordinal_mapper import OrdinalPathMapper

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

try:
    from progressive_markdown.list_navigator import ENCODING as _ENCODING

    _ENCODING_AVAILABLE: bool = _ENCODING is not None
except (ImportError, OSError):
    _ENCODING_AVAILABLE = False

_skip_without_real_enc = pytest.mark.skipif(
    not _ENCODING_AVAILABLE, reason="cl100k_base encoding unavailable (offline environment)."
)

# ---------------------------------------------------------------------------
# Reproduction builder — the item's own repro steps, verbatim
# ---------------------------------------------------------------------------

_STRUCK_TS = "2026-08-23T11:49:14.766159Z"
_LIVE_TS = "2026-08-23T12:00:00.000000Z"
_STRUCK_CONTENT = "RT-ICA Snapshot: original assessment, since superseded."
_LIVE_CONTENT = "RT-ICA Final: resolved assessment."


def _build_mixed_struck_view_result() -> tuple[ViewItemResult, str, str]:
    """Build a real ``ViewItemResult`` with one struck and one live entry.

    Reproduces item #3187's RT-ICA section shape via the real entry pipeline:
    ``wrap_entry_with_timestamp`` → ``strike_entry`` → ``parse_entries(show="all")``
    → ``SectionEntryDict`` list → ``ViewItemResult``. Only ``operations.view_item``
    (the backend fetch) is ever bypassed by callers of this helper.

    Returns:
        Tuple of ``(ViewItemResult, struck_entry_id, live_entry_id)``.
    """
    struck_block_raw = wrap_entry_with_timestamp(_STRUCK_CONTENT, _STRUCK_TS)
    struck_block = strike_entry(struck_block_raw, reason="superseded by final assessment")
    live_block = wrap_entry_with_timestamp(_LIVE_CONTENT, _LIVE_TS)

    section_body = f"{struck_block}\n\n{live_block}"
    entries: list[Entry] = parse_entries(section_body, show="all")
    assert len(entries) == 2, f"Precondition: reproduction must parse exactly 2 entries; got {len(entries)}."
    assert entries[0].struck is True, "Precondition: first parsed entry must be struck (the Snapshot)."
    assert entries[1].struck is False, "Precondition: second parsed entry must be live (the Final)."

    entry_dicts: list[SectionEntryDict] = [
        SectionEntryDict(id=e.id, struck=e.struck, content=e.content) for e in entries
    ]
    section_meta = SectionEntryMetadata(num_entries=1, num_struck=1, entries=entry_dicts)
    body = "## Sections\n[0] RT-ICA (2 entries)\n"
    result = ViewItemResult(sections={"RT-ICA": section_meta}, body=body, sections_index="")
    return result, entries[0].id, entries[1].id


# ---------------------------------------------------------------------------
# Sanity: the real pipeline threads struck/entry_id into NormalizedEntry
# ---------------------------------------------------------------------------


class TestReproductionNormalizesStruckAndEntryId:
    """The real entry_blocks → normalizer pipeline preserves struck/entry_id.

    This class is expected to PASS already — it only exercises
    ``ItemContentNormalizer``, which the RED-phase dataclass change already wires
    correctly. It anchors that the reproduction builder itself is sound before the
    downstream (ordinal_mapper / disclosure_handler) RED assertions below.
    """

    def test_normalized_entries_carry_struck_and_entry_id(self) -> None:
        """NormalizedEntry.struck/.entry_id exactly mirror the parsed Entry objects."""
        result, struck_id, live_id = _build_mixed_struck_view_result()

        normalized = ItemContentNormalizer().normalize(result)

        assert len(normalized) == 1, f"Expected exactly 1 section; got {len(normalized)}."
        struck_entry, live_entry = normalized[0].entries
        assert struck_entry.struck is True, f"First entry must be struck; got {struck_entry.struck!r}."
        assert struck_entry.entry_id == struck_id, (
            f"First entry_id must be {struck_id!r}; got {struck_entry.entry_id!r}."
        )
        assert live_entry.struck is False, f"Second entry must be live; got {live_entry.struck!r}."
        assert live_entry.entry_id == live_id, f"Second entry_id must be {live_id!r}; got {live_entry.entry_id!r}."


# ---------------------------------------------------------------------------
# RED: the AC-4 gate — build_map()'s level-1 aggregate must not merge struck
# and live content into one indistinguishable string
# ---------------------------------------------------------------------------


class TestReproductionBuildMapLevelOneAggregateFlagsStruckContent:
    """AC-4 gate row: a half-fix that only adds fields to ``NormalizedEntry`` and
    the response types — without also changing ``build_map()``'s level-1 content
    join — still reproduces the exact defect: ``navigate="0"`` (item #3187's
    ``navigate="16"``) returns struck+live text merged with no marker anywhere.
    """

    @_skip_without_real_enc
    def test_level1_aggregate_content_marks_struck_and_not_live(self) -> None:
        """resolve('0').content must carry '[struck:{struck_id}]' immediately before
        the Snapshot text, and no marker anywhere near the Final text.
        """
        result, struck_id, live_id = _build_mixed_struck_view_result()
        normalized = ItemContentNormalizer().normalize(result)
        mapper = OrdinalPathMapper(normalized)
        mapper.build_map()

        resolved = mapper.resolve("0")

        marker = f"[struck:{struck_id}]"
        assert marker in resolved.content, (
            f"Level-1 aggregate content must carry the struck marker for the struck entry; got: {resolved.content!r}"
        )
        assert resolved.content.index(marker) < resolved.content.index(_STRUCK_CONTENT), (
            "Struck marker must precede the struck entry's own text."
        )
        assert f"[struck:{live_id}]" not in resolved.content, (
            "The live entry must never be marked struck — no marker keyed to its entry_id."
        )
        assert _LIVE_CONTENT in resolved.content, "Live entry text must still be present, unmarked."


# ---------------------------------------------------------------------------
# RED: AC-1 — both entries independently addressable and oppositely flagged
# ---------------------------------------------------------------------------


class TestReproductionBothVariantsIndependentlyAddressableAndOppositelyFlagged:
    """Both AC-1 variants ('16.0'/'16.1' in the live item, '0.0'/'0.1' here) are
    present, independently addressable, and oppositely flagged — the core claim
    of the bug report: a caller can no longer confuse the two.
    """

    @_skip_without_real_enc
    def test_level2_entries_are_independently_and_oppositely_flagged(self) -> None:
        """build_map() emits '0.0' (struck=True) and '0.1' (struck=False) — never
        the same flag value for both.
        """
        result, struck_id, live_id = _build_mixed_struck_view_result()
        normalized = ItemContentNormalizer().normalize(result)
        mapper = OrdinalPathMapper(normalized)
        entries = mapper.build_map()

        by_ordinal = {e.ordinal: e for e in entries}
        assert "0.0" in by_ordinal, f"Level-2 ordinal '0.0' must be addressable. Got: {sorted(by_ordinal)}"
        assert "0.1" in by_ordinal, f"Level-2 ordinal '0.1' must be addressable. Got: {sorted(by_ordinal)}"

        struck_entry = by_ordinal["0.0"]
        live_entry = by_ordinal["0.1"]

        # AttributeError expected here until OrdinalEntry carries a struck field.
        assert struck_entry.struck is True, f"'0.0' (Snapshot) must report struck=True; got {struck_entry!r}."
        assert live_entry.struck is False, f"'0.1' (Final) must report struck=False; got {live_entry!r}."
        assert struck_entry.entry_id == struck_id
        assert live_entry.entry_id == live_id

    @_skip_without_real_enc
    def test_handler_map_mode_reports_struck_ordinals_for_the_reproduction(self, mocker: MockerFixture) -> None:
        """End to end through the handler: MAP mode's struck_ordinals contains
        exactly the struck level-2 ordinal from the reproduction.
        """
        result, _struck_id, _live_id = _build_mixed_struck_view_result()
        mocker.patch("backlog_core.operations.view_item", return_value=result)

        response = BacklogViewDisclosureHandler().handle("#repro-3187", DisclosureRequestParser().parse(map=True))

        assert isinstance(response, MapResponse), f"Expected MapResponse; got {type(response).__name__}."
        assert response.struck_ordinals == ["0.0"], (
            f"struck_ordinals must list exactly '0.0'; got {response.struck_ordinals!r}."
        )
