"""Tests for backlog_core.github_sync — render, parse, and merge operations."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure backlog_core is importable from the plugin root
_PLUGIN_ROOT = Path(__file__).parent.parent
if str(_PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(_PLUGIN_ROOT))

from backlog_core import rendering as _rendering
from backlog_core.github_sync import merge_item, parse_issue_body, render_issue_body
from backlog_core.models import BacklogItem, Entry, GroomedData, Section
from backlog_core.operations import _normalize_section_key
from backlog_core.parsing import extract_sections
from hypothesis import HealthCheck, example, given, settings, strategies as st

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_item(
    *,
    title: str = "Test Item",
    description: str = "A test description.",
    priority: str = "P1",
    item_type: str = "Feature",
    status: str = "open",
    added: str = "2026-01-01",
    sections: dict | None = None,
) -> BacklogItem:
    """Build a BacklogItem for use in tests."""
    return BacklogItem(
        title=title,
        description=description,
        priority=priority,
        item_type=item_type,
        status=status,
        added=added,
        sections=sections or {},
    )


# ---------------------------------------------------------------------------
# render_issue_body — metadata block
# ---------------------------------------------------------------------------


class TestRenderIssueBodyMetadata:
    """render_issue_body: metadata HTML comment block."""

    def test_render_metadata_comment_present(self) -> None:
        """render_issue_body output contains the backlog-metadata comment block."""
        item = _make_item(priority="P0", item_type="Bug", status="open", added="2026-03-01")
        body = render_issue_body(item)
        assert "<!-- backlog-metadata:" in body
        assert "-->" in body

    def test_render_metadata_priority_field(self) -> None:
        """render_issue_body embeds priority in the metadata comment."""
        item = _make_item(priority="P0")
        body = render_issue_body(item)
        assert "priority: P0" in body

    def test_render_metadata_type_field(self) -> None:
        """render_issue_body embeds type in the metadata comment."""
        item = _make_item(item_type="Bug")
        body = render_issue_body(item)
        assert "type: Bug" in body

    def test_render_metadata_status_field(self) -> None:
        """render_issue_body embeds status in the metadata comment."""
        item = _make_item(status="in-progress")
        body = render_issue_body(item)
        assert "status: in-progress" in body

    def test_render_metadata_added_field(self) -> None:
        """render_issue_body embeds added date in the metadata comment."""
        item = _make_item(added="2026-03-15")
        body = render_issue_body(item)
        assert "added: 2026-03-15" in body


# ---------------------------------------------------------------------------
# render_issue_body — groomed section
# ---------------------------------------------------------------------------


class TestRenderIssueBodyGroomed:
    """render_issue_body: GroomedData section rendering."""

    def test_render_groomed_heading(self) -> None:
        """render_issue_body renders GroomedData with ## Groomed (date) heading."""
        groomed = GroomedData(date="2026-03-01", subsections={"Priority": "High"})
        item = _make_item(sections={"groomed": groomed})
        body = render_issue_body(item)
        assert "## Groomed (2026-03-01)" in body

    def test_render_groomed_subsection_as_h3(self) -> None:
        """render_issue_body renders GroomedData subsections as ### headings."""
        groomed = GroomedData(date="2026-03-01", subsections={"Priority": "High", "Impact": "Major"})
        item = _make_item(sections={"groomed": groomed})
        body = render_issue_body(item)
        assert "### Priority" in body
        assert "### Impact" in body

    def test_render_groomed_subsection_content(self) -> None:
        """render_issue_body includes subsection content under each ### heading."""
        groomed = GroomedData(date="2026-03-01", subsections={"Priority": "Critical path item."})
        item = _make_item(sections={"groomed": groomed})
        body = render_issue_body(item)
        assert "Critical path item." in body

    def test_render_groomed_canonical_order(self) -> None:
        """render_issue_body emits canonical subsections before extra ones."""
        groomed = GroomedData(
            date="2026-03-01",
            subsections={
                "Zebra": "last alphabetically",
                "Priority": "first canonically",
                "Impact": "second canonically",
            },
        )
        item = _make_item(sections={"groomed": groomed})
        body = render_issue_body(item)
        priority_pos = body.index("### Priority")
        impact_pos = body.index("### Impact")
        zebra_pos = body.index("### Zebra")
        assert priority_pos < impact_pos < zebra_pos


# ---------------------------------------------------------------------------
# render_issue_body — struck entries
# ---------------------------------------------------------------------------


class TestRenderIssueBodyStruckEntries:
    """render_issue_body: struck entry rendering."""

    def test_render_struck_entry_details_wrapper(self) -> None:
        """render_issue_body wraps struck entries in <details><summary> block."""
        struck_entry = Entry(
            id="2026-01-01T10:00:00Z",
            content="old content",
            struck=True,
            struck_at="2026-01-02T10:00:00Z",
            struck_reason="superseded",
        )
        section = Section(entries=[struck_entry])
        item = _make_item(sections={"fact_check": section})
        body = render_issue_body(item)
        assert "<details>" in body
        assert "<summary>" in body
        assert "struck: 2026-01-02T10:00:00Z — superseded" in body

    def test_render_struck_entry_summary_format(self) -> None:
        """render_issue_body struck summary contains struck_at and struck_reason."""
        struck_entry = Entry(
            id="2026-01-01T10:00:00Z",
            content="fact content",
            struck=True,
            struck_at="2026-01-05T08:00:00Z",
            struck_reason="outdated",
        )
        section = Section(entries=[struck_entry])
        item = _make_item(sections={"rt_ica": section})
        body = render_issue_body(item)
        assert "struck: 2026-01-05T08:00:00Z — outdated" in body

    def test_render_active_entry_no_details_wrapper(self) -> None:
        """render_issue_body active entries are NOT wrapped in <details>."""
        active_entry = Entry(id="2026-01-01T10:00:00Z", content="current analysis")
        section = Section(entries=[active_entry])
        item = _make_item(sections={"fact_check": section})
        body = render_issue_body(item)
        assert "<details>" not in body
        assert "current analysis" in body


