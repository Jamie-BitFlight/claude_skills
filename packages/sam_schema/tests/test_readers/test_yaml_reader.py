"""Tests for sam_schema.readers.yaml_reader — PURE_YAML and DIRECTORY formats."""

from __future__ import annotations

import pathlib

import pytest
from sam_schema.core.dependencies import DependencyGraph
from sam_schema.core.models import AcceptanceCriterion, BookendResult, BookendVerification, CriterionStatus
from sam_schema.core.query import load_plan
from sam_schema.readers.detect import FormatType
from sam_schema.readers.yaml_reader import read_yaml_plan
from sam_schema.writers.yaml_writer import write_plan

# Shared fixtures directory
_FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures"


# ---------------------------------------------------------------------------
# Single-file YAML
# ---------------------------------------------------------------------------


def test_read_yaml_plan_single_file_returns_three_tasks():
    path = _FIXTURES / "pure_yaml_single.yaml"
    _plan_meta, task_dicts, _fmt = read_yaml_plan(path)
    assert len(task_dicts) == 3


def test_read_yaml_plan_single_file_returns_pure_yaml_format_type():
    path = _FIXTURES / "pure_yaml_single.yaml"
    _, _, fmt = read_yaml_plan(path)
    assert fmt == FormatType.PURE_YAML


def test_read_yaml_plan_single_file_plan_meta_has_feature():
    path = _FIXTURES / "pure_yaml_single.yaml"
    plan_meta, _, _ = read_yaml_plan(path)
    assert plan_meta.get("feature") == "auth-system"


def test_read_yaml_plan_single_file_plan_meta_has_version():
    path = _FIXTURES / "pure_yaml_single.yaml"
    plan_meta, _, _ = read_yaml_plan(path)
    assert plan_meta.get("version") == "1.0"


def test_read_yaml_plan_single_file_task_dicts_are_plain_dicts():
    path = _FIXTURES / "pure_yaml_single.yaml"
    _, task_dicts, _ = read_yaml_plan(path)
    for task in task_dicts:
        assert type(task) is dict, f"Expected plain dict, got {type(task)}"


def test_read_yaml_plan_single_file_first_task_has_correct_id():
    path = _FIXTURES / "pure_yaml_single.yaml"
    _, task_dicts, _ = read_yaml_plan(path)
    assert task_dicts[0].get("id") == "T1"


def test_read_yaml_plan_single_file_first_task_has_correct_status():
    path = _FIXTURES / "pure_yaml_single.yaml"
    _, task_dicts, _ = read_yaml_plan(path)
    assert task_dicts[0].get("status") == "complete"


def test_read_yaml_plan_single_file_second_task_has_dependency_list():
    path = _FIXTURES / "pure_yaml_single.yaml"
    _, task_dicts, _ = read_yaml_plan(path)
    deps = task_dicts[1].get("dependencies")
    assert isinstance(deps, list)
    assert "T1" in deps


def test_read_yaml_plan_single_file_tasks_list_removed_from_plan_meta():
    path = _FIXTURES / "pure_yaml_single.yaml"
    plan_meta, _, _ = read_yaml_plan(path)
    assert "tasks" not in plan_meta


# ---------------------------------------------------------------------------
# Directory format
# ---------------------------------------------------------------------------


def test_read_yaml_plan_directory_returns_three_tasks():
    path = _FIXTURES / "pure_yaml_directory"
    _, task_dicts, _ = read_yaml_plan(path)
    assert len(task_dicts) == 3


def test_read_yaml_plan_directory_returns_pure_yaml_format_type():
    path = _FIXTURES / "pure_yaml_directory"
    _, _, fmt = read_yaml_plan(path)
    assert fmt == FormatType.PURE_YAML


def test_read_yaml_plan_directory_plan_meta_has_feature_from_plan_yaml():
    path = _FIXTURES / "pure_yaml_directory"
    plan_meta, _, _ = read_yaml_plan(path)
    assert plan_meta.get("feature") == "logging-pipeline"


def test_read_yaml_plan_directory_tasks_have_ids():
    path = _FIXTURES / "pure_yaml_directory"
    _, task_dicts, _ = read_yaml_plan(path)
    task_ids = {t.get("id") for t in task_dicts}
    assert "T1" in task_ids


def test_read_yaml_plan_directory_no_plan_yaml_synthesizes_feature_from_dirname(tmp_path):
    task_dir = tmp_path / "tasks-99-my-feature"
    task_dir.mkdir()
    task_file = task_dir / "task-T1.yaml"
    task_file.write_text("id: T1\ntitle: A task\nstatus: not-started\n")
    plan_meta, task_dicts, _ = read_yaml_plan(task_dir)
    assert plan_meta.get("feature") == "my-feature"
    assert len(task_dicts) == 1


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


def test_read_yaml_plan_nonexistent_path_raises_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_yaml_plan(tmp_path / "nonexistent.yaml")


