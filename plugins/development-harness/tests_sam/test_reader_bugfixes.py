"""Regression tests for three confirmed silent data-loss bugs in the SAM migrate pipeline.

BUG-1: global_manifest — prose parallelize-with value drops tasks.
BUG-2: global_manifest — string-format tasks: entries silently dropped.
BUG-3: legacy_markdown — Unicode emoji-prefixed status values drop all tasks.

Tests: Each bug's previously-silent-drop now produces correct output.
How: Construct minimal in-memory inputs that reproduce the exact failure path,
     run the reader/normalizer pipeline, assert tasks survive with correct values.
Why: normalize_plan silently catches ValueError from individual task normalization
     and skips the task — without these tests, regressions are invisible.
"""

from __future__ import annotations

from textwrap import dedent
from typing import TYPE_CHECKING

import pytest
from sam_schema.readers.manifest_reader import _build_task_dict, _extract_bold_fields, read_manifest_plan
from sam_schema.readers.normalize import _normalize_status, normalize_plan

if TYPE_CHECKING:
    from pathlib import Path

# ---------------------------------------------------------------------------
# BUG-1: prose parallelize-with value should be parsed as empty list, not
#        stored as raw string that fails Task model ID-pattern validation.
# ---------------------------------------------------------------------------


class TestBug1ProseParallelizeWithDroppedTasks:
    """Verify that prose 'parallelize-with' values do not drop tasks.

    Tests: _extract_bold_fields maps 'can parallelize with' through
           _parse_dependency_value, not the raw-string else branch.
    How: Extract bold fields from prose containing the exact value observed in
         tasks-1-deduplicate-agents-phase4.md for T1.
    Why: Before the fix, the raw prose string reached Task model validation and
         raised ValueError, causing normalize_plan to silently skip the task.
    """

    def test_extract_bold_fields_prose_parallelize_with_returns_empty_list(self) -> None:
        """Prose 'nothing — T2 depends on this decision' maps to []."""
        prose = "**Can parallelize with**: nothing — T2 depends on this decision"
        result = _extract_bold_fields(prose)
        assert result["parallelize-with"] == []

    def test_extract_bold_fields_none_parallelize_with_returns_empty_list(self) -> None:
        """Plain 'none' value for parallelize-with maps to []."""
        prose = "**Can parallelize with**: none"
        result = _extract_bold_fields(prose)
        assert result["parallelize-with"] == []

    def test_extract_bold_fields_task_id_parallelize_with_preserved(self) -> None:
        """Valid task IDs in parallelize-with are preserved."""
        prose = "**Can parallelize with**: T3, T4"
        result = _extract_bold_fields(prose)
        assert result["parallelize-with"] == ["T3", "T4"]

    def test_task_with_prose_parallelize_with_survives_normalize_plan(self, tmp_path: Path) -> None:
        """Task with prose parallelize-with value is not dropped by normalize_plan."""
        # Minimal global_manifest plan file reproducing the T1 scenario
        content = dedent("""\
            ---
            slug: bug1-test
            version: "1.0"
            tasks:
              - T1: Decision gate task
            ---

            ## T1: Decision gate task

            **Status**: COMPLETE
            **Dependencies**: None
            **Priority**: 1
            **Complexity**: Low
            **Agent**: general-purpose
            **Skills**: []
            **Can parallelize with**: nothing — T2 depends on this decision
        """)
        plan_file = tmp_path / "tasks-1-bug1-test.md"
        plan_file.write_text(content, encoding="utf-8")

        plan_meta, task_dicts, fmt = read_manifest_plan(plan_file)
        result = normalize_plan(plan_meta, task_dicts, fmt, plan_file)

        assert len(result.plan.tasks) == 1, (
            f"Expected 1 task but got {len(result.plan.tasks)}. Gaps: {[g.actual for g in result.gaps]}"
        )
        assert result.plan.tasks[0].id == "T1"
        assert result.plan.tasks[0].parallelize_with == []


# ---------------------------------------------------------------------------
# BUG-2: string-format tasks: entries are silently dropped when the YAML
#        tasks list contains quoted strings "N.N: title" rather than dicts.
# ---------------------------------------------------------------------------