# ---------------------------------------------------------------------------
# parse_issue_body — round-trip
# ---------------------------------------------------------------------------


class TestParseIssueBodyRoundTrip:
    """parse_issue_body(render_issue_body(item)) round-trips correctly."""

    def test_round_trip_entry_count(self) -> None:
        """Round-trip preserves entry count in entry-bearing sections."""
        entries = [
            Entry(id="2026-01-01T10:00:00Z", content="entry one"),
            Entry(id="2026-01-02T10:00:00Z", content="entry two"),
        ]
        section = Section(entries=entries)
        item = _make_item(sections={"fact_check": section})
        parsed = parse_issue_body(render_issue_body(item))
        parsed_sec = parsed.sections.get("fact_check")
        assert isinstance(parsed_sec, Section)
        assert len(parsed_sec.entries) == 2

    def test_round_trip_entry_ids(self) -> None:
        """Round-trip preserves entry ids."""
        entries = [Entry(id="2026-01-01T10:00:00Z", content="alpha"), Entry(id="2026-01-03T12:00:00Z", content="beta")]
        section = Section(entries=entries)
        item = _make_item(sections={"rt_ica": section})
        parsed = parse_issue_body(render_issue_body(item))
        parsed_sec = parsed.sections.get("rt_ica")
        assert isinstance(parsed_sec, Section)
        parsed_ids = {e.id for e in parsed_sec.entries}
        assert "2026-01-01T10:00:00Z" in parsed_ids
        assert "2026-01-03T12:00:00Z" in parsed_ids

    def test_round_trip_groomed_subsection_keys(self) -> None:
        """Round-trip preserves GroomedData subsection keys."""
        groomed = GroomedData(
            date="2026-03-01", subsections={"Priority": "High", "Impact": "Major", "Benefits": "Efficiency"}
        )
        item = _make_item(sections={"groomed": groomed})
        parsed = parse_issue_body(render_issue_body(item))
        parsed_groomed = parsed.sections.get("groomed")
        assert isinstance(parsed_groomed, GroomedData)
        assert set(parsed_groomed.subsections.keys()) == {"Priority", "Impact", "Benefits"}

    def test_round_trip_metadata_priority(self) -> None:
        """Round-trip preserves priority from metadata comment."""
        item = _make_item(priority="P0", item_type="Bug", status="open", added="2026-01-10")
        parsed = parse_issue_body(render_issue_body(item))
        assert parsed.priority == "P0"

    def test_round_trip_metadata_type(self) -> None:
        """Round-trip preserves item type from metadata comment."""
        item = _make_item(item_type="Bug")
        parsed = parse_issue_body(render_issue_body(item))
        assert parsed.item_type == "Bug"

    def test_round_trip_description(self) -> None:
        """Round-trip preserves description text."""
        item = _make_item(description="Detailed description here.")
        parsed = parse_issue_body(render_issue_body(item))
        assert parsed.description == "Detailed description here."


# ---------------------------------------------------------------------------
# merge_item — struck wins over active
# ---------------------------------------------------------------------------


class TestMergeItemStruckWins:
    """merge_item: struck entry wins over active entry for the same id."""

    def test_local_struck_remote_active_keeps_struck(self) -> None:
        """When local has struck and remote has same id active, merged is struck."""
        eid = "2026-01-01T10:00:00Z"
        local_entries = [
            Entry(id=eid, content="fact", struck=True, struck_at="2026-01-02T00:00:00Z", struck_reason="wrong")
        ]
        remote_entries = [Entry(id=eid, content="fact")]
        local = _make_item(sections={"fact_check": Section(entries=local_entries)})
        remote = _make_item(sections={"fact_check": Section(entries=remote_entries)})
        merged = merge_item(local, remote)
        merged_sec = merged.sections.get("fact_check")
        assert isinstance(merged_sec, Section)
        assert len(merged_sec.entries) == 1
        assert merged_sec.entries[0].struck is True

    def test_remote_struck_local_active_keeps_struck(self) -> None:
        """When remote has struck and local has same id active, merged is struck."""
        eid = "2026-01-05T08:00:00Z"
        local_entries = [Entry(id=eid, content="claim")]
        remote_entries = [
            Entry(id=eid, content="claim", struck=True, struck_at="2026-01-06T00:00:00Z", struck_reason="debunked")
        ]
        local = _make_item(sections={"fact_check": Section(entries=local_entries)})
        remote = _make_item(sections={"fact_check": Section(entries=remote_entries)})
        merged = merge_item(local, remote)
        merged_sec = merged.sections.get("fact_check")
        assert isinstance(merged_sec, Section)
        assert merged_sec.entries[0].struck is True


# ---------------------------------------------------------------------------
# merge_item — unique remote entries preserved
# ---------------------------------------------------------------------------


class TestMergeItemUniqueEntries:
    """merge_item: entries unique to remote appear in merged result."""

    def test_remote_only_entry_preserved(self) -> None:
        """Entry present only in remote is included in merged result."""
        local_entries = [Entry(id="2026-01-01T10:00:00Z", content="local fact")]
        remote_entries = [
            Entry(id="2026-01-01T10:00:00Z", content="local fact"),
            Entry(id="2026-01-02T10:00:00Z", content="remote-only fact"),
        ]
        local = _make_item(sections={"fact_check": Section(entries=local_entries)})
        remote = _make_item(sections={"fact_check": Section(entries=remote_entries)})
        merged = merge_item(local, remote)
        merged_sec = merged.sections.get("fact_check")
        assert isinstance(merged_sec, Section)
        assert len(merged_sec.entries) == 2
        entry_ids = {e.id for e in merged_sec.entries}
        assert "2026-01-02T10:00:00Z" in entry_ids

    def test_local_only_entry_preserved(self) -> None:
        """Entry present only in local is included in merged result."""
        local_entries = [
            Entry(id="2026-01-01T10:00:00Z", content="local only"),
            Entry(id="2026-01-03T10:00:00Z", content="shared"),
        ]
        remote_entries = [Entry(id="2026-01-03T10:00:00Z", content="shared")]
        local = _make_item(sections={"rt_ica": Section(entries=local_entries)})
        remote = _make_item(sections={"rt_ica": Section(entries=remote_entries)})
        merged = merge_item(local, remote)
        merged_sec = merged.sections.get("rt_ica")
        assert isinstance(merged_sec, Section)
        assert len(merged_sec.entries) == 2


