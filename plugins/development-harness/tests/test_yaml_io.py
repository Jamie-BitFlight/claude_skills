"""Tests for backlog_core.yaml_io — YAML file I/O and format detection.

Covers load_item, save_item, detect_format, and load_item_text with both
.yaml and legacy .md paths.  Uses real parse_item_file and real YAML loading
to maintain integration fidelity.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import pytest
from backlog_core.models import BacklogItem, GroomedData, Section
from backlog_core.yaml_io import detect_format, load_item, load_item_text, save_item

# ---------------------------------------------------------------------------
# Fixture directory
# ---------------------------------------------------------------------------

_FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# detect_format
# ---------------------------------------------------------------------------


class TestDetectFormat:
    """detect_format: returns format literal from path suffix."""

    def test_detect_format_yaml_returns_yaml(self) -> None:
        """detect_format returns 'yaml' for a .yaml file path.

        Verifies the dispatch key used by load_item to choose the YAML parser.
        """
        # Arrange
        path = Path("/some/dir/item.yaml")

        # Act
        result = detect_format(path)

        # Assert
        assert result == "yaml"

    def test_detect_format_md_returns_legacy_md(self) -> None:
        """detect_format returns 'legacy_md' for a .md file path.

        Verifies the dispatch key used by load_item to choose the legacy parser.
        """
        # Arrange
        path = Path("/some/dir/item.md")

        # Act
        result = detect_format(path)

        # Assert
        assert result == "legacy_md"

    def test_detect_format_unsupported_raises_value_error(self) -> None:
        """detect_format raises ValueError for unsupported file extensions.

        .txt is not a supported backlog item format and must fail fast.
        """
        # Arrange
        path = Path("/some/dir/item.txt")

        # Act / Assert
        with pytest.raises(ValueError, match="Unsupported file extension"):
            detect_format(path)

    def test_detect_format_json_raises_value_error(self) -> None:
        """detect_format raises ValueError for .json extension.

        Only .yaml and .md are valid backlog item extensions.
        """
        # Arrange
        path = Path("/some/dir/item.json")

        # Act / Assert
        with pytest.raises(ValueError, match="Unsupported file extension"):
            detect_format(path)


# ---------------------------------------------------------------------------
# load_item — .yaml files
# ---------------------------------------------------------------------------


class TestLoadItemYaml:
    """load_item: reads BacklogItem from .yaml files."""

    def test_load_item_returns_backlog_item(self, tmp_path: Path) -> None:
        """load_item returns a BacklogItem instance from a valid .yaml file.

        Checks the basic contract that load_item produces the right type.
        """
        # Arrange
        src = _FIXTURES_DIR / "sample_item.yaml"
        dest = tmp_path / "item.yaml"
        dest.write_bytes(src.read_bytes())

        # Act
        result = load_item(dest)

        # Assert
        assert isinstance(result, BacklogItem)

    def test_load_item_title_field(self, tmp_path: Path) -> None:
        """load_item populates the title field from the YAML file.

        Title must match the value written in the fixture to verify field mapping.
        """
        # Arrange
        src = _FIXTURES_DIR / "sample_item.yaml"
        dest = tmp_path / "item.yaml"
        dest.write_bytes(src.read_bytes())

        # Act
        result = load_item(dest)

        # Assert
        assert result.title == "Add YAML-based backlog item storage"

    def test_load_item_metadata_priority(self, tmp_path: Path) -> None:
        """load_item populates metadata.priority from the YAML file.

        Priority must be accessible through both the flat field and metadata.
        """
        # Arrange
        src = _FIXTURES_DIR / "sample_item.yaml"
        dest = tmp_path / "item.yaml"
        dest.write_bytes(src.read_bytes())

        # Act
        result = load_item(dest)

        # Assert
        assert result.priority == "P1"
        assert result.metadata.priority == "P1"

    def test_load_item_description_field(self, tmp_path: Path) -> None:
        """load_item populates the description field correctly.

        Description field maps directly to BacklogItem.description.
        """
        # Arrange
        src = _FIXTURES_DIR / "sample_item.yaml"
        dest = tmp_path / "item.yaml"
        dest.write_bytes(src.read_bytes())

        # Act
        result = load_item(dest)

        # Assert
        assert "pure-YAML file I/O" in result.description

    def test_load_item_file_path_set_to_resolved(self, tmp_path: Path) -> None:
        """load_item sets file_path to the resolved absolute path.

        file_path is used downstream for issue linking and must be absolute.
        """
        # Arrange
        src = _FIXTURES_DIR / "sample_item.yaml"
        dest = tmp_path / "item.yaml"
        dest.write_bytes(src.read_bytes())

        # Act
        result = load_item(dest)

        # Assert
        assert result.file_path == str(dest.resolve())

    def test_load_item_empty_sections(self, tmp_path: Path) -> None:
        """load_item returns empty sections dict when YAML has no sections.

        sample_item.yaml has sections: {} — BacklogItem.sections must be empty.
        """
        # Arrange
        src = _FIXTURES_DIR / "sample_item.yaml"
        dest = tmp_path / "item.yaml"
        dest.write_bytes(src.read_bytes())

        # Act
        result = load_item(dest)

        # Assert
        assert result.sections == {}

    def test_load_item_all_four_section_types(self, tmp_path: Path) -> None:
        """load_item parses all four section types from the groomed fixture.

        fact_check, rt_ica, issue_classification, and groomed sections must
        all be present after loading sample_item_groomed.yaml.
        """
        # Arrange
        src = _FIXTURES_DIR / "sample_item_groomed.yaml"
        dest = tmp_path / "groomed.yaml"
        dest.write_bytes(src.read_bytes())

        # Act
        result = load_item(dest)

        # Assert
        assert "fact_check" in result.sections
        assert "rt_ica" in result.sections
        assert "issue_classification" in result.sections
        assert "groomed" in result.sections

    def test_load_item_section_types_are_correct_models(self, tmp_path: Path) -> None:
        """load_item maps entry-bearing sections to Section and groomed to GroomedData.

        The discriminator in BacklogItem.sections must produce the right model types.
        """
        # Arrange
        src = _FIXTURES_DIR / "sample_item_groomed.yaml"
        dest = tmp_path / "groomed.yaml"
        dest.write_bytes(src.read_bytes())

        # Act
        result = load_item(dest)

        # Assert
        assert isinstance(result.sections["fact_check"], Section)
        assert isinstance(result.sections["groomed"], GroomedData)

    def test_load_item_groomed_date(self, tmp_path: Path) -> None:
        """load_item populates GroomedData.date from the groomed section.

        date field in the groomed section must survive the YAML round-trip.
        """
        # Arrange
        src = _FIXTURES_DIR / "sample_item_groomed.yaml"
        dest = tmp_path / "groomed.yaml"
        dest.write_bytes(src.read_bytes())

        # Act
        result = load_item(dest)
        groomed = result.sections.get("groomed")

        # Assert
        assert isinstance(groomed, GroomedData)
        assert groomed.date == "2026-01-15"

    def test_load_item_groomed_subsections(self, tmp_path: Path) -> None:
        """load_item populates GroomedData.subsections from the groomed section.

        Subsection keys must match what was written in the fixture.
        """
        # Arrange
        src = _FIXTURES_DIR / "sample_item_groomed.yaml"
        dest = tmp_path / "groomed.yaml"
        dest.write_bytes(src.read_bytes())

        # Act
        result = load_item(dest)
        groomed = result.sections.get("groomed")

        # Assert
        assert isinstance(groomed, GroomedData)
        assert "Priority" in groomed.subsections
        assert "Impact" in groomed.subsections

    def test_load_item_struck_entry_struck_true(self, tmp_path: Path) -> None:
        """load_item sets Entry.struck=True for entries with struck=true in YAML.

        Struck entries must be identifiable so merge and render logic works.
        """
        # Arrange
        src = _FIXTURES_DIR / "sample_item_entries.yaml"
        dest = tmp_path / "entries.yaml"
        dest.write_bytes(src.read_bytes())

        # Act
        result = load_item(dest)
        sec = result.sections.get("fact_check")

        # Assert
        assert isinstance(sec, Section)
        struck_entries = [e for e in sec.entries if e.struck]
        assert len(struck_entries) == 1

    def test_load_item_struck_entry_struck_reason(self, tmp_path: Path) -> None:
        """load_item populates struck_reason for struck entries.

        struck_reason is required for _render_entry to produce a valid details block.
        """
        # Arrange
        src = _FIXTURES_DIR / "sample_item_entries.yaml"
        dest = tmp_path / "entries.yaml"
        dest.write_bytes(src.read_bytes())

        # Act
        result = load_item(dest)
        sec = result.sections.get("fact_check")

        # Assert
        assert isinstance(sec, Section)
        struck = next(e for e in sec.entries if e.struck)
        assert struck.struck_reason == "superseded by deeper investigation"

    def test_load_item_struck_entry_struck_at(self, tmp_path: Path) -> None:
        """load_item populates struck_at for struck entries.

        struck_at timestamp is required for the Entry model validator.
        """
        # Arrange
        src = _FIXTURES_DIR / "sample_item_entries.yaml"
        dest = tmp_path / "entries.yaml"
        dest.write_bytes(src.read_bytes())

        # Act
        result = load_item(dest)
        sec = result.sections.get("fact_check")

        # Assert
        assert isinstance(sec, Section)
        struck = next(e for e in sec.entries if e.struck)
        assert struck.struck_at == "2026-02-02T14:00:00Z"


# ---------------------------------------------------------------------------
# save_item
# ---------------------------------------------------------------------------


class TestSaveItem:
    """save_item: writes BacklogItem to a .yaml file."""

    def test_save_item_produces_readable_yaml(self, tmp_path: Path) -> None:
        """save_item writes YAML that ruamel.yaml can load without errors.

        The output must be valid YAML so load_item can read it back.
        """
        # Arrange
        from ruamel.yaml import YAML

        item = BacklogItem(
            title="Test save item",
            description="Checking save produces valid YAML.",
            priority="P2",
            item_type="Chore",
            status="open",
            added="2026-03-01",
        )
        dest = tmp_path / "saved.yaml"

        # Act
        save_item(item, dest)
        yaml = YAML(typ="safe")
        with dest.open(encoding="utf-8") as fh:
            data = yaml.load(fh)

        # Assert
        assert data is not None
        assert data["title"] == "Test save item"

    def test_save_item_writes_metadata_block(self, tmp_path: Path) -> None:
        """save_item writes the metadata sub-object into the YAML file.

        metadata.priority must be present in the serialised output.
        """
        # Arrange
        item = BacklogItem(title="Metadata test", priority="P0", item_type="Bug", status="open", added="2026-03-01")
        dest = tmp_path / "metadata.yaml"

        # Act
        save_item(item, dest)
        content = dest.read_text(encoding="utf-8")

        # Assert
        assert "priority: P0" in content

    def test_save_item_excludes_file_path(self, tmp_path: Path) -> None:
        """save_item does not write file_path to the YAML output.

        file_path is a runtime field and must not be persisted to disk.
        """
        # Arrange
        item = BacklogItem(title="Exclude test", file_path="/some/path/item.yaml")
        dest = tmp_path / "exclude.yaml"

        # Act
        save_item(item, dest)
        content = dest.read_text(encoding="utf-8")

        # Assert
        assert "file_path" not in content

    def test_save_item_excludes_skip(self, tmp_path: Path) -> None:
        """save_item does not write skip to the YAML output.

        skip is a runtime field derived from status and must not be persisted.
        """
        # Arrange
        item = BacklogItem(title="Skip exclude test", skip=False)
        dest = tmp_path / "skip_exclude.yaml"

        # Act
        save_item(item, dest)
        content = dest.read_text(encoding="utf-8")

        # Assert
        assert "skip:" not in content

    def test_save_item_with_md_file_path_auto_migrates_to_yaml(self, tmp_path: Path) -> None:
        """save_item auto-migrates when item.file_path ends with .md.

        When path is omitted and item.file_path is an .md path, save_item must
        write the .yaml file, rename the original .md to .md.bak, and update
        item.file_path to the .yaml path.
        """
        # Arrange
        md_path = tmp_path / "item.md"
        md_path.write_text("# placeholder", encoding="utf-8")
        item = BacklogItem(
            title="Auto-migrate test",
            description="Testing .md to .yaml auto-migration.",
            priority="P2",
            item_type="Chore",
            status="open",
            added="2026-03-31",
            file_path=str(md_path),
        )

        # Act
        save_item(item)

        # Assert — .yaml written
        yaml_path = tmp_path / "item.yaml"
        assert yaml_path.exists(), f"Expected {yaml_path} to exist after auto-migration"
        # Assert — .md.bak created
        bak_path = tmp_path / "item.md.bak"
        assert bak_path.exists(), f"Expected {bak_path} to exist after auto-migration"
        # Assert — item.file_path updated to .yaml
        assert item.file_path == str(yaml_path.resolve())

    def test_save_item_with_yaml_file_path_writes_to_same_path(self, tmp_path: Path) -> None:
        """save_item writes to item.file_path when it ends with .yaml and path is None.

        No renaming should occur; item.file_path is updated to the resolved path.
        """
        # Arrange
        yaml_path = tmp_path / "item.yaml"
        item = BacklogItem(
            title="Yaml path test",
            description="Direct .yaml path.",
            priority="P1",
            item_type="Feature",
            status="open",
            added="2026-03-31",
            file_path=str(yaml_path),
        )

        # Act
        save_item(item)

        # Assert — file written
        assert yaml_path.exists(), f"Expected {yaml_path} to exist"
        # Assert — item.file_path updated to resolved path
        assert item.file_path == str(yaml_path.resolve())
        # Assert — no stray .bak file
        assert not (tmp_path / "item.yaml.bak").exists()

    def test_save_item_with_no_path_and_no_file_path_raises(self) -> None:
        """save_item raises ValueError when path is None and item.file_path is empty.

        Fail-fast: the caller must supply a write destination.
        """
        # Arrange
        item = BacklogItem(
            title="No path test",
            description="Item with no file_path.",
            priority="P3",
            item_type="Chore",
            status="open",
            added="2026-03-31",
            file_path="",
        )

        # Act / Assert
        with pytest.raises(ValueError, match="file_path is empty"):
            save_item(item)


# ---------------------------------------------------------------------------
# Round-trip: load → save → load
# ---------------------------------------------------------------------------


class TestRoundTrip:
    """Round-trip: load_item → save_item → load_item preserves field equality."""

    def test_round_trip_title(self, tmp_path: Path) -> None:
        """Round-trip preserves the item title.

        Title must be equal before save and after reload for correct display.
        """
        # Arrange
        src = _FIXTURES_DIR / "sample_item_groomed.yaml"
        path1 = tmp_path / "original.yaml"
        path2 = tmp_path / "roundtrip.yaml"
        path1.write_bytes(src.read_bytes())
        original = load_item(path1)

        # Act
        save_item(original, path2)
        reloaded = load_item(path2)

        # Assert
        assert reloaded.title == original.title

    def test_round_trip_priority(self, tmp_path: Path) -> None:
        """Round-trip preserves the metadata priority.

        Priority drives issue labelling and must survive save/load.
        """
        # Arrange
        src = _FIXTURES_DIR / "sample_item_groomed.yaml"
        path1 = tmp_path / "original.yaml"
        path2 = tmp_path / "roundtrip.yaml"
        path1.write_bytes(src.read_bytes())
        original = load_item(path1)

        # Act
        save_item(original, path2)
        reloaded = load_item(path2)

        # Assert
        assert reloaded.priority == original.priority

    def test_round_trip_section_keys(self, tmp_path: Path) -> None:
        """Round-trip preserves the set of section keys.

        All four section types (fact_check, rt_ica, issue_classification, groomed)
        must be present after the round-trip.
        """
        # Arrange
        src = _FIXTURES_DIR / "sample_item_groomed.yaml"
        path1 = tmp_path / "original.yaml"
        path2 = tmp_path / "roundtrip.yaml"
        path1.write_bytes(src.read_bytes())
        original = load_item(path1)

        # Act
        save_item(original, path2)
        reloaded = load_item(path2)

        # Assert
        assert set(reloaded.sections.keys()) == set(original.sections.keys())

    def test_round_trip_groomed_date(self, tmp_path: Path) -> None:
        """Round-trip preserves the GroomedData date.

        Groomed date is displayed in the GitHub issue body and must not change.
        """
        # Arrange
        src = _FIXTURES_DIR / "sample_item_groomed.yaml"
        path1 = tmp_path / "original.yaml"
        path2 = tmp_path / "roundtrip.yaml"
        path1.write_bytes(src.read_bytes())
        original = load_item(path1)
        original_groomed = original.sections["groomed"]

        # Act
        save_item(original, path2)
        reloaded = load_item(path2)
        reloaded_groomed = reloaded.sections["groomed"]

        # Assert
        assert isinstance(original_groomed, GroomedData)
        assert isinstance(reloaded_groomed, GroomedData)
        assert reloaded_groomed.date == original_groomed.date

    def test_round_trip_struck_entry_state(self, tmp_path: Path) -> None:
        """Round-trip preserves struck entry state.

        A struck entry must still be struck and have the same struck_reason after reload.
        """
        # Arrange
        src = _FIXTURES_DIR / "sample_item_entries.yaml"
        path1 = tmp_path / "original.yaml"
        path2 = tmp_path / "roundtrip.yaml"
        path1.write_bytes(src.read_bytes())
        original = load_item(path1)

        # Act
        save_item(original, path2)
        reloaded = load_item(path2)

        # Assert
        original_sec = original.sections["fact_check"]
        reloaded_sec = reloaded.sections["fact_check"]
        assert isinstance(original_sec, Section)
        assert isinstance(reloaded_sec, Section)
        orig_struck = next(e for e in original_sec.entries if e.struck)
        reload_struck = next(e for e in reloaded_sec.entries if e.struck)
        assert reload_struck.struck is True
        assert reload_struck.struck_reason == orig_struck.struck_reason
        assert reload_struck.struck_at == orig_struck.struck_at


# ---------------------------------------------------------------------------
# load_item — legacy .md files
# ---------------------------------------------------------------------------

_LEGACY_MD_TEXT = """\
---
name: Legacy Test Item
description: A legacy description for migration.
metadata:
  source: legacy-source
  added: '2026-01-01'
  priority: P1
  type: Feature
  status: open
