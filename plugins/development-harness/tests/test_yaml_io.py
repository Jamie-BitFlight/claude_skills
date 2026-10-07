"""Consumer contracts for backlog YAML persistence and legacy readers."""

from __future__ import annotations

from pathlib import Path

import backlog_core.operations as ops
import pytest
from backlog_core.models import BacklogItem, Entry, GroomedData, Section
from backlog_core.yaml_io import detect_format, load_item, load_item_text, save_item
from ruamel.yaml import YAML

_FIXTURES_DIR = Path(__file__).parent / "fixtures"
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
_YAML_TEXT = """\
title: In-memory item
description: Loaded from text without disk I/O.
metadata:
  source: test
  added: '2026-03-10'
  priority: P2
  item_type: Docs
  status: open
sections: {}
"""


@pytest.mark.parametrize(("suffix", "expected"), [(".yaml", "yaml"), (".md", "legacy_md")])
def test_detect_format_routes_supported_readers(suffix: str, expected: str) -> None:
    assert detect_format(Path(f"/items/item{suffix}")) == expected


@pytest.mark.parametrize("suffix", [".json", ".txt"])
def test_detect_format_rejects_unsupported_readers(suffix: str) -> None:
    with pytest.raises(ValueError, match="Unsupported file extension"):
        detect_format(Path(f"/items/item{suffix}"))


def test_load_item_reads_the_complete_basic_persisted_contract(tmp_path: Path) -> None:
    path = tmp_path / "item.yaml"
    path.write_bytes((_FIXTURES_DIR / "sample_item.yaml").read_bytes())

    item = load_item(path)

    assert item.title == "Add YAML-based backlog item storage"
    assert item.description == "Implement pure-YAML file I/O for backlog items to replace legacy markdown format."
    assert item.priority == "P1"
    assert item.file_path == str(path.resolve())
    assert item.sections == {}


def test_load_item_reads_typed_grooming_sections(tmp_path: Path) -> None:
    path = tmp_path / "groomed.yaml"
    path.write_bytes((_FIXTURES_DIR / "sample_item_groomed.yaml").read_bytes())

    item = load_item(path)

    assert set(item.sections) == {"fact_check", "rt_ica", "issue_classification", "groomed"}
    assert isinstance(item.sections["fact_check"], Section)
    groomed = item.sections["groomed"]
    assert isinstance(groomed, GroomedData)
    assert groomed.date == "2026-01-15"
    assert groomed.subsections["Priority"] == "High — needed for milestone 2 backlog migration."
    assert groomed.subsections["Impact"] == "All backlog operations will use pure YAML after this lands."


def test_load_item_reads_struck_entry_fields(tmp_path: Path) -> None:
    path = tmp_path / "entries.yaml"
    path.write_bytes((_FIXTURES_DIR / "sample_item_entries.yaml").read_bytes())

    section = load_item(path).sections["fact_check"]

    assert isinstance(section, Section)
    struck = next(entry for entry in section.entries if entry.struck)
    assert (struck.content, struck.struck_reason, struck.struck_at) == (
        "Original analysis before new findings.",
        "superseded by deeper investigation",
        "2026-02-02T14:00:00Z",
    )


def test_load_item_preserves_legacy_unknown_section_migration_rules(tmp_path: Path) -> None:
    path = tmp_path / "item.yaml"
    save_item(
        BacklogItem(
            sections={
                "unknown__story": Section(entries=[Entry(id="old", content="legacy")]),
                "story": Section(entries=[Entry(id="new", content="canonical")]),
                "unknown__custom_analysis": Section(entries=[]),
            }
        ),
        path,
    )

    sections = load_item(path).sections

    story = sections["story"]
    assert isinstance(story, Section)
    assert {entry.content for entry in story.entries} == {"legacy", "canonical"}
    assert "unknown__story" not in sections
    assert "unknown__custom_analysis" in sections


def test_load_item_migration_reaches_title_selector_view_consumers(tmp_path: Path) -> None:
    path = tmp_path / "item.yaml"
    save_item(
        BacklogItem(
            sections={
                "unknown__impact_radius": Section(entries=[Entry(content="plugins/foo.py")]),
                "unknown__files": Section(entries=[Entry(content="plugins/bar.py")]),
                "unknown__priority": Section(entries=[Entry(content="P1")]),
            }
        ),
        path,
    )

    sections = ops._build_sections_from_yaml_item(load_item(path))

    assert {"Impact Radius", "Files", "Priority"}.issubset(sections)
    assert not {"unknown__impact_radius", "unknown__files", "unknown__priority"}.intersection(sections)


