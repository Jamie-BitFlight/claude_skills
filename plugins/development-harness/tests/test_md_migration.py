"""Tests for parse_md_body_sections and the .md → BacklogItem → .yaml round-trip.

Verifies Gap 1 of P964: legacy .md body sections are parsed into
BacklogItem.sections so that a write/reload cycle preserves all content.
"""

from __future__ import annotations

from pathlib import Path

from backlog_core.models import GroomedData, Section
from backlog_core.parsing import parse_md_body_sections
from backlog_core.yaml_io import load_item_text, save_item

# ---------------------------------------------------------------------------
# Shared fixture bodies
# ---------------------------------------------------------------------------

_PLAIN_SECTIONS_BODY = """\
## Story

As a developer, I want to do X so that Y happens.

## Description

This is the description paragraph.

## Context

- **Source**: somewhere
- **Priority**: P1
"""

_ENTRY_BLOCK_BODY = """\
## RT-ICA

<div><sub>2026-03-22T01:51:03Z</sub>

RT-ICA Snapshot: Build agent-profile MCP tool
Conditions:
1. FastMCP API | AVAILABLE
Decision: APPROVED
</div>

## Fact-Check

<div><sub>2026-03-22T01:53:10Z</sub>

Claim 1: something VERIFIED
</div>
"""

_GROOMED_WITH_SUBSECTIONS_BODY = """\
## Groomed (2026-02-28)

### Priority

3/10 — Low priority.

### Scope

Build the thing.

### Acceptance Criteria

<div><sub>2026-03-22T01:55:03Z</sub>

- [ ] criterion 1
- [ ] criterion 2
</div>
"""

_DUPLICATE_HEADINGS_BODY = """\
## RT-ICA

<div><sub>2026-03-22T01:51:03Z</sub>

First RT-ICA entry.
</div>

## Groomed (2026-03-22)

### Priority

High

## RT-ICA

<div><sub>2026-03-22T01:56:35Z</sub>

Second RT-ICA entry — final assessment.
</div>
"""

_FULL_ITEM_MD = """\
---
name: Test migration item
description: A test item for migration.
metadata:
  source: test-session
  added: '2026-01-15'
  priority: P1
  type: Feature
  status: open
  issue: '#42'
  groomed: '2026-01-20'
---

## RT-ICA

<div><sub>2026-01-20T10:00:00Z</sub>

Snapshot: things look good.
AVAILABLE: 4, MISSING: 0
Decision: APPROVED
</div>

## Groomed (2026-01-20)

### Priority

7/10

### Scope

Implement the migration thing.

### Acceptance Criteria

<div><sub>2026-01-20T10:01:00Z</sub>

- [ ] round-trip works
- [ ] sections populated
</div>

## Impact Radius

Some impact notes here.
No entry blocks, just plain text.
"""

_FENCED_CODE_BODY = """\
## Description

Here is some code:

```python
## this looks like a heading but is inside a fence
def foo():
    pass
```

Real content after fence.
"""


# ---------------------------------------------------------------------------
# parse_md_body_sections — plain sections (no entry blocks)
# ---------------------------------------------------------------------------


def test_parse_md_body_sections_plain_sections_present() -> None:
    """Plain ## sections without entry blocks produce Section objects."""
    result = parse_md_body_sections(_PLAIN_SECTIONS_BODY)

    assert "story" in result
    assert "description" in result
    assert "context" in result


def test_parse_md_body_sections_plain_sections_are_section_type() -> None:
    """Plain-text sections become Section instances with one synthetic entry."""
    result = parse_md_body_sections(_PLAIN_SECTIONS_BODY)

    story = result["story"]
    assert isinstance(story, Section)
    assert len(story.entries) == 1


def test_parse_md_body_sections_plain_section_synthetic_id() -> None:
    """Synthetic entry id uses the supplied added_date."""
    result = parse_md_body_sections(_PLAIN_SECTIONS_BODY, added_date="2026-01-15")

    story = result["story"]
    assert isinstance(story, Section)
    assert story.entries[0].id == "2026-01-15T00:00:00Z"


def test_parse_md_body_sections_plain_section_content_preserved() -> None:
    """Section content is captured verbatim in the entry."""
    result = parse_md_body_sections(_PLAIN_SECTIONS_BODY)

    description = result["description"]
    assert isinstance(description, Section)
    assert "This is the description paragraph." in description.entries[0].content


# ---------------------------------------------------------------------------
# parse_md_body_sections — entry block sections
# ---------------------------------------------------------------------------


