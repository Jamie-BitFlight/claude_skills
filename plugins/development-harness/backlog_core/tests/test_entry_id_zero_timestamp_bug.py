"""Regression tests for the zero-timestamp entry-ID bug in view_item / backlog_view.

Every entry in every section returned by ``view_item`` / ``backlog_view`` has
``"id": "0000-00-00T00:00:00Z"`` regardless of the real timestamp persisted in
YAML.  Two independent mechanisms destroy the real IDs at read/render time.

**Mechanism 1 — GitHub-enriched path** (operations.py ~line 3269)
    ``view_enrich_from_github`` injects a plain-text body (no
    ``<div><sub>…</sub>`` wrappers).  ``_build_sections_metadata`` then parses
    that plain-text body, finds no ``ENTRY_RE`` matches, and falls back to
    ``f"{added_date}T00:00:00Z"`` for every entry.

**Mechanism 2 — Paginated YAML path** (operations.py ~lines 3288-3290)
    ``render_sections_as_body`` drops ``e.id`` when serialising YAML entries to
    markdown (only ``e.content`` is emitted).  When pagination is active
    (``offset > 0`` or ``limit > 0``), the post-pagination metadata rebuild
    calls ``_build_sections_metadata(result.body, …)`` on that ID-stripped
    rendered body, overwriting the correctly-populated ``result.sections`` from
    ``_build_sections_from_yaml_item`` with zero-ID entries.

The fallback producing the zero ID lives in ``entry_blocks.py:158``::

    entry_id = ts_match.group(1) if ts_match else f"{added_date}T00:00:00Z"

where ``added_date`` defaults to ``"0000-00-00"``.

Each test here:

1. Sets up a ``BacklogItem`` with at least one ``Entry`` whose ``id`` is a real
   ``now_iso()`` timestamp persisted in the YAML structure.
2. Simulates exactly the condition that triggers zero-ID output for that
   mechanism (GitHub body enrichment for M1; pagination for M2).
3. Asserts that every entry in the returned sections carries the real persisted
   ID, not the zero-timestamp default.
4. **Fails on the current (pre-fix) codebase.**  The assertion message names
   both the mechanism and the actual-vs-expected ID so CI output pinpoints
   which mechanism fired.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backlog_core.models import BacklogItem, Entry, Section, ViewItemResult
from backlog_core.operations import view_item
from backlog_core.parsing import now_iso

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

_ZERO_ID_PREFIX = "0000-00-00"
"""Prefix that uniquely identifies a zero-timestamp entry ID."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_item_with_real_entry(section_name: str = "Acceptance Criteria") -> tuple[BacklogItem, str]:
    """Create a BacklogItem with one entry carrying a real now_iso() timestamp ID.

    Args:
        section_name: Name of the single section to create.

    Returns:
        A 2-tuple of (BacklogItem, real_entry_id) so callers can assert the
        expected ID without re-deriving it from the item structure.
    """
    real_id = now_iso()
    entry = Entry(id=real_id, content="This entry has a real timestamp ID.")
    section = Section(entries=[entry])
    item = BacklogItem(title="Zero-ID regression item", sections={section_name: section})
    return item, real_id


def _collect_entry_ids(result: ViewItemResult) -> list[tuple[str, str]]:
    """Collect (section_name, entry_id) pairs from result.sections.

    Args:
        result: The ViewItemResult to inspect.

    Returns:
        A flat list of (section_name, entry_id) tuples for every entry across
        all sections, in section iteration order.
    """
    pairs: list[tuple[str, str]] = []
    for sec_name, sec_meta in result.sections.items():
        if not isinstance(sec_meta, dict):
            continue
        entries = sec_meta.get("entries", [])
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            entry_id = str(entry.get("id", ""))
            pairs.append((sec_name, entry_id))
    return pairs


# ---------------------------------------------------------------------------
# M1 — GitHub-enriched path: plain-text body destroys entry IDs
# ---------------------------------------------------------------------------


