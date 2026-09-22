#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pydantic>=2.0",
#   "pytest",
# ]
# [tool.ty.environment]
# root = ["."]
# ///
"""Rename and merge-topology scenarios for the accounted rebase workflow."""

from __future__ import annotations

from pathlib import Path

from rebase_test_support import commit_file, initialize_repository, run_git
from test_rebase_scenarios import (
    CandidateFixture,
    assert_gate_precedes_rebase,
    begin_scenario,
    finish_scenario,
    scenario_plan_data,
    start_rebase,
    validate_plan_event,
)


def test_rename_edit_adapts_feature_change_to_target_path(tmp_path: Path) -> None:
    """Replay a branch edit through a target rename and verify the renamed result."""
    repository = tmp_path / "rename-edit"
    initialize_repository(repository)
    commit_file(repository, "old.py", "value = 1\n", "add old path")
    merge_base = run_git(repository, "rev-parse", "HEAD").stdout.strip()
    run_git(repository, "switch", "-c", "feature")
    candidate = commit_file(repository, "old.py", "value = 2\n", "edit old path")
    run_git(repository, "switch", "main")
    run_git(repository, "mv", "old.py", "new.py")
    run_git(repository, "commit", "-m", "rename path")
    target_oid = run_git(repository, "rev-parse", "HEAD").stdout.strip()
    run_git(repository, "switch", "feature")

    evidence = begin_scenario(repository)
    plan = validate_plan_event(
        repository,
        scenario_plan_data(
            old_tip=candidate,
            target_oid=target_oid,
            merge_base_oid=merge_base,
            candidates=[CandidateFixture(oid=candidate, parents=[merge_base], paths=["old.py"], disposition="ADAPT")],
        ),
        evidence,
    )
    assert start_rebase(repository, plan, evidence) == 0

    assert_gate_precedes_rebase(evidence)
    assert not (repository / "old.py").exists()
    assert (repository / "new.py").read_text(encoding="utf-8") == "value = 2\n"
    finish_scenario(repository, evidence)


def test_merge_candidate_requires_policy_before_preserving_topology(tmp_path: Path) -> None:
    """Block an unbound merge policy, then preserve topology under a validated plan."""
    repository = tmp_path / "merge-policy"
    merge_base = initialize_repository(repository)
    run_git(repository, "switch", "-c", "feature")
    first_parent = commit_file(repository, "feature.txt", "feature\n", "feature change")
    run_git(repository, "switch", "-c", "side", merge_base)
    side_parent = commit_file(repository, "side.txt", "side\n", "side change")
    run_git(repository, "switch", "feature")
    run_git(repository, "merge", "--no-ff", "side", "-m", "merge side")
    merge_candidate = run_git(repository, "rev-parse", "HEAD").stdout.strip()
    run_git(repository, "switch", "main")
    commit_file(repository, "target.txt", "target\n", "target change")
    target_oid = run_git(repository, "rev-parse", "HEAD").stdout.strip()
    run_git(repository, "switch", "feature")

    data = scenario_plan_data(
        old_tip=merge_candidate,
        target_oid=target_oid,
        merge_base_oid=merge_base,
        candidates=[
            CandidateFixture(oid=first_parent, parents=[merge_base], paths=["feature.txt"]),
            CandidateFixture(oid=side_parent, parents=[merge_base], paths=["side.txt"]),
            CandidateFixture(
                oid=merge_candidate, parents=[first_parent, side_parent], paths=["feature.txt", "side.txt"]
            ),
        ],
    )
    data["merge_policy"] = "PRESERVE_TOPOLOGY"
    evidence = begin_scenario(repository)
    plan = validate_plan_event(repository, data, evidence)
    assert start_rebase(repository, plan, evidence, preserve_merges=True) == 0

    assert_gate_precedes_rebase(evidence)
    parent_records = run_git(repository, "rev-list", "--parents", f"{target_oid}..feature").stdout.splitlines()
    assert any(len(record.split()) > 2 for record in parent_records)
    finish_scenario(repository, evidence)