# ---------------------------------------------------------------------------
# merge_item — groomed subsection content
# ---------------------------------------------------------------------------


class TestMergeItemGroomed:
    """merge_item: groomed subsection with longer remote content is kept."""

    def test_longer_remote_subsection_wins(self) -> None:
        """Remote groomed subsection content replaces local when it is longer."""
        local_groomed = GroomedData(date="2026-03-01", subsections={"Priority": "High"})
        remote_groomed = GroomedData(
            date="2026-03-01", subsections={"Priority": "High — needs immediate attention due to customer SLA impact."}
        )
        local = _make_item(sections={"groomed": local_groomed})
        remote = _make_item(sections={"groomed": remote_groomed})
        merged = merge_item(local, remote)
        merged_groomed = merged.sections.get("groomed")
        assert isinstance(merged_groomed, GroomedData)
        assert "SLA impact" in merged_groomed.subsections.get("Priority", "")

    def test_longer_local_subsection_kept(self) -> None:
        """Local groomed subsection content is kept when it is longer than remote."""
        local_groomed = GroomedData(
            date="2026-03-01",
            subsections={"Impact": "Very significant — affects all downstream pipelines and reporting."},
        )
        remote_groomed = GroomedData(date="2026-03-01", subsections={"Impact": "Significant."})
        local = _make_item(sections={"groomed": local_groomed})
        remote = _make_item(sections={"groomed": remote_groomed})
        merged = merge_item(local, remote)
        merged_groomed = merged.sections.get("groomed")
        assert isinstance(merged_groomed, GroomedData)
        impact = merged_groomed.subsections.get("Impact", "")
        assert "downstream pipelines" in impact

    def test_remote_only_subsection_added(self) -> None:
        """Subsection present only in remote is included in merged result."""
        local_groomed = GroomedData(date="2026-03-01", subsections={"Priority": "High"})
        remote_groomed = GroomedData(
            date="2026-03-01", subsections={"Priority": "High", "Impact": "Remote-only impact."}
        )
        local = _make_item(sections={"groomed": local_groomed})
        remote = _make_item(sections={"groomed": remote_groomed})
        merged = merge_item(local, remote)
        merged_groomed = merged.sections.get("groomed")
        assert isinstance(merged_groomed, GroomedData)
        assert "Impact" in merged_groomed.subsections


# ---------------------------------------------------------------------------
# Import / circular-dependency check
# ---------------------------------------------------------------------------


class TestImportNoCycles:
    """github_sync.py imports do not create circular dependencies."""

    def test_importable(self) -> None:
        """github_sync module is importable without errors."""
        import backlog_core.github_sync  # ruff: ignore[unused-import]

    def test_public_functions_importable(self) -> None:
        """All three public functions are importable from backlog_core.github_sync."""
        from backlog_core.github_sync import merge_item, parse_issue_body, render_issue_body

        assert callable(render_issue_body)
        assert callable(parse_issue_body)
        assert callable(merge_item)

    def test_models_not_imported_from_github_sync(self) -> None:
        """models.py does not import from github_sync (no cycle)."""
        import sys

        # Reload models to inspect its import graph
        models_mod = sys.modules.get("backlog_core.models")
        if models_mod is not None:
            source_file = getattr(models_mod, "__file__", "") or ""
            content = Path(source_file).read_text(encoding="utf-8") if source_file else ""
            assert "github_sync" not in content, "models.py must not import github_sync"


# ---------------------------------------------------------------------------
# render_issue_body — empty description branch (line 145)
# ---------------------------------------------------------------------------


class TestRenderIssueBodyEmptyDescription:
    """render_issue_body: items with no description omit the Description section."""

    def test_render_no_description_omits_section(self) -> None:
        """render_issue_body with empty description does not include ## Description.

        When description is empty the Description heading must not appear so
        the rendered body stays clean and round-trippable.
        """
        # Arrange
        item = _make_item(description="")

        # Act
        body = render_issue_body(item)

        # Assert
        assert "## Description" not in body

    def test_render_with_description_includes_section(self) -> None:
        """render_issue_body with non-empty description includes ## Description.

        Contrasts with empty-description case to confirm the conditional branch.
        """
        # Arrange
        item = _make_item(description="A meaningful description.")

        # Act
        body = render_issue_body(item)

        # Assert
        assert "## Description" in body
        assert "A meaningful description." in body

    def test_render_empty_sections_no_section_headings(self) -> None:
        """render_issue_body with no sections and no description only has metadata.

        Items with no sections must render only the metadata comment block.
        Verifies the empty-sections branch in render_issue_body.
        """
        # Arrange
        item = _make_item(description="", sections={})

        # Act
        body = render_issue_body(item)

        # Assert
        assert "## Fact-Check" not in body
        assert "## RT-ICA" not in body
        assert "## Groomed" not in body


# ---------------------------------------------------------------------------
# parse_issue_body — no metadata block (line 179)
# ---------------------------------------------------------------------------


