"""Tests for sam_schema.readers.manifest_reader — global manifest format reader."""

from __future__ import annotations

import pathlib

import pytest
from sam_schema.readers.detect import FormatType
from sam_schema.readers.manifest_reader import read_manifest_plan

_FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures"


# ---------------------------------------------------------------------------
# Basic reading from fixture
# ---------------------------------------------------------------------------


def test_read_manifest_plan_returns_four_tasks():
    path = _FIXTURES / "global_manifest.md"
    _, task_dicts, _ = read_manifest_plan(path)
    assert len(task_dicts) == 4


def test_read_manifest_plan_returns_global_manifest_format_type():
    path = _FIXTURES / "global_manifest.md"
    _, _, fmt = read_manifest_plan(path)
    assert fmt == FormatType.GLOBAL_MANIFEST


def test_read_manifest_plan_plan_meta_has_feature_from_slug():
    # Fixture uses slug: not feature: — reader normalizes slug -> feature
    path = _FIXTURES / "global_manifest.md"
    plan_meta, _, _ = read_manifest_plan(path)
    assert plan_meta.get("feature") == "data-pipeline-optimization"


def test_read_manifest_plan_plan_meta_does_not_contain_tasks_key():
    path = _FIXTURES / "global_manifest.md"
    plan_meta, _, _ = read_manifest_plan(path)
    assert "tasks" not in plan_meta


# ---------------------------------------------------------------------------
# Task ID and title extraction
# ---------------------------------------------------------------------------


def test_read_manifest_plan_task_ids_match_expected_set():
    path = _FIXTURES / "global_manifest.md"
    _, task_dicts, _ = read_manifest_plan(path)
    ids = {t.get("task") for t in task_dicts}
    assert ids == {"T1", "T2", "T3", "T4"}


def test_read_manifest_plan_first_task_title_is_correct():
    path = _FIXTURES / "global_manifest.md"
    _, task_dicts, _ = read_manifest_plan(path)
    first = next(t for t in task_dicts if t.get("task") == "T1")
    assert first.get("title") == "Refactor batch processor"


def test_read_manifest_plan_tasks_have_default_status_not_started():
    path = _FIXTURES / "global_manifest.md"
    _, task_dicts, _ = read_manifest_plan(path)
    for task in task_dicts:
        assert task.get("status") == "not-started"


# ---------------------------------------------------------------------------
# Prose body merging — ## TN: heading format
# ---------------------------------------------------------------------------


def test_read_manifest_plan_tasks_have_description_from_body_sections():
    path = _FIXTURES / "global_manifest.md"
    _, task_dicts, _ = read_manifest_plan(path)
    # T1 has a prose body section in the fixture
    t1 = next(t for t in task_dicts if t.get("task") == "T1")
    assert t1.get("description")


# ---------------------------------------------------------------------------
# Hybrid format — global manifest frontmatter + per-task YAML blocks in body
# ---------------------------------------------------------------------------


def test_read_manifest_plan_hybrid_body_task_blocks_provide_description(tmp_path: pathlib.Path) -> None:
    """Verify per-task YAML blocks in body populate description via ## Context section.

    Tests: Hybrid format — body YAML blocks + prose extraction.
    How: Write a manifest with simple {TN: title} frontmatter and a per-task YAML
         block + ## Context section in the body.
    Why: Some plan files (e.g. tasks-1-backlog-state-reconciliation.md) use this
         hybrid structure.  Before the fix, description was always empty.
    """
    content = (
        "---\n"
        "feature: hybrid-test\n"
        "tasks:\n"
        "  - T1: First task\n"
        "---\n"
        "\n"
        "# Plan header\n"
        "\n"
        "---\n"
        "\n"
        "---\n"
        "task: T1\n"
        "title: First task\n"
        "status: not-started\n"
        "agent: test-agent\n"
        "priority: 1\n"
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
    )
    f = tmp_path / "tasks-1-hybrid-test.md"
    f.write_text(content)
    _, task_dicts, _ = read_manifest_plan(f)
    assert len(task_dicts) == 1
    t1 = task_dicts[0]
    assert t1.get("description") == "This is the context for T1."
    assert "Criterion one" in (t1.get("acceptance-criteria") or "")


