"""Tests for backlog_core.github_sync — render, parse, and merge operations."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure backlog_core is importable from the plugin root
_PLUGIN_ROOT = Path(__file__).parent.parent
if str(_PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(_PLUGIN_ROOT))

from backlog_core.github_sync import merge_item, parse_issue_body, render_issue_body
from backlog_core.models import BacklogItem, Entry, GroomedData, Section

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
        import backlog_core.github_sync  # noqa: F401

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
        prefixed keys so content is not silently dropped.
        """
        # Arrange
        body = (
            "<!-- backlog-metadata:\n"
            "priority: P1\n"
            "type: Feature\n"
            "status: open\n"
            "added: 2026-01-01\n"
            "-->\n\n"
            "## Story\n\nAs a developer.\n\n"
            "## Acceptance Criteria\n\n- [ ] Done\n"
        )

        # Act
        result = parse_issue_body(body)

        # Assert — no bare key; sections stored under unknown__ prefix
        assert isinstance(result, BacklogItem)
        assert "story" not in result.sections
        assert "acceptance_criteria" not in result.sections
        assert "unknown__story" in result.sections
        assert "unknown__acceptance_criteria" in result.sections

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
        # First parse: build from raw markdown
        body = (
            "<!-- backlog-metadata:\n"
            "priority: P1\ntype: Feature\nstatus: open\nadded: 2026-01-01\n-->\n\n"
            "## Impact Radius\n\n<div><sub>2026-03-01T00:00:00Z</sub>\n\nContent.\n</div>\n"
        )
        first_parsed = parse_issue_body(body)
        assert "unknown__impact_radius" in first_parsed.sections

        # Re-render then re-parse
        rendered = render_issue_body(first_parsed)
        second_parsed = parse_issue_body(rendered, first_parsed)

        assert "unknown__impact_radius" in second_parsed.sections
        sec = second_parsed.sections["unknown__impact_radius"]
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