class TestParseIssueBodyNoMetadata:
    """parse_issue_body: body without backlog-metadata comment returns defaults."""

    def test_parse_body_without_metadata_comment(self) -> None:
        """parse_issue_body on body with no metadata comment returns BacklogItem.

        The metadata block is optional; missing it must not raise.
        """
        # Arrange
        body = "## Description\n\nSome plain description.\n"

        # Act
        result = parse_issue_body(body)

        # Assert
        assert isinstance(result, BacklogItem)

    def test_parse_body_without_metadata_uses_base_priority(self) -> None:
        """parse_issue_body with no metadata comment inherits existing priority.

        When metadata comment is absent, base.priority is used as-is.
        """
        # Arrange
        body = "## Description\n\nNo metadata here.\n"
        existing = _make_item(priority="P0")

        # Act
        result = parse_issue_body(body, existing)

        # Assert
        assert result.priority == "P0"

    def test_parse_metadata_block_with_non_matching_line(self) -> None:
        """parse_issue_body skips malformed lines in the metadata comment.

        Lines that do not match key: value format must be silently skipped.
        The metadata block regex requires matching lines — a blank or free-form
        line must not raise and must not pollute the result dict.
        """
        # Arrange — metadata block with a non-matching line
        body = (
            "<!-- backlog-metadata:\n"
            "priority: P2\n"
            "  \n"  # blank line inside block — no key:value
            "type: Feature\n"
            "-->\n\n"
            "## Description\n\nBody.\n"
        )

        # Act
        result = parse_issue_body(body)

        # Assert — valid lines still parse; blank line is skipped
        assert result.priority == "P2"
        assert result.item_type == "Feature"


# ---------------------------------------------------------------------------
# parse_issue_body — unknown heading skipped (line 250)
# ---------------------------------------------------------------------------


class TestParseIssueBodyUnknownHeading:
    """parse_issue_body: unknown ## headings are preserved under unknown__ keys."""

    def test_parse_unknown_heading_does_not_raise(self) -> None:
        """parse_issue_body preserves ## headings that are not in _HEADING_TO_KEY.

        Unknown headings must not raise and must be stored under ``unknown__``
        prefixed keys so content is not silently dropped. Uses headings
        confirmed absent from ``rendering.SECTION_HEADING`` (unlike "Story" and
        "Acceptance Criteria", which are registered canonical sections).
        """
        # Arrange
        body = (
            "<!-- backlog-metadata:\n"
            "priority: P1\n"
            "type: Feature\n"
            "status: open\n"
            "added: 2026-01-01\n"
            "-->\n\n"
            "## Migration Steps\n\nAs a developer.\n\n"
            "## Custom Analysis\n\n- [ ] Done\n"
        )

        # Act
        result = parse_issue_body(body)

        # Assert — no bare key; sections stored under unknown__ prefix
        assert isinstance(result, BacklogItem)
        assert "migration_steps" not in result.sections
        assert "custom_analysis" not in result.sections
        assert "unknown__migration_steps" in result.sections
        assert "unknown__custom_analysis" in result.sections

    def test_parse_unregistered_groomed_heading_does_not_collide_with_groomed_section(self) -> None:
        """A bare '## Groomed' heading (no date parens) is an unregistered section, not GroomedData.

        Regression test for the fix that replaced a loose
        ``heading_name.startswith("Groomed")`` check with
        ``parsing._GROOMED_DATE_RE`` (requires a ``(date)`` suffix). An
        unregistered section stored under a
        key like ``"GROOMED"`` round-trips through ``unknown_key_to_heading`` to
        the display heading ``"Groomed"`` (title-cased, no parens) — identical
        text to what the loose check matched, misrouting it into
        ``_parse_groomed_section`` and producing a spurious ``GroomedData`` under
        the ``"groomed"`` key alongside the correct ``unknown__groomed`` key.
        """
        # Arrange — a heading identical to the unregistered-key fallback text,
        # with no date suffix, alongside a real canonical Groomed section.
        body = (
            "<!-- backlog-metadata:\n"
            "priority: P1\n"
            "type: Feature\n"
            "status: open\n"
            "added: 2026-01-01\n"
            "-->\n\n"
            "## Groomed\n\nUnrelated content that happens to share the fallback heading.\n\n"
            "## Groomed (2026-01-01)\n\n### Priority\n\nHigh priority.\n"
        )

        # Act
        result = parse_issue_body(body)

        # Assert — the bare heading is stored as an unknown section, not folded
        # into "groomed", and the real Groomed section still parses correctly.
        assert "unknown__groomed" in result.sections
        assert isinstance(result.sections["unknown__groomed"], Section)
        groomed = result.sections["groomed"]
        assert isinstance(groomed, GroomedData)
        assert groomed.date == "2026-01-01"
        assert groomed.subsections.get("Priority") == "High priority."

    def test_parse_issue_body_existing_carries_non_body_fields(self) -> None:
        """parse_issue_body with existing carries over title, issue, source, plan.

        Non-body fields from the existing item must appear in the returned item.
        """
        # Arrange
        body = "<!-- backlog-metadata:\npriority: P0\ntype: Bug\nstatus: open\nadded: 2026-01-01\n-->\n"
        existing = BacklogItem(
            title="My Existing Title", issue="#77", source="jira", plan="plan/task.yaml", file_path="/some/path.yaml"
        )

        # Act
        result = parse_issue_body(body, existing)

        # Assert
        assert result.title == "My Existing Title"
        assert result.issue == "#77"
        assert result.source == "jira"
        assert result.plan == "plan/task.yaml"
        assert result.file_path == "/some/path.yaml"


# ---------------------------------------------------------------------------
# merge_item — remote-only and local-only section keys (lines 359, 361)
# ---------------------------------------------------------------------------


class TestMergeItemSectionPresence:
    """merge_item: sections present only on one side are preserved."""

    def test_remote_only_section_added_to_merged(self) -> None:
        """merge_item includes a section that exists only in the remote item.

        When the remote has a section the local lacks, it must appear in the merged
        result so content added on GitHub is not lost.
        """
        # Arrange
        local = _make_item(sections={})
        remote_entries = [Entry(id="2026-01-01T10:00:00Z", content="remote only fact")]
        remote = _make_item(sections={"fact_check": Section(entries=remote_entries)})

        # Act
        merged = merge_item(local, remote)

        # Assert
        assert "fact_check" in merged.sections

    def test_local_only_section_kept_in_merged(self) -> None:
        """merge_item retains a section that exists only in the local item.

        Local-only sections must not be dropped during merge.
        """
        # Arrange
        local_entries = [Entry(id="2026-01-01T10:00:00Z", content="local only rt-ica")]
        local = _make_item(sections={"rt_ica": Section(entries=local_entries)})
        remote = _make_item(sections={})

        # Act
        merged = merge_item(local, remote)

        # Assert
        assert "rt_ica" in merged.sections