def test_read_manifest_plan_hybrid_body_task_blocks_provide_agent_field(tmp_path: pathlib.Path) -> None:
    """Verify per-task YAML blocks in body provide structured fields like agent.

    Tests: Hybrid format structured field merging (agent, priority).
    How: Write manifest with simple frontmatter entry and body YAML block with agent field.
    Why: Body YAML blocks provide extended metadata absent from simple frontmatter entries.
    """
    content = (
        "---\n"
        "feature: hybrid-agent-test\n"
        "tasks:\n"
        "  - T1: First task\n"
        "---\n"
        "\n"
        "---\n"
        "\n"
        "---\n"
        "task: T1\n"
        "title: First task\n"
        "status: not-started\n"
        "agent: python3-development:python-cli-architect\n"
        "priority: 1\n"
        "complexity: high\n"
        "---\n"
        "\n"
        "## Context\n"
        "\n"
        "Context text here.\n"
    )
    f = tmp_path / "tasks-1-hybrid-agent.md"
    f.write_text(content)
    _, task_dicts, _ = read_manifest_plan(f)
    t1 = task_dicts[0]
    assert t1.get("agent") == "python3-development:python-cli-architect"
    assert t1.get("priority") == 1
    assert t1.get("complexity") == "high"


def test_read_manifest_plan_hybrid_frontmatter_status_overrides_body_block(tmp_path: pathlib.Path) -> None:
    """Verify frontmatter entry status takes precedence over body YAML block status.

    Tests: Merge priority — frontmatter entry fields win over body block fields.
    How: Set status in both frontmatter full-dict entry and body YAML block with
         different values.
    Why: The frontmatter is the authoritative registry; body blocks fill gaps only.
    """
    content = (
        "---\n"
        "feature: precedence-test\n"
        "tasks:\n"
        "  - id: T1\n"
        "    title: First task\n"
        "    status: complete\n"
        "---\n"
        "\n"
        "---\n"
        "\n"
        "---\n"
        "task: T1\n"
        "title: First task\n"
        "status: not-started\n"
        "agent: test-agent\n"
        "---\n"
        "\n"
        "## Context\n"
        "\n"
        "Context text.\n"
    )
    f = tmp_path / "tasks-1-precedence.md"
    f.write_text(content)
    _, task_dicts, _ = read_manifest_plan(f)
    t1 = task_dicts[0]
    # Frontmatter says complete; body block says not-started — frontmatter wins
    assert t1.get("status") == "complete"
    # But agent from the body block fills the gap
    assert t1.get("agent") == "test-agent"


def test_read_manifest_plan_hybrid_body_round_trip(tmp_path: pathlib.Path) -> None:
    """Verify body content survives the read -> write round-trip for the hybrid format.

    Tests: Hybrid format read -> YAML write round-trip.
    How: Build a manifest with per-task YAML blocks + prose in body, load through
         load_plan, write to YAML, verify description/acceptance-criteria/verification-steps
         are present in the YAML output.
    Why: This is the primary regression guard for the fix — the exact scenario where
         body content was silently discarded.
    """
    from sam_schema.core.query import load_plan
    from sam_schema.writers.yaml_writer import write_plan

    content = (
        "---\n"
        "feature: round-trip-test\n"
        "tasks:\n"
        "  - T1: State handler helpers\n"
        "  - T2: Core reconciliation\n"
        "---\n"
        "\n"
        "# Plan header\n"
        "\n"
        "---\n"
        "\n"
        "---\n"
        "task: T1\n"
        "title: State handler helpers\n"
        "status: not-started\n"
        "agent: python3-development:python-cli-architect\n"
        "priority: 1\n"
        "complexity: low\n"
        "---\n"
        "\n"
        "## Context\n"
        "\n"
        "Add is_terminal_state() and find_valid_path() to state_handler.py.\n"
        "\n"
        "## Acceptance Criteria\n"
        "\n"
        '1. is_terminal_state("done") returns True\n'
        "2. find_valid_path() returns None for unreachable states\n"
        "\n"
        "## Verification Steps\n"
        "\n"
        '1. uv run python -c "from state_handler import is_terminal_state; print(PASS)"\n'
        "\n"
        "---\n"
        "\n"
        "---\n"
        "task: T2\n"
        "title: Core reconciliation\n"
        "status: not-started\n"
        "agent: python3-development:python-cli-architect\n"
        "priority: 2\n"
        "dependencies:\n"
        "  - T1\n"
        "---\n"
        "\n"
        "## Context\n"
        "\n"
        "Add reconciliation functions to backlog.py.\n"
        "\n"
        "## Acceptance Criteria\n"
        "\n"
        "1. ReconcileResult dataclass exists\n"
    )
    md_file = tmp_path / "tasks-1-round-trip-test.md"
    md_file.write_text(content)

    # Verify raw read
    _, task_dicts, _ = read_manifest_plan(md_file)
    t1 = next(t for t in task_dicts if t.get("task") == "T1")
    t2 = next(t for t in task_dicts if t.get("task") == "T2")
    assert t1.get("description"), "T1 description must be non-empty after read"
    assert t1.get("acceptance-criteria"), "T1 acceptance-criteria must be non-empty after read"
    assert t1.get("verification-steps"), "T1 verification-steps must be non-empty after read"
    assert t2.get("description"), "T2 description must be non-empty after read"
    assert t2.get("acceptance-criteria"), "T2 acceptance-criteria must be non-empty after read"

    # Verify YAML write round-trip
    result = load_plan(md_file)
    out_yaml = tmp_path / "out.yaml"
    write_plan(result.plan, out_yaml)
    yaml_content = out_yaml.read_text()

    assert "is_terminal_state" in yaml_content, "T1 description content must survive YAML write"
    assert "acceptance-criteria" in yaml_content, "acceptance-criteria field must be in YAML output"
    assert "verification-steps" in yaml_content, "verification-steps field must be in YAML output"
    assert "ReconcileResult" in yaml_content, "T2 acceptance-criteria content must survive YAML write"


