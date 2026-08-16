"""Regression tests for sections_index data loss bug.

Bug summary:
    ``backlog_groom(selector, section="RT-ICA", content="...")`` stores the raw
    section name ``"RT-ICA"`` as the key in ``BacklogItem.sections``.
    ``_render_section_index`` then calls ``section_display_title("RT-ICA")``, which
    does NOT match the ``SECTION_HEADING`` lookup table (keyed by ``"rt_ica"``) and
    falls through to ``"RT-ICA".replace("_", " ").title()`` → ``"Rt-Ica"``.

    The resulting ``sections_index`` contains ``"[N] Rt-Ica (M entries)"`` — the
    string ``"RT-ICA"`` is absent.  Any agent that checks
    ``"RT-ICA" in sections_index`` concludes the section does not exist and may
    overwrite real content.

    The same defect affects "Fact-Check" (stored as ``"Fact-Check"``, rendered as
    ``"Fact-Check"`` — actually title-stable, but still not matched by
    ``SECTION_HEADING["fact_check"]``) and "Impact Radius" (stored as
    ``"Impact Radius"``, rendered as ``"Impact Radius"`` — also title-stable).

    By contrast, sections whose names happen to be title-case invariant
    (e.g. ``"Reproducibility"``, ``"Priority"``) produce correct output because
    ``"Reproducibility".replace("_", " ").title() == "Reproducibility"``.

Tests:
    test_sections_index_missing_rt_ica_section:
        Stores an item whose sections dict has key ``"RT-ICA"``.  Calls
        ``view_item(include_content=False)`` and asserts ``"RT-ICA"`` appears in
        ``result.sections_index``.  FAILS with the current code (bug present) because
        the index renders ``"Rt-Ica"`` not ``"RT-ICA"``.

    test_sections_index_contains_reproducibility_section:
        Same setup but with key ``"Reproducibility"``.  Asserts ``"Reproducibility"``
        appears in ``result.sections_index``.  PASSES, confirming the test
        infrastructure is correct and the asymmetry is a real bug in the code.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backlog_core.models import BacklogItem, Entry, Section, ViewItemResult
from backlog_core.operations import _render_section_index, view_item
from backlog_core.tests._view_test_helpers import _configure_memory_view

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_item_with_section(section_name: str, content: str = "Some entry content") -> BacklogItem:
    """Return a BacklogItem whose sections dict contains exactly one entry under *section_name*.

    The key is the literal string *section_name* — exactly as backlog_groom stores it
    when the caller passes ``section="RT-ICA"`` (or any other name) to
    ``_write_groomed_to_yaml_item``.

    Args:
        section_name: The section storage key (e.g. ``"RT-ICA"`` or ``"Reproducibility"``).
        content: Content string to place in the single entry.

    Returns:
        BacklogItem with one section, one non-struck entry.
    """
    entry = Entry(id="2026-01-01T00:00:00Z", content=content)
    section = Section(entries=[entry])
    return BacklogItem(title="Test Backlog Item", sections={section_name: section})


# ---------------------------------------------------------------------------
# _render_section_index — unit tests (no I/O)
# ---------------------------------------------------------------------------


class TestRenderSectionIndex:
    """Unit tests for _render_section_index with section names as stored by groom.

    Tests the rendering layer directly — no mocking, no I/O.
    These tests validate the exact mechanism that produces the data loss.
    """

    def test_rt_ica_section_name_appears_verbatim_in_index(self) -> None:
        """_render_section_index must include ``RT-ICA`` when section key is ``"RT-ICA"``.

        Tests: sections_index accuracy for mixed-case section names stored by groom.
        How: Build a BacklogItem with sections[\"RT-ICA\"] = Section(entries=[...]).
             Call _render_section_index and assert the output contains \"RT-ICA\".
        Why: backlog_groom stores section names as literal strings (e.g. \"RT-ICA\").
             section_display_title(\"RT-ICA\") falls through to .title() → \"Rt-Ica\".
             This assertion FAILS with the current code — confirming the bug.
        """
        # Arrange
        item = _make_item_with_section("RT-ICA")

        # Act
        index = _render_section_index(item)

        # Assert
        assert "RT-ICA" in index, (
            f"Expected 'RT-ICA' in sections_index but got:\n{index!r}\n"
            "The section was stored as key 'RT-ICA' but section_display_title() "
            "rendered it as something else (likely 'Rt-Ica' via .title() fallthrough)."
        )

    def test_reproducibility_section_name_appears_in_index(self) -> None:
        """_render_section_index includes ``Reproducibility`` when section key is ``"Reproducibility"``.

        Tests: sections_index accuracy for title-case-invariant section names.
        How: Build a BacklogItem with sections[\"Reproducibility\"] = Section(entries=[...]).
             Call _render_section_index and assert the output contains \"Reproducibility\".
        Why: Confirms test infrastructure is correct and the asymmetry is real.
             \"Reproducibility\".replace(\"_\", \" \").title() == \"Reproducibility\" — this
             happens to be stable, so the groomer-written section name survives rendering.
             This assertion PASSES with the current code.
        """
        # Arrange
        item = _make_item_with_section("Reproducibility")

        # Act
        index = _render_section_index(item)

        # Assert
        assert "Reproducibility" in index, f"Expected 'Reproducibility' in sections_index but got:\n{index!r}"


# ---------------------------------------------------------------------------
# view_item integration — exercises the full sections_index generation path
# ---------------------------------------------------------------------------


class TestViewItemSectionsIndex:
    """Integration tests for sections_index via view_item(include_content=False).

    Uses ``_configure_memory_view`` to back ``view_item`` with an ``InMemoryBackend``
    seeded with the item under test, so no filesystem or GitHub access is needed. This
    is the established pattern shared by the rest of the #2495 view test suite (see
    ``backlog_core/tests/_view_test_helpers.py``); it patches only ``get_config`` (and
    the backend's ``view_enrich_from_github``), letting the real ``find_item`` and
    ``parse_issue_selector`` run against the seeded backend. The sections_index
    generation path (_assemble_view_content → _render_section_index) is NOT mocked —
    it must run against real BacklogItem.sections data to reproduce the bug.
    """

    def test_rt_ica_section_appears_in_sections_index_after_groom(self, mocker: MockerFixture) -> None:
        """sections_index from view_item must contain ``RT-ICA`` when section key is ``"RT-ICA"``.

        Tests: End-to-end sections_index accuracy for RT-ICA section (data loss bug).
        How: Construct BacklogItem with sections[\"RT-ICA\"] set; seed an InMemoryBackend
             with it via _configure_memory_view; call view_item(include_content=False);
             assert \"RT-ICA\" in result.sections_index.
        Why: This is the exact agent-facing path. Agents call backlog_view(summary=True)
             which calls view_item(include_content=False). When sections_index lacks
             \"RT-ICA\" the agent treats the section as absent and overwrites real content.
             This assertion FAILS with the current code — confirming the bug.
        """
        # Arrange — item as the groomer would leave it
        item = _make_item_with_section("RT-ICA", content="RT-ICA analysis content")
        _configure_memory_view(mocker, item=item)

        # Act
        result: ViewItemResult = view_item(selector="Test Backlog Item", include_content=False)

        # Assert
        assert "RT-ICA" in result.sections_index, (
            f"Expected 'RT-ICA' in sections_index but got:\n{result.sections_index!r}\n"
            "Bug confirmed: section stored as 'RT-ICA' is rendered under a different "
            "display title (likely 'Rt-Ica') so agents cannot find it by its original name."
        )

    def test_reproducibility_section_appears_in_sections_index(self, mocker: MockerFixture) -> None:
        """sections_index from view_item contains ``Reproducibility`` when section key matches.

        Tests: sections_index accuracy for title-case-invariant groomer section names.
        How: Same setup as above but with key ``"Reproducibility"``; assert it appears in index.
        Why: Confirms the asymmetry — groomer-written sections with title-stable names DO
             appear correctly. Only mixed-case names (RT-ICA, Fact-Check) are affected.
             This assertion PASSES with the current code.
        """
        # Arrange
        item = _make_item_with_section("Reproducibility", content="Steps to reproduce the issue")
        _configure_memory_view(mocker, item=item)

        # Act
        result: ViewItemResult = view_item(selector="Test Backlog Item", include_content=False)

        # Assert
        assert "Reproducibility" in result.sections_index, (
            f"Expected 'Reproducibility' in sections_index but got:\n{result.sections_index!r}"
        )