# ---------------------------------------------------------------------------
# merge_item — type mismatch branch (lines 367-369)
# ---------------------------------------------------------------------------


class TestMergeItemTypeMismatch:
    """merge_item: type mismatch between local and remote section uses local."""

    def test_type_mismatch_local_section_wins(self) -> None:
        """merge_item uses local value when local is Section and remote is GroomedData.

        When a key maps to incompatible types in local and remote, local is
        authoritative per the documented merge rules.
        """
        # Arrange
        local_entries = [Entry(id="2026-01-01T10:00:00Z", content="fact")]
        local_sec = Section(entries=local_entries)
        remote_groomed = GroomedData(date="2026-01-01", subsections={"Priority": "High"})
        local = _make_item(sections={"fact_check": local_sec})
        remote = _make_item(sections={"fact_check": remote_groomed})

        # Act
        merged = merge_item(local, remote)

        # Assert
        merged_sec = merged.sections.get("fact_check")
        assert isinstance(merged_sec, Section)
        assert len(merged_sec.entries) == 1


# ---------------------------------------------------------------------------
# _merge_entries — same struck state, longer content wins (AC11)
# ---------------------------------------------------------------------------


class TestMergeEntriesSameStruckState:
    """_merge_entries: same struck state — longer content wins; local wins on tie."""

    def test_longer_remote_content_wins_when_both_active(self) -> None:
        """_merge_entries picks remote entry when remote content is longer and both active.

        Used to reconcile GitHub edits that extend existing entries.
        """
        # Arrange
        eid = "2026-01-01T10:00:00Z"
        local_entries = [Entry(id=eid, content="short")]
        remote_entries = [Entry(id=eid, content="much longer remote content here")]
        local = _make_item(sections={"fact_check": Section(entries=local_entries)})
        remote = _make_item(sections={"fact_check": Section(entries=remote_entries)})

        # Act
        merged = merge_item(local, remote)
        sec = merged.sections.get("fact_check")

        # Assert
        assert isinstance(sec, Section)
        assert "much longer remote content here" in sec.entries[0].content

    def test_equal_content_local_wins_on_tie(self) -> None:
        """_merge_entries picks local entry when content lengths are equal.

        Local is authoritative on tie so idempotent merges are stable.
        """
        # Arrange
        eid = "2026-01-01T10:00:00Z"
        local_entries = [Entry(id=eid, content="same")]
        remote_entries = [Entry(id=eid, content="same")]
        local = _make_item(sections={"fact_check": Section(entries=local_entries)})
        remote = _make_item(sections={"fact_check": Section(entries=remote_entries)})

        # Act
        merged = merge_item(local, remote)
        sec = merged.sections.get("fact_check")

        # Assert — local wins on tie; both have "same" but we confirm no error
        assert isinstance(sec, Section)
        assert sec.entries[0].content == "same"


# ---------------------------------------------------------------------------
# _merge_groomed — local date authoritative, remote-only keys preserved (AC12)
# ---------------------------------------------------------------------------


class TestMergeGroomedDateAndKeys:
    """_merge_groomed: local date is authoritative; remote-only keys are preserved."""

    def test_local_date_is_authoritative(self) -> None:
        """merge_item uses local GroomedData.date even when remote has different date.

        The grooming date is set by the local author and must not be overwritten
        by GitHub content that may lag behind.
        """
        # Arrange
        local_groomed = GroomedData(date="2026-03-20", subsections={"Priority": "High"})
        remote_groomed = GroomedData(date="2026-03-01", subsections={"Priority": "High"})
        local = _make_item(sections={"groomed": local_groomed})
        remote = _make_item(sections={"groomed": remote_groomed})

        # Act
        merged = merge_item(local, remote)
        merged_groomed = merged.sections.get("groomed")

        # Assert
        assert isinstance(merged_groomed, GroomedData)
        assert merged_groomed.date == "2026-03-20"

    def test_remote_only_subsection_keys_preserved(self) -> None:
        """_merge_groomed keeps subsection keys that exist only in remote.

        Remote-only subsection keys must appear in the merged GroomedData so
        grooming content added on GitHub is not discarded.
        """
        # Arrange
        local_groomed = GroomedData(date="2026-03-01", subsections={"Priority": "High"})
        remote_groomed = GroomedData(
            date="2026-03-01", subsections={"Priority": "High", "Dependencies": "Needs auth module"}
        )
        local = _make_item(sections={"groomed": local_groomed})
        remote = _make_item(sections={"groomed": remote_groomed})

        # Act
        merged = merge_item(local, remote)
        merged_groomed = merged.sections.get("groomed")

        # Assert
        assert isinstance(merged_groomed, GroomedData)
        assert "Dependencies" in merged_groomed.subsections


# ---------------------------------------------------------------------------
# Unknown section preservation (A & B)
# ---------------------------------------------------------------------------


