"""RED regression tests for blank/whitespace section normalization.

Bug: When a caller passes ``section=""`` or ``section="   "`` (blank/whitespace
only), ``_resolve_section_indices`` strips the value to ``""`` and then executes
the substring fallback.  Because ``"" in name.lower()`` is ``True`` for every
string, all candidates are returned as matched — the blank filter matches
everything instead of nothing.

Callers downstream check ``section is not None`` but never check
``section.strip()``, so a blank string is treated as an explicit, successful
filter hit.  This suppresses the section-index path, silently returns the full
body/sections as if a real section filter had been applied, and never sets
``section_filter_miss``.

The fix normalises blank/whitespace-only ``section`` values to ``None`` at the
``view_item`` boundary — before any filter logic runs — so the behaviour is
identical to omitting ``section`` entirely.

Test naming: every test contains ``blank_section`` so
``pytest -k blank_section`` selects the entire suite.

Two groups of tests:

1. ``TestResolveBlankSectionReturnsNoIndices`` — direct unit tests for
   ``_resolve_section_indices``: a blank or whitespace-only filter against a
   non-empty candidate list must return an empty list, NOT all indices.

2. ``TestViewItemBlankSectionBehavesLikeNone`` — integration tests via
   ``view_item``: passing ``section=""`` or ``section="   "`` must produce the
   same result as passing ``section=None`` (section-index path, no
   ``section_filter_miss``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from backlog_core.models import BacklogItem, Section
from backlog_core.operations import _resolve_section_indices, view_item

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from backlog_core.models import ViewItemResult

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_CANDIDATES: list[str] = ["Acceptance Criteria", "Concerns", "Impact Radius", "Plan"]

_MULTI_SECTION_BODY = """\
### Acceptance Criteria

- Must not regress blank filter behaviour.

### Concerns

There is a race condition when two agents write.

### Impact Radius

Affects dispatch orchestrator.

### Plan