class TestMechanism1GitHubEnrichedZeroId:
    """M1 regression: GitHub-enriched body overwrites YAML entry IDs with zero timestamps.

    ``view_enrich_from_github`` injects a plain-text body string.
    ``_assemble_view_content`` then calls ``_build_sections_metadata(body, ...)``
    on that plain-text body.  Because the body contains no
    ``<div><sub>timestamp</sub>`` wrappers, ``parse_entries`` finds no
    ``ENTRY_RE`` matches and falls back to ``f"{added_date}T00:00:00Z"`` for
    every entry, discarding the real IDs from the YAML structure.

    The test isolates M1 by: (a) providing a local item with a real entry ID,
    (b) injecting a plain-text GitHub body with NO entry-block wrappers,
    (c) disabling pagination (limit=0, offset=0) so M2 cannot fire.
    """

    def test_github_enriched_view_item_returns_real_entry_id_not_zero(self, mocker: MockerFixture) -> None:
        """view_item with GitHub enrichment must return the real YAML entry ID.

        Arrange: local BacklogItem with one entry whose id is a real now_iso()
        timestamp.  GitHub enrichment injects a plain-text body (no entry-block
        wrappers) for the same section.

        Act: view_item(include_content=True, offset=0, limit=0) — no pagination,
        GitHub enrichment active.

        Assert: every entry in result.sections carries the real persisted ID,
        not the zero-timestamp fallback from entry_blocks.py:158.

        RED (pre-fix): ``_build_sections_metadata`` parses the plain-text GitHub
        body, finds no ENTRY_RE matches, and emits ``"0000-00-00T00:00:00Z"``
        for every entry — the real YAML ID is silently discarded.
        """
        section_name = "Acceptance Criteria"
        item, real_id = _make_item_with_real_entry(section_name)

        # Patch the operations layer so view_item reads from our controlled item
        # and GitHub enrichment injects a plain-text body for the same section.
        # The injected body contains NO <div><sub> entry-block wrappers — exactly
        # the condition that triggers M1 zero-ID production.
        mocker.patch("backlog_core.operations.parse_backlog", return_value=[item])
        mocker.patch("backlog_core.operations.find_item", return_value=item)
        mocker.patch("backlog_core.operations.parse_issue_selector", return_value=9901)

        plain_text_body = f"## {section_name}\n\nThis entry has a real timestamp ID.\n"

        def _inject_plain_text_body(result: ViewItemResult, issue_num: str, repo: str = "") -> bool:
            """Simulate GitHub body enrichment with plain-text (no entry-block wrappers)."""
            result.body = plain_text_body
            return True

        mocker.patch("backlog_core.operations.view_enrich_from_github", side_effect=_inject_plain_text_body)

        # Act — no pagination (limit=0, offset=0) isolates M1 from M2
        result = view_item(selector="9901", include_content=True, offset=0, limit=0)

        # Assert — result.sections must be populated
        assert result.sections, (
            "M1 (GitHub-enriched): result.sections must not be empty. "
            "If empty the test arrangement is wrong — check the mock setup."
        )

        entry_pairs = _collect_entry_ids(result)
        assert entry_pairs, (
            "M1 (GitHub-enriched): no entries found in result.sections. "
            "The section must contain the entry from the injected GitHub body."
        )

        for sec_name, got_id in entry_pairs:
            assert not got_id.startswith(_ZERO_ID_PREFIX), (
                f"M1 (GitHub-enriched path): section={sec_name!r} entry id={got_id!r} "
                f"is the zero-timestamp default from entry_blocks.py:158. "
                f"Expected real id={real_id!r}. "
                "Root cause: _build_sections_metadata parses the plain-text GitHub body "
                "and finds no <div><sub> wrappers, so parse_entries falls back to "
                "f'{added_date}T00:00:00Z'. Fix: preserve YAML entry IDs when enriching "
                "from GitHub, or write entry-block wrappers into the GitHub body."
            )
            assert got_id == real_id, (
                f"M1 (GitHub-enriched path): section={sec_name!r} entry id={got_id!r} "
                f"does not match the real persisted id={real_id!r}. "
                "The entry ID from the YAML structure must survive GitHub body enrichment."
            )


# ---------------------------------------------------------------------------
# M2 — Paginated YAML path: render_sections_as_body drops e.id
# ---------------------------------------------------------------------------