class TestUnknownSectionPreservation:
    """parse_issue_body preserves unknown sections; render_issue_body emits them."""

    def test_parse_unknown_section_stored_under_unknown_prefix(self) -> None:
        """parse_issue_body stores unknown ## headings under the unknown__ prefix.

        A heading not in _HEADING_TO_KEY must produce a key of the form
        ``unknown__{normalised}`` in BacklogItem.sections.
        """
        body = "## Custom Analysis\n\n<div><sub>2026-01-01T00:00:00Z</sub>\n\nSome insight.\n</div>\n"
        result = parse_issue_body(body)
        assert "unknown__custom_analysis" in result.sections
        sec = result.sections["unknown__custom_analysis"]
        assert isinstance(sec, Section)

    def test_parse_unknown_section_entry_content_preserved(self) -> None:
        """Entry content within an unknown section is parsed and preserved."""
        body = "## My Notes\n\n<div><sub>2026-03-01T10:00:00Z</sub>\n\nImportant note.\n</div>\n"
        result = parse_issue_body(body)
        sec = result.sections.get("unknown__my_notes")
        assert isinstance(sec, Section)
        assert len(sec.entries) == 1
        assert "Important note." in sec.entries[0].content

    def test_render_unknown_section_emits_heading(self) -> None:
        """render_issue_body emits ## heading for unknown sections.

        Sections stored under ``unknown__`` keys must be rendered so that the
        round-trip is symmetric.
        """
        entry = Entry(id="2026-03-01T00:00:00Z", content="analysis result")
        section = Section(entries=[entry])
        item = _make_item(sections={"unknown__custom_analysis": section})
        body = render_issue_body(item)
        assert "## Custom Analysis" in body
        assert "analysis result" in body

    def test_unknown_section_round_trip(self) -> None:
        """Unknown section survives parse → render → parse round-trip.

        An unknown section present after the first parse must still be present
        (same key, same entry count) after re-rendering and re-parsing.
        """
        # First parse: build from raw markdown. "Custom Analysis" is confirmed
        # absent from rendering.SECTION_HEADING (unlike "Impact Radius", now
        # registered), so this genuinely exercises the unknown__ fallback path.
        body = (
            "<!-- backlog-metadata:\n"
            "priority: P1\ntype: Feature\nstatus: open\nadded: 2026-01-01\n-->\n\n"
            "## Custom Analysis\n\n<div><sub>2026-03-01T00:00:00Z</sub>\n\nContent.\n</div>\n"
        )
        first_parsed = parse_issue_body(body)
        assert "unknown__custom_analysis" in first_parsed.sections

        # Re-render then re-parse
        rendered = render_issue_body(first_parsed)
        second_parsed = parse_issue_body(rendered, first_parsed)

        assert "unknown__custom_analysis" in second_parsed.sections
        sec = second_parsed.sections["unknown__custom_analysis"]
        assert isinstance(sec, Section)
        assert len(sec.entries) == 1

    def test_render_unknown_section_not_emitted_when_empty(self) -> None:
        """render_issue_body does not emit an empty unknown section.

        An unknown section with no entries must not produce a heading in the
        rendered output, consistent with how known sections behave.
        """
        empty_section = Section(entries=[])
        item = _make_item(sections={"unknown__ghost": empty_section})
        body = render_issue_body(item)
        assert "## Ghost" not in body

    def test_heading_spacing_normalised_to_underscores(self) -> None:
        """Multi-word unknown headings are stored with underscores, not spaces."""
        body = "## My Custom Section\n\n<div><sub>2026-01-01T00:00:00Z</sub>\n\ndata\n</div>\n"
        result = parse_issue_body(body)
        # Space-separated key must not appear
        assert "my_custom_section" not in result.sections
        assert "unknown__my_custom_section" in result.sections


# ---------------------------------------------------------------------------
# Regression: #2956 — local-write / GitHub-parse key-space mismatch
# ---------------------------------------------------------------------------


