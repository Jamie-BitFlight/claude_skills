"""Agent-facing recovery of historical section-key spellings."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from backlog_core.models import BacklogItem, ViewItemResult
from backlog_core.operations import view_item
from backlog_core.tests._view_test_helpers import _configure_memory_view
from backlog_core.yaml_io import load_item_text

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def _load_legacy_item_with_section(section_name: str, content: str) -> BacklogItem:
    """Load a historical display-key spelling through the YAML read boundary."""
    return load_item_text(
        f"""title: Test Backlog Item
sections:
  "{section_name}":
    entries:
      - id: "2026-01-01T00:00:00Z"
        content: "{content}"
""",
        Path("legacy-item.yaml"),
    )


class TestViewItemSectionsIndex:
    """Legacy persisted sections remain discoverable from the agent-facing view."""

    def test_rt_ica_section_appears_in_sections_index_after_groom(self, mocker: MockerFixture) -> None:
        """A historical ``RT-ICA`` YAML key is normalized and rendered for agents."""
        item = _load_legacy_item_with_section("RT-ICA", "RT-ICA analysis content")
        assert set(item.sections) == {"rt_ica"}
        _configure_memory_view(mocker, item=item)

        result: ViewItemResult = view_item(selector="Test Backlog Item", include_content=False)

        assert "RT-ICA" in result.sections_index

    def test_reproducibility_section_appears_in_sections_index(self, mocker: MockerFixture) -> None:
        """A historical ``Reproducibility`` YAML key is normalized and rendered for agents."""
        item = _load_legacy_item_with_section("Reproducibility", "Steps to reproduce the issue")
        assert set(item.sections) == {"reproducibility"}
        _configure_memory_view(mocker, item=item)

        result: ViewItemResult = view_item(selector="Test Backlog Item", include_content=False)

        assert "Reproducibility" in result.sections_index
