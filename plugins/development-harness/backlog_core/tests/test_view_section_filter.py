"""Regression tests for two related bugs in backlog_view section filtering.

Bug A: backlog_view(selector="...", summary=False, section="Concerns") returns
the full item body (100k+ characters) instead of only the Concerns section
content.  Root cause: _assemble_view_content only applies the ``section``
parameter in the ``elif item and item.sections:`` branch (YAML items with no
raw body).  When ``result.body`` is populated by view_enrich_from_github the
``if body:`` branch runs instead and ignores ``section`` entirely.

Bug B: When a GitHub-backed item body contains a ``## Heading`` (double-hash)
between two ``###`` sections, the section boundary detection in
_build_sections_metadata uses ``r"^### (.+?)$"`` — only triple-hash headers
are recognised as boundaries.  A double-hash heading between two sections is
therefore absorbed into the preceding section's ``sec_body``, and the content
field of a plain-text entry for that section includes the double-hash heading
that belongs to the next logical block.

Both tests MUST FAIL before the fix is applied and PASS after.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeGuard

from backlog_core.models import BacklogItem, Section
from backlog_core.operations import _build_sections_compact, view_item

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from backlog_core.models import GroomedSectionMetadata, SectionEntryDict, SectionEntryMetadata, ViewItemResult


def _is_section_entry_metadata(
    section: SectionEntryMetadata | GroomedSectionMetadata,
) -> TypeGuard[SectionEntryMetadata]:
    """Narrow a section union to SectionEntryMetadata by presence of the 'entries' key.

    SectionEntryMetadata is discriminated from GroomedSectionMetadata by the 'entries'
    key (entry-block sections have timestamped entries; groomed sections do not).
    This TypeGuard lets ty narrow the union after an assertion or conditional check.
    """
    return "entries" in section


# ---------------------------------------------------------------------------
# Test body fixtures
# ---------------------------------------------------------------------------

# Bug A fixture: a multi-section body with a large Concerns section followed by
# an Impact Radius section.  After the fix, requesting section="Concerns" must
# return ONLY the Concerns section — not the full body.
_MULTI_SECTION_BODY_BUG_A = """\
### Concerns

There is a race condition when two agents write to the same cache key
simultaneously.  The write-back lock is per-process, not per-agent, so
concurrent agents in the same process can interleave their writes.

This is a critical risk for the dispatch orchestrator which spawns N agents
that all update the task state file.

### Impact Radius

Affects: dispatch orchestrator, task-worker, all agents that write task state.

Risk level: high.
"""

# Bug B fixture: a body where a ``## Heading`` (double-hash) appears BETWEEN
# two ``###`` sections.  _build_sections_metadata only splits on ``###``, so
# the double-hash heading is absorbed into the Concerns section's sec_body.
# When parse_entries finds no entry blocks it returns sec_body.strip() as the
# single entry's content — which therefore contains the double-hash heading.
_MULTI_SECTION_BODY_BUG_B = """\
### Concerns

Race condition X exists between writer agents.

## Impact Radius

Affects modules A and B.

### Plan