---
Body content from legacy format.
"""


class TestLoadItemLegacyMd:
    """load_item: legacy .md files delegate to parse_item_file with DeprecationWarning."""

    def test_load_item_md_returns_backlog_item(self, tmp_path: Path) -> None:
        """load_item returns a BacklogItem when loading a .md file.

        Legacy files must still produce a usable BacklogItem for migration.
        """
        # Arrange
        path = tmp_path / "item.md"
        path.write_text(_LEGACY_MD_TEXT, encoding="utf-8")

        # Act
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = load_item(path)

        # Assert
        assert isinstance(result, BacklogItem)

    def test_load_item_md_emits_deprecation_warning(self, tmp_path: Path) -> None:
        """load_item emits DeprecationWarning when loading a legacy .md file.

        The warning is the migration signal — consumers must see it to know
        the item needs conversion.
        """
        # Arrange
        path = tmp_path / "item.md"
        path.write_text(_LEGACY_MD_TEXT, encoding="utf-8")

        # Act / Assert
        with pytest.warns(DeprecationWarning, match="legacy .md format"):
            load_item(path)

    def test_load_item_md_title_from_parse_item_file(self, tmp_path: Path) -> None:
        """load_item .md path returns BacklogItem with title from parse_item_file.

        parse_item_file is the real legacy parser — title must come from it.
        """
        # Arrange
        path = tmp_path / "item.md"
        path.write_text(_LEGACY_MD_TEXT, encoding="utf-8")

        # Act
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = load_item(path)

        # Assert
        assert result.title == "Legacy Test Item"

    def test_load_item_md_file_path_set(self, tmp_path: Path) -> None:
        """load_item .md path sets file_path on the returned item.

        file_path must be set regardless of file format for downstream use.
        """
        # Arrange
        path = tmp_path / "item.md"
        path.write_text(_LEGACY_MD_TEXT, encoding="utf-8")

        # Act
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = load_item(path)

        # Assert
        assert result.file_path == str(path.resolve())


# ---------------------------------------------------------------------------
# load_item_text
# ---------------------------------------------------------------------------

_YAML_TEXT = """\
title: In-memory item
description: Loaded from text without disk I/O.
type_: ''
section: ''
metadata:
  source: test
  added: '2026-03-10'
  priority: P2
  item_type: Docs
  status: open
  issue: ''
  last_synced: ''
  groomed: ''
  plan: ''
  topic: ''
  research_first: ''
  files: ''
  suggested_location: ''