Step 1: normalise blank section to None.
"""


def _make_local_item(title: str = "Blank Section Test Item") -> BacklogItem:
    """Return a minimal BacklogItem with multiple sections for testing."""
    return BacklogItem(
        title=title,
        sections={
            "Acceptance Criteria": Section(),
            "Concerns": Section(),
            "Impact Radius": Section(),
            "Plan": Section(),
        },
    )


# ---------------------------------------------------------------------------
# Group 1: unit tests on _resolve_section_indices
# ---------------------------------------------------------------------------


class TestResolveBlankSectionReturnsNoIndices:
    """``_resolve_section_indices`` with a blank or whitespace-only filter.

    A blank filter is not a real filter expression — it is an omitted/empty
    input from the caller.  The resolver must return an empty list (no match),
    NOT all indices.

    These tests are RED before the fix because ``"" in name.lower()`` is True
    for every candidate string, so the current code returns all indices.
    """

    def test_blank_section_returns_no_indices_for_non_empty_candidates(self) -> None:
        """``_resolve_section_indices(candidates, "")`` returns [] not all indices.

        Arrange: four candidate names.
        Act: call with section="".
        Assert: returns [] — a blank filter matches nothing, not everything.

        RED: current code returns [0, 1, 2, 3] because "" is in every string.
        """
        result = _resolve_section_indices(_CANDIDATES, "")

        assert result == [], (
            f"_resolve_section_indices with section='' must return [] "
            f"(no match, not all-match).  Got {result!r}.  "
            "A blank filter should match nothing — the current code returns all "
            "indices because '' is a substring of every string."
        )

    @pytest.mark.parametrize("blank", ["   ", "\t", "\n", "  \t  "])
    def test_whitespace_only_section_returns_no_indices(self, blank: str) -> None:
        """``_resolve_section_indices(candidates, whitespace)`` returns [].

        Parameterised over common whitespace-only inputs that may arrive from
        MCP/form clients sending blank field values.

        RED: current code strips to '' then returns all indices.
        """
        result = _resolve_section_indices(_CANDIDATES, blank)

        assert result == [], (
            f"_resolve_section_indices with section={blank!r} must return [] "
            f"(whitespace-only is treated as omitted filter).  Got {result!r}."
        )

    def test_blank_section_with_empty_candidates_still_returns_empty(self) -> None:
        """``_resolve_section_indices([], "")`` returns [] regardless of the fix.

        Non-regression: the early-exit for empty candidates must remain correct.
        This test is GREEN before and after the fix — included as a guard.
        """
        result = _resolve_section_indices([], "")
        assert result == [], "Empty candidates with blank section must return []."


# ---------------------------------------------------------------------------
# Group 2: integration tests via view_item
# ---------------------------------------------------------------------------


class TestViewItemBlankSectionBehavesLikeNone:
    """``view_item`` with ``section=""`` or ``section="   "`` must behave like
    ``section=None``.

    A blank section from an MCP/form client must not:
    - Return all sections as if a real filter hit occurred.
    - Suppress the section-index path.
    - Set ``section_filter_miss=False`` while having matched everything.

    It must:
    - Return the same result as omitting ``section`` entirely.
    - Populate ``sections_index`` as the no-filter path does.
    - Not report ``section_filter_miss=True`` (no filter means no miss).

    These tests are RED before the fix because the blank filter returns all
    candidates, suppressing the section-index path and diverging from the
    ``section=None`` path.
    """

    def _setup_github_mock(self, mocker: MockerFixture, issue_num: int) -> BacklogItem:
        """Patch parse_backlog, find_item, parse_issue_selector, and view_enrich."""
        local_item = _make_local_item()
        mocker.patch("backlog_core.operations.parse_backlog", return_value=[local_item])
        mocker.patch("backlog_core.operations.find_item", return_value=local_item)
        mocker.patch("backlog_core.operations.parse_issue_selector", return_value=issue_num)

        def _inject_body(result: ViewItemResult, inum: str, repo: str = "") -> bool:
            result.body = _MULTI_SECTION_BODY
            return True

        mocker.patch("backlog_core.operations.view_enrich_from_github", side_effect=_inject_body)
        return local_item

    def test_blank_section_does_not_suppress_sections_index(self, mocker: MockerFixture) -> None:
        """``view_item`` with ``section=""`` populates ``sections_index`` as if no filter.

        When no section filter is active, ``view_item`` builds a section index
        listing all sections.  A blank section must not suppress this index.

        RED: the blank filter returns all candidates, the code treats this as a
        successful filter hit, and suppresses the section-index block.
        """
        self._setup_github_mock(mocker, 300)

        result_blank = view_item("#300", include_content=True, section="")
        result_none = view_item("#300", include_content=True, section=None)

        assert result_blank.sections_index == result_none.sections_index, (
            "sections_index for section='' must equal sections_index for section=None. "
            f"Got section='': {result_blank.sections_index!r}, "
            f"section=None: {result_none.sections_index!r}.  "
            "A blank filter must not suppress the section-index path."
        )

    def test_whitespace_section_does_not_suppress_sections_index(self, mocker: MockerFixture) -> None:
        """``view_item`` with ``section="   "`` populates ``sections_index`` as if no filter."""
        self._setup_github_mock(mocker, 301)

        result_ws = view_item("#301", include_content=True, section="   ")
        result_none = view_item("#301", include_content=True, section=None)

        assert result_ws.sections_index == result_none.sections_index, (
            "sections_index for section='   ' must equal sections_index for section=None. "
            f"Got section='   ': {result_ws.sections_index!r}, "
            f"section=None: {result_none.sections_index!r}.  "
            "A whitespace-only filter must not suppress the section-index path."
        )

    def test_blank_section_does_not_set_section_filter_miss_false_while_matching_all(
        self, mocker: MockerFixture
    ) -> None:
        """``view_item`` with ``section=""`` does not falsely report a successful filter.

        The bug: blank filter returns all sections as matched, section_filter_miss
        stays False (appearing to be a successful filter), but no real filtering
        occurred.  After the fix, section_filter_miss must remain False AND the
        result must match the no-filter path.

        RED: blank filter matches all candidates — the sections dict is populated
        with all sections as if the filter selected them.  Callers cannot
        distinguish this from a real filter result.
        """
        self._setup_github_mock(mocker, 302)

        result_blank = view_item("#302", include_content=True, section="")
        result_none = view_item("#302", include_content=True, section=None)

        # The blank result must not be a section-filtered subset — it must be
        # identical to no filter.  Checking section count and section_filter_miss.
        assert not result_blank.section_filter_miss, (
            "section_filter_miss must be False for section='' (treated as no filter)."
        )

        blank_section_keys = set(result_blank.sections.keys()) if result_blank.sections else set()
        none_section_keys = set(result_none.sections.keys()) if result_none.sections else set()

        assert blank_section_keys == none_section_keys, (
            f"Sections returned for section='' must equal sections for section=None. "
            f"Got blank: {blank_section_keys!r}, none: {none_section_keys!r}.  "
            "A blank filter must not restrict the section set — it is not a filter."
        )

    def test_blank_section_compact_mode_behaves_like_none(self, mocker: MockerFixture) -> None:
        """``view_item`` with ``section=""`` and ``include_content=False`` matches ``section=None``.

        Compact mode (include_content=False) uses a separate path for section
        metadata.  Blank normalization must apply to both paths.
        """
        self._setup_github_mock(mocker, 303)

        result_blank = view_item("#303", include_content=False, section="")
        result_none = view_item("#303", include_content=False, section=None)

        blank_names = [m["name"] for m in result_blank.sections_metadata]
        none_names = [m["name"] for m in result_none.sections_metadata]

        assert blank_names == none_names, (
            f"sections_metadata names for section='' must equal section=None. "
            f"Got blank: {blank_names!r}, none: {none_names!r}.  "
            "Blank normalization must apply in compact mode (include_content=False)."
        )
