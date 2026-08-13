"""RED tests for ViewItemResult.section_filter_miss feature.

These tests MUST FAIL before implementation and PASS after.

Feature: Add ``section_filter_miss: bool = False`` to ``ViewItemResult``.
When ``_apply_body_section_filter`` finds no matching section header for the
requested ``section=`` parameter it sets ``result.section_filter_miss = True``
and leaves ``result.body`` unchanged.  The flag is exposed in all three
``backlog_view`` response shapes (full, compact/summary, and over-budget).

Test coverage:
    1. ``_apply_body_section_filter`` sets flag when section NOT found.
    2. ``_apply_body_section_filter`` does NOT set flag when section IS found.
    3. ``view_item`` full response includes ``section_filter_miss: True``
       when section header is absent.
    4. ``view_item`` compact response (include_content=False) includes
       ``section_filter_miss: True`` when section header is absent.
    5. ``_build_compact_manifest`` (summary shape) includes
       ``section_filter_miss: True`` from a result that already has the flag set.
    6. ``_build_over_budget_view`` (over-budget shape) includes
       ``section_filter_miss: True`` from a result that already has the flag set.

All six test functions contain ``section_filter_miss`` in their names so
``pytest -k section_filter_miss`` selects the entire suite.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backlog_core.models import BacklogItem, Section, ViewItemResult
from backlog_core.operations import _apply_body_section_filter, view_item

from ._view_test_helpers import _configure_memory_view

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_BODY_WITH_CONCERNS = """\
### Concerns

There is a race condition when two agents write simultaneously.

### Impact Radius