sections: {}
"""


class TestLoadItemText:
    """load_item_text: parses BacklogItem from in-memory string."""

    def test_load_item_text_yaml_returns_backlog_item(self) -> None:
        """load_item_text with .yaml suffix returns a BacklogItem.

        The path suffix drives format detection; no disk read occurs.
        """
        # Arrange
        path = Path("/fake/item.yaml")

        # Act
        result = load_item_text(_YAML_TEXT, path)

        # Assert
        assert isinstance(result, BacklogItem)

    def test_load_item_text_yaml_title_field(self) -> None:
        """load_item_text populates the title from the YAML content string.

        Correct field mapping through model_validate must work without file I/O.
        """
        # Arrange
        path = Path("/fake/item.yaml")

        # Act
        result = load_item_text(_YAML_TEXT, path)

        # Assert
        assert result.title == "In-memory item"

    def test_load_item_text_yaml_priority_field(self) -> None:
        """load_item_text populates priority from the YAML content string.

        Priority must be read from the metadata block in the YAML text.
        """
        # Arrange
        path = Path("/fake/item.yaml")

        # Act
        result = load_item_text(_YAML_TEXT, path)

        # Assert
        assert result.priority == "P2"

    def test_load_item_text_yaml_sets_file_path_to_path_str(self) -> None:
        """load_item_text sets file_path to str(path), not a resolved path.

        load_item_text uses str(path) directly (no disk access), while
        load_item uses str(path.resolve()). Both are valid for their context.
        """
        # Arrange
        path = Path("/fake/item.yaml")

        # Act
        result = load_item_text(_YAML_TEXT, path)

        # Assert
        assert result.file_path == str(path)

    def test_load_item_text_md_delegates_to_parse_item_file(self) -> None:
        """load_item_text with .md suffix delegates to parse_item_file.

        The path suffix must select legacy parsing without any disk read.
        """
        # Arrange
        path = Path("/fake/item.md")

        # Act — parse_item_file is NOT mocked (integration fidelity requirement)
        result = load_item_text(_LEGACY_MD_TEXT, path)

        # Assert
        assert isinstance(result, BacklogItem)
        assert result.title == "Legacy Test Item"

    def test_load_item_text_md_sets_file_path_to_path_str(self) -> None:
        """load_item_text .md path sets file_path to str(path).

        file_path must be set for legacy format items loaded in-memory.
        """
        # Arrange
        path = Path("/fake/legacy.md")

        # Act
        result = load_item_text(_LEGACY_MD_TEXT, path)

        # Assert
        assert result.file_path == str(path)

    def test_load_item_text_unsupported_suffix_raises(self) -> None:
        """load_item_text raises ValueError for unsupported file suffix.

        detect_format is called internally; .txt must propagate as ValueError.
        """
        # Arrange
        path = Path("/fake/item.txt")

        # Act / Assert
        with pytest.raises(ValueError, match="Unsupported file extension"):
            load_item_text(_YAML_TEXT, path)
