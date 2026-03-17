"""Tests for sam_schema.readers.frontmatter_reader — YAML frontmatter in markdown."""

from __future__ import annotations

import pathlib

import pytest
from sam_schema.core.models import AcceptanceCriterion
from sam_schema.core.query import load_plan
from sam_schema.readers.detect import FormatType
from sam_schema.readers.frontmatter_reader import read_frontmatter_plan

_FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures"


# ---------------------------------------------------------------------------
# Single-task frontmatter file
# ---------------------------------------------------------------------------


def test_read_frontmatter_plan_single_returns_one_task():
    path = _FIXTURES / "yaml_frontmatter_single.md"
    _, task_dicts, _ = read_frontmatter_plan(path)
    assert len(task_dicts) == 1


def test_read_frontmatter_plan_single_returns_yaml_frontmatter_format_type():
    path = _FIXTURES / "yaml_frontmatter_single.md"
    _, _, fmt = read_frontmatter_plan(path)
    assert fmt == FormatType.YAML_FRONTMATTER


def test_read_frontmatter_plan_single_task_has_correct_id():
    path = _FIXTURES / "yaml_frontmatter_single.md"
    _, task_dicts, _ = read_frontmatter_plan(path)
    assert task_dicts[0].get("task") == "T1"


def test_read_frontmatter_plan_single_task_has_correct_title():
    path = _FIXTURES / "yaml_frontmatter_single.md"
    _, task_dicts, _ = read_frontmatter_plan(path)
    assert task_dicts[0].get("title") == "Implement database migration framework"


def test_read_frontmatter_plan_single_task_has_correct_status():
    path = _FIXTURES / "yaml_frontmatter_single.md"
    _, task_dicts, _ = read_frontmatter_plan(path)
    assert task_dicts[0].get("status") == "not-started"


# ---------------------------------------------------------------------------
# Multi-task frontmatter file
# ---------------------------------------------------------------------------


def test_read_frontmatter_plan_multi_returns_three_tasks():
    path = _FIXTURES / "yaml_frontmatter_multi.md"
    _, task_dicts, _ = read_frontmatter_plan(path)
    assert len(task_dicts) == 3


def test_read_frontmatter_plan_multi_returns_yaml_frontmatter_format_type():
    path = _FIXTURES / "yaml_frontmatter_multi.md"
    _, _, fmt = read_frontmatter_plan(path)
    assert fmt == FormatType.YAML_FRONTMATTER


def test_read_frontmatter_plan_multi_plan_meta_has_feature():
    path = _FIXTURES / "yaml_frontmatter_multi.md"
    plan_meta, _, _ = read_frontmatter_plan(path)
    assert plan_meta.get("feature") == "cache-layer"


def test_read_frontmatter_plan_multi_first_task_is_complete():
    path = _FIXTURES / "yaml_frontmatter_multi.md"
    _, task_dicts, _ = read_frontmatter_plan(path)
    first = next(t for t in task_dicts if t.get("task") == "T1")
    assert first.get("status") == "complete"


def test_read_frontmatter_plan_multi_second_task_is_in_progress():
    path = _FIXTURES / "yaml_frontmatter_multi.md"
    _, task_dicts, _ = read_frontmatter_plan(path)
    second = next(t for t in task_dicts if t.get("task") == "T2")
    assert second.get("status") == "in-progress"


def test_read_frontmatter_plan_multi_third_task_is_not_started():
    path = _FIXTURES / "yaml_frontmatter_multi.md"
    _, task_dicts, _ = read_frontmatter_plan(path)
    third = next(t for t in task_dicts if t.get("task") == "T3")
    assert third.get("status") == "not-started"


def test_read_frontmatter_plan_multi_second_task_has_dependency():
    path = _FIXTURES / "yaml_frontmatter_multi.md"
    _, task_dicts, _ = read_frontmatter_plan(path)
    second = next(t for t in task_dicts if t.get("task") == "T2")
    deps = second.get("dependencies", [])
    assert "T1" in deps


# ---------------------------------------------------------------------------
# Body content extraction — prose sections after each task YAML block
# ---------------------------------------------------------------------------


def test_read_frontmatter_plan_multi_first_task_has_description_from_body():
    """Verify that the prose body following a task YAML block populates description.

    Tests: Prose body content extraction for multi-task frontmatter files.
    How: Point read_frontmatter_plan at yaml_frontmatter_multi.md, check T1.description.
    Why: Body content was previously discarded; this is the regression guard for the fix.
    """
    path = _FIXTURES / "yaml_frontmatter_multi.md"
    _, task_dicts, _ = read_frontmatter_plan(path)
    t1 = next(t for t in task_dicts if t.get("task") == "T1")
    assert t1.get("description"), "T1 description should be populated from the prose body"