def test_read_manifest_plan_hybrid_real_file_body_content_non_empty() -> None:
    """Verify the real tasks-1-backlog-state-reconciliation.md has non-empty body fields.

    Tests: Real-world hybrid manifest file produces tasks with populated body fields.
    How: Load the real plan file and check T1's description, acceptance_criteria,
         and verification_steps are non-empty.
    Why: This is the exact file that triggered the bug report. Regression guard.
    """
    from sam_schema.core.query import load_plan

    real_file = pathlib.Path("/home/ubuntulinuxqa2/repos/claude_skills/plan/tasks-1-backlog-state-reconciliation.md")
    if not real_file.exists():
        pytest.skip("Real manifest file not present in this environment")

    result = load_plan(real_file)
    t1 = next(t for t in result.plan.tasks if t.id == "T1")
    assert len(t1.description) > 0, "T1 description must be non-empty"
    assert len(t1.acceptance_criteria) > 0, "T1 acceptance_criteria must be non-empty"
    assert len(t1.verification_steps) > 0, "T1 verification_steps must be non-empty"


# ---------------------------------------------------------------------------
# Full task dict format in frontmatter tasks list
# ---------------------------------------------------------------------------


def test_read_manifest_plan_full_task_dict_entry_preserves_fields(tmp_path):
    # A manifest where tasks: list contains full task dicts (not just {TN: title})
    content = (
        "---\n"
        "feature: full-dict-test\n"
        "tasks:\n"
        "  - id: T1\n"
        "    title: First task\n"
        "    status: in-progress\n"
        "    priority: 1\n"
        "---\n"
        "\n"
        "## T1: First task\n"
        "\n"
        "Some prose here.\n"
    )
    f = tmp_path / "manifest.md"
    f.write_text(content)
    _, task_dicts, _ = read_manifest_plan(f)
    assert len(task_dicts) == 1
    t = task_dicts[0]
    assert t.get("status") == "in-progress"
    assert t.get("priority") == 1


# ---------------------------------------------------------------------------
# Feature name synthesis from filename
# ---------------------------------------------------------------------------


def test_read_manifest_plan_synthesizes_feature_from_filename_when_no_feature_field(tmp_path):
    content = "---\nversion: '1.0'\ntasks:\n  - T1: A task\n---\n\n## T1: A task\n\nBody.\n"
    f = tmp_path / "tasks-3-some-feature.md"
    f.write_text(content)
    plan_meta, _, _ = read_manifest_plan(f)
    assert plan_meta.get("feature") == "some-feature"


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


def test_read_manifest_plan_nonexistent_path_raises_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_manifest_plan(tmp_path / "missing.md")


def test_read_manifest_plan_no_frontmatter_raises_value_error(tmp_path):
    f = tmp_path / "no_fm.md"
    f.write_text("# Just a heading\n\nNo frontmatter.\n")
    with pytest.raises(ValueError, match="frontmatter"):
        read_manifest_plan(f)


def test_read_manifest_plan_no_closing_delimiter_raises_value_error(tmp_path):
    f = tmp_path / "unclosed.md"
    f.write_text("---\nfeature: test\ntasks:\n  - T1: A task\n")
    with pytest.raises(ValueError, match="closing"):
        read_manifest_plan(f)


def test_read_manifest_plan_no_tasks_list_raises_value_error(tmp_path):
    f = tmp_path / "no_tasks.md"
    f.write_text("---\nfeature: test\n---\n\nNo tasks list.\n")
    with pytest.raises(ValueError, match="tasks"):
        read_manifest_plan(f)


def test_read_manifest_plan_tasks_not_a_list_raises_type_error(tmp_path):
    f = tmp_path / "bad_tasks.md"
    f.write_text("---\nfeature: test\ntasks: not-a-list\n---\n\nBody.\n")
    with pytest.raises(TypeError):
        read_manifest_plan(f)


# ---------------------------------------------------------------------------
# Edge cases — non-dict entry skipping
# ---------------------------------------------------------------------------


