"""Tests for sam_schema.readers.detect — format detection logic.

Tests: Format detection for all five format types plus unrecognized formats.
How: Point detect_format at fixture files and dynamic tmp_path files.
Why: Format detection is the entry point for the reader pipeline. Wrong format
detection silently routes files to the wrong reader, producing garbage.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sam_schema.readers.detect import FormatDetectionError, FormatType, detect_format, read_plan

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_FIXTURES: Path = Path(__file__).parent.parent / "fixtures"


# ---------------------------------------------------------------------------
# detect_format — PURE_YAML
# ---------------------------------------------------------------------------


def test_detect_format_pure_yaml_single_file_returns_pure_yaml() -> None:
    """Verify .yaml file is detected as PURE_YAML.

    Tests: PURE_YAML format detection for single YAML files.
    How: Point detect_format at a .yaml fixture file.
    Why: Canonical format must be reliably identified.
    """
    path = _FIXTURES / "pure_yaml_single.yaml"
    result = detect_format(path)
    assert result == FormatType.PURE_YAML


def test_detect_format_directory_with_task_files_returns_directory() -> None:
    """Verify directory with task files is detected as DIRECTORY.

    Tests: DIRECTORY format detection.
    How: Point detect_format at a directory fixture.
    Why: Directory-based plans use a different reader path.
    """
    path = _FIXTURES / "pure_yaml_directory"
    result = detect_format(path)
    assert result == FormatType.DIRECTORY


# ---------------------------------------------------------------------------
# detect_format — LEGACY_MARKDOWN
# ---------------------------------------------------------------------------


def test_detect_format_legacy_markdown_returns_legacy_markdown() -> None:
    """Verify .md file with ## Task N: headings is detected as LEGACY_MARKDOWN.

    Tests: LEGACY_MARKDOWN format detection.
    How: Point detect_format at a legacy markdown fixture.
    Why: Legacy format must be detected to route to the legacy reader.
    """
    path = _FIXTURES / "legacy_markdown.md"
    result = detect_format(path)
    assert result == FormatType.LEGACY_MARKDOWN


# ---------------------------------------------------------------------------
# detect_format — YAML_FRONTMATTER
# ---------------------------------------------------------------------------


def test_detect_format_yaml_frontmatter_single_returns_yaml_frontmatter() -> None:
    """Verify single-task frontmatter .md is detected as YAML_FRONTMATTER.

    Tests: YAML_FRONTMATTER detection for single-task files.
    How: Point detect_format at a single-task frontmatter fixture.
    Why: Single-task frontmatter is a distinct sub-format.
    """
    path = _FIXTURES / "yaml_frontmatter_single.md"
    result = detect_format(path)
    assert result == FormatType.YAML_FRONTMATTER


def test_detect_format_yaml_frontmatter_multi_returns_yaml_frontmatter() -> None:
    """Verify multi-task frontmatter .md is detected as YAML_FRONTMATTER.

    Tests: YAML_FRONTMATTER detection for multi-task files.
    How: Point detect_format at a multi-task frontmatter fixture.
    Why: Multi-task frontmatter uses the same format type.
    """
    path = _FIXTURES / "yaml_frontmatter_multi.md"
    result = detect_format(path)
    assert result == FormatType.YAML_FRONTMATTER


# ---------------------------------------------------------------------------
# detect_format — GLOBAL_MANIFEST
# ---------------------------------------------------------------------------


def test_detect_format_global_manifest_returns_global_manifest() -> None:
    """Verify global manifest .md is detected as GLOBAL_MANIFEST.

    Tests: GLOBAL_MANIFEST format detection.
    How: Point detect_format at the global manifest fixture.
    Why: This is the format that triggered issue #715.
    """
    path = _FIXTURES / "global_manifest.md"
    result = detect_format(path)
    assert result == FormatType.GLOBAL_MANIFEST


def test_detect_format_global_manifest_with_slug_field_returns_global_manifest(tmp_path: Path) -> None:
    """Verify slug: + tasks: frontmatter is detected as GLOBAL_MANIFEST.

    Tests: GLOBAL_MANIFEST detection with slug instead of feature.
    How: Create dynamic file with slug: field.
    Why: Global manifests may use slug instead of feature.
    """
    f = tmp_path / "tasks.md"
    f.write_text("---\nslug: my-feature\ntasks:\n  - T1: First task\n---\n\n## T1: First task\n\nSome body.\n")
    result = detect_format(f)
    assert result == FormatType.GLOBAL_MANIFEST


# ---------------------------------------------------------------------------
# detect_format — YAML_FRONTMATTER tasks-list variant
# ---------------------------------------------------------------------------


def test_detect_format_tasks_list_without_feature_returns_yaml_frontmatter() -> None:
    """Verify frontmatter with tasks: list (no feature/slug) is YAML_FRONTMATTER.

    Tests: YAML_FRONTMATTER detection for tasks-list variant.
    How: Point detect_format at the tasks-list fixture.
    Why: About 20 follow-up task files in plan/ use this structure; they must
         not raise FormatDetectionError.
    """
    path = _FIXTURES / "yaml_frontmatter_tasks_list.md"
    result = detect_format(path)
    assert result == FormatType.YAML_FRONTMATTER


def test_detect_format_tasks_list_dynamic_returns_yaml_frontmatter(tmp_path: Path) -> None:
    """Verify dynamic tasks-list frontmatter file is YAML_FRONTMATTER.

    Tests: YAML_FRONTMATTER detection for tasks-list variant via dynamic file.
    How: Write a minimal tasks-list file and call detect_format.
    Why: Confirm the detection branch works with minimal required structure.
    """
    f = tmp_path / "followup.md"
    f.write_text(
        "---\n"
        "tasks:\n"
        '  - task: "Do the thing"\n'
        "    status: pending\n"
        '    parent_task: "plan/tasks-1-something.md"\n'
        "---\n"
        "\n"
        "# Human-readable body\n"
    )
    result = detect_format(f)
    assert result == FormatType.YAML_FRONTMATTER


def test_detect_format_real_followup_file_does_not_raise() -> None:
    """Verify the actual follow-up task file that triggered this bug is detected.

    Tests: FormatDetectionError not raised for tasks-3 follow-up file.
    How: Call detect_format on the real plan file.
    Why: Regression guard — the exact file that failed before the fix.
    """
    real_file = Path("/home/ubuntulinuxqa2/repos/claude_skills/plan/tasks-3-unified-sam-task-schema-followup-1.md")
    if not real_file.exists():
        pytest.skip("Real follow-up file not present in this environment")
    result = detect_format(real_file)
    assert result == FormatType.YAML_FRONTMATTER


# ---------------------------------------------------------------------------
# detect_format — errors
# ---------------------------------------------------------------------------


def test_detect_format_nonexistent_path_raises_file_not_found(tmp_path: Path) -> None:
    """Verify FileNotFoundError for nonexistent path.

    Tests: Missing file detection.
    How: Pass a path that does not exist.
    Why: Callers depend on FileNotFoundError for missing files.
    """
    path = tmp_path / "nonexistent.yaml"
    with pytest.raises(FileNotFoundError):
        detect_format(path)


def test_detect_format_unknown_md_raises_format_detection_error(tmp_path: Path) -> None:
    """Verify FormatDetectionError for .md with no task structure.

    Tests: Unrecognized markdown format.
    How: Create .md file with no frontmatter or task headings.
    Why: Unknown formats must fail loud, not silently return wrong type.
    """
    f = tmp_path / "unknown.md"
    f.write_text("# Just a regular markdown file\n\nNo task structure here.\n")
    with pytest.raises(FormatDetectionError):
        detect_format(f)


def test_detect_format_unrecognized_extension_raises_format_detection_error(tmp_path: Path) -> None:
    """Verify FormatDetectionError for unsupported file extension.

    Tests: Unrecognized file extension detection.
    How: Create a .txt file.
    Why: Only .yaml and .md are supported formats.
    """
    f = tmp_path / "tasks.txt"
    f.write_text("some content\n")
    with pytest.raises(FormatDetectionError):
        detect_format(f)


def test_detect_format_empty_directory_raises_format_detection_error(tmp_path: Path) -> None:
    """Verify FormatDetectionError for empty directory.

    Tests: Empty directory detection.
    How: Create an empty directory.
    Why: A directory with no task files is not a valid plan.
    """
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    with pytest.raises(FormatDetectionError):
        detect_format(empty_dir)


def test_format_detection_error_includes_path_and_first_lines(tmp_path: Path) -> None:
    """Verify FormatDetectionError includes path and inspected content.

    Tests: Error message quality for debugging.
    How: Trigger the error and inspect attributes.
    Why: Error messages must contain enough info to diagnose the problem.
    """
    f = tmp_path / "weird.md"
    f.write_text("Some content\nwithout any structure\n")
    with pytest.raises(FormatDetectionError) as exc_info:
        detect_format(f)
    assert exc_info.value.path == f
    assert "Some content" in exc_info.value.first_lines


# ---------------------------------------------------------------------------
# detect_format — directory with .md files
# ---------------------------------------------------------------------------


def test_detect_format_directory_with_only_md_files_returns_directory(tmp_path: Path) -> None:
    """Verify directory with .md files (no .yaml) is detected as DIRECTORY.

    Tests: DIRECTORY format detection with .md files only.
    How: Create a directory with only .md files.
    Why: Directory format supports both .yaml and .md per-task files.
    """
    task_dir = tmp_path / "plan-dir"
    task_dir.mkdir()
    (task_dir / "task-T1.md").write_text("# Task T1\n")
    result = detect_format(task_dir)
    assert result == FormatType.DIRECTORY


# ---------------------------------------------------------------------------
# read_plan — routing
# ---------------------------------------------------------------------------


def test_read_plan_routes_pure_yaml_returns_tuple_with_format_type() -> None:
    """Verify read_plan routes PURE_YAML to yaml_reader.

    Tests: read_plan routing for PURE_YAML format.
    How: Call read_plan on YAML fixture, verify format type.
    Why: Routing must match detect_format result.
    """
    path = _FIXTURES / "pure_yaml_single.yaml"
    plan_meta, task_dicts, fmt = read_plan(path)
    assert fmt == FormatType.PURE_YAML
    assert isinstance(plan_meta, dict)
    assert isinstance(task_dicts, list)


def test_read_plan_routes_legacy_markdown_returns_tuple_with_format_type() -> None:
    """Verify read_plan routes LEGACY_MARKDOWN to legacy_reader.

    Tests: read_plan routing for LEGACY_MARKDOWN format.
    How: Call read_plan on legacy markdown fixture.
    Why: Correct routing ensures tasks are parsed by the right reader.
    """
    path = _FIXTURES / "legacy_markdown.md"
    _plan_meta, task_dicts, fmt = read_plan(path)
    assert fmt == FormatType.LEGACY_MARKDOWN
    assert len(task_dicts) == 3


def test_read_plan_routes_global_manifest_returns_tuple_with_format_type() -> None:
    """Verify read_plan routes GLOBAL_MANIFEST to manifest_reader.

    Tests: read_plan routing for GLOBAL_MANIFEST format.
    How: Call read_plan on global manifest fixture.
    Why: This is the format that triggered issue #715.
    """
    path = _FIXTURES / "global_manifest.md"
    _plan_meta, task_dicts, fmt = read_plan(path)
    assert fmt == FormatType.GLOBAL_MANIFEST
    assert len(task_dicts) == 4


def test_read_plan_routes_yaml_frontmatter_returns_tuple_with_format_type() -> None:
    """Verify read_plan routes YAML_FRONTMATTER to frontmatter_reader.

    Tests: read_plan routing for YAML_FRONTMATTER format.
    How: Call read_plan on frontmatter fixture.
    Why: Multi-task frontmatter files require a dedicated reader.
    """
    path = _FIXTURES / "yaml_frontmatter_multi.md"
    _plan_meta, task_dicts, fmt = read_plan(path)
    assert fmt == FormatType.YAML_FRONTMATTER
    assert len(task_dicts) == 3


def test_read_plan_routes_directory_returns_tuple_with_format_type() -> None:
    """Verify read_plan routes DIRECTORY to yaml_reader.

    Tests: read_plan routing for DIRECTORY format.
    How: Call read_plan on directory fixture.
    Why: Directory plans must be read with the yaml_reader.
    """
    path = _FIXTURES / "pure_yaml_directory"
    _plan_meta, task_dicts, fmt = read_plan(path)
    assert fmt == FormatType.PURE_YAML
    assert len(task_dicts) == 3