Step 1: add distributed lock.
Step 2: add integration test.
"""


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_local_item(title: str = "Test Item") -> BacklogItem:
    """Return a minimal BacklogItem with one section for local cache.

    The local item is intentionally different from the GitHub body so tests can
    distinguish which source drove the result.
    """
    return BacklogItem(title=title, sections={"Acceptance Criteria": Section()})


# ---------------------------------------------------------------------------
# Bug A: section filter is ignored when result.body is populated from GitHub
# ---------------------------------------------------------------------------


class TestViewItemSectionFilterAppliesToGithubBody:
    """Bug A regression suite.

    Before the fix, _assemble_view_content ignores the ``section`` parameter
    when ``result.body`` is already set by view_enrich_from_github.  The full
    body is returned regardless of what section the caller requested.
    """

    def test_section_filter_returns_only_requested_section(self, mocker: MockerFixture) -> None:
        """Requesting section='Concerns' returns only the Concerns section content.

        Arrange: view_enrich_from_github injects a multi-section body.
        Act: call view_item with section='Concerns'.
        Assert: result.sections contains only 'Concerns'; 'Impact Radius' is absent.

        This test FAILS before the fix because _assemble_view_content drops
        the ``section`` parameter when ``body`` is populated, populating
        result.sections with ALL sections instead of the one requested.
        """
        # Arrange
        local_item = _make_local_item()
        mocker.patch("backlog_core.operations.parse_backlog", return_value=[local_item])
        mocker.patch("backlog_core.operations.find_item", return_value=local_item)
        mocker.patch("backlog_core.operations.parse_issue_selector", return_value=99)

        def _inject_body(result: ViewItemResult, issue_num: str, repo: str = "") -> bool:
            result.body = _MULTI_SECTION_BODY_BUG_A
            return True

        mocker.patch("backlog_core.operations.view_enrich_from_github", side_effect=_inject_body)

        # Act
        result = view_item("#99", include_content=True, section="Concerns")

        # Assert — only the requested section may appear
        assert "Concerns" in result.sections, (
            "result.sections must contain 'Concerns' when section='Concerns' is requested. "
            "If this fails, the section filter was not applied at all."
        )
        assert "Impact Radius" not in result.sections, (
            "'Impact Radius' must NOT appear in result.sections when section='Concerns' "
            "is requested.  If this fails, the section filter was silently dropped and the "
            "full body was returned instead of the filtered view.  This is Bug A."
        )

    def test_section_filter_does_not_include_full_body_from_github(self, mocker: MockerFixture) -> None:
        """result.body after section filter must not contain the next section's header.

        When section='Concerns' is requested the body returned must not include
        '### Impact Radius' — text that belongs to a different section.

        This test FAILS before the fix because the full injected body (including
        all sections) is returned when the ``section`` parameter is ignored.
        """
        # Arrange
        local_item = _make_local_item()
        mocker.patch("backlog_core.operations.parse_backlog", return_value=[local_item])
        mocker.patch("backlog_core.operations.find_item", return_value=local_item)
        mocker.patch("backlog_core.operations.parse_issue_selector", return_value=99)

        def _inject_body(result: ViewItemResult, issue_num: str, repo: str = "") -> bool:
            result.body = _MULTI_SECTION_BODY_BUG_A
            return True

        mocker.patch("backlog_core.operations.view_enrich_from_github", side_effect=_inject_body)

        # Act
        result = view_item("#99", include_content=True, section="Concerns")

        # Assert — the body must not contain the Impact Radius section header
        assert "### Impact Radius" not in result.body, (
            "result.body must not contain '### Impact Radius' when section='Concerns' "
            "is requested.  The section filter was dropped (Bug A): the full multi-section "
            "body was returned instead of the filtered Concerns content only."
        )


# ---------------------------------------------------------------------------
# Bug B: section entry content includes the following ## heading
# ---------------------------------------------------------------------------


class TestSectionEntryDoesNotIncludeNextSectionHeader:
    """Bug B regression suite.

    _build_sections_metadata uses r"^### (.+?)$" to detect section boundaries.
    A ``## Heading`` (double-hash) that appears between two ``###`` sections is
    NOT a boundary — it is absorbed into the preceding section's sec_body.
    When parse_entries finds no entry blocks it returns sec_body.strip() as the
    single plain-text entry, and that entry's content includes the double-hash
    heading that logically belongs to the next block.
    """

    def test_concerns_entry_content_does_not_include_impact_radius_heading(self, mocker: MockerFixture) -> None:
        """Entry content for Concerns must not include '## Impact Radius'.

        Arrange: body contains '### Concerns', then '## Impact Radius', then
        '### Plan'.  The section boundaries are the two ### headers.  The
        '## Impact Radius' text falls inside the Concerns sec_body because it
        uses double-hash, which the section regex does not match.

        Assert: result.sections['Concerns']['entries'][0]['content'] does not
        contain '## Impact Radius'.

        This test FAILS before the fix because sec_body for Concerns spans from
        the end of '### Concerns' to the start of '### Plan', absorbing the
        '## Impact Radius' heading, and parse_entries returns it as part of the
        entry content (no entry blocks present — falls back to sec_body.strip()).
        """
        # Arrange — no local item; test via raw body injection only
        mocker.patch("backlog_core.operations.parse_backlog", return_value=[])
        mocker.patch("backlog_core.operations.find_item", return_value=None)
        mocker.patch("backlog_core.operations.parse_issue_selector", return_value=100)

        def _inject_body(result: ViewItemResult, issue_num: str, repo: str = "") -> bool:
            result.body = _MULTI_SECTION_BODY_BUG_B
            return True

        mocker.patch("backlog_core.operations.view_enrich_from_github", side_effect=_inject_body)

        # Act
        result = view_item("#100", include_content=True)

        # Assert — Concerns section must be present
        assert "Concerns" in result.sections, (
            "result.sections must contain 'Concerns' when the body has a '### Concerns' "
            "header.  If absent, section parsing failed entirely."
        )

        concerns: SectionEntryMetadata | GroomedSectionMetadata = result.sections["Concerns"]
        assert _is_section_entry_metadata(concerns), (
            "Concerns section must be a SectionEntryMetadata (entry-block) not a GroomedSectionMetadata"
        )
        assert concerns["entries"], (
            "Concerns section must have at least one entry.  The body contains plain "
            "text under '### Concerns' so parse_entries must produce one entry."
        )

        first_entry: SectionEntryDict = concerns["entries"][0]
        assert "## Impact Radius" not in first_entry["content"], (
            "The content of the first Concerns entry must not include '## Impact Radius'. "
            "The double-hash heading is a section separator that belongs to a separate "
            "logical block, not to the Concerns entry text.  If this assertion fails, "
            "Bug B is present: _build_sections_metadata absorbed '## Impact Radius' into "
            "the Concerns sec_body because its section boundary regex only matches ### "
            "headers, not ## headers."
        )

    def test_plan_entry_content_does_not_include_impact_radius_heading(self, mocker: MockerFixture) -> None:
        """Entry content for Plan must contain only Plan content, not Impact Radius text.

        Complementary to the Concerns test: verifies that the Plan section is
        correctly parsed after the ## Impact Radius heading.  This confirms the
        bug is localised to the preceding section's sec_body, not the next one.

        This test PASSES both before and after the fix (Plan's sec_body runs from
        '### Plan' to end-of-body so no contamination occurs in that direction).
        It is included as a non-regression anchor: it must stay green.
        """
        # Arrange
        mocker.patch("backlog_core.operations.parse_backlog", return_value=[])
        mocker.patch("backlog_core.operations.find_item", return_value=None)
        mocker.patch("backlog_core.operations.parse_issue_selector", return_value=101)

        def _inject_body(result: ViewItemResult, issue_num: str, repo: str = "") -> bool:
            result.body = _MULTI_SECTION_BODY_BUG_B
            return True

        mocker.patch("backlog_core.operations.view_enrich_from_github", side_effect=_inject_body)

        # Act
        result = view_item("#101", include_content=True)

        # Assert — Plan section must be present and clean
        assert "Plan" in result.sections, "result.sections must contain 'Plan' when the body has a '### Plan' header."

        plan: SectionEntryMetadata | GroomedSectionMetadata = result.sections["Plan"]
        assert _is_section_entry_metadata(plan), (
            "Plan section must be a SectionEntryMetadata (entry-block) not a GroomedSectionMetadata"
        )
        assert plan["entries"], "Plan section must have at least one entry."

        plan_content = plan["entries"][0]["content"]
        assert "## Impact Radius" not in plan_content, (
            "Plan entry content must not include '## Impact Radius' text.  The Plan "
            "section starts after the Impact Radius block so it should not be present."
        )
        assert "Step 1" in plan_content, (
            "Plan entry content must contain 'Step 1' from the fixture.  If absent, "
            "the Plan section was parsed incorrectly."
        )


# ---------------------------------------------------------------------------
# Finding 1: _build_sections_compact must use _SECTION_BOUNDARY_RE (#{2,3})
# ---------------------------------------------------------------------------

# Body containing a mix of ## and ### section headers — as occurs in real issue
# bodies where top-level sections use ## and subsections use ###.
_MIXED_HEADER_BODY = """\
### Concerns