def test_read_frontmatter_plan_multi_first_task_has_objective_from_body():
    """Verify that ### Objective sections are extracted into the objective field.

    Tests: Named prose section extraction (### Objective).
    How: Check T1.objective against yaml_frontmatter_multi.md fixture content.
    Why: The fixture has an explicit ### Objective section; it must survive the read.
    """
    path = _FIXTURES / "yaml_frontmatter_multi.md"
    _, task_dicts, _ = read_frontmatter_plan(path)
    t1 = next(t for t in task_dicts if t.get("task") == "T1")
    assert t1.get("objective"), "T1 objective should be populated from ### Objective section"


def test_read_frontmatter_plan_multi_body_content_round_trip(tmp_path: pathlib.Path) -> None:
    """Verify body content survives the read -> write round-trip.

    Tests: Body content fields preserved through read_frontmatter_plan -> YAML write.
    How: Build a two-task frontmatter file with acceptance criteria and verification
         steps in prose bodies, read it, write to YAML, verify content in output.
    Why: The fix must not only parse prose — it must feed the parsed content into
         the Task model fields that the YAML writer serialises as literal block scalars.
    """
    from sam_schema.core.query import load_plan
    from sam_schema.readers.detect import read_plan
    from sam_schema.writers.yaml_writer import write_plan

    content = (
        "---\n"
        "feature: round-trip-test\n"
        "---\n"
        "\n"
        "\n"
        "task: T1\n"
        "title: First task\n"
        "status: not-started\n"
        "\n"
        "---\n"
        "\n"
        "## Context\n"
        "\n"
        "This is the context for T1.\n"
        "\n"
        "## Acceptance Criteria\n"
        "\n"
        "1. Criterion one\n"
        "2. Criterion two\n"
        "\n"
        "## Verification Steps\n"
        "\n"
        "1. Run pytest\n"
        "2. Check output\n"
        "\n"
        "---\n"
        "\n"
        "\n"
        "task: T2\n"
        "title: Second task\n"
        "status: not-started\n"
        "dependencies:\n"
        "  - T1\n"
        "\n"
        "---\n"
        "\n"
        "## Context\n"
        "\n"
        "This is the context for T2.\n"
        "\n"
        "## Acceptance Criteria\n"
        "\n"
        "1. T2 criterion\n"
    )
    md_file = tmp_path / "tasks-1-round-trip-test.md"
    md_file.write_text(content)

    # Read the plan
    _plan_meta, task_dicts, _ = read_plan(md_file)
    t1 = next(t for t in task_dicts if t.get("task") == "T1")
    t2 = next(t for t in task_dicts if t.get("task") == "T2")

    # Verify description and acceptance-criteria are in the task dicts
    assert t1.get("description") == "This is the context for T1."
    assert "Criterion one" in (t1.get("acceptance-criteria") or "")
    assert "Run pytest" in (t1.get("verification-steps") or "")
    assert t2.get("description") == "This is the context for T2."
    assert "T2 criterion" in (t2.get("acceptance-criteria") or "")

    # Write to YAML and verify content survives
    result = load_plan(md_file)
    out_yaml = tmp_path / "out.yaml"
    write_plan(result.plan, out_yaml)
    yaml_content = out_yaml.read_text()

    assert "This is the context for T1" in yaml_content
    assert "Criterion one" in yaml_content
    assert "Run pytest" in yaml_content
    assert "This is the context for T2" in yaml_content
    assert "T2 criterion" in yaml_content


def test_read_frontmatter_plan_multi_prose_not_duplicated_in_yaml_block_task(tmp_path: pathlib.Path) -> None:
    """Verify that prose fields are not overwritten when YAML block already has them.

    Tests: setdefault semantics — YAML block fields take precedence.
    How: Build a task YAML block that already contains a 'description' field,
         followed by a ## Context prose section with different text.
    Why: The fix uses setdefault so explicit YAML fields are not overwritten.
    """
    content = (
        "---\n"
        "feature: precedence-test\n"
        "---\n"
        "\n"
        "\n"
        "task: T1\n"
        "title: Task with explicit description\n"
        "status: not-started\n"
        "description: Explicit description from YAML block.\n"
        "\n"
        "---\n"
        "\n"
        "## Context\n"
        "\n"
        "Prose context that should NOT override the YAML description.\n"
    )
    f = tmp_path / "tasks-1-precedence.md"
    f.write_text(content)
    _, task_dicts, _ = read_frontmatter_plan(f)
    t1 = task_dicts[0]
    # The YAML block's description must win over the prose section
    assert t1.get("description") == "Explicit description from YAML block."


