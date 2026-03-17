"""Tests for sam_schema.readers.legacy_reader — legacy markdown format reader."""

from __future__ import annotations

import pathlib

import pytest
from sam_schema.core.query import load_plan
from sam_schema.readers.detect import FormatType
from sam_schema.readers.legacy_reader import read_legacy_plan

_FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures"


# ---------------------------------------------------------------------------
# Basic reading
# ---------------------------------------------------------------------------


def test_read_legacy_plan_returns_three_tasks():
    path = _FIXTURES / "legacy_markdown.md"
    _, task_dicts, _ = read_legacy_plan(path)
    assert len(task_dicts) == 3


def test_read_legacy_plan_returns_legacy_markdown_format_type():
    path = _FIXTURES / "legacy_markdown.md"
    _, _, fmt = read_legacy_plan(path)
    assert fmt == FormatType.LEGACY_MARKDOWN


def test_read_legacy_plan_plan_meta_has_feature_from_h1():
    path = _FIXTURES / "legacy_markdown.md"
    plan_meta, _, _ = read_legacy_plan(path)
    # The H1 is "API Rate Limiting - Task Plan"
    assert "api" in plan_meta.get("feature", "").lower()


# ---------------------------------------------------------------------------
# First task — title and status
# ---------------------------------------------------------------------------


def test_read_legacy_plan_first_task_number_is_1():
    path = _FIXTURES / "legacy_markdown.md"
    _, task_dicts, _ = read_legacy_plan(path)
    assert task_dicts[0].get("task") == "1"


def test_read_legacy_plan_first_task_title_is_correct():
    path = _FIXTURES / "legacy_markdown.md"
    _, task_dicts, _ = read_legacy_plan(path)
    assert task_dicts[0].get("title") == "Define rate limit configuration model"


def test_read_legacy_plan_first_task_status_is_complete():
    # Fixture uses :white_check_mark: COMPLETE emoji marker
    path = _FIXTURES / "legacy_markdown.md"
    _, task_dicts, _ = read_legacy_plan(path)
    # Legacy reader returns the raw string — normalize is tested in test_normalize.py
    assert task_dicts[0].get("status") is not None


# ---------------------------------------------------------------------------
# Second task — dependencies and priority
# ---------------------------------------------------------------------------


def test_read_legacy_plan_second_task_number_is_2():
    path = _FIXTURES / "legacy_markdown.md"
    _, task_dicts, _ = read_legacy_plan(path)
    assert task_dicts[1].get("task") == "2"


def test_read_legacy_plan_second_task_has_dependency_list():
    path = _FIXTURES / "legacy_markdown.md"
    _, task_dicts, _ = read_legacy_plan(path)
    deps = task_dicts[1].get("dependencies")
    assert isinstance(deps, list)
    assert len(deps) >= 1


def test_read_legacy_plan_second_task_raw_dependency_contains_task_prefix():
    # Legacy reader emits raw values like "Task 1" — normalizer strips prefix
    path = _FIXTURES / "legacy_markdown.md"
    _, task_dicts, _ = read_legacy_plan(path)
    deps = task_dicts[1].get("dependencies", [])
    # Raw value from fixture is "Task 1"
    assert any("1" in d for d in deps)


def test_read_legacy_plan_second_task_priority_is_integer():
    path = _FIXTURES / "legacy_markdown.md"
    _, task_dicts, _ = read_legacy_plan(path)
    priority = task_dicts[1].get("priority")
    assert isinstance(priority, int)
    assert priority == 2


# ---------------------------------------------------------------------------
# Third task — multi-dependency, complexity
# ---------------------------------------------------------------------------


def test_read_legacy_plan_third_task_has_multiple_dependencies():
    path = _FIXTURES / "legacy_markdown.md"
    _, task_dicts, _ = read_legacy_plan(path)
    deps = task_dicts[2].get("dependencies", [])
    assert len(deps) >= 2


