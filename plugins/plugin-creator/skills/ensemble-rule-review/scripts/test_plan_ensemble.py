#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pytest"]
# ///
"""Tests for the ensemble-rule-review planner.

Run: uv run --with pytest pytest test_plan_ensemble.py
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import plan_ensemble as p

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

GROUPS = {
    "1": ["no bare except", "no swallowed exceptions"],
    "2": ["no Any outside boundaries", "no legacy typing imports"],
    "3": ["functions under 50 lines", "no deep nesting"],
}


def test_rotate_assignment_is_cyclic_window() -> None:
    assignment = p.rotate_assignment(["1", "2", "3"], window=2)
    assert assignment == [["1", "2"], ["2", "3"], ["3", "1"]]


def test_redundancy_is_uniform_equal_to_window() -> None:
    assignment = p.rotate_assignment(["1", "2", "3"], window=2)
    counts = p.redundancy(assignment, ["1", "2", "3"])
    assert counts == {"1": 2, "2": 2, "3": 2}
    assert set(counts.values()) == {2}


def test_window_three_over_five_groups_uniform() -> None:
    gids = ["1", "2", "3", "4", "5"]
    counts = p.redundancy(p.rotate_assignment(gids, window=3), gids)
    assert set(counts.values()) == {3}


def test_build_plan_assigns_absolute_outfiles_per_worker() -> None:
    plans = p.build_plan(GROUPS, window=2, report_dir="/abs/reports")
    assert [pl.worker_id for pl in plans] == ["A", "B", "C"]
    assert plans[0].outfile == "/abs/reports/worker-A.md"
    assert all(pl.outfile.startswith("/abs/reports/") for pl in plans)


def test_build_plan_carries_rules_per_covered_group() -> None:
    plans = p.build_plan(GROUPS, window=2, report_dir="/abs/reports")
    worker_a = plans[0]
    # Worker A covers groups 1 and 2 — its rules must come from BOTH, keyed by group.
    assert set(worker_a.rules_by_group) == {"1", "2"}
    assert worker_a.rules_by_group["2"] == GROUPS["2"]


def test_validate_rejects_too_few_groups() -> None:
    errors = p.validate_inputs({"1": ["a"], "2": ["b"]}, window=2, report_dir="/abs")
    assert any("at least" in e for e in errors)


def test_validate_rejects_relative_report_dir() -> None:
    errors = p.validate_inputs(GROUPS, window=2, report_dir="relative/reports")
    assert any("absolute" in e for e in errors)


def test_validate_rejects_bad_window() -> None:
    assert any("window" in e for e in p.validate_inputs(GROUPS, window=1, report_dir="/abs"))
    assert any("window" in e for e in p.validate_inputs(GROUPS, window=3, report_dir="/abs"))


def test_validate_rejects_empty_group() -> None:
    errors = p.validate_inputs({"1": ["a"], "2": [], "3": ["c"]}, window=2, report_dir="/abs")
    assert any("no rules" in e for e in errors)


def test_validate_accepts_valid_inputs() -> None:
    assert p.validate_inputs(GROUPS, window=2, report_dir="/abs/reports") == []


def test_main_json_plan_round_trips(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rules_file = tmp_path / "rules.json"
    rules_file.write_text(json.dumps(GROUPS), encoding="utf-8")
    code = p.main([str(rules_file), "--report-dir", "/abs/reports", "--json"])
    assert code == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["window"] == 2
    assert plan["keep_threshold_precision"] == 2
    assert plan["redundancy"] == {"1": 2, "2": 2, "3": 2}
    assert len(plan["workers"]) == 3
    assert plan["workers"][0]["outfile"] == "/abs/reports/worker-A.md"


def test_main_errors_on_relative_report_dir(tmp_path: Path) -> None:
    rules_file = tmp_path / "rules.json"
    rules_file.write_text(json.dumps(GROUPS), encoding="utf-8")
    assert p.main([str(rules_file), "--report-dir", "rel"]) == 2


def test_main_errors_on_missing_file(tmp_path: Path) -> None:
    assert p.main([str(tmp_path / "nope.json"), "--report-dir", "/abs"]) == 2