# ---------------------------------------------------------------------------
# Tasks-list variant — frontmatter tasks: list without feature/slug
# ---------------------------------------------------------------------------


def test_read_frontmatter_plan_tasks_list_returns_two_tasks():
    """Verify tasks-list variant returns all tasks from frontmatter list.

    Tests: Tasks-list variant returns correct task count.
    How: Point read_frontmatter_plan at the tasks-list fixture.
    Why: Core parsing requirement for the new format variant.
    """
    path = _FIXTURES / "yaml_frontmatter_tasks_list.md"
    _, task_dicts, _ = read_frontmatter_plan(path)
    assert len(task_dicts) == 2


def test_read_frontmatter_plan_tasks_list_returns_yaml_frontmatter_format_type():
    """Verify tasks-list variant returns YAML_FRONTMATTER format type.

    Tests: Format type for tasks-list variant.
    How: Point read_frontmatter_plan at the tasks-list fixture.
    Why: Callers depend on the format type for downstream processing.
    """
    path = _FIXTURES / "yaml_frontmatter_tasks_list.md"
    _, _, fmt = read_frontmatter_plan(path)
    assert fmt == FormatType.YAML_FRONTMATTER


def test_read_frontmatter_plan_tasks_list_returns_empty_plan_meta():
    """Verify tasks-list variant returns empty plan metadata dict.

    Tests: Plan metadata for tasks-list variant.
    How: Point read_frontmatter_plan at the tasks-list fixture.
    Why: There is no plan-level metadata separate from task list items.
    """
    path = _FIXTURES / "yaml_frontmatter_tasks_list.md"
    plan_meta, _, _ = read_frontmatter_plan(path)
    assert plan_meta == {}


def test_read_frontmatter_plan_tasks_list_first_task_has_correct_name():
    """Verify tasks-list variant first task has its task name preserved.

    Tests: Task name field extraction for tasks-list variant.
    How: Point read_frontmatter_plan at the tasks-list fixture.
    Why: Task name is required for downstream processing.
    """
    path = _FIXTURES / "yaml_frontmatter_tasks_list.md"
    _, task_dicts, _ = read_frontmatter_plan(path)
    assert task_dicts[0].get("task") == "Fix the widget rendering bug"


def test_read_frontmatter_plan_tasks_list_task_has_status():
    """Verify tasks-list variant tasks have their status field preserved.

    Tests: Status field extraction for tasks-list variant.
    How: Point read_frontmatter_plan at the tasks-list fixture.
    Why: Status field drives orchestration readiness logic.
    """
    path = _FIXTURES / "yaml_frontmatter_tasks_list.md"
    _, task_dicts, _ = read_frontmatter_plan(path)
    assert task_dicts[0].get("status") == "pending"


def test_read_frontmatter_plan_tasks_list_task_has_parent_task():
    """Verify tasks-list variant tasks have their parent_task field preserved.

    Tests: Extra fields preserved for tasks-list variant.
    How: Point read_frontmatter_plan at the tasks-list fixture.
    Why: Parent task linkage is used for traceability.
    """
    path = _FIXTURES / "yaml_frontmatter_tasks_list.md"
    _, task_dicts, _ = read_frontmatter_plan(path)
    assert task_dicts[0].get("parent_task") == "plan/tasks-1-widget-overhaul.md"


def test_read_frontmatter_plan_tasks_list_empty_list_raises_value_error(tmp_path: pathlib.Path) -> None:
    """Verify ValueError when tasks: list is present but empty.

    Tests: Empty tasks-list raises an error.
    How: Write a file with tasks: [] frontmatter.
    Why: An empty tasks list is a data error — there are no tasks to return.
    """
    f = tmp_path / "empty_tasks.md"
    f.write_text("---\ntasks: []\n---\n\n# Body\n")
    with pytest.raises(ValueError, match="No task entries"):
        read_frontmatter_plan(f)