def test_parse_md_body_sections_entry_blocks_produce_entries() -> None:
    """Entry block HTML produces individual Entry objects, not a synthetic one."""
    result = parse_md_body_sections(_ENTRY_BLOCK_BODY)

    # Legacy .md headings like "## RT-ICA" are normalised to the canonical
    # underscore key "rt_ica" so they are visible to render_issue_body.
    rtica = result["rt_ica"]
    assert isinstance(rtica, Section)
    assert len(rtica.entries) == 1
    assert rtica.entries[0].id == "2026-03-22T01:51:03Z"


def test_parse_md_body_sections_entry_block_content_captured() -> None:
    """Entry content is the text inside the <div><sub> block."""
    result = parse_md_body_sections(_ENTRY_BLOCK_BODY)

    rtica = result["rt_ica"]
    assert isinstance(rtica, Section)
    assert "RT-ICA Snapshot" in rtica.entries[0].content


def test_parse_md_body_sections_multiple_entry_sections() -> None:
    """Multiple sections with entry blocks all land in the result."""
    result = parse_md_body_sections(_ENTRY_BLOCK_BODY)

    assert "rt_ica" in result
    assert "fact_check" in result


# ---------------------------------------------------------------------------
# parse_md_body_sections — Groomed section
# ---------------------------------------------------------------------------


def test_parse_md_body_sections_groomed_key_is_groomed() -> None:
    """## Groomed (date) heading maps to key 'groomed'."""
    result = parse_md_body_sections(_GROOMED_WITH_SUBSECTIONS_BODY)

    assert "groomed" in result


def test_parse_md_body_sections_groomed_is_groomeddata_type() -> None:
    """## Groomed section produces a GroomedData instance."""
    result = parse_md_body_sections(_GROOMED_WITH_SUBSECTIONS_BODY)

    groomed = result["groomed"]
    assert isinstance(groomed, GroomedData)


def test_parse_md_body_sections_groomed_date_extracted() -> None:
    """Date is extracted from the ## Groomed (YYYY-MM-DD) heading."""
    result = parse_md_body_sections(_GROOMED_WITH_SUBSECTIONS_BODY)

    groomed = result["groomed"]
    assert isinstance(groomed, GroomedData)
    assert groomed.date == "2026-02-28"


def test_parse_md_body_sections_groomed_subsections_present() -> None:
    """### subsections become GroomedData.subsections keys."""
    result = parse_md_body_sections(_GROOMED_WITH_SUBSECTIONS_BODY)

    groomed = result["groomed"]
    assert isinstance(groomed, GroomedData)
    assert "Priority" in groomed.subsections
    assert "Scope" in groomed.subsections
    assert "Acceptance Criteria" in groomed.subsections


def test_parse_md_body_sections_groomed_subsection_content_verbatim() -> None:
    """Subsection content is stored verbatim including any entry block HTML."""
    result = parse_md_body_sections(_GROOMED_WITH_SUBSECTIONS_BODY)

    groomed = result["groomed"]
    assert isinstance(groomed, GroomedData)
    ac = groomed.subsections["Acceptance Criteria"]
    assert "<div><sub>" in ac
    assert "- [ ] criterion 1" in ac


def test_parse_md_body_sections_groomed_plain_subsection_text() -> None:
    """Plain ### subsection (no entry blocks) stores text directly."""
    result = parse_md_body_sections(_GROOMED_WITH_SUBSECTIONS_BODY)

    groomed = result["groomed"]
    assert isinstance(groomed, GroomedData)
    assert "3/10" in groomed.subsections["Priority"]


# ---------------------------------------------------------------------------
# parse_md_body_sections — duplicate headings
# ---------------------------------------------------------------------------


def test_parse_md_body_sections_duplicate_headings_merged() -> None:
    """Duplicate ## headings are merged — entries from both are present."""
    result = parse_md_body_sections(_DUPLICATE_HEADINGS_BODY)

    rtica = result["rt_ica"]
    assert isinstance(rtica, Section)
    assert len(rtica.entries) == 2


def test_parse_md_body_sections_duplicate_headings_content_order() -> None:
    """Merged entries preserve document order: first occurrence, then second."""
    result = parse_md_body_sections(_DUPLICATE_HEADINGS_BODY)

    rtica = result["rt_ica"]
    assert isinstance(rtica, Section)
    assert rtica.entries[0].id == "2026-03-22T01:51:03Z"
    assert rtica.entries[1].id == "2026-03-22T01:56:35Z"


