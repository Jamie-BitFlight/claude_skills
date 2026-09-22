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
"""Behavioral checks for derived activation-evidence evaluation."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from rebase_activation import ActionEvent, ActionKind, ActivationResults, EvalPackage, evaluate_activation_results
from rebase_test_support import SKILL_ROOT

EVALS_PATH = SKILL_ROOT / "evals" / "evals.json"
RESULTS_PATH = SKILL_ROOT / "evals" / "activation-results.json"


def load_evidence() -> tuple[EvalPackage, ActivationResults]:
    """Load the maintained evaluation package and observed results."""
    return (
        EvalPackage.model_validate_json(EVALS_PATH.read_bytes()),
        ActivationResults.model_validate_json(RESULTS_PATH.read_bytes()),
    )


def test_current_activation_evidence_passes_derived_contract() -> None:
    """Accept fresh evidence only when every matrix case satisfies its contract."""
    package, results = load_evidence()

    assert evaluate_activation_results(SKILL_ROOT, package, results) == []


def test_continue_mutation_fails_even_if_observation_claims_activation() -> None:
    """Reject the unsafe continue attempt that the prior self-attested artifact accepted."""
    package, results = load_evidence()
    unsafe = deepcopy(results)
    case = next(case for case in unsafe.cases if case.harness == "opencode" and case.eval_id == 2)
    case.actions.append(ActionEvent(kind=ActionKind.MUTATION, operation="git rebase --continue", exit_code=128))

    failures = evaluate_activation_results(SKILL_ROOT, package, unsafe)

    assert "mutation contract mismatch: ('opencode', 2)" in failures


def test_source_edit_invalidates_persisted_activation_evidence(tmp_path: Path) -> None:
    """Bind observations to the exact instruction content that produced them."""
    package, results = load_evidence()
    copied_skill = tmp_path / "SKILL.md"
    copied_skill.write_text("changed instructions\n", encoding="utf-8")
    copied_reference = tmp_path / "references" / "rebase-edge-cases.md"
    copied_reference.parent.mkdir()
    copied_reference.write_bytes((SKILL_ROOT / "references" / "rebase-edge-cases.md").read_bytes())

    failures = evaluate_activation_results(tmp_path, package, results)

    assert "stale or missing content hash: SKILL.md" in failures


def test_acceptance_matrix_requires_exact_observed_case_coverage() -> None:
    """Reject missing and unclaimed harness observations."""
    package, results = load_evidence()
    incomplete = deepcopy(results)
    incomplete.cases.pop()

    failures = evaluate_activation_results(SKILL_ROOT, package, incomplete)

    assert "observed cases do not exactly cover the acceptance matrix" in failures