def test_read_frontmatter_plan_real_followup_file_returns_one_task() -> None:
    """Verify the actual follow-up task file that triggered this bug can be read.

    Tests: Real-world tasks-list file produces one task dict.
    How: Call read_frontmatter_plan on the real plan file.
    Why: Regression guard — the exact file that failed before the fix.
    """
    real_file = pathlib.Path(
        "/home/ubuntulinuxqa2/repos/claude_skills/plan/tasks-3-unified-sam-task-schema-followup-1.md"
    )
    if not real_file.exists():
        pytest.skip("Real follow-up file not present in this environment")
    _, task_dicts, fmt = read_frontmatter_plan(real_file)
    assert fmt == FormatType.YAML_FRONTMATTER
    assert len(task_dicts) == 1
    assert task_dicts[0].get("status") == "pending"


# ---------------------------------------------------------------------------
# Code fence edge case — --- inside ``` blocks must not split segments
# ---------------------------------------------------------------------------


def test_read_frontmatter_plan_code_fence_does_not_split_on_dashes_inside_fence(tmp_path):
    # A multi-task file where a task body has a --- inside a code block.
    # The reader must not split there and must return exactly 2 tasks.
    content = (
        "---\n"
        "feature: fence-test\n"
        "---\n"
        "\n"
        "\n"
        "task: T1\n"
        "title: Task with code fence\n"
        "status: not-started\n"
        "\n"
        "---\n"
        "\n"
        "### Notes\n"
        "\n"
        "```yaml\n"
        "key: value\n"
        "---\n"
        "another: thing\n"
        "```\n"
        "\n"
        "---\n"
        "\n"
        "\n"
        "task: T2\n"
        "title: Second task\n"
        "status: not-started\n"
        "\n"
        "---\n"
    )
    f = tmp_path / "fence_test.md"
    f.write_text(content)
    _, task_dicts, _ = read_frontmatter_plan(f)
    assert len(task_dicts) == 2
    assert task_dicts[0].get("task") == "T1"
    assert task_dicts[1].get("task") == "T2"


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


def test_read_frontmatter_plan_nonexistent_path_raises_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_frontmatter_plan(tmp_path / "missing.md")


def test_read_frontmatter_plan_no_frontmatter_raises_value_error(tmp_path):
    f = tmp_path / "no_fm.md"
    f.write_text("# Just a heading\n\nSome body text.\n")
    with pytest.raises(ValueError, match="frontmatter"):
        read_frontmatter_plan(f)


def test_read_frontmatter_plan_no_closing_delimiter_raises_value_error(tmp_path: pathlib.Path) -> None:
    """Verify ValueError when frontmatter has no closing '---'.

    Tests: Missing closing delimiter detection.
    How: Write file with opening --- but no closing ---.
    Why: Unclosed frontmatter would produce garbage task data.
    """
    f = tmp_path / "unclosed.md"
    f.write_text("---\ntask: T1\ntitle: Unclosed\nstatus: not-started\n")
    with pytest.raises(ValueError, match="closing"):
        read_frontmatter_plan(f)


def test_read_frontmatter_plan_invalid_yaml_in_frontmatter_raises_value_error(tmp_path: pathlib.Path) -> None:
    """Verify ValueError when frontmatter contains invalid YAML.

    Tests: Invalid YAML detection in frontmatter block.
    How: Write file with syntactically broken YAML in frontmatter.
    Why: Corrupt YAML must be rejected, not silently ignored.
    """
    f = tmp_path / "bad_yaml.md"
    f.write_text("---\n  bad: yaml: indentation:\n    - nested\n  bad\n---\n\nBody.\n")
    with pytest.raises(ValueError, match="parse"):
        read_frontmatter_plan(f)


def test_read_frontmatter_plan_multi_with_no_task_blocks_raises_error(tmp_path: pathlib.Path) -> None:
    """Verify error when multi-task file body contains no valid task blocks.

    Tests: No task blocks detection in multi-task frontmatter file.
    How: Write a file with feature frontmatter but only plain key-value YAML
    in the body (no 'task:' or 'task_id:' fields).
    Why: A multi-task file with zero recognized tasks is a data loss scenario.
    """
    # The body must contain valid YAML dicts (not prose) but without task:/task_id: fields
    content = "---\nfeature: empty-feature\n---\n\n---\n\nkey: value\nother: data\n\n---\n"
    f = tmp_path / "no_tasks.md"
    f.write_text(content)
    with pytest.raises(ValueError, match="No task blocks"):
        read_frontmatter_plan(f)


def test_read_frontmatter_plan_single_task_with_task_id_key(tmp_path: pathlib.Path) -> None:
    """Verify single-task file with 'task_id' key works.

    Tests: Alternative task_id key in frontmatter.
    How: Write file using 'task_id' instead of 'task'.
    Why: Some generators use 'task_id' as the key name.
    """
    content = "---\ntask_id: T5\ntitle: Alt key\nstatus: not-started\n---\n\nBody.\n"
    f = tmp_path / "alt_key.md"
    f.write_text(content)
    _, task_dicts, fmt = read_frontmatter_plan(f)
    assert len(task_dicts) == 1
    assert task_dicts[0].get("task") == "T5"
    assert fmt == FormatType.YAML_FRONTMATTER


