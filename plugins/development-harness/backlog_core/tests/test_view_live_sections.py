"""Regression tests for Failure 1: stale sections_index when GitHub is reachable.

Before the T1 fix, ``_assemble_view_content`` derived ``sections_index`` from
``item.sections`` (the provider-owned structured record) even when ``result.body`` was already
populated with live GitHub content.  This caused incoherent view responses
when concurrent groom agents wrote partial provider records and the live body on GitHub
was the only complete source of truth.

These four tests verify that ``view_item`` now prefers the live GitHub body
over the structured provider record when building ``sections_index``, and that the
stored-record path still works when live enrichment is unavailable.

Reference: GitHub issue #2452.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backlog_core.models import BacklogItem, Section
from backlog_core.operations import view_item

from ._view_test_helpers import _configure_memory_view

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

# ---------------------------------------------------------------------------
# Live body fixtures
# ---------------------------------------------------------------------------

# Three-section body used to simulate a live GitHub issue with more sections
# than the stored provider record.  MUST use ### (triple hash) headers so that
# _build_sections_compact detects them as section boundaries.
_LIVE_BODY_THREE_SECTIONS = """\
### Acceptance Criteria

No entry blocks — count 0, section still detected.

### Risk Summary

No entry blocks.

### Implementation Notes

No entry blocks.
"""

# Two-section body used for the concurrent-write race test.
# Both sections appear on GitHub even after the provider record was clobbered by
# the second write.
_LIVE_BODY_BOTH_SECTIONS = """\
### Section Alpha

Alpha content written by agent 1.

### Section Beta

