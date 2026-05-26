"""Regression tests for Failure 1 concurrent-write race scenario (cache coherence fix).

Failure 1 summary: when multiple groom agents write to the same backlog item in rapid
succession, the local YAML reflects only the last write. Before the T1 fix, view_item
used item.sections (local YAML cache) to build sections_index. This meant sections
written by earlier agents could be silently dropped from the index if a subsequent
groom agent clobbered the YAML file without re-including those sections.

Path A fix (T1): view_item now prefers result.body (live GitHub data) when available,
calling _build_sections_index_from_body() instead of _render_section_index(). The local
YAML is only used as a fallback when the backend is unreachable (ADR-002 offline contract).

Tests simulate the post-race state by constructing a BacklogItem whose sections reflect
only the clobbered state (agent 2's write), while mocking view_enrich_from_github to
inject the canonical live body with all sections. No filesystem writes are required.
Per architect §8.1: "True concurrency tests are impractical in a unit suite."

Reference: GitHub issue #2452.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backlog_core.models import BacklogItem, Section
from backlog_core.operations import view_item

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from backlog_core.models import ViewItemResult

# Live GitHub body injected by the mock to simulate a successful enrichment call.
# Contains BOTH sections that existed at the time of the concurrent writes.
# In the race scenario, the local BacklogItem only has the second agent's section, but
# GitHub retains the complete history -- both sections are present on GitHub.
_LIVE_BODY_BOTH_SECTIONS = """\
### Acceptance Criteria

Requirements groomed by agent 1.

### Risk Summary

Risks groomed by agent 2.
"""


class TestConcurrentGroomWriteRace:
    """Regression suite for Failure 1: stale local-cache reads under concurrent groom writes.

    The bug was: _assemble_view_content unconditionally called _render_section_index(item),
    which reads item.sections from the local YAML cache. When agent 2 overwrote the YAML
    with only its own sections, agent 1's sections disappeared from the view response --
    even though GitHub still had both sections in the canonical issue body.

    The fix: _assemble_view_content checks result.body first. When body is populated (live
    enrichment succeeded), it calls _build_sections_index_from_body(body) so the sections
    index reflects the live GitHub state, not the racing local cache.
    """

    def test_second_groom_write_does_not_clobber_first_sections_on_view(self, mocker: MockerFixture) -> None:
        """sections_index reflects live body even when local item was overwritten by a race.

        Agent 1 writes both Acceptance Criteria and Risk Summary. Agent 2 then overwrites
        the local state with only Risk Summary (simulating the clobber race). The live
        GitHub body still contains both sections. After the T1 fix, view_item must report
        both sections in sections_index -- derived from the live body, not the partial
        local cache.
        """
        # Arrange -- local item reflects agent 2's clobber: only Risk Summary
        race_clobbered_item = BacklogItem(title="Race Condition Item", sections={"Risk Summary": Section()})
        mocker.patch("backlog_core.operations.parse_backlog", return_value=[race_clobbered_item])
        mocker.patch("backlog_core.operations.find_item", return_value=race_clobbered_item)
        mocker.patch("backlog_core.operations.parse_issue_selector", return_value=42)

        # Arrange -- live GitHub body contains both sections (canonical truth)
        def _enrich_with_live_body(result: ViewItemResult, issue_num: str, repo: str = "") -> bool:
            result.body = _LIVE_BODY_BOTH_SECTIONS
            return True

        mocker.patch("backlog_core.operations.view_enrich_from_github", side_effect=_enrich_with_live_body)

        # Act
        result = view_item("#42", include_content=False)

        # Assert -- sections_index is non-empty (precondition for subsequent checks)
        assert result.sections_index, (
            "sections_index must be non-empty when live body is available. "
            "If empty, _build_sections_index_from_body did not run or body was not set."
        )

        # Assert -- live body drives the index; both sections must be visible
        assert "Acceptance Criteria" in result.sections_index, (
            "sections_index must include 'Acceptance Criteria' from the live GitHub body. "
            "The local item had only 'Risk Summary' (simulating agent 2's clobber), but "
            "the live body still contains both sections. The fix must prefer live data."
        )
        assert "Risk Summary" in result.sections_index, (
            "sections_index must include 'Risk Summary' from the live GitHub body."
        )

    def test_offline_fallback_emits_staleness_warning(self, mocker: MockerFixture) -> None:
        """view_item emits a staleness warning when the backend is unreachable.

        When view_enrich_from_github returns False (backend offline), the sections_index
        falls back to local item.sections. Per ADR-002, result.warnings must include the
        substring 'backend unreachable' to alert callers that the cached data may be stale.
        """
        # Arrange -- item with partial local sections
        local_item = BacklogItem(title="Offline Item", sections={"Implementation Notes": Section()})
        mocker.patch("backlog_core.operations.parse_backlog", return_value=[local_item])
        mocker.patch("backlog_core.operations.find_item", return_value=local_item)
        mocker.patch("backlog_core.operations.parse_issue_selector", return_value=42)
        mocker.patch("backlog_core.operations.view_enrich_from_github", return_value=False)

        # Act
        result = view_item("#42", include_content=False)

        # Assert -- ADR-002 staleness warning is present
        assert any("backend unreachable" in w for w in result.warnings), (
            "result.warnings must contain 'backend unreachable' when view_enrich_from_github "
            "returns False. This satisfies ADR-002: callers must be able to detect that "
            "sections_index reflects the local cache, not live GitHub state."
        )