# ---------------------------------------------------------------------------
# Integration: structured acceptance criteria in frontmatter format
# ---------------------------------------------------------------------------


def test_frontmatter_structured_criteria_parsed_into_acceptance_criterion_objects(tmp_path: pathlib.Path) -> None:
    """Verify frontmatter reader handles structured criteria from YAML header.

    Tests: acceptance-criteria-structured field parsed from frontmatter format.
    How: Create a multi-task frontmatter .md file with acceptance-criteria-structured
         in the plan-level header, load via load_plan, verify AcceptanceCriterion
         objects are populated correctly.
    Why: Frontmatter format must support structured criteria identically to pure YAML.
    """
    content = (
        "---\n"
        "feature: fm-structured-test\n"
        "acceptance-criteria-structured:\n"
        "  - criterion-id: AC-1\n"
        "    description: Widget renders\n"
        "    check-command: uv run pytest tests/test_widget.py -v\n"
        "    expected-baseline: fail\n"
        "    expected-final: pass\n"
        "  - criterion-id: AC-2\n"
        "    check-command: uv run ruff check src/\n"
        "---\n"
        "\n"
        "\n"
        "task: T1\n"
        "title: Implement widget\n"
        "status: not-started\n"
        "\n"
        "---\n"
        "\n"
        "## Context\n"
        "\n"
        "Widget implementation task.\n"
    )
    f = tmp_path / "tasks-1-fm-structured.md"
    f.write_text(content)

    result = load_plan(f)
    criteria = result.plan.acceptance_criteria_structured

    assert len(criteria) == 2
    assert isinstance(criteria[0], AcceptanceCriterion)
    assert criteria[0].criterion_id == "AC-1"
    assert criteria[0].check_command == "uv run pytest tests/test_widget.py -v"
    assert criteria[0].expected_baseline == "fail"
    assert criteria[0].expected_final == "pass"
    assert criteria[0].description == "Widget renders"
    assert criteria[1].criterion_id == "AC-2"
    assert criteria[1].expected_baseline == "any"  # default value


def test_frontmatter_without_structured_criteria_returns_empty_list(tmp_path: pathlib.Path) -> None:
    """Verify frontmatter plans without structured criteria produce empty list.

    Tests: Backward compatibility for frontmatter format without new fields.
    How: Load yaml_frontmatter_multi.md (no structured criteria), verify
         acceptance_criteria_structured is an empty list.
    Why: Existing frontmatter plans must not break when new fields are absent.
    """
    path = _FIXTURES / "yaml_frontmatter_multi.md"
    result = load_plan(path)
    assert result.plan.acceptance_criteria_structured == []


def test_frontmatter_bookend_task_fields_parsed(tmp_path: pathlib.Path) -> None:
    """Verify frontmatter reader parses is-bookend and bookend-type on tasks.

    Tests: Bookend field parsing for frontmatter task blocks.
    How: Create a multi-task frontmatter file with bookend fields on tasks,
         load via load_plan, verify bookend metadata on each task.
    Why: Bookend fields must work in all reader formats, not just pure YAML.
    """
    content = (
        "---\n"
        "feature: fm-bookend-test\n"
        "---\n"
        "\n"
        "\n"
        "task: T0\n"
        "title: Capture baseline\n"
        "status: not-started\n"
        "dependencies: []\n"
        "priority: 1\n"
        "complexity: low\n"
        "is-bookend: true\n"
        "bookend-type: t0-baseline\n"
        "\n"
        "---\n"
        "\n"
        "\n"
        "task: T1\n"
        "title: Implement feature\n"
        "status: not-started\n"
        "dependencies:\n"
        "  - T0\n"
        "priority: 2\n"
        "complexity: medium\n"
        "\n"
        "---\n"
    )
    f = tmp_path / "tasks-1-fm-bookend.md"
    f.write_text(content)

    result = load_plan(f)
    tasks_by_id = {t.id: t for t in result.plan.tasks}

    t0 = tasks_by_id["T0"]
    assert t0.is_bookend is True
    assert t0.bookend_type == "t0-baseline"

    t1 = tasks_by_id["T1"]
    assert t1.is_bookend is False
    assert t1.bookend_type is None
