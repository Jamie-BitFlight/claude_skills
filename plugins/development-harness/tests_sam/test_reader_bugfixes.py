"""Regression tests for confirmed silent data-loss bugs in the SAM migrate pipeline.

BUG-1: global_manifest — prose parallelize-with value drops tasks.
BUG-2: global_manifest — string-format tasks: entries silently dropped.

Tests: Each bug's previously-silent-drop now produces correct output.
How: Construct minimal in-memory inputs that reproduce the exact failure path,
     run the reader/normalizer pipeline, assert tasks survive with correct values.
Why: normalize_plan silently catches ValueError from individual task normalization
     and skips the task — without these tests, regressions are invisible.
"""

from __future__ import annotations

from textwrap import dedent
from typing import TYPE_CHECKING

from sam_schema.readers.manifest_reader import _build_task_dict, _extract_bold_fields, read_manifest_plan
from sam_schema.readers.normalize import normalize_plan

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
            **Agent**: python3-development:python-cli-architect
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