Beta content written by agent 2.
"""


class TestViewItemSectionsCoherence:
    """Regression suite for Failure 1: stale sections_index when GitHub is reachable.

    The pre-fix bug: _assemble_view_content called _render_section_index(item),
    reading item.sections from the provider record unconditionally — even when
    result.body was already populated with live GitHub data.

    The fix: when result.body is populated, derive sections_index from the live
    body via _build_sections_index_from_body(body).  Fall back to the stored item
    when live enrichment is unavailable.
    """

    def test_view_returns_sections_from_live_body_when_enrichment_succeeds(self, mocker: MockerFixture) -> None:
        """sections_index reflects all live-body sections when enrichment succeeds.

        Arrange: local item has only one section (Acceptance Criteria).  Live
        GitHub body has three sections.  view_enrich_from_github sets result.body
        and returns True.

        Assert: sections_index contains all three live section headers — not just
        the one present in the structured provider record.  Without the T1 fix this test would fail
        because the pre-fix code read item.sections (1 section) rather than
        result.body (3 sections).
        """
        # Arrange — local item: one section only
        local_item = BacklogItem(title="Sections Coherence Item", sections={"Acceptance Criteria": Section()})
        _configure_memory_view(mocker, item=local_item, issue_num=2452, body=_LIVE_BODY_THREE_SECTIONS)

        # Act
        result = view_item("#2452", include_content=False)

        # Assert — sections_index non-empty (precondition for subsequent checks)
        assert result.sections_index, (
            "sections_index must be non-empty when view_enrich_from_github returns True. "
            "If empty, _build_sections_index_from_body did not run."
        )

        # Assert — all three live sections must appear in sections_index
        for header in ("Acceptance Criteria", "Risk Summary", "Implementation Notes"):
            assert header in result.sections_index, (
                f"'{header}' must appear in sections_index when derived from live body. "
                f"The local item only has 'Acceptance Criteria', so if this assertion "
                f"fails for 'Risk Summary' or 'Implementation Notes' the pre-fix path "
                f"(_render_section_index reading the provider record) is still active."
            )

    def test_view_returns_local_sections_when_backend_unreachable(self, mocker: MockerFixture) -> None:
        """sections_index falls back to the provider record and warns when enrichment is unavailable.

        When view_enrich_from_github returns False, result.body is not populated.
        view_item must fall back to item.sections from the provider and append a
        staleness warning.
        """
        # Arrange — local item: two sections available as offline fallback
        local_item = BacklogItem(
            title="Offline Fallback Item", sections={"Implementation Notes": Section(), "Risk Summary": Section()}
        )
        _configure_memory_view(mocker, item=local_item, issue_num=42, reachable=False)

        # Act
        result = view_item("#42", include_content=False)

        # Assert — sections_index non-empty (local fallback must activate)
        assert result.sections_index, (
            "sections_index must be non-empty when enrichment is unavailable; use the provider record."
        )

        # Assert — ADR-002 staleness warning present
        assert any("backend unreachable" in w for w in result.warnings), (
            "result.warnings must contain 'backend unreachable' when view_enrich_from_github "
            "returns False.  This satisfies ADR-002: callers must be able to detect that "
            "sections_index reflects the stored provider record, not live GitHub state."
        )

    def test_view_sections_index_matches_body_content(self, mocker: MockerFixture) -> None:
        """sections_index section names are consistent with the injected live body.

        Coherence check: every section name surfaced in sections_metadata must
        correspond to a ### header present in the live body we injected.  This
        verifies that sections_index is derived from the live body, not from an
        independent or stale source.

        Note: with include_content=False the result.body field is cleared after
        assembly (only sections_metadata and sections_index are populated).  The
        coherence assertion therefore compares sections_metadata names against the
        known injected live-body constant rather than result.body directly.
        """
        # Arrange — local item: one section (intentionally fewer than live body)
        local_item = BacklogItem(title="Body Coherence Item", sections={"Acceptance Criteria": Section()})
        _configure_memory_view(mocker, item=local_item, issue_num=2452, body=_LIVE_BODY_THREE_SECTIONS)

        # Act
        result = view_item("#2452", include_content=False)

        # Assert — sections_index non-empty (primary coherence gate)
        assert result.sections_index, "sections_index must be non-empty when live body is available."

        # Assert — each section name from sections_metadata appears in the live body
        # (include_content=False clears result.body after assembly; compare against
        # the known injected body constant to verify the index was derived from live data)
        for meta in result.sections_metadata:
            assert f"### {meta['name']}" in _LIVE_BODY_THREE_SECTIONS, (
                f"Section '{meta['name']}' appears in sections_metadata but not as a "
                f"### header in the injected live body.  The index must be derived "
                f"exclusively from live body content, not from the stored provider record."
            )

    def test_concurrent_writes_do_not_cause_stale_sections_index(self, mocker: MockerFixture) -> None:
        """sections_index reflects live body even when the provider record was clobbered by a race.

        Simulate the concurrent-write race: agent 1 writes Section Alpha; agent 2
        overwrites with Section Beta only (last-writer-wins clobber).  The live
        GitHub body still contains both sections.  After the T1 fix, sections_index
        must show both sections.

        Without the fix, sections_index would only contain Section Beta because
        _render_section_index reads the final provider record (clobbered by agent 2),
        silently dropping Section Alpha.
        """
        # Arrange — local item after race: only Section Beta survived
        clobbered_item = BacklogItem(title="Concurrent Write Item", sections={"Section Beta": Section()})
        _configure_memory_view(mocker, item=clobbered_item, issue_num=2452, body=_LIVE_BODY_BOTH_SECTIONS)

        # Act
        result = view_item("#2452", include_content=False)

        # Assert — sections_index non-empty
        assert result.sections_index, "sections_index must be non-empty when live body is available."

        # Assert — both sections visible; pre-fix: only Section Beta would appear
        assert "Section Alpha" in result.sections_index, (
            "Section Alpha must appear in sections_index even though the provider record "
            "was clobbered by agent 2.  The live body is the source of truth and must "
            "drive sections_index when view_enrich_from_github succeeds."
        )
        assert "Section Beta" in result.sections_index, (
            "Section Beta must appear in sections_index; this section survived in the "
            "provider record after the race, so both fix path and fallback path agree."
        )
