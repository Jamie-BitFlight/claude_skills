"""Integration test: full entry block lifecycle.

Tests the round-trip: create item -> groom with entries -> strike -> view -> verify.

"""

from __future__ import annotations

from typing import cast

from backlog_core import operations
from backlog_core.models import Output, SectionEntryMetadata


def test_full_entry_lifecycle(backlog_dir, mock_github):
    """Create item -> groom with entries -> strike one -> view -> verify."""
    out = Output()

    # Create
    operations.add_item(title="Lifecycle Test", priority="P1", description="Test lifecycle", output=out)

    operations.groom_item(selector="Lifecycle Test", section="Decision", content="First decision.", output=out)
    operations.groom_item(selector="Lifecycle Test", section="Decision", content="Second decision.", output=out)

    # View — should show 2 active entries
    result = operations.view_item(selector="Lifecycle Test", output=out)
    sections = result.sections
    assert isinstance(sections, dict), f"sections should be dict, got {type(sections)}"
    assert "Decision" in sections, f"Expected 'Decision' in sections, got: {list(sections.keys())}"
    decision = cast("SectionEntryMetadata", sections["Decision"])
    assert decision["num_entries"] == 2, f"Expected 2 active entries, got {decision['num_entries']}"

    # Strike the first entry
    entries = list(decision["entries"])
    first_id = entries[0]["id"]
    operations.strike_entry(selector="Lifecycle Test", entry_id=first_id, reason="superseded", output=out)

    # View again — should show 1 active, 1 struck
    result = operations.view_item(selector="Lifecycle Test", output=out)
    sections = result.sections
    assert isinstance(sections, dict)
    decision = cast("SectionEntryMetadata", sections["Decision"])
    assert decision["num_entries"] == 1, f"Expected 1 active entry, got {decision['num_entries']}"
    assert decision["num_struck"] == 1, f"Expected 1 struck entry, got {decision['num_struck']}"

    # Overwrite the remaining active entry
    entries2 = list(decision["entries"])
    active_entries = [e for e in entries2 if not e.get("struck")]
    assert len(active_entries) == 1
    second_id = active_entries[0]["id"]
    operations.groom_item(
        selector="Lifecycle Test",
        section="Decision",
        content="Updated second decision.",
        entry_id=second_id,
        output=out,
    )

    # Final view — verify overwrite
    result = operations.view_item(selector="Lifecycle Test", output=out)
    sections = result.sections
    assert isinstance(sections, dict)
    entries3 = list(cast("SectionEntryMetadata", sections["Decision"])["entries"])
    active = [e for e in entries3 if not e.get("struck")]
    assert len(active) == 1
    assert "Updated second decision." in active[0]["content"]
