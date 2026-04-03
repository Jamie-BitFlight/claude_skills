"""Tests for the new Pydantic data models added in the pure-YAML migration.

Covers: Entry (with struck validator), GroomedData, Section,
BacklogItemMetadata (with field validators), and BacklogItem (with
metadata sub-model, property accessors, and serialisation exclusions).
"""

from __future__ import annotations

import pytest
from backlog_core.models import BacklogItem, BacklogItemMetadata, Entry, GroomedData, Section
from pydantic import ValidationError as PydanticValidationError

# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------


class TestEntryFields:
    """Entry has the expected fields and no raw field."""

    def test_entry_has_id_field(self) -> None:
        e = Entry(id="E1", content="text", struck=False, struck_reason="", struck_at="")
        assert e.id == "E1"

    def test_entry_has_content_field(self) -> None:
        e = Entry(content="some content")
        assert e.content == "some content"

    def test_entry_has_struck_field(self) -> None:
        e = Entry()
        assert e.struck is False

    def test_entry_has_struck_reason_field(self) -> None:
        e = Entry(struck_reason="done")
        assert e.struck_reason == "done"

    def test_entry_has_struck_at_field(self) -> None:
        e = Entry(struck_at="2026-01-01")
        assert e.struck_at == "2026-01-01"

    def test_entry_does_not_have_raw_field(self) -> None:
        e = Entry()
        assert not hasattr(e, "raw")

    def test_entry_model_fields_does_not_include_raw(self) -> None:
        assert "raw" not in Entry.model_fields


class TestEntryStruckValidator:
    """Entry validator: struck=True only when struck_at is non-empty."""

    def test_entry_struck_true_with_struck_at_is_valid(self) -> None:
        e = Entry(struck=True, struck_at="2026-03-01")
        assert e.struck is True

    def test_entry_struck_false_with_empty_struck_at_is_valid(self) -> None:
        e = Entry(struck=False, struck_at="")
        assert e.struck is False

    def test_entry_struck_true_with_empty_struck_at_raises_validation_error(self) -> None:
        with pytest.raises(PydanticValidationError):
            Entry(struck=True, struck_at="")

    def test_entry_struck_false_with_struck_at_is_valid(self) -> None:
        e = Entry(struck=False, struck_at="2026-01-01")
        assert e.struck is False


# ---------------------------------------------------------------------------
# GroomedData
# ---------------------------------------------------------------------------


class TestGroomedData:
    """GroomedData has date and subsections fields."""

    def test_groomed_data_default_date_is_empty(self) -> None:
        g = GroomedData()
        assert g.date == ""

    def test_groomed_data_default_subsections_is_empty_dict(self) -> None:
        g = GroomedData()
        assert g.subsections == {}

    def test_groomed_data_stores_date(self) -> None:
        g = GroomedData(date="2026-03-30")
        assert g.date == "2026-03-30"

    def test_groomed_data_stores_subsections(self) -> None:
        g = GroomedData(subsections={"priority": "P1", "impact": "high"})
        assert g.subsections["priority"] == "P1"

    def test_groomed_data_model_validate_empty_subsections(self) -> None:
        g = GroomedData.model_validate({"date": "2026-01-01", "subsections": {}})
        assert g.date == "2026-01-01"
        assert g.subsections == {}

    def test_groomed_data_model_validate_no_subsections_key(self) -> None:
        g = GroomedData.model_validate({})
        assert g.subsections == {}


# ---------------------------------------------------------------------------
# Section
# ---------------------------------------------------------------------------


class TestSection:
    """Section has an entries list."""

    def test_section_default_entries_is_empty_list(self) -> None:
        s = Section()
        assert s.entries == []

    def test_section_stores_entries(self) -> None:
        e = Entry(id="E1", content="x")
        s = Section(entries=[e])
        assert len(s.entries) == 1
        assert s.entries[0].id == "E1"

    def test_section_model_validate_empty_list(self) -> None:
        s = Section.model_validate({"entries": []})
        assert s.entries == []

    def test_section_model_validate_no_entries_key(self) -> None:
        s = Section.model_validate({})
        assert s.entries == []


# ---------------------------------------------------------------------------
# BacklogItemMetadata
# ---------------------------------------------------------------------------


class TestBacklogItemMetadataDefaults:
    """BacklogItemMetadata default values."""

    def test_metadata_default_source(self) -> None:
        m = BacklogItemMetadata()
        assert m.source == "Not specified"

    def test_metadata_default_priority_empty(self) -> None:
        m = BacklogItemMetadata()
        assert m.priority == ""

    def test_metadata_default_item_type_feature(self) -> None:
        m = BacklogItemMetadata()
        assert m.item_type == "Feature"

    def test_metadata_default_status_empty(self) -> None:
        m = BacklogItemMetadata()
        assert m.status == ""

    def test_metadata_default_added_empty(self) -> None:
        m = BacklogItemMetadata()
        assert m.added == ""