class TestSectionKeyRoundTripRegression:
    """#2956: local writes and GitHub-parsed sections must converge on one key.

    Before the fix, ``operations._normalize_section_key`` passed unrecognised
    section names through verbatim (e.g. ``"Files"``) while
    ``github_sync.parse_issue_body`` normalised the same heading, once parsed
    back from a rendered GitHub body, to ``"unknown__files"``. The two keys
    never collided, so every groom + reconcile cycle accumulated a duplicate
    section under the ``unknown__`` prefix.
    """

    def test_normalize_section_key_matches_parse_side_for_unregistered_names(self) -> None:
        """_normalize_section_key produces the same key parse_issue_body would.

        Reproduces the exact mismatch reported in #2956 at the unit level for
        names deliberately NOT registered in ``rendering.SECTION_HEADING``:
        before the fix, ``_normalize_section_key("Files") == "Files"`` while a
        GitHub round-trip of the same heading produced ``"unknown__files"`` —
        two different dict keys for one section. This proves the underlying
        write-path/parse-path fix works for ANY unregistered name, not just
        the specific ones later added to the registry as a display-quality
        improvement (see the next test).
        """
        for display_name, expected_key in [
            ("Custom Analysis", "unknown__custom_analysis"),
            ("Migration Steps", "unknown__migration_steps"),
            ("Root Cause Investigation Notes", "unknown__root_cause_investigation_notes"),
        ]:
            assert _normalize_section_key(display_name) == expected_key

    def test_normalize_section_key_resolves_registered_display_names(self) -> None:
        """Sections registered in SECTION_HEADING resolve to their clean canonical key.

        Canonical sections (the original 3, plus the commonly-observed set
        added for #2956/#2964 — see rendering.SECTION_HEADING) resolve to a
        clean snake_case key instead of falling through to the unknown__
        fallback. This is a display-quality property (storage key cleanliness),
        not the correctness fix — see the previous test for the property that
        actually prevents data loss, which holds regardless of registration.
        """
        assert _normalize_section_key("RT-ICA") == "rt_ica"
        assert _normalize_section_key("Fact-Check") == "fact_check"
        assert _normalize_section_key("Issue Classification") == "issue_classification"
        assert _normalize_section_key("Files") == "files"
        assert _normalize_section_key("Impact Radius") == "impact_radius"
        assert _normalize_section_key("Design Intent Alignment") == "design_intent_alignment"

    def test_normalize_section_key_display_lookup_is_case_insensitive(self) -> None:
        """The reverse display-value scan matches case-insensitively.

        Regression guard: the parse-side lookup (github_sync._HEADING_TO_KEY,
        keyed by ``heading.lower()``) is case-insensitive in both directions,
        but the write-side reverse scan previously compared ``display == name``
        exactly — so ``_normalize_section_key("Story")`` resolved to ``"story"``
        while ``_normalize_section_key("story")`` fell through to
        ``"unknown__story"``. Both casings of a registered display name must
        resolve to the same canonical key.
        """
        assert _normalize_section_key("Story") == "story"
        assert _normalize_section_key("story") == "story"
        assert _normalize_section_key("STORY") == "story"
        assert _normalize_section_key("rt-ica") == "rt_ica"

    def test_custom_section_write_then_github_round_trip_does_not_duplicate(self) -> None:
        """A locally-written custom section survives render+parse+merge under one key.

        End-to-end reproduction of the #2956 duplication: write "Files" via the
        same normalisation `backlog_groom` uses, render to a GitHub body, parse
        that body back (simulating a reconcile), and merge. Only one section
        key must exist afterward.
        """
        key = _normalize_section_key("Files")
        item = _make_item(sections={key: Section(entries=[Entry(id="2026-01-01T00:00:00Z", content="src/app.py")])})

        rendered = render_issue_body(item)
        remote = parse_issue_body(rendered, item)
        merged = merge_item(item, remote)

        assert list(merged.sections.keys()) == [key]

    def test_unregistered_section_write_then_github_round_trip_preserves_content(self) -> None:
        """A section name NOT in SECTION_HEADING still round-trips losslessly.

        Explicit demonstration (requested for #2956/#2964) that the fix is a
        general write-path/parse-path key-derivation guarantee, not something
        that only works for the specific names later added to
        rendering.SECTION_HEADING as a display-quality improvement. Uses
        "Root Cause Investigation Notes" — confirmed absent from
        SECTION_HEADING — for both the key AND the content round trip.
        """
        heading = "Root Cause Investigation Notes"
        key = _normalize_section_key(heading)
        assert key not in _rendering.SECTION_HEADING, f"{heading!r} must stay unregistered for this test to be valid"

        content = "The root cause was traced to a stale cache entry."
        item = _make_item(sections={key: Section(entries=[Entry(id="2026-01-01T00:00:00Z", content=content)])})

        rendered = render_issue_body(item)
        assert "## Root Cause Investigation Notes" in rendered
        remote = parse_issue_body(rendered, item)
        merged = merge_item(item, remote)

        assert list(merged.sections.keys()) == [key]
        sec = merged.sections[key]
        assert isinstance(sec, Section)
        assert len(sec.entries) == 1
        assert sec.entries[0].content == content

    def test_fact_checker_verdict_with_embedded_claim_headings_stays_one_section(self) -> None:
        """A Fact-Check verdict quoting per-claim '## Claim N' headings does not fragment.

        Reproduces the #2956 per-claim fragmentation: a fact-checker verdict
        legitimately embeds ``## Claim N: "..."`` headings inside its own
        content. Before the fix, ``extract_sections`` could not tell those
        apart from real section boundaries, so a GitHub round-trip shattered
        one Fact-Check entry into N spurious ``unknown__claim_n...`` sections.
        """
        key = _normalize_section_key("Fact-Check")
        verdict = (
            '## Claim 1: "some claim"\n\nVERDICT: VERIFIED\n\n---\n\n## Claim 2: "another claim"\n\nVERDICT: REFUTED'
        )
        item = _make_item(sections={key: Section(entries=[Entry(id="2026-01-01T00:00:00Z", content=verdict)])})

        rendered = render_issue_body(item)
        remote = parse_issue_body(rendered, item)
        merged = merge_item(item, remote)

        assert list(merged.sections.keys()) == [key]
        sec = merged.sections[key]
        assert isinstance(sec, Section)
        assert len(sec.entries) == 1
        assert "Claim 1" in sec.entries[0].content
        assert "Claim 2" in sec.entries[0].content


class TestExtractSectionsEntryBoundary:
    """#2956: extract_sections must not split on '## ' lines inside an entry div."""

    def test_embedded_heading_inside_entry_div_is_not_a_new_section(self) -> None:
        """A '## ' line inside <div>...</div> entry content stays part of the section."""
        body = (
            "## Fact-Check\n\n"
            "<div><sub>2026-01-01T00:00:00Z</sub>\n\n"
            '## Claim 1: "something"\n\nVERDICT: VERIFIED\n'
            "</div>\n"
        )
        sections = extract_sections(body)
        assert list(sections.keys()) == ["## Fact-Check"]
        assert 'Claim 1: "something"' in sections["## Fact-Check"]

    def test_heading_after_entry_div_closes_is_still_a_new_section(self) -> None:
        """A '## ' line after the entry div closes is correctly treated as a boundary."""
        body = (
            "## Fact-Check\n\n"
            "<div><sub>2026-01-01T00:00:00Z</sub>\n\ncontent\n</div>\n\n"
            "## Resources\n\n"
            "<div><sub>2026-01-01T00:00:01Z</sub>\n\nmore content\n</div>\n"
        )
        sections = extract_sections(body)
        assert set(sections.keys()) == {"## Fact-Check", "## Resources"}

    def test_embedded_heading_after_nested_unrelated_div_stays_in_same_section(self) -> None:
        """A '## ' line is not a boundary even after a nested, unrelated <div>...</div> closes.

        Regression for a depth-tracking gap: stopping entry-block opacity at the
        *first* bare '</div>' line (rather than tracking balanced <div>/</div>
        nesting) would let this fake heading — which appears after an inner,
        unrelated div fragment closes — escape back into ordinary markdown
        parsing and fragment the section a second, different way.
        """
        body = (
            "## Fact-Check\n\n"
            "<div><sub>2026-01-01T00:00:00Z</sub>\n\n"
            "before\n<div>\nnested\n</div>\n\n"
            "## Claim 1: fake heading after inner div closes\n\nVERDICT: VERIFIED\n"
            "</div>\n"
        )
        sections = extract_sections(body)
        assert list(sections.keys()) == ["## Fact-Check"]
        assert "fake heading after inner div closes" in sections["## Fact-Check"]

    def test_embedded_heading_after_attributed_nested_div_stays_in_same_section(self) -> None:
        """A nested div with attributes (e.g. ``<div class="note">``) does not escape opacity.

        Regression for a literal-substring counting bug: ``line.count("<div>")``
        does not match an attributed opening tag like ``<div class="note">``,
        while ``line.count("</div>")`` still matches its close unconditionally.
        That asymmetry drove the nesting-depth counter negative and ended entry
        opacity one line early, letting a heading-lookalike line further down
        escape as a spurious section (#2964 follow-up).
        """
        body = (
            "## Fact-Check\n\n"
            "<div><sub>2026-01-01T00:00:00Z</sub>\n\n"
            'before\n<div class="note">inner note</div>\n\n'
            "## Claim 1: fake heading after attributed div closes\n\nVERDICT: VERIFIED\n"
            "</div>\n"
        )
        sections = extract_sections(body)
        assert list(sections.keys()) == ["## Fact-Check"]
        assert "fake heading after attributed div closes" in sections["## Fact-Check"]