Affects the dispatch orchestrator.
"""

_BODY_NO_NONEXISTENT = _BODY_WITH_CONCERNS  # "NonExistent" is not in this body


def _make_local_item(title: str = "Test Item") -> BacklogItem:
    """Return a minimal BacklogItem with one section."""
    return BacklogItem(title=title, sections={"Acceptance Criteria": Section()})


# ---------------------------------------------------------------------------
# Tests 1 & 2: _apply_body_section_filter flag setting
# ---------------------------------------------------------------------------


class TestApplyBodySectionFilterSectionFilterMiss:
    """Unit tests for the section_filter_miss flag on _apply_body_section_filter.

    These tests exercise the function directly without server or MCP machinery.
    """

    def test_section_filter_miss_set_true_when_section_header_not_found(self) -> None:
        """_apply_body_section_filter sets section_filter_miss=True when header absent.

        Arrange: body with '### Concerns' and '### Impact Radius'; section='NonExistent'.
        Act: call _apply_body_section_filter.
        Assert: result.section_filter_miss is True AND body is left unchanged.

        RED: fails because ViewItemResult has no section_filter_miss field.
        """
        # Arrange
        result = ViewItemResult()
        original_body = _BODY_NO_NONEXISTENT

        # Act
        returned_body = _apply_body_section_filter(result, original_body, "NonExistent")

        # Assert — flag must be set
        assert result.section_filter_miss is True, (
            "result.section_filter_miss must be True when the requested section header "
            "is not found in the body.  If this fails with AttributeError, "
            "section_filter_miss has not been added to ViewItemResult."
        )
        # Assert — body must be left unchanged (silent-drop prevention)
        assert returned_body == original_body, (
            "When no section header matches, _apply_body_section_filter must return "
            "the original body unchanged.  Returning a different value would silently "
            "discard content."
        )
        assert result.body == original_body, (
            "result.body must be the original body when no section header matches.  "
            "Overwriting with empty string or a slice would lose content silently."
        )

    def test_section_filter_miss_not_set_when_section_header_found(self) -> None:
        """_apply_body_section_filter does NOT set section_filter_miss when header found.

        Arrange: body with '### Concerns'; section='Concerns'.
        Act: call _apply_body_section_filter.
        Assert: result.section_filter_miss is False (default) — not set to True.

        RED: fails because ViewItemResult has no section_filter_miss field.
        """
        # Arrange
        result = ViewItemResult()

        # Act
        _apply_body_section_filter(result, _BODY_WITH_CONCERNS, "Concerns")

        # Assert — flag must stay False when section IS found
        assert result.section_filter_miss is False, (
            "result.section_filter_miss must remain False when the requested section "
            "header IS found.  Setting the flag unconditionally would break callers "
            "that rely on False as the 'all good' signal."
        )
        # Sanity: body was narrowed to Concerns section
        assert "Concerns" in result.body, "result.body must contain 'Concerns' after a successful section filter."
        assert "Impact Radius" not in result.body, (
            "result.body must not contain 'Impact Radius' after section='Concerns' filter."
        )


# ---------------------------------------------------------------------------
# Tests 3 & 4: view_item surfaces section_filter_miss in full and compact shapes
# ---------------------------------------------------------------------------


class TestViewItemSectionFilterMissExposedInResponse:
    """Integration tests: view_item response carries section_filter_miss.

    Tests 3 and 4 exercise the view_item function with mocked GitHub enrichment
    so we can inject a controlled body without network calls.
    """

    def test_section_filter_miss_true_in_full_view_when_section_not_found(self, mocker: MockerFixture) -> None:
        """view_item full response has section_filter_miss=True when section absent.

        Arrange: GitHub enrichment injects a small body (well under token budget);
                 section='NonExistent' is not present in that body.
        Act: call view_item with include_content=True, section='NonExistent'.
        Assert: result.section_filter_miss is True.

        RED: fails because ViewItemResult has no section_filter_miss field.
        """
        # Arrange
        local_item = _make_local_item()
        _configure_memory_view(mocker, item=local_item, issue_num=300, body=_BODY_NO_NONEXISTENT)

        # Act
        result = view_item("#300", include_content=True, section="NonExistent")

        # Assert
        assert result.section_filter_miss is True, (
            "result.section_filter_miss must be True when the requested section is "
            "absent from the body.  If this fails with AttributeError, "
            "section_filter_miss has not been added to ViewItemResult."
        )

    def test_section_filter_miss_false_in_full_view_when_section_found(self, mocker: MockerFixture) -> None:
        """view_item full response has section_filter_miss=False when section present.

        Non-regression: the happy path must not set the miss flag.

        Arrange: same setup but section='Concerns' which IS present.
        Assert: result.section_filter_miss is False.
        """
        # Arrange
        local_item = _make_local_item()
        _configure_memory_view(mocker, item=local_item, issue_num=301, body=_BODY_WITH_CONCERNS)

        # Act
        result = view_item("#301", include_content=True, section="Concerns")

        # Assert
        assert result.section_filter_miss is False, (
            "result.section_filter_miss must be False when the requested section IS "
            "found.  If True, the flag is set unconditionally — breaking the contract."
        )

    def test_section_filter_miss_true_in_compact_view_when_section_not_found(self, mocker: MockerFixture) -> None:
        """view_item compact response has section_filter_miss=True when section absent.

        Arrange: same body injection but include_content=False (compact/summary mode).
        Act: call view_item with include_content=False, section='NonExistent'.
        Assert: result.section_filter_miss is True.

        RED: fails because ViewItemResult has no section_filter_miss field.
        The compact path (_assemble_view_compact) must also set the flag through
        the same _apply_body_section_filter code path, or detect the miss independently.
        """
        # Arrange
        local_item = _make_local_item()
        _configure_memory_view(mocker, item=local_item, issue_num=302, body=_BODY_NO_NONEXISTENT)

        # Act
        result = view_item("#302", include_content=False, section="NonExistent")

        # Assert
        assert result.section_filter_miss is True, (
            "result.section_filter_miss must be True in compact mode when the requested "
            "section is absent from the body.  The compact path (include_content=False) "
            "must propagate the miss flag the same way the full path does."
        )


# ---------------------------------------------------------------------------
# Tests 5 & 6: server response shapes include section_filter_miss
# ---------------------------------------------------------------------------


class TestServerResponseShapesSectionFilterMiss:
    """Tests that all three server response shapes carry section_filter_miss.

    These tests exercise _build_compact_manifest and _build_over_budget_view
    directly (sync helpers), which avoids the async/mcp.tool decorator.
    The helper functions receive a ViewItemResult that already has the flag set,
    and the assertion checks that the returned dict includes the field.
    """

    def test_section_filter_miss_in_compact_manifest_summary_shape(self) -> None:
        """_build_compact_manifest dict includes section_filter_miss=True.

        Arrange: construct a ViewItemResult with section_filter_miss=True.
        Act: call _build_compact_manifest.
        Assert: returned dict has 'section_filter_miss': True.

        RED: fails because _build_compact_manifest does not include this field.
        """
        from backlog_core.server import _build_compact_manifest

        # Arrange — result with flag already set (as view_item would produce it)
        result = ViewItemResult(title="Test Item", issue="300")
        result.section_filter_miss = True  # type: ignore[attr-defined]

        full_response: dict[str, object] = result.model_dump()
        full_response["section_filter_miss"] = True  # mirror flag in full response

        # Act
        compact = _build_compact_manifest(result, full_response, "#300")

        # Assert
        assert compact.get("section_filter_miss") is True, (
            "_build_compact_manifest must include 'section_filter_miss': True when "
            "result.section_filter_miss is True.  If absent, callers using summary=True "
            "cannot detect that their requested section was not found."
        )

    def test_section_filter_miss_false_in_compact_manifest_when_not_set(self) -> None:
        """_build_compact_manifest dict includes section_filter_miss=False by default.

        Non-regression: a normal result (miss flag False) should still expose the field
        so callers have a consistent schema regardless of whether a miss occurred.

        Arrange: result with section_filter_miss=False (default).
        Act: call _build_compact_manifest.
        Assert: returned dict has 'section_filter_miss': False.

        RED: fails because _build_compact_manifest does not include this field at all.
        """
        from backlog_core.server import _build_compact_manifest

        # Arrange
        result = ViewItemResult(title="Normal Item", issue="301")
        full_response: dict[str, object] = result.model_dump()

        # Act
        compact = _build_compact_manifest(result, full_response, "#301")

        # Assert — key must be present even when False
        assert "section_filter_miss" in compact, (
            "'section_filter_miss' key must always be present in _build_compact_manifest "
            "output so callers have a consistent schema.  When not a miss, value is False."
        )
        assert compact["section_filter_miss"] is False, (
            "'section_filter_miss' must be False in a normal (non-miss) compact manifest."
        )

    def test_section_filter_miss_in_over_budget_shape(self) -> None:
        """_build_over_budget_view dict includes section_filter_miss=True.

        Arrange: construct a ViewItemResult with section_filter_miss=True.
        Act: call _build_over_budget_view.
        Assert: returned dict has 'section_filter_miss': True.

        RED: fails because _build_over_budget_view does not include this field.
        """
        from backlog_core.server import _build_over_budget_view

        # Arrange
        result = ViewItemResult(title="Big Item", issue="400")
        result.section_filter_miss = True  # type: ignore[attr-defined]

        # Act
        over_budget = _build_over_budget_view(result, full_chars=100_000, selector="#400")

        # Assert
        assert over_budget.get("section_filter_miss") is True, (
            "_build_over_budget_view must include 'section_filter_miss': True when "
            "result.section_filter_miss is True.  Callers that receive the over-budget "
            "shape must still be able to detect that their section was not found."
        )