def test_read_legacy_plan_third_task_complexity_is_extracted():
    path = _FIXTURES / "legacy_markdown.md"
    _, task_dicts, _ = read_legacy_plan(path)
    complexity = task_dicts[2].get("complexity")
    assert complexity is not None


# ---------------------------------------------------------------------------
# Agent field extraction
# ---------------------------------------------------------------------------


def test_read_legacy_plan_tasks_have_agent_field():
    path = _FIXTURES / "legacy_markdown.md"
    _, task_dicts, _ = read_legacy_plan(path)
    for task in task_dicts:
        assert "agent" in task, f"Task {task.get('task')} missing 'agent' field"


# ---------------------------------------------------------------------------
# Feature name synthesis from filename
# ---------------------------------------------------------------------------


def test_read_legacy_plan_synthesizes_feature_from_filename_when_no_h1(tmp_path):
    # A legacy file with no # heading — feature is synthesized from filename
    content = (
        "## Task 1: A simple task\n\n"
        "**Status**: NOT STARTED\n"
        "**Agent**: some-agent\n"
        "**Priority**: 1\n"
        "**Complexity**: Low\n"
    )
    f = tmp_path / "tasks-7-my-feature.md"
    f.write_text(content)
    plan_meta, task_dicts, _ = read_legacy_plan(f)
    assert plan_meta.get("feature") == "my-feature"
    assert len(task_dicts) == 1


def test_read_legacy_plan_uses_h1_as_feature_when_present(tmp_path):
    content = "# My Feature Plan\n\n## Task 1: A task\n\n**Status**: NOT STARTED\n**Agent**: agent\n"
    f = tmp_path / "tasks.md"
    f.write_text(content)
    plan_meta, _, _ = read_legacy_plan(f)
    assert plan_meta.get("feature") == "My Feature Plan"


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


def test_read_legacy_plan_nonexistent_path_raises_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_legacy_plan(tmp_path / "missing.md")


def test_read_legacy_plan_no_task_headings_raises_value_error(tmp_path):
    f = tmp_path / "no_tasks.md"
    f.write_text("# A Plan\n\nNo task headings here.\n")
    with pytest.raises(ValueError, match="No '## Task N:'"):
        read_legacy_plan(f)


# ---------------------------------------------------------------------------
# Field value parsing — list fields return empty list for "None"
# ---------------------------------------------------------------------------


def test_read_legacy_plan_none_dependency_returns_empty_list(tmp_path):
    content = "## Task 1: A task\n\n**Status**: NOT STARTED\n**Dependencies**: None\n**Agent**: agent\n"
    f = tmp_path / "tasks.md"
    f.write_text(content)
    _, task_dicts, _ = read_legacy_plan(f)
    assert task_dicts[0].get("dependencies") == []


# ---------------------------------------------------------------------------
# Field value parsing — divergence-notes non-integer fallback
# ---------------------------------------------------------------------------


def test_read_legacy_plan_divergence_notes_non_integer_returns_zero(tmp_path: pathlib.Path) -> None:
    """Verify non-integer divergence-notes value falls back to 0.

    Tests: divergence-notes field parsing with invalid value.
    How: Write task with 'abc' as divergence-notes value.
    Why: Malformed divergence-notes must not crash the reader.
    """
    content = "## Task 1: A task\n\n**Status**: NOT STARTED\n**Divergence Notes**: abc\n**Agent**: agent\n"
    f = tmp_path / "tasks.md"
    f.write_text(content)
    _, task_dicts, _ = read_legacy_plan(f)
    assert task_dicts[0].get("divergence-notes") == 0