def test_read_yaml_plan_invalid_yaml_raises_value_error(tmp_path):
    f = tmp_path / "bad.yaml"
    f.write_text("feature: test\n  broken: yaml: indentation:\n    - nested\n  bad\n")
    with pytest.raises(ValueError, match="Failed to parse YAML"):
        read_yaml_plan(f)


def test_read_yaml_plan_non_mapping_top_level_raises_type_error(tmp_path):
    f = tmp_path / "list.yaml"
    f.write_text("- item1\n- item2\n")
    with pytest.raises(TypeError):
        read_yaml_plan(f)


# ---------------------------------------------------------------------------
# Integration: structured acceptance criteria parsing
# ---------------------------------------------------------------------------


def test_load_plan_with_structured_criteria_populates_acceptance_criterion_objects() -> None:
    """Verify load_plan populates AcceptanceCriterion objects from YAML.

    Tests: End-to-end parsing of acceptance-criteria-structured field.
    How: Load plan_with_bookends.yaml fixture via load_plan, check the
         acceptance_criteria_structured list contains AcceptanceCriterion
         instances with correct field values.
    Why: AC-3 requires YAML reader to parse structured criteria into models.
    """
    path = _FIXTURES / "plan_with_bookends.yaml"
    result = load_plan(path)
    criteria = result.plan.acceptance_criteria_structured

    assert len(criteria) == 2
    assert isinstance(criteria[0], AcceptanceCriterion)
    assert criteria[0].criterion_id == "AC-1"
    assert criteria[0].check_command == "uv run pytest tests/test_models.py -v"
    assert criteria[0].expected_baseline == "fail"
    assert criteria[0].expected_final == "pass"
    assert criteria[1].criterion_id == "AC-2"
    assert criteria[1].description == "Linting passes"


def test_load_plan_without_structured_criteria_returns_empty_list() -> None:
    """Verify load_plan returns empty list when no structured criteria present.

    Tests: Backward compatibility for plans without acceptance-criteria-structured.
    How: Load existing pure_yaml_single.yaml (no structured criteria), check the
         acceptance_criteria_structured field is an empty list.
    Why: Existing plans must continue to work without bookend fields.
    """
    path = _FIXTURES / "pure_yaml_single.yaml"
    result = load_plan(path)
    assert result.plan.acceptance_criteria_structured == []


def test_load_plan_with_bookends_parses_bookend_task_fields() -> None:
    """Verify load_plan parses is-bookend and bookend-type fields on tasks.

    Tests: Bookend field parsing through the full reader pipeline.
    How: Load plan_with_bookends.yaml, verify T0 has is_bookend=True and
         bookend_type='t0-baseline', T99 has bookend_type='tn-verification',
         and non-bookend tasks have defaults.
    Why: Bookend fields on tasks must survive the read pipeline.
    """
    path = _FIXTURES / "plan_with_bookends.yaml"
    result = load_plan(path)
    tasks_by_id = {t.id: t for t in result.plan.tasks}

    t0 = tasks_by_id["T0"]
    assert t0.is_bookend is True
    assert t0.bookend_type == "t0-baseline"

    t99 = tasks_by_id["T99"]
    assert t99.is_bookend is True
    assert t99.bookend_type == "tn-verification"

    t1 = tasks_by_id["T1"]
    assert t1.is_bookend is False
    assert t1.bookend_type is None


def test_write_then_read_roundtrip_preserves_structured_criteria(tmp_path: pathlib.Path) -> None:
    """Verify write-then-read roundtrip preserves acceptance-criteria-structured.

    Tests: Roundtrip fidelity of structured criteria through yaml_writer and yaml_reader.
    How: Load plan_with_bookends.yaml, write to tmp_path via write_plan, reload
         via load_plan, verify criteria count and field values match.
    Why: AC-2 roundtrip requirement: structured criteria must survive write-then-read.
    """
    source_path = _FIXTURES / "plan_with_bookends.yaml"
    original = load_plan(source_path)
    original_criteria = original.plan.acceptance_criteria_structured

    out_path = tmp_path / "roundtrip.yaml"
    write_plan(original.plan, out_path)
    reloaded = load_plan(out_path)
    reloaded_criteria = reloaded.plan.acceptance_criteria_structured

    assert len(reloaded_criteria) == len(original_criteria)
    for orig, reread in zip(original_criteria, reloaded_criteria, strict=True):
        assert reread.criterion_id == orig.criterion_id
        assert reread.check_command == orig.check_command
        assert reread.expected_baseline == orig.expected_baseline
        assert reread.expected_final == orig.expected_final
        assert reread.description == orig.description