def test_parse_md_body_sections_duplicate_groomed_merged() -> None:
    """Duplicate ## Groomed sections merge subsections (later overwrites same key)."""
    body = """\
## Groomed (2026-01-01)

### Priority

Low

## Groomed (2026-02-01)

### Priority

High

### Scope

Big scope.
"""
    result = parse_md_body_sections(body)

    groomed = result["groomed"]
    assert isinstance(groomed, GroomedData)
    # Later occurrence wins for same key
    assert "High" in groomed.subsections["Priority"]
    # New key from second occurrence is present
    assert "Scope" in groomed.subsections


# ---------------------------------------------------------------------------
# parse_md_body_sections — fenced code block guard
# ---------------------------------------------------------------------------


def test_parse_md_body_sections_fenced_code_block_not_split() -> None:
    """## inside a fenced code block is not treated as a heading."""
    result = parse_md_body_sections(_FENCED_CODE_BODY)

    # Only "description" should be present; the ## inside the fence is not a section
    assert "description" in result
    # The heading-looking line inside the fence must NOT appear as a key
    assert "this looks like a heading but is inside a fence" not in result


def test_parse_md_body_sections_fenced_code_content_preserved() -> None:
    """Content after a fenced block is captured in the section entry."""
    result = parse_md_body_sections(_FENCED_CODE_BODY)

    description = result["description"]
    assert isinstance(description, Section)
    assert "Real content after fence." in description.entries[0].content


# ---------------------------------------------------------------------------
# parse_md_body_sections — empty body
# ---------------------------------------------------------------------------


def test_parse_md_body_sections_empty_body_returns_empty_dict() -> None:
    """Empty body produces an empty dict without raising."""
    result = parse_md_body_sections("")
    assert result == {}


def test_parse_md_body_sections_body_with_no_headings_returns_preamble() -> None:
    """Body text with no ## headings is preserved as a 'preamble' section (edge case 1)."""
    from backlog_core.models import Section

    result = parse_md_body_sections("Just some text with no headings.\n")
    assert "preamble" in result
    assert isinstance(result["preamble"], Section)
    assert result["preamble"].entries[0].content == "Just some text with no headings."


# ---------------------------------------------------------------------------
# parse_item_file wiring — sections populated on .md load
# ---------------------------------------------------------------------------


def test_parse_item_file_populates_sections() -> None:
    """parse_item_file wires body sections into BacklogItem.sections."""
    from backlog_core.parsing import parse_item_file

    path = Path("test-item.md")
    item = parse_item_file(_FULL_ITEM_MD, path)

    assert item.sections, "sections should be non-empty for item with body"


def test_parse_item_file_sections_has_groomed() -> None:
    """'groomed' key is present in sections when ## Groomed heading exists."""
    from backlog_core.parsing import parse_item_file

    path = Path("test-item.md")
    item = parse_item_file(_FULL_ITEM_MD, path)

    assert "groomed" in item.sections
    assert isinstance(item.sections["groomed"], GroomedData)


def test_parse_item_file_sections_has_rt_ica() -> None:
    """'rt_ica' key is present in sections when ## RT-ICA heading exists."""
    from backlog_core.parsing import parse_item_file

    path = Path("test-item.md")
    item = parse_item_file(_FULL_ITEM_MD, path)

    assert "rt_ica" in item.sections
    assert isinstance(item.sections["rt_ica"], Section)


def test_parse_item_file_existing_fields_unaffected() -> None:
    """Wiring body sections does not break existing frontmatter fields."""
    from backlog_core.parsing import parse_item_file

    path = Path("test-item.md")
    item = parse_item_file(_FULL_ITEM_MD, path)

    assert item.title == "Test migration item"
    assert item.priority == "P1"
    assert item.issue == "#42"
    assert item.status == "open"


# ---------------------------------------------------------------------------
# Round-trip: load_item_text(.md) → save_item(.yaml) → load_item_text(.yaml)
# ---------------------------------------------------------------------------


def test_roundtrip_sections_preserved(tmp_path: Path) -> None:
    """Sections present after .md load survive save/reload as .yaml."""
    md_path = Path("migration-item.md")
    item = load_item_text(_FULL_ITEM_MD, md_path)

    assert item.sections, "sections must be populated from .md body before round-trip"

    yaml_path = tmp_path / "migration-item.yaml"
    save_item(item, yaml_path)

    reloaded = load_item_text(yaml_path.read_text(encoding="utf-8"), yaml_path)

    assert reloaded.sections, "sections must survive save/reload cycle"
    assert set(reloaded.sections.keys()) == set(item.sections.keys())


