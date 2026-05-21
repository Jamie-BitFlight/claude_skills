"""Tests for quality_gates.py — phase definitions and plan builder.

Verifies that _PHASE_DEFINITIONS includes the T0 Multi-Perspective Review phase
and that build_quality_gate_plan emits it as the first task in the generated YAML.
"""

from __future__ import annotations

import io

from ruamel.yaml import YAML
from sam_schema.core.quality_gates import _PHASE_DEFINITIONS, _phase_body, build_quality_gate_plan


def _parse_yaml(text: str) -> dict:
    yaml = YAML()
    return yaml.load(io.StringIO(text))


# ---------------------------------------------------------------------------
# _PHASE_DEFINITIONS structure
# ---------------------------------------------------------------------------


class TestPhaseDefinitions:
    """_PHASE_DEFINITIONS includes the T0 phase before T1."""

    def test_t0_is_first_phase(self) -> None:
        assert _PHASE_DEFINITIONS[0]["id"] == "T0"

    def test_t0_title(self) -> None:
        t0 = _PHASE_DEFINITIONS[0]
        assert t0["title"] == "Multi-Perspective Review"

    def test_t0_phase_number(self) -> None:
        t0 = _PHASE_DEFINITIONS[0]
        assert t0["phase"] == 0

    def test_t0_dependencies_empty(self) -> None:
        t0 = _PHASE_DEFINITIONS[0]
        assert t0["dependencies"] == []

    def test_t0_agent(self) -> None:
        t0 = _PHASE_DEFINITIONS[0]
        assert t0["agent"] == "task-worker"

    def test_t1_still_second(self) -> None:
        assert _PHASE_DEFINITIONS[1]["id"] == "T1"

    def test_t1_dependencies_unchanged(self) -> None:
        t1 = _PHASE_DEFINITIONS[1]
        assert t1["dependencies"] == []

    def test_all_seven_phases_present(self) -> None:
        ids = [p["id"] for p in _PHASE_DEFINITIONS]
        assert ids == ["T0", "T1", "T2", "T3", "T4", "T5", "T6"]


# ---------------------------------------------------------------------------
# _phase_body for phase 0
# ---------------------------------------------------------------------------


class TestPhaseBody:
    """_phase_body(phase=0, ...) returns the multi-perspective review body."""

    def test_phase_0_body_contains_skill_invocation(self) -> None:
        body = _phase_body(0, "P001")
        assert "dh:multi-perspective-review" in body

    def test_phase_0_body_contains_impl_plan_address(self) -> None:
        body = _phase_body(0, "Pabcdef01")
        assert "Pabcdef01" in body

    def test_phase_0_body_has_phase_header(self) -> None:
        body = _phase_body(0, "P001")
        assert "Quality Gate Phase 0" in body

    def test_phase_0_body_contains_diff_arg(self) -> None:
        body = _phase_body(0, "P001")
        assert "--diff" in body

    def test_phase_0_body_contains_issue_arg_when_provided(self) -> None:
        body = _phase_body(0, "P001", issue="42")
        assert "--issue 42" in body

    def test_phase_0_body_omits_issue_arg_when_none(self) -> None:
        body = _phase_body(0, "P001", issue=None)
        assert "--issue" not in body

    def test_phase_1_body_unchanged(self) -> None:
        body = _phase_body(1, "P001")
        assert "Code Review" in body
        assert "P001" in body


# ---------------------------------------------------------------------------
# build_quality_gate_plan output
# ---------------------------------------------------------------------------


class TestBuildQualityGatePlan:
    """build_quality_gate_plan emits 7 tasks with T0 first."""

    def test_plan_contains_seven_tasks(self) -> None:
        plan = _parse_yaml(build_quality_gate_plan(slug="test-feature", issue="42", impl_plan_address="P001"))
        assert len(plan["tasks"]) == 7

    def test_first_task_is_t0(self) -> None:
        plan = _parse_yaml(build_quality_gate_plan(slug="test-feature", issue="42", impl_plan_address="P001"))
        assert plan["tasks"][0]["id"] == "T0"

    def test_t0_task_title(self) -> None:
        plan = _parse_yaml(build_quality_gate_plan(slug="test-feature", issue="42", impl_plan_address="P001"))
        assert plan["tasks"][0]["title"] == "Multi-Perspective Review"

    def test_t1_task_second(self) -> None:
        plan = _parse_yaml(build_quality_gate_plan(slug="test-feature", issue="42", impl_plan_address="P001"))
        assert plan["tasks"][1]["id"] == "T1"

    def test_t1_dependencies_unchanged(self) -> None:
        plan = _parse_yaml(build_quality_gate_plan(slug="test-feature", issue="42", impl_plan_address="P001"))
        t1 = plan["tasks"][1]
        assert t1["dependencies"] == []

    def test_t0_body_contains_skill_invocation(self) -> None:
        plan = _parse_yaml(build_quality_gate_plan(slug="test-feature", issue="42", impl_plan_address="P001"))
        t0_body = plan["tasks"][0]["body"]
        assert "dh:multi-perspective-review" in t0_body

    def test_plan_feature_slug(self) -> None:
        yaml_text = build_quality_gate_plan(slug="my-feature", issue=None, impl_plan_address="P002")
        plan = _parse_yaml(yaml_text)
        assert plan["feature"] == "my-feature"