def test_write_then_read_roundtrip_preserves_bookend_fields(tmp_path: pathlib.Path) -> None:
    """Verify write-then-read roundtrip preserves is-bookend and bookend-type.

    Tests: Bookend field fidelity through the writer and reader pipeline.
    How: Load plan_with_bookends.yaml, write and reload, verify bookend fields
         on T0 and T99 match the originals, and non-bookend tasks have defaults.
    Why: Bookend metadata must not be lost during serialization.
    """
    source_path = _FIXTURES / "plan_with_bookends.yaml"
    original = load_plan(source_path)

    out_path = tmp_path / "roundtrip_bookends.yaml"
    write_plan(original.plan, out_path)
    reloaded = load_plan(out_path)

    orig_by_id = {t.id: t for t in original.plan.tasks}
    reload_by_id = {t.id: t for t in reloaded.plan.tasks}

    for task_id in ("T0", "T99"):
        assert reload_by_id[task_id].is_bookend == orig_by_id[task_id].is_bookend
        assert reload_by_id[task_id].bookend_type == orig_by_id[task_id].bookend_type

    for task_id in ("T1", "T2"):
        assert reload_by_id[task_id].is_bookend is False
        assert reload_by_id[task_id].bookend_type is None


def test_get_ready_tasks_returns_t0_first_on_fresh_bookend_plan() -> None:
    """Verify get_ready_tasks returns T0 as the only ready task on a fresh plan.

    Tests: T0 dispatches first due to no dependencies and highest priority.
    How: Load plan_with_bookends.yaml (all tasks not-started), build dependency
         graph, query ready tasks, verify T0 is first (and only) ready task.
    Why: T0 must run before any implementation tasks; this is the core ordering
         guarantee of the bookend system.
    """
    path = _FIXTURES / "plan_with_bookends.yaml"
    result = load_plan(path)
    graph = DependencyGraph(result.plan.tasks)
    ready = graph.get_ready_tasks()

    assert len(ready) == 1
    assert ready[0].id == "T0"
    assert ready[0].is_bookend is True
    assert ready[0].bookend_type == "t0-baseline"


def test_t0_baseline_fixture_is_valid_yaml() -> None:
    """Verify t0_baseline_sample.yaml is valid YAML matching the T0 output schema.

    Tests: Fixture file structure matches architect spec section 5.3.
    How: Parse the fixture with ruamel.yaml and validate top-level fields and
         result entries against BookendResult model fields.
    Why: Sample fixtures must match the schemas agents will produce.
    """
    from sam_schema.readers._yaml_utils import load_yaml

    path = _FIXTURES / "t0_baseline_sample.yaml"
    data = load_yaml(path.read_text(encoding="utf-8"))

    assert data["feature"] == "auth-system"
    assert "captured_at" in data
    assert "plan_path" in data
    assert data["criteria_count"] == 3
    assert isinstance(data["results"], list)
    assert len(data["results"]) == 3

    first = data["results"][0]
    result = BookendResult(**{
        "criterion-id": first["criterion-id"],
        "check-command": first["check-command"],
        "exit-code": first["exit-code"],
        "stdout": first.get("stdout", ""),
        "stderr": first.get("stderr", ""),
        "timestamp": first.get("timestamp", ""),
        "duration-seconds": first.get("duration-seconds", 0.0),
    })
    assert result.criterion_id == "AC-1"
    assert result.exit_code == 1


def test_tn_verification_fixture_is_valid_yaml() -> None:
    """Verify tn_verification_sample.yaml is valid YAML matching the TN output schema.

    Tests: Fixture file structure matches architect spec section 5.4.
    How: Parse the fixture with ruamel.yaml and validate top-level fields and
         result entries against BookendVerification model fields.
    Why: Sample fixtures must match the schemas agents will produce.
    """
    from sam_schema.readers._yaml_utils import load_yaml

    path = _FIXTURES / "tn_verification_sample.yaml"
    data = load_yaml(path.read_text(encoding="utf-8"))

    assert data["feature"] == "auth-system"
    assert data["verdict"] == "PASS"
    assert data["regressions"] == 0
    assert data["newly_passing"] == 1
    assert data["criteria_count"] == 3
    assert isinstance(data["results"], list)
    assert len(data["results"]) == 3

    first = data["results"][0]
    verification = BookendVerification(**{
        "criterion-id": first["criterion-id"],
        "check-command": first["check-command"],
        "t0-exit-code": first["t0-exit-code"],
        "tn-exit-code": first["tn-exit-code"],
        "status": first["status"],
        "stdout-diff-summary": first.get("stdout-diff-summary", ""),
    })
    assert verification.criterion_id == "AC-1"
    assert verification.status == CriterionStatus.NEWLY_PASSING
    assert verification.t0_exit_code == 1
    assert verification.tn_exit_code == 0


def test_write_then_read_roundtrip_omits_default_bookend_fields(tmp_path: pathlib.Path) -> None:
    """Verify writer omits is-bookend and bookend-type when they have default values.

    Tests: YAML output does not contain noisy default bookend fields.
    How: Load pure_yaml_single.yaml (no bookend tasks), write to tmp, verify
         the output YAML text does not contain 'is-bookend' or 'bookend-type'.
    Why: Default-valued bookend fields should not clutter existing plan output.
    """
    path = _FIXTURES / "pure_yaml_single.yaml"
    result = load_plan(path)

    out_path = tmp_path / "no_bookends.yaml"
    write_plan(result.plan, out_path)
    yaml_text = out_path.read_text(encoding="utf-8")

    assert "is-bookend" not in yaml_text
    assert "bookend-type" not in yaml_text