def test_read_manifest_plan_non_dict_task_entry_skipped(tmp_path: pathlib.Path) -> None:
    """Verify non-dict entries in tasks list are skipped.

    Tests: Non-dict task entry handling.
    How: Include a string entry in the tasks list.
    Why: Malformed entries must not crash the reader.
    """
    content = (
        "---\n"
        "feature: skip-test\n"
        "tasks:\n"
        "  - T1: First task\n"
        "  - just a string\n"
        "  - T2: Second task\n"
        "---\n"
        "\n"
        "## T1: First task\n\nBody 1.\n"
        "\n"
        "## T2: Second task\n\nBody 2.\n"
    )
    f = tmp_path / "manifest.md"
    f.write_text(content)
    _, task_dicts, _ = read_manifest_plan(f)
    # The string entry is skipped; only T1 and T2 are returned
    ids = {t.get("task") for t in task_dicts}
    assert "T1" in ids
    assert "T2" in ids


def test_read_manifest_plan_multi_key_dict_entry_skipped(tmp_path: pathlib.Path) -> None:
    """Verify multi-key dict without id/task is skipped.

    Tests: Multi-key dict without task identifiers.
    How: Include a dict with two keys but no 'id' or 'task'.
    Why: Multi-key entries that aren't full task dicts must be skipped.
    """
    content = (
        "---\n"
        "feature: multi-key-test\n"
        "tasks:\n"
        "  - T1: First task\n"
        "  - foo: bar\n"
        "    baz: qux\n"
        "---\n"
        "\n"
        "## T1: First task\n\nBody.\n"
    )
    f = tmp_path / "manifest.md"
    f.write_text(content)
    _, task_dicts, _ = read_manifest_plan(f)
    assert len(task_dicts) == 1
    assert task_dicts[0].get("task") == "T1"


def test_read_manifest_plan_full_dict_with_task_key(tmp_path: pathlib.Path) -> None:
    """Verify full task dict with 'task' key (not 'id') works.

    Tests: Full task dict format with 'task' key.
    How: Write manifest with 'task: T1' in dict entry.
    Why: Both 'id' and 'task' keys must be accepted.
    """
    content = (
        "---\n"
        "feature: task-key-test\n"
        "tasks:\n"
        "  - task: T1\n"
        "    title: First task\n"
        "    status: complete\n"
        "---\n"
        "\n"
        "## T1: First task\n\nProse body.\n"
    )
    f = tmp_path / "manifest.md"
    f.write_text(content)
    _, task_dicts, _ = read_manifest_plan(f)
    assert len(task_dicts) == 1
    assert task_dicts[0].get("task") == "T1"
    assert task_dicts[0].get("status") == "complete"


def test_read_manifest_plan_full_dict_without_prose_omits_description(tmp_path: pathlib.Path) -> None:
    """Verify full task dict without matching prose section has no description.

    Tests: Full task dict entry with no matching body section.
    How: Write manifest with task dict but no ## T1 section in body.
    Why: Tasks without prose sections must not get empty descriptions.
    """
    content = (
        "---\n"
        "feature: no-prose-test\n"
        "tasks:\n"
        "  - id: T1\n"
        "    title: First task\n"
        "    status: not-started\n"
        "---\n"
        "\n"
        "# Overview\n\nNo task headings here.\n"
    )
    f = tmp_path / "manifest.md"
    f.write_text(content)
    _, task_dicts, _ = read_manifest_plan(f)
    assert len(task_dicts) == 1
    # description not set because no matching prose section
    assert task_dicts[0].get("description") is None or task_dicts[0].get("description") == ""


def test_read_manifest_plan_frontmatter_non_mapping_raises_type_error(tmp_path: pathlib.Path) -> None:
    """Verify TypeError when frontmatter is not a YAML mapping.

    Tests: Non-mapping frontmatter detection.
    How: Write frontmatter as a YAML list instead of a dict.
    Why: Frontmatter must be a mapping; list is a format error.
    """
    content = "---\n- item1\n- item2\n---\n\nBody.\n"
    f = tmp_path / "non_mapping.md"
    f.write_text(content)
    with pytest.raises(TypeError):
        read_manifest_plan(f)


def test_read_manifest_plan_yaml_parse_error_raises_value_error(tmp_path: pathlib.Path) -> None:
    """Verify ValueError when frontmatter YAML is invalid.

    Tests: Invalid YAML detection in manifest frontmatter.
    How: Write syntactically broken YAML.
    Why: Invalid YAML must be detected and reported.
    """
    content = "---\n  bad: yaml: indentation:\n    - nested\n  bad\n---\n\nBody.\n"
    f = tmp_path / "bad_yaml.md"
    f.write_text(content)
    with pytest.raises(ValueError, match="Failed to parse YAML"):
        read_manifest_plan(f)