class TestBacklogItemMetadataPriorityValidator:
    """BacklogItemMetadata.priority validator."""

    @pytest.mark.parametrize("p", ["P0", "P1", "P2", "Ideas", "completed"])
    def test_valid_priority_accepted(self, p: str) -> None:
        m = BacklogItemMetadata(priority=p)
        assert m.priority == p

    def test_empty_priority_accepted(self) -> None:
        m = BacklogItemMetadata(priority="")
        assert m.priority == ""

    def test_p3_accepted_verbatim(self) -> None:
        """P3 is a valid priority not in the canonical set — accepted verbatim."""
        m = BacklogItemMetadata(priority="P3")
        assert m.priority == "P3"

    def test_unknown_priority_accepted_verbatim(self) -> None:
        """Unknown priority values are preserved verbatim, not rejected."""
        m = BacklogItemMetadata(priority="critical")
        assert m.priority == "critical"

    @pytest.mark.parametrize(("raw", "expected"), [("IDEA", "Ideas"), ("Idea", "Ideas"), ("idea", "Ideas")])
    def test_idea_variants_normalised(self, raw: str, expected: str) -> None:
        """case-insensitive idea* prefix is normalised to 'Ideas'."""
        m = BacklogItemMetadata(priority=raw)
        assert m.priority == expected


class TestBacklogItemMetadataTypeValidator:
    """BacklogItemMetadata.item_type (alias 'type') validator."""

    @pytest.mark.parametrize("t", ["Feature", "Bug", "Refactor", "Docs", "Chore"])
    def test_valid_type_accepted(self, t: str) -> None:
        m = BacklogItemMetadata(item_type=t)
        assert m.item_type == t

    def test_empty_type_accepted(self) -> None:
        m = BacklogItemMetadata(item_type="")
        assert m.item_type == ""

    def test_documentation_alias_normalised(self) -> None:
        """'Documentation' is a known alias for 'Docs'."""
        m = BacklogItemMetadata(item_type="Documentation")
        assert m.item_type == "Docs"

    def test_enhancement_accepted_verbatim(self) -> None:
        """Unknown type values like 'Enhancement' are preserved verbatim."""
        m = BacklogItemMetadata(item_type="Enhancement")
        assert m.item_type == "Enhancement"

    def test_tech_debt_accepted_verbatim(self) -> None:
        """Unknown type values like 'Tech Debt' are preserved verbatim."""
        m = BacklogItemMetadata(item_type="Tech Debt")
        assert m.item_type == "Tech Debt"

    def test_unknown_type_accepted_verbatim(self) -> None:
        """Previously-rejected type values are now preserved verbatim."""
        m = BacklogItemMetadata(item_type="Epic")
        assert m.item_type == "Epic"


class TestBacklogItemMetadataStatusValidator:
    """BacklogItemMetadata.status validator."""

    @pytest.mark.parametrize("s", ["open", "done", "in-progress", "needs-grooming", "closed"])
    def test_valid_status_accepted(self, s: str) -> None:
        m = BacklogItemMetadata(status=s)
        assert m.status == s

    def test_empty_status_accepted(self) -> None:
        m = BacklogItemMetadata(status="")
        assert m.status == ""

    def test_legacy_resolved_accepted(self) -> None:
        """Legacy 'resolved' status is accepted verbatim."""
        m = BacklogItemMetadata(status="resolved")
        assert m.status == "resolved"

    def test_legacy_groomed_accepted(self) -> None:
        """Legacy 'groomed' status is accepted verbatim."""
        m = BacklogItemMetadata(status="groomed")
        assert m.status == "groomed"

    def test_unknown_status_accepted_verbatim(self) -> None:
        """Previously-rejected status values are now preserved verbatim."""
        m = BacklogItemMetadata(status="unknown")
        assert m.status == "unknown"


class TestBacklogItemMetadataCloseReason:
    """BacklogItemMetadata.close_reason field."""

    def test_close_reason_default_empty(self) -> None:
        m = BacklogItemMetadata()
        assert m.close_reason == ""

    def test_close_reason_accepted(self) -> None:
        m = BacklogItemMetadata(close_reason="superseded")
        assert m.close_reason == "superseded"

    def test_unknown_metadata_key_ignored(self) -> None:
        """Extra keys in frontmatter must be silently discarded, not raise ValidationError."""
        m = BacklogItemMetadata.model_validate({"status": "closed", "unknown_future_key": "value"})
        assert m.status == "closed"
        assert not hasattr(m, "unknown_future_key")