Race condition X exists between writer agents.

## Impact Radius

Affects modules A and B.

### Plan

Step 1: add distributed lock.
Step 2: add integration test.
"""


class TestBuildSectionsCompactUsesSectionBoundaryRe:
    """Finding 1: _build_sections_compact must recognise both ## and ### headers.

    Before the fix, _build_sections_compact used an inline ``r"^### (.+?)$"``
    regex, while _build_sections_metadata used the module-level
    ``_SECTION_BOUNDARY_RE = re.compile(r"^#{2,3} (.+?)$")``.  This caused
    compact-mode (include_content=False) and content-mode (include_content=True)
    to disagree on section boundaries for the same body.
    """

    def test_build_sections_compact_detects_double_hash_boundary(self) -> None:
        """_build_sections_compact returns three sections for a mixed ## / ### body.

        Arrange: body with ``### Concerns``, ``## Impact Radius``, ``### Plan``.
        Act: call _build_sections_compact directly.
        Assert: result contains exactly three sections — Concerns, Impact Radius,
        and Plan — proving the double-hash header is recognised as a boundary.

        Before the fix: returns 2 sections (Concerns, Plan), because the inline
        ``r"^### (.+?)$"`` regex skips the ``## Impact Radius`` header.
        """
        # Arrange / Act
        sections = _build_sections_compact(_MIXED_HEADER_BODY)
        names = [str(s.get("name", "")) for s in sections]

        # Assert
        assert len(sections) == 3, (
            f"Expected 3 sections (Concerns, Impact Radius, Plan), got {len(sections)}: {names}. "
            "Before the fix, only 2 sections are returned because the inline ### regex "
            "does not match the ## Impact Radius header."
        )
        assert "Concerns" in names, "'Concerns' section must be present."
        assert "Impact Radius" in names, (
            "'Impact Radius' section must be present.  If absent, the double-hash "
            "header was not recognised as a boundary (Finding 1 not fixed)."
        )
        assert "Plan" in names, "'Plan' section must be present."

    def test_build_sections_compact_agrees_with_build_sections_metadata(self) -> None:
        """Section count from _build_sections_compact matches _build_sections_metadata.

        Verifies that both functions use the same boundary rule so compact-mode
        and content-mode produce a consistent section inventory.
        """
        from backlog_core.operations import _build_sections_metadata

        compact_names = {str(s.get("name", "")) for s in _build_sections_compact(_MIXED_HEADER_BODY)}
        metadata_names = set(_build_sections_metadata(_MIXED_HEADER_BODY, show=None, since=None).keys())

        assert compact_names == metadata_names, (
            f"compact names {compact_names!r} differ from metadata names {metadata_names!r}. "
            "Both functions must agree on section boundaries."
        )


# ---------------------------------------------------------------------------
# Finding 2: _assemble_view_compact must respect the section parameter
# ---------------------------------------------------------------------------


class TestAssembleViewCompactSectionFilter:
    """Finding 2: compact view (include_content=False) must honour section filter.

    Before the fix, _assemble_view_compact lacked a ``section`` parameter.
    A caller passing ``section='Concerns'`` with ``include_content=False``
    received sections_metadata for ALL sections, not just 'Concerns'.
    """

    def test_compact_view_returns_only_requested_section_metadata(self, mocker: MockerFixture) -> None:
        """sections_metadata contains exactly the requested section when filtered.

        Arrange: view_enrich_from_github injects a multi-section body.
        Act: call view_item with include_content=False, section='Concerns'.
        Assert: sections_metadata has exactly one entry named 'Concerns'.

        Before the fix: sections_metadata lists all sections regardless of
        the section parameter because _assemble_view_compact ignores it.
        """
        # Arrange
        local_item = _make_local_item()
        mocker.patch("backlog_core.operations.parse_backlog", return_value=[local_item])
        mocker.patch("backlog_core.operations.find_item", return_value=local_item)
        mocker.patch("backlog_core.operations.parse_issue_selector", return_value=200)

        def _inject_body(result: ViewItemResult, issue_num: str, repo: str = "") -> bool:
            result.body = _MULTI_SECTION_BODY_BUG_A
            return True

        mocker.patch("backlog_core.operations.view_enrich_from_github", side_effect=_inject_body)

        # Act
        result = view_item("#200", include_content=False, section="Concerns")

        # Assert — only one entry in sections_metadata
        assert len(result.sections_metadata) == 1, (
            f"sections_metadata must contain exactly 1 entry when section='Concerns' "
            f"is requested.  Got {len(result.sections_metadata)}: "
            f"{[m['name'] for m in result.sections_metadata]}.  "
            "Before the fix, all sections are returned because the section parameter is ignored."
        )
        assert result.sections_metadata[0]["name"] == "Concerns", (
            "The single sections_metadata entry must be named 'Concerns'."
        )

    def test_compact_view_omits_sections_index_when_section_filter_active(self, mocker: MockerFixture) -> None:
        """sections_index is empty when a section filter is active in compact mode.

        When section is specified, the index covers only one section and would be
        misleading to callers who want a full section inventory.  Omitting it is
        consistent with the include_content=True path which also omits the index
        when section is set.
        """
        # Arrange
        local_item = _make_local_item()
        mocker.patch("backlog_core.operations.parse_backlog", return_value=[local_item])
        mocker.patch("backlog_core.operations.find_item", return_value=local_item)
        mocker.patch("backlog_core.operations.parse_issue_selector", return_value=201)

        def _inject_body(result: ViewItemResult, issue_num: str, repo: str = "") -> bool:
            result.body = _MULTI_SECTION_BODY_BUG_A
            return True

        mocker.patch("backlog_core.operations.view_enrich_from_github", side_effect=_inject_body)

        # Act
        result = view_item("#201", include_content=False, section="Concerns")

        # Assert — sections_index should not be populated when section filter is active
        assert not result.sections_index, (
            "sections_index must be empty when section='Concerns' is active in compact mode. "
            "A partial index for a single section is misleading — omitting it mirrors the "
            "include_content=True path behaviour."
        )

    def test_compact_view_returns_all_sections_when_no_filter(self, mocker: MockerFixture) -> None:
        """sections_metadata contains all sections when no section filter is applied.

        Non-regression: the default compact-mode path (section=None) must not be
        broken by the new section parameter.
        """
        # Arrange
        local_item = _make_local_item()
        mocker.patch("backlog_core.operations.parse_backlog", return_value=[local_item])
        mocker.patch("backlog_core.operations.find_item", return_value=local_item)
        mocker.patch("backlog_core.operations.parse_issue_selector", return_value=202)

        def _inject_body(result: ViewItemResult, issue_num: str, repo: str = "") -> bool:
            result.body = _MULTI_SECTION_BODY_BUG_A
            return True

        mocker.patch("backlog_core.operations.view_enrich_from_github", side_effect=_inject_body)

        # Act
        result = view_item("#202", include_content=False)

        # Assert — both sections from the fixture appear
        names = [m["name"] for m in result.sections_metadata]
        assert "Concerns" in names, "'Concerns' must appear in sections_metadata when no filter is active."
        assert "Impact Radius" in names, "'Impact Radius' must appear in sections_metadata when no filter is active."
        assert result.sections_index, "sections_index must be populated when no section filter is active."