def test_read_legacy_plan_divergence_notes_integer_returns_int(tmp_path: pathlib.Path) -> None:
    """Verify integer divergence-notes value is parsed correctly.

    Tests: divergence-notes field parsing with valid integer.
    How: Write task with '3' as divergence-notes value.
    Why: Valid integers must be preserved.
    """
    content = "## Task 1: A task\n\n**Status**: NOT STARTED\n**Divergence Notes**: 3\n**Agent**: agent\n"
    f = tmp_path / "tasks.md"
    f.write_text(content)
    _, task_dicts, _ = read_legacy_plan(f)
    assert task_dicts[0].get("divergence-notes") == 3


# ---------------------------------------------------------------------------
# Field value parsing — priority non-integer fallback
# ---------------------------------------------------------------------------


def test_read_legacy_plan_priority_non_integer_returns_raw_string(tmp_path: pathlib.Path) -> None:
    """Verify non-integer priority value returns the raw string.

    Tests: Priority field parsing with non-numeric value.
    How: Write task with 'high' as priority value.
    Why: Some legacy files use 'high'/'low' labels instead of integers.
    """
    content = "## Task 1: A task\n\n**Status**: NOT STARTED\n**Priority**: high\n**Agent**: agent\n"
    f = tmp_path / "tasks.md"
    f.write_text(content)
    _, task_dicts, _ = read_legacy_plan(f)
    assert task_dicts[0].get("priority") == "high"


# ---------------------------------------------------------------------------
# Field value parsing — null-like values return None
# ---------------------------------------------------------------------------


def test_read_legacy_plan_null_like_field_value_returns_none(tmp_path: pathlib.Path) -> None:
    """Verify null-like field values (N/A, none, -) return None.

    Tests: Null detection in field value parsing.
    How: Write task with 'N/A' as agent value.
    Why: Null-like markers in legacy files must be treated as absent.
    """
    content = "## Task 1: A task\n\n**Status**: NOT STARTED\n**Agent**: N/A\n"
    f = tmp_path / "tasks.md"
    f.write_text(content)
    _, task_dicts, _ = read_legacy_plan(f)
    # 'N/A' is null-like — the field should not be set (None returned from parser,
    # and the field extraction skips None values)
    assert "agent" not in task_dicts[0]


# ---------------------------------------------------------------------------
# Complexity normalization — title case to lowercase
# ---------------------------------------------------------------------------


def test_read_legacy_plan_complexity_title_case_normalized_to_lower(tmp_path: pathlib.Path) -> None:
    """Verify title-case complexity is normalized to lowercase.

    Tests: Complexity field case normalization.
    How: Write task with 'Medium' complexity (title case).
    Why: Legacy files use title case; Complexity enum expects lowercase.
    """
    content = "## Task 1: A task\n\n**Status**: NOT STARTED\n**Complexity**: Medium\n**Agent**: agent\n"
    f = tmp_path / "tasks.md"
    f.write_text(content)
    _, task_dicts, _ = read_legacy_plan(f)
    assert task_dicts[0].get("complexity") == "medium"


# ---------------------------------------------------------------------------
# Prose subsection extraction — ### Acceptance Criteria, ### Problem, etc.
# ---------------------------------------------------------------------------


def test_read_legacy_plan_acceptance_criteria_section_populates_field(tmp_path: pathlib.Path) -> None:
    """Verify ### Acceptance Criteria section is extracted into acceptance-criteria field.

    Tests: Legacy reader prose subsection extraction.
    How: Write task with inline markers + ### Acceptance Criteria subsection.
    Why: Before the fix, prose subsections were silently discarded.
    """
    content = (
        "## Task 1: A task with criteria\n\n"
        "**Status**: NOT STARTED\n"
        "**Agent**: test-agent\n"
        "**Priority**: 1\n"
        "\n"
        "### Acceptance Criteria\n"
        "\n"
        "- Criterion A\n"
        "- Criterion B\n"
    )
    f = tmp_path / "tasks.md"
    f.write_text(content)
    _, task_dicts, _ = read_legacy_plan(f)
    ac = task_dicts[0].get("acceptance-criteria") or ""
    assert "Criterion A" in ac, "Acceptance criteria content must be extracted from ### section"
    assert "Criterion B" in ac