def test_roundtrip_groomed_data_preserved(tmp_path: Path) -> None:
    """GroomedData (date + subsections) survives save/reload as .yaml."""
    md_path = Path("migration-item.md")
    item = load_item_text(_FULL_ITEM_MD, md_path)

    yaml_path = tmp_path / "migration-item.yaml"
    save_item(item, yaml_path)

    reloaded = load_item_text(yaml_path.read_text(encoding="utf-8"), yaml_path)

    groomed = reloaded.sections.get("groomed")
    assert isinstance(groomed, GroomedData)
    assert groomed.date == "2026-01-20"
    assert "Priority" in groomed.subsections
    assert "Scope" in groomed.subsections
    assert "Acceptance Criteria" in groomed.subsections


def test_roundtrip_section_entries_preserved(tmp_path: Path) -> None:
    """Section entries (id + content) survive save/reload as .yaml."""
    md_path = Path("migration-item.md")
    item = load_item_text(_FULL_ITEM_MD, md_path)

    yaml_path = tmp_path / "migration-item.yaml"
    save_item(item, yaml_path)

    reloaded = load_item_text(yaml_path.read_text(encoding="utf-8"), yaml_path)

    rtica = reloaded.sections.get("rt_ica")
    assert isinstance(rtica, Section)
    assert len(rtica.entries) == 1
    assert rtica.entries[0].id == "2026-01-20T10:00:00Z"
    assert "Snapshot: things look good." in rtica.entries[0].content


def test_roundtrip_plain_section_preserved(tmp_path: Path) -> None:
    """Plain-text section (no entry blocks) survives save/reload as .yaml."""
    md_path = Path("migration-item.md")
    item = load_item_text(_FULL_ITEM_MD, md_path)

    yaml_path = tmp_path / "migration-item.yaml"
    save_item(item, yaml_path)

    reloaded = load_item_text(yaml_path.read_text(encoding="utf-8"), yaml_path)

    impact = reloaded.sections.get("impact radius")
    assert isinstance(impact, Section)
    assert "Some impact notes here." in impact.entries[0].content


def test_roundtrip_frontmatter_fields_preserved(tmp_path: Path) -> None:
    """Frontmatter fields are unchanged after save/reload cycle."""
    md_path = Path("migration-item.md")
    item = load_item_text(_FULL_ITEM_MD, md_path)

    yaml_path = tmp_path / "migration-item.yaml"
    save_item(item, yaml_path)

    reloaded = load_item_text(yaml_path.read_text(encoding="utf-8"), yaml_path)

    assert reloaded.title == "Test migration item"
    assert reloaded.priority == "P1"
    assert reloaded.issue == "#42"
    assert reloaded.description == "A test item for migration."


def test_domain_model_identity_md_and_yaml_adapters_produce_equal_sections(tmp_path: Path) -> None:
    """Both storage adapters produce identical domain model sections.

    load_item(.md).sections == load_item(.yaml_written_from_same_source).sections
    verifies that the .md loader is a complete storage adapter — the domain
    model is identical regardless of which adapter read the source.
    """
    md_path = Path("identity-item.md")
    item_from_md = load_item_text(_FULL_ITEM_MD, md_path)

    yaml_path = tmp_path / "identity-item.yaml"
    save_item(item_from_md, yaml_path)

    item_from_yaml = load_item_text(yaml_path.read_text(encoding="utf-8"), yaml_path)

    # Section keys identical from both adapters
    assert set(item_from_md.sections.keys()) == set(item_from_yaml.sections.keys())

    # Deep equality: GroomedData subsection keys match
    groomed_md = item_from_md.sections.get("groomed")
    groomed_yaml = item_from_yaml.sections.get("groomed")
    assert isinstance(groomed_md, GroomedData)
    assert isinstance(groomed_yaml, GroomedData)
    assert groomed_md.date == groomed_yaml.date
    assert set(groomed_md.subsections.keys()) == set(groomed_yaml.subsections.keys())

    # Deep equality: Section entry ids match
    rtica_md = item_from_md.sections.get("rt_ica")
    rtica_yaml = item_from_yaml.sections.get("rt_ica")
    assert isinstance(rtica_md, Section)
    assert isinstance(rtica_yaml, Section)
    assert [e.id for e in rtica_md.entries] == [e.id for e in rtica_yaml.entries]
