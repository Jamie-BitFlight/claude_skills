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
    # "Decision" is not a canonical section name (see rendering.SECTION_HEADING), so its raw
    # storage key is "unknown__decision" — but view_item keys its output by display title
    # (see operations._build_sections_from_yaml_item / #2971), not the raw storage key.
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


def test_full_entry_lifecycle_with_nested_html_survives_resubmission(backlog_dir, mock_github):
    """Real write -> render -> parse cycle through operations, not entry_blocks directly.

    Regression for the residual ENTRY_RE/STRUCK_RE extent divergence
    (.tmp/scratch/reports/20260823-entry-extent-residual.md): groom content
    containing a nested <div> and a nested <details>, view it back, resubmit
    exactly what view_item returned (the echo-back an agent performs), and
    verify no entry is lost, duplicated, or has its tail truncated.
    """
    out = Output()
    operations.add_item(title="Nested HTML Lifecycle Test", priority="P1", description="Test", output=out)

    content = 'Finding A.\n\n<div align="center">a nested figure</div>\n\nFinding B - the important part.'
    operations.groom_item(selector="Nested HTML Lifecycle Test", section="Fact-Check", content=content, output=out)

    result = operations.view_item(selector="Nested HTML Lifecycle Test", output=out)
    sections = result.sections
    assert isinstance(sections, dict)
    fact_check = cast("SectionEntryMetadata", sections["Fact-Check"])
    assert fact_check["num_entries"] == 1
    entries = list(fact_check["entries"])
    assert len(entries) == 1
    returned_content = entries[0]["content"]
    assert "Finding B - the important part." in returned_content

    # Resubmit exactly what view_item returned — the echo-back path that corrupted the
    # wrapper before find_entry_spans replaced ENTRY_RE in wrap_entry.
    operations.groom_item(
        selector="Nested HTML Lifecycle Test",
        section="Fact-Check",
        content=returned_content,
        entry_id=entries[0]["id"],
        output=out,
    )

    result = operations.view_item(selector="Nested HTML Lifecycle Test", output=out)
    sections = result.sections
    assert isinstance(sections, dict)
    fact_check = cast("SectionEntryMetadata", sections["Fact-Check"])
    assert fact_check["num_entries"] == 1, (
        f"Resubmission must not grow junk entries, got {fact_check['num_entries']}: {fact_check['entries']}"
    )
    entries = list(fact_check["entries"])
    assert "Finding B - the important part." in entries[0]["content"]

    # Strike the entry — its content survives a nested <details> the same way the read
    # path (STRUCK_RE -> _match_struck) must.
    struck_content = "Notes.\n\n<details><summary>detail</summary>\ninner\n</details>\n\nTail that matters."
    operations.groom_item(
        selector="Nested HTML Lifecycle Test",
        section="Fact-Check",
        content=struck_content,
        entry_id=entries[0]["id"],
        output=out,
    )
    result = operations.view_item(selector="Nested HTML Lifecycle Test", output=out)
    sections = result.sections
    assert isinstance(sections, dict)
    fact_check = cast("SectionEntryMetadata", sections["Fact-Check"])
    entries = list(fact_check["entries"])
    target_id = entries[0]["id"]
    operations.strike_entry(selector="Nested HTML Lifecycle Test", entry_id=target_id, reason="superseded", output=out)

    result = operations.view_item(selector="Nested HTML Lifecycle Test", output=out)
    sections = result.sections
    assert isinstance(sections, dict)
    fact_check = cast("SectionEntryMetadata", sections["Fact-Check"])
    assert fact_check["num_struck"] == 1
    struck_entries = [e for e in fact_check["entries"] if e.get("struck")]
    assert len(struck_entries) == 1
    assert "Tail that matters." in struck_entries[0]["content"]