def test_read_legacy_plan_problem_section_populates_description(tmp_path: pathlib.Path) -> None:
    """Verify ### Problem section is mapped to the description field.

    Tests: Legacy reader ### Problem → description mapping.
    How: Write task with ### Problem subsection.
    Why: Legacy plan files often use ### Problem instead of ### Context.
    """
    content = (
        "## Task 1: A task with problem\n\n"
        "**Status**: NOT STARTED\n"
        "**Agent**: test-agent\n"
        "\n"
        "### Problem\n"
        "\n"
        "The widget rendering is broken.\n"
    )
    f = tmp_path / "tasks.md"
    f.write_text(content)
    _, task_dicts, _ = read_legacy_plan(f)
    desc = task_dicts[0].get("description") or ""
    assert "widget rendering is broken" in desc


def test_read_legacy_plan_body_content_round_trip(tmp_path: pathlib.Path) -> None:
    """Verify body content survives the read -> write round-trip for legacy format.

    Tests: Legacy reader read -> YAML write round-trip with prose subsections.
    How: Build a two-task legacy file with acceptance criteria, load through
         load_plan, write to YAML, verify content in output.
    Why: The fix must feed parsed prose content into the Task model fields
         that the YAML writer serialises as literal block scalars.
    """
    from sam_schema.core.query import load_plan
    from sam_schema.writers.yaml_writer import write_plan

    content = (
        "# Legacy Plan\n\n"
        "## Task 1: Implement rate limiting\n\n"
        "**Status**: NOT STARTED\n"
        "**Agent**: python3-development:python-cli-architect\n"
        "**Priority**: 1\n"
        "**Complexity**: Medium\n"
        "\n"
        "### Problem\n"
        "\n"
        "API requests are not rate-limited.\n"
        "\n"
        "### Acceptance Criteria\n"
        "\n"
        "- Rate limit is enforced per user\n"
        "- Requests over limit return HTTP 429\n"
        "\n"
        "## Task 2: Add tests\n\n"
        "**Status**: NOT STARTED\n"
        "**Agent**: python3-development:python-pytest-architect\n"
        "**Priority**: 2\n"
        "**Dependencies**: 1\n"
        "\n"
        "### Acceptance Criteria\n"
        "\n"
        "- Tests cover rate limit enforcement\n"
    )
    md_file = tmp_path / "tasks-1-legacy-round-trip.md"
    md_file.write_text(content)

    result = load_plan(md_file)
    t1 = next(t for t in result.plan.tasks if t.id == "1")
    t2 = next(t for t in result.plan.tasks if t.id == "2")

    assert "API requests are not rate-limited" in t1.description
    assert "Rate limit is enforced" in t1.acceptance_criteria
    assert "Tests cover rate limit" in t2.acceptance_criteria

    out_yaml = tmp_path / "out.yaml"
    write_plan(result.plan, out_yaml)
    yaml_content = out_yaml.read_text()

    assert "API requests are not rate-limited" in yaml_content
    assert "acceptance-criteria" in yaml_content
    assert "Rate limit is enforced" in yaml_content
    assert "Tests cover rate limit" in yaml_content


# ---------------------------------------------------------------------------
# Integration: legacy reader returns empty acceptance_criteria_structured
# ---------------------------------------------------------------------------


def test_legacy_reader_returns_empty_structured_criteria() -> None:
    """Verify legacy reader produces empty acceptance_criteria_structured.

    Tests: Legacy format backward compatibility for structured criteria.
    How: Load legacy_markdown.md fixture via load_plan, verify the
         acceptance_criteria_structured field is an empty list.
    Why: Legacy format does not support structured criteria; the field must
         default to an empty list rather than causing errors.
    """
    path = _FIXTURES / "legacy_markdown.md"
    result = load_plan(path)
    assert result.plan.acceptance_criteria_structured == []