class TestMechanism2PaginatedYamlZeroId:
    """M2 regression: paginated YAML path overwrites entry IDs with zero timestamps.

    ``render_sections_as_body`` serialises entries as plain text (only
    ``e.content``, never ``e.id``).  When pagination is active
    (``limit > 0`` or ``offset > 0``), ``_assemble_view_content`` calls
    ``result.sections = _build_sections_metadata(result.body, ...)`` on the
    ID-stripped rendered body at lines 3288-3290, overwriting the correct
    ``result.sections`` produced by ``_build_sections_from_yaml_item``.

    The test isolates M2 by: (a) providing a local item with a real entry ID,
    (b) making GitHub enrichment unavailable (returns False) so only the YAML
    path runs, (c) passing limit=1 to activate the pagination branch.
    """

    def test_paginated_yaml_view_item_returns_real_entry_id_not_zero(self, mocker: MockerFixture) -> None:
        """view_item with pagination on a YAML item must return the real entry ID.

        Arrange: local BacklogItem with one entry whose id is a real now_iso()
        timestamp.  GitHub enrichment returns False (backend unreachable) so the
        YAML path is the sole source.

        Act: view_item(include_content=True, offset=1, limit=0) — pagination
        active (offset>0 sets paginate=True), no GitHub enrichment.

        Assert: every entry in result.sections carries the real persisted ID,
        not the zero-timestamp fallback from entry_blocks.py:158.

        RED (pre-fix): ``_populate_yaml_item_content`` first writes the correct
        ``result.sections`` via ``_build_sections_from_yaml_item``.  Then the
        pagination branch at line 3288-3290 calls
        ``result.sections = _build_sections_metadata(result.body, ...)`` on the
        ID-stripped body from ``render_sections_as_body``, overwriting the real
        IDs with ``"0000-00-00T00:00:00Z"``.
        """
        section_name = "Acceptance Criteria"
        item, real_id = _make_item_with_real_entry(section_name)

        # Patch the operations layer — GitHub backend is unreachable so only the
        # YAML path executes.  parse_issue_selector returns None to ensure
        # view_enrich_from_github is never called (no issue number to enrich from).
        mocker.patch("backlog_core.operations.parse_backlog", return_value=[item])
        mocker.patch("backlog_core.operations.find_item", return_value=item)
        # No GitHub issue number: view_item skips the enrichment branch entirely
        mocker.patch("backlog_core.operations.parse_issue_selector", return_value=None)

        # Act — offset=1 activates the pagination branch (paginate=True) while
        # keeping the section content in the returned body, isolating M2.
        # limit=1 would crop to one line and lose the section content entirely,
        # leaving result.sections empty and masking the zero-ID bug.  offset=1
        # skips the first line ("## Sections" index header) but retains the
        # "## Acceptance Criteria" section with its plain-text entry content.
        result = view_item(selector="Zero-ID regression item", include_content=True, offset=1, limit=0)

        # Assert — result.sections must be populated
        assert result.sections, (
            "M2 (paginated YAML): result.sections must not be empty. "
            "If empty, check that the BacklogItem has at least one entry and "
            "that render_sections_as_body produced a non-empty body."
        )

        entry_pairs = _collect_entry_ids(result)
        assert entry_pairs, (
            "M2 (paginated YAML): no entries found in result.sections. "
            "The section must contain the entry from the YAML BacklogItem. "
            "offset=1 skips the '## Sections' index line so the 'Acceptance Criteria' "
            "section and its entry remain in the paginated body."
        )

        for sec_name, got_id in entry_pairs:
            assert not got_id.startswith(_ZERO_ID_PREFIX), (
                f"M2 (paginated YAML path): section={sec_name!r} entry id={got_id!r} "
                f"is the zero-timestamp default from entry_blocks.py:158. "
                f"Expected real id={real_id!r}. "
                "Root cause: render_sections_as_body drops e.id (only e.content is emitted); "
                "the pagination branch at ops.py:3288-3290 then calls "
                "_build_sections_metadata(result.body, ...) on the ID-stripped body, "
                "overwriting the correct result.sections from _build_sections_from_yaml_item. "
                "Fix: either write entry-block wrappers in render_sections_as_body, or skip "
                "the _build_sections_metadata overwrite when result.sections is already correct."
            )
            assert got_id == real_id, (
                f"M2 (paginated YAML path): section={sec_name!r} entry id={got_id!r} "
                f"does not match the real persisted id={real_id!r}. "
                "The entry ID from the YAML structure must survive pagination."
            )


# ---------------------------------------------------------------------------
# Shared contract guard — zero ID is detectable
# ---------------------------------------------------------------------------


class TestZeroIdSentinelIsDetectable:
    """Sanity check: the zero-ID prefix we assert against is the actual fallback.

    This test verifies that ``_ZERO_ID_PREFIX`` matches the ``added_date``
    default in ``entry_blocks.py:158`` so the assertion in M1/M2 tests is
    not comparing against the wrong sentinel.
    """

    def test_zero_id_prefix_matches_entry_blocks_fallback(self) -> None:
        """The zero-timestamp ID produced by entry_blocks fallback starts with '0000-00-00'.

        Directly invoke ``parse_entries`` on a plain-text body that contains no
        entry-block wrappers and no leading ISO timestamp.  The resulting entry
        must have an ID starting with '0000-00-00' — the value this module uses
        as its detection sentinel.
        """
        from backlog_core.entry_blocks import parse_entries

        plain_content = "Some entry content with no timestamp wrapper."
        entries = parse_entries(plain_content, show="all", since=None)

        assert entries, "parse_entries must return at least one Entry for non-empty plain content."
        fallback_id = entries[0].id
        assert fallback_id.startswith(_ZERO_ID_PREFIX), (
            f"The fallback entry ID from parse_entries is {fallback_id!r}. "
            f"Expected it to start with {_ZERO_ID_PREFIX!r}. "
            "If this fails, the fallback format changed — update _ZERO_ID_PREFIX."
        )