class TestBug2StringFormatTaskEntriesDropped:
    """Verify that string entries in tasks: list are parsed and retained.

    Tests: _build_task_dict handles str entries of form 'N.N: title text'.
    How: Call _build_task_dict directly with a string entry and with the full
         read_manifest_plan pipeline on a file reproducing the bug.
    Why: Before the fix, isinstance(entry, dict) guard returned None for strings,
         causing normalize_plan to receive an empty task list — 100% data loss.
    """

    def test_build_task_dict_string_entry_returns_task_dict(self) -> None:
        """String entry '1.1: Update some-file.md — note' is parsed correctly."""
        result = _build_task_dict("1.1: Update some-file.md — note", {})
        assert result is not None
        assert result["task"] == "1.1"
        assert result["title"] == "Update some-file.md — note"

    def test_build_task_dict_string_entry_without_colon_returns_none(self) -> None:
        """String entry with no colon cannot be parsed and returns None."""
        result = _build_task_dict("no colon here at all", {})
        assert result is None

    def test_build_task_dict_string_entry_defaults_status_to_not_started(self) -> None:
        """String entry without prose gets default status not-started."""
        result = _build_task_dict("T1: Some title", {})
        assert result is not None
        assert result["status"] == "not-started"

    def test_build_task_dict_non_string_non_dict_returns_none(self) -> None:
        """Non-string non-dict entry (e.g. integer) is still rejected."""
        result = _build_task_dict(42, {})
        assert result is None

    def test_string_format_tasks_survive_full_pipeline(self, tmp_path: Path) -> None:
        """All 3 string-format tasks in a global_manifest file are retained."""
        # Reproduces the tasks-24-research-freshness-delta.md structure
        content = dedent("""\
            ---
            feature: freshness-delta-test
            version: "1.0"
            tasks:
              - "1.1: Update entry-template.md — Freshness Tracking note"
              - "1.2: Update research-curator SKILL.md — Batch Mode"
              - "1.3: Integration verification — 6 acceptance criteria"
            ---

            # Task Plan: Freshness Delta Test
        """)
        plan_file = tmp_path / "tasks-24-freshness-delta-test.md"
        plan_file.write_text(content, encoding="utf-8")

        plan_meta, task_dicts, fmt = read_manifest_plan(plan_file)
        result = normalize_plan(plan_meta, task_dicts, fmt, plan_file)

        assert len(result.plan.tasks) == 3, (
            f"Expected 3 tasks but got {len(result.plan.tasks)}. Gaps: {[g.actual for g in result.gaps]}"
        )
        task_ids = [t.id for t in result.plan.tasks]
        assert "1.1" in task_ids
        assert "1.2" in task_ids
        assert "1.3" in task_ids


# ---------------------------------------------------------------------------
# BUG-3: Unicode emoji-prefixed status values drop all tasks in legacy_markdown
#        files that use ✅ COMPLETE instead of :white_check_mark: COMPLETE.
# ---------------------------------------------------------------------------


class TestBug3UnicodeEmojiStatusDroppedTasks:
    """Verify that Unicode emoji-prefixed status values are normalized correctly.

    Tests: _normalize_status strips leading Unicode emoji characters before lookup.
    How: Pass status strings with common Unicode emoji prefixes directly to
         _normalize_status, and run the full pipeline on a legacy_markdown file.
    Why: Before the fix, '✅ COMPLETE' failed all status lookups and raised
         ValueError, causing normalize_plan to silently drop every task.
    """

    def test_normalize_status_checkmark_emoji_complete(self) -> None:
        """✅ COMPLETE normalizes to 'complete'."""
        assert _normalize_status("✅ COMPLETE") == "complete"

    def test_normalize_status_checkmark_emoji_lowercase_complete(self) -> None:
        """✅ complete normalizes to 'complete'."""
        assert _normalize_status("✅ complete") == "complete"

    def test_normalize_status_x_emoji_not_started(self) -> None:
        """❌ NOT STARTED normalizes to 'not-started'."""
        assert _normalize_status("❌ NOT STARTED") == "not-started"

    def test_normalize_status_hourglass_in_progress(self) -> None:
        """⏳ IN PROGRESS normalizes to 'in-progress'."""
        assert _normalize_status("⏳ IN PROGRESS") == "in-progress"

    def test_normalize_status_without_emoji_still_works(self) -> None:
        """Existing non-emoji status values are unaffected."""
        assert _normalize_status("COMPLETE") == "complete"
        assert _normalize_status("not-started") == "not-started"
        assert _normalize_status(":white_check_mark: COMPLETE") == "complete"

    def test_normalize_status_unrecognized_raises_value_error(self) -> None:
        """Completely unrecognized status still raises ValueError."""
        with pytest.raises(ValueError, match="Unrecognized status"):
            _normalize_status("totally-invalid-status")

    def test_legacy_markdown_with_unicode_emoji_status_survives_normalize_plan(self, tmp_path: Path) -> None:
        """Tasks with ✅ COMPLETE status are not dropped by normalize_plan."""
        # Reproduces the pattern in tasks-17-backlog-mcp-migration.md
        from sam_schema.readers.legacy_reader import read_legacy_plan

        content = dedent("""\
            # Task Plan: Emoji Status Test

            ## Task 1: First task

            **Status**: ✅ COMPLETE
            **Priority**: 1
            **Complexity**: low
            **Agent**: general-purpose
            **Dependencies**: None

            ## Task 2: Second task

            **Status**: ✅ COMPLETE
            **Priority**: 2
            **Complexity**: low
            **Agent**: general-purpose
            **Dependencies**: Task 1
        """)
        plan_file = tmp_path / "tasks-99-emoji-status-test.md"
        plan_file.write_text(content, encoding="utf-8")

        plan_meta, task_dicts, fmt = read_legacy_plan(plan_file)
        result = normalize_plan(plan_meta, task_dicts, fmt, plan_file)

        assert len(result.plan.tasks) == 2, (
            f"Expected 2 tasks but got {len(result.plan.tasks)}. Gaps: {[g.actual for g in result.gaps]}"
        )
        statuses = {t.id: t.status for t in result.plan.tasks}
        assert statuses["1"] == "complete"
        assert statuses["2"] == "complete"