# ---------------------------------------------------------------------------
# Property-based round trip: write -> render -> parse -> merge is lossless
# ---------------------------------------------------------------------------

# Balanced, individually well-formed adversarial fragments -- deliberately including
# heading-lookalike lines, nested <div> content, and code fences (the exact bug
# classes #2956 fixed). Each fragment keeps its own <div>/</div> tags balanced so a
# generated example never trips an unmatched tag in the separate, out-of-scope
# entry_blocks.find_entry_spans extent logic -- this property targets section-boundary
# detection, not entry-content extent matching. A "<div><sub>...</sub>...</div>"-shaped
# fragment (mimicking a literal nested entry marker) is deliberately excluded: it
# surfaced a real but distinct bug in entry_blocks.parse_entries's own entry-extent
# matching (filed as #2967), not in the section-boundary logic #2956 fixed.
_ADVERSARIAL_FRAGMENTS = st.sampled_from([
    "## Fake Heading Inside Content",
    "### Fake Subheading",
    "#### Even deeper fake heading",
    "<div>\nnested content\n</div>",
    "```python\nprint('fenced code fence lookalike')\n```",
    "~~~\nfenced with tildes\n~~~",
    "plain prose line",
])

_content_strategy = (
    st.lists(_ADVERSARIAL_FRAGMENTS, min_size=1, max_size=8).map("\n\n".join).map(str.strip).filter(lambda s: s != "")
)

_section_name_strategy = st.text(
    # Scoped to the realistic domain: printable ASCII letters/digits/punctuation,
    # matching how agents and humans actually name sections ("Files", "Fact-Check",
    # "Impact Radius"). Full-Unicode section names surfaced a real but narrow and
    # unrelated defect during development of this test: rendering.py's display-title
    # round trip (str.lower() / str.title()) is not idempotent for a handful of
    # Unicode characters with special-case title mappings (e.g. MICRO SIGN U+00B5 ->
    # title-cases to GREEK CAPITAL MU, a different codepoint) — filed separately as
    # #2966 rather than fixed here, since it is a distinct bug class (a Unicode
    # casing quirk) from what #2956 fixed (write-path vs. parse-path key mismatch).
    # Requiring at least one alphanumeric character, and excluding literal
    # underscores entirely, excludes another real but narrow and unrelated
    # defect this test surfaced: any name containing a literal underscore
    # (e.g. "_", "0_") round-trips through a different key each time, because
    # heading_to_unknown_key's space<->underscore substitution cannot distinguish
    # a literal underscore in the name from one it introduced itself — filed as
    # #2968 rather than fixed here (a real display name is always a readable
    # phrase and never contains a raw underscore, so this class of input is
    # unrealistic for what this function is actually used for).
    alphabet=st.characters(min_codepoint=32, max_codepoint=126, blacklist_characters="\n\r_"),
    min_size=1,
    max_size=40,
).filter(lambda s: any(c.isalnum() for c in s))


class TestSectionRoundTripProperty:
    """Property: write -> render -> parse -> merge is lossless for arbitrary section names/content.

    This is the guardrail #2956 exposed the absence of: nothing previously
    enforced that the local-write key derivation (``_normalize_section_key``)
    and the GitHub-parse key derivation (``parse_issue_body`` /
    ``extract_sections``) actually agree — they were two independently
    written functions that merely happened to be *expected* to match.
    Adversarial content deliberately includes ``## ``-prefixed lines, nested
    ``<div>`` fragments, and code fences so the property covers the exact bug
    classes #2956 fixed, not just the originally reported symptom.
    """

    @given(section_name=_section_name_strategy, content=_content_strategy)
    @settings(max_examples=200, suppress_health_check=[HealthCheck.function_scoped_fixture])
    # #3370 regression pin: ":EFFORT" -> "unknown__effort" -> heading "Effort"
    # -> re-resolves to canonical "effort" on reparse, duplicating the key.
    # Hypothesis doesn't reliably draw this case on its own; pin it explicitly.
    @example(section_name=":EFFORT", content="## Fake Heading Inside Content")
    def test_write_render_parse_round_trip_is_lossless(self, section_name: str, content: str) -> None:
        """A section written locally survives a GitHub render -> parse -> merge cycle intact.

        For any section name and any content (including adversarial content
        that looks like markdown structure), the derived storage key must be
        identical before and after the round trip, under one key only (no
        ``unknown__`` duplicate), and the entry content must be preserved.
        """
        key = _normalize_section_key(section_name)
        item = _make_item(sections={key: Section(entries=[Entry(id="2026-01-01T00:00:00Z", content=content)])})

        rendered = render_issue_body(item)
        remote = parse_issue_body(rendered, item)
        merged = merge_item(item, remote)

        assert list(merged.sections.keys()) == [key], (
            f"Key did not round-trip for section_name={section_name!r}: "
            f"expected [{key!r}], got {list(merged.sections.keys())!r}"
        )
        sec = merged.sections[key]
        assert isinstance(sec, Section)
        assert len(sec.entries) == 1
        assert sec.entries[0].content == content