def test_save_and_load_preserve_explicit_persisted_values_and_runtime_omissions(tmp_path: Path) -> None:
    path = tmp_path / "persisted.yaml"
    save_item(
        BacklogItem(
            title="Persisted title",
            description="first line\nsecond line",
            priority="P0",
            item_type="Bug",
            status="open",
            added="2026-03-01",
            file_path="/runtime/only.yaml",
            skip=True,
            sections={
                "fact_check": Section(
                    entries=[
                        Entry(
                            id="entry-1",
                            content="A struck durable entry",
                            struck=True,
                            struck_reason="replaced",
                            struck_at="2026-03-02T03:04:05Z",
                        )
                    ]
                ),
                "groomed": GroomedData(date="2026-03-03", subsections={"Impact": "high"}),
            },
        ),
        path,
    )

    persisted = YAML(typ="safe").load(path)
    reloaded = load_item(path)

    assert persisted["title"] == "Persisted title"
    assert persisted["description"] == "first line\nsecond line"
    assert persisted["metadata"]["priority"] == "P0"
    assert persisted["metadata"]["added"] == "2026-03-01"
    assert persisted["metadata"]["item_type"] == "Bug"
    assert persisted["metadata"]["status"] == "open"
    assert persisted["sections"]["groomed"] == {"date": "2026-03-03", "subsections": {"Impact": "high"}}
    assert "file_path" not in persisted
    assert "skip" not in persisted
    assert reloaded.title == "Persisted title"
    assert reloaded.description == "first line\nsecond line"
    assert reloaded.priority == "P0"
    assert (reloaded.added, reloaded.item_type, reloaded.status) == ("2026-03-01", "Bug", "open")
    groomed = reloaded.sections["groomed"]
    assert isinstance(groomed, GroomedData)
    assert (groomed.date, groomed.subsections) == ("2026-03-03", {"Impact": "high"})
    section = reloaded.sections["fact_check"]
    assert isinstance(section, Section)
    assert [
        (entry.id, entry.content, entry.struck, entry.struck_reason, entry.struck_at) for entry in section.entries
    ] == [("entry-1", "A struck durable entry", True, "replaced", "2026-03-02T03:04:05Z")]


def test_save_item_preserves_file_migration_and_destination_guards(tmp_path: Path) -> None:
    legacy = tmp_path / "item.md"
    legacy.write_text("# placeholder", encoding="utf-8")
    item = BacklogItem(title="Migrated", file_path=str(legacy))

    save_item(item)

    assert (tmp_path / "item.yaml").exists()
    assert (tmp_path / "item.md.bak").exists()
    assert item.file_path == str((tmp_path / "item.yaml").resolve())
    with pytest.raises(ValueError, match="file_path is empty"):
        save_item(BacklogItem())


def test_save_item_uses_a_yaml_destination_without_a_backup(tmp_path: Path) -> None:
    path = tmp_path / "item.yaml"
    item = BacklogItem(title="Direct YAML", file_path=str(path))

    save_item(item)

    assert item.file_path == str(path.resolve())
    assert not (tmp_path / "item.yaml.bak").exists()


def test_load_item_reads_legacy_file_with_its_migration_signal(tmp_path: Path) -> None:
    path = tmp_path / "item.md"
    path.write_text(_LEGACY_MD_TEXT, encoding="utf-8")

    with pytest.warns(DeprecationWarning, match="legacy .md format"):
        item = load_item(path)

    assert (item.title, item.file_path) == ("Legacy Test Item", str(path.resolve()))


def test_load_item_text_reads_yaml_without_resolving_its_caller_path() -> None:
    path = Path("/fake/item.yaml")

    item = load_item_text(_YAML_TEXT, path)

    assert (item.title, item.priority, item.file_path) == ("In-memory item", "P2", str(path))


@pytest.mark.parametrize(
    ("priority", "item_type", "status", "expected"),
    [
        ("IDEA", "Documentation", "resolved", ("Ideas", "Docs", "resolved")),
        ("critical", "Legacy Type", "legacy-status", ("critical", "Legacy Type", "legacy-status")),
    ],
)
def test_load_item_text_preserves_metadata_compatibility(
    priority: str, item_type: str, status: str, expected: tuple[str, str, str]
) -> None:
    text = f"""\
title: Compatibility item
metadata:
  added: '2026-03-10'
  priority: {priority}
  type: {item_type}
  status: {status}
  unknown_future_key: ignored
sections: {{}}
"""

    item = load_item_text(text, Path("/fake/compatibility.yaml"))

    assert (item.priority, item.item_type, item.status) == expected
    assert item.added == "2026-03-10"
    assert not hasattr(item.metadata, "unknown_future_key")


def test_load_item_text_reads_legacy_md_and_rejects_unknown_suffix() -> None:
    path = Path("/fake/item.md")

    item = load_item_text(_LEGACY_MD_TEXT, path)

    assert (item.title, item.file_path) == ("Legacy Test Item", str(path))
    with pytest.raises(ValueError, match="Unsupported file extension"):
        load_item_text(_YAML_TEXT, Path("/fake/item.txt"))