class TestBacklogItemMetadataAddedValidator:
    """BacklogItemMetadata.added validator (YYYY-MM-DD)."""

    def test_valid_added_accepted(self) -> None:
        m = BacklogItemMetadata(added="2026-03-30")
        assert m.added == "2026-03-30"

    def test_empty_added_accepted(self) -> None:
        m = BacklogItemMetadata(added="")
        assert m.added == ""

    def test_invalid_added_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            BacklogItemMetadata(added="March 30 2026")

    def test_invalid_added_partial_date_rejected(self) -> None:
        with pytest.raises(PydanticValidationError):
            BacklogItemMetadata(added="2026-03")


# ---------------------------------------------------------------------------
# BacklogItem
# ---------------------------------------------------------------------------


class TestBacklogItemModelValidate:
    """BacklogItem.model_validate() succeeds on structured YAML dicts."""

    def test_model_validate_full_yaml_dict(self) -> None:
        data = {
            "title": "My feature",
            "description": "Does X",
            "type_": "",
            "section": "P1",
            "metadata": {
                "source": "team",
                "added": "2026-01-01",
                "priority": "P1",
                "type": "Feature",
                "status": "open",
                "issue": "#42",
                "last_synced": "",
                "groomed": "",
                "plan": "",
                "topic": "",
                "research_first": "",
                "files": "",
                "suggested_location": "",
            },
            "sections": {
                "groomed": {"date": "2026-03-01", "subsections": {"impact": "high"}},
                "notes": {
                    "entries": [{"id": "E1", "content": "note", "struck": False, "struck_reason": "", "struck_at": ""}]
                },
            },
        }
        item = BacklogItem.model_validate(data)
        assert item.title == "My feature"
        assert item.priority == "P1"
        assert item.issue == "#42"

    def test_model_validate_minimal_dict(self) -> None:
        item = BacklogItem.model_validate({"title": "minimal"})
        assert item.title == "minimal"
        assert item.priority == ""


class TestBacklogItemProperties:
    """BacklogItem property accessors delegate to metadata."""

    def test_priority_property_returns_metadata_priority(self) -> None:
        item = BacklogItem(priority="P2")
        assert item.priority == item.metadata.priority

    def test_issue_property_returns_metadata_issue(self) -> None:
        item = BacklogItem(issue="#7")
        assert item.issue == item.metadata.issue

    def test_source_property_returns_metadata_source(self) -> None:
        item = BacklogItem(source="github")
        assert item.source == item.metadata.source

    def test_added_property_returns_metadata_added(self) -> None:
        item = BacklogItem(added="2026-02-01")
        assert item.added == item.metadata.added

    def test_status_property_returns_metadata_status(self) -> None:
        item = BacklogItem(status="open")
        assert item.status == item.metadata.status

    def test_plan_property_returns_metadata_plan(self) -> None:
        item = BacklogItem(plan="plan/tasks.yaml")
        assert item.plan == item.metadata.plan

    def test_item_type_property_returns_metadata_item_type(self) -> None:
        item = BacklogItem(item_type="Bug")
        assert item.item_type == item.metadata.item_type

    def test_groomed_property_returns_metadata_groomed(self) -> None:
        item = BacklogItem(groomed="2026-03-01")
        assert item.groomed == item.metadata.groomed

    def test_last_synced_property_returns_metadata_last_synced(self) -> None:
        item = BacklogItem(last_synced="2026-03-30T10:00:00Z")
        assert item.last_synced == item.metadata.last_synced


class TestBacklogItemSerialisation:
    """BacklogItem.model_dump() excludes file_path and skip."""

    def test_file_path_excluded_from_model_dump(self) -> None:
        item = BacklogItem(file_path="/some/path.md")
        result = item.model_dump()
        assert "file_path" not in result

    def test_skip_excluded_from_model_dump(self) -> None:
        item = BacklogItem(skip=True)
        result = item.model_dump()
        assert "skip" not in result

    def test_file_path_excluded_when_exclude_none_false(self) -> None:
        item = BacklogItem(file_path="/path.md")
        result = item.model_dump(exclude_none=False)
        assert "file_path" not in result

    def test_skip_excluded_when_exclude_none_false(self) -> None:
        item = BacklogItem(skip=True)
        result = item.model_dump(exclude_none=False)
        assert "skip" not in result

    def test_model_dump_contains_metadata_key(self) -> None:
        item = BacklogItem()
        result = item.model_dump()
        assert "metadata" in result

    def test_model_dump_contains_sections_key(self) -> None:
        item = BacklogItem()
        result = item.model_dump()
        assert "sections" in result

    def test_file_path_still_accessible_as_attribute(self) -> None:
        item = BacklogItem(file_path="/path.md")
        assert item.file_path == "/path.md"

    def test_skip_still_accessible_as_attribute(self) -> None:
        item = BacklogItem(skip=True)
        assert item.skip is True
