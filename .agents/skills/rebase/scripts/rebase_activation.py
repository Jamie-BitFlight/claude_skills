"""Typed, derived evaluation of persisted rebase-skill activation evidence."""

from __future__ import annotations

import hashlib
from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from rebase_states import WorkflowState


class ActionKind(StrEnum):
    """Observable action classes used by activation evidence."""

    READ = "read"
    COMMAND = "command"
    MUTATION = "mutation"
    PROVIDER = "provider"
    TERMINAL = "terminal"


class ActionEvent(BaseModel):
    """One structured action observed in a harness transcript."""

    kind: ActionKind
    operation: str = Field(min_length=1)
    exit_code: int | None = None


class EvalCase(BaseModel):
    """One activation request and its fixture-specific observable contract."""

    id: int
    prompt: str
    expected_activation: bool
    required_terminal: str
    required_sources: list[str]
    allowed_mutations: list[str]
    allowed_provider_actions: list[str]
    exact_action_order: list[str] = Field(default_factory=list)
    expectations: list[str]


class EvalPackage(BaseModel):
    """Validated activation-evaluation package."""

    schema_version: Literal[3]
    skill_name: str
    evals: list[EvalCase]


class AcceptanceCase(BaseModel):
    """One harness/evaluation pair required by the acceptance matrix."""

    harness: str
    eval_id: int


class ActivationCaseResult(BaseModel):
    """Observed evidence for one fresh harness invocation."""

    harness: str
    model: str
    proxy: str
    session_id: str
    eval_id: int
    prompt: str
    observed_activation: bool
    loaded_sources: list[str]
    actions: list[ActionEvent]
    state_transitions: list[WorkflowState]
    final_terminal: str
    repository_head_before: str
    repository_head_after: str
    repository_status_before: str
    repository_status_after: str


class ActivationResults(BaseModel):
    """Persisted evidence plus an explicit harness/branch acceptance matrix."""

    schema_version: Literal[4]
    skill_name: str
    observed_on: str
    content_sha256: dict[str, str]
    acceptance_matrix: list[AcceptanceCase]
    cases: list[ActivationCaseResult]


def content_digest(path: Path) -> str:
    """Return the SHA-256 for one loaded instruction source.

    Returns:
        Hexadecimal SHA-256 digest.
    """
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evaluate_package_shape(package: EvalPackage, results: ActivationResults) -> list[str]:
    """Evaluate identity, uniqueness, and acceptance-matrix coverage.

    Returns:
        Every package-shape failure.
    """
    failures: list[str] = []
    evaluations = {evaluation.id: evaluation for evaluation in package.evals}
    observed = {(case.harness, case.eval_id): case for case in results.cases}
    required = {(case.harness, case.eval_id) for case in results.acceptance_matrix}
    if results.skill_name != package.skill_name:
        failures.append("result skill name differs from evaluation package")
    if len(evaluations) != len(package.evals):
        failures.append("evaluation IDs are not unique")
    if len(observed) != len(results.cases):
        failures.append("observed harness/evaluation pairs are not unique")
    if required != set(observed):
        failures.append("observed cases do not exactly cover the acceptance matrix")
    return failures


def evaluate_content_hashes(skill_root: Path, results: ActivationResults) -> list[str]:
    """Evaluate every instruction-source content binding.

    Returns:
        Every missing or stale hash failure.
    """
    failures: list[str] = []
    for relative_path, recorded_digest in results.content_sha256.items():
        path = skill_root / relative_path
        if not path.is_file() or content_digest(path) != recorded_digest:
            failures.append(f"stale or missing content hash: {relative_path}")
    return failures


def evaluate_case(case: ActivationCaseResult, evaluation: EvalCase) -> list[str]:
    """Evaluate one observed harness invocation against its request contract.

    Returns:
        Every failure for the case.
    """
    key = (case.harness, case.eval_id)
    failures: list[str] = []
    canonical_states = {state.value for state in WorkflowState}
    if case.prompt != evaluation.prompt:
        failures.append(f"prompt mismatch: {key}")
    if case.observed_activation is not evaluation.expected_activation:
        failures.append(f"activation mismatch: {key}")
    if case.final_terminal != evaluation.required_terminal:
        failures.append(f"terminal mismatch: {key}")
    if not set(evaluation.required_sources) <= set(case.loaded_sources):
        failures.append(f"required source was not loaded: {key}")
    if any(state.value not in canonical_states for state in case.state_transitions):
        failures.append(f"undeclared workflow transition: {key}")
    failures.extend(evaluate_terminal_trace(case, evaluation))
    mutations = [action.operation for action in case.actions if action.kind is ActionKind.MUTATION]
    if mutations != evaluation.allowed_mutations:
        failures.append(f"mutation contract mismatch: {key}")
    provider_actions = [action.operation for action in case.actions if action.kind is ActionKind.PROVIDER]
    if provider_actions != evaluation.allowed_provider_actions:
        failures.append(f"provider-action contract mismatch: {key}")
    if case.repository_head_before != case.repository_head_after:
        failures.append(f"repository HEAD changed: {key}")
    if case.repository_status_before != case.repository_status_after:
        failures.append(f"repository status changed: {key}")
    return failures


def evaluate_terminal_trace(case: ActivationCaseResult, evaluation: EvalCase) -> list[str]:
    """Evaluate action ordering and the terminal boundary.

    Returns:
        Every terminal-trace failure for the case.
    """
    key = (case.harness, case.eval_id)
    failures: list[str] = []
    terminal_positions = [index for index, action in enumerate(case.actions) if action.kind is ActionKind.TERMINAL]
    if len(terminal_positions) != 1:
        failures.append(f"terminal-event contract mismatch: {key}")
    else:
        terminal_position = terminal_positions[0]
        terminal_action = case.actions[terminal_position]
        if terminal_position != len(case.actions) - 1:
            failures.append(f"actions observed after terminal: {key}")
        if terminal_action.operation != case.final_terminal:
            failures.append(f"terminal event differs from final terminal: {key}")
    if evaluation.exact_action_order and [action.operation for action in case.actions] != evaluation.exact_action_order:
        failures.append(f"action-order contract mismatch: {key}")
    return failures


def evaluate_activation_results(skill_root: Path, package: EvalPackage, results: ActivationResults) -> list[str]:
    """Derive failures from expectations, actions, terminals, hashes, and unchanged state.

    Returns:
        Every observed contract failure.
    """
    failures = evaluate_package_shape(package, results)
    failures.extend(evaluate_content_hashes(skill_root, results))
    evaluations = {evaluation.id: evaluation for evaluation in package.evals}
    for case in results.cases:
        evaluation = evaluations.get(case.eval_id)
        if evaluation is None:
            failures.append(f"missing evaluation definition: {(case.harness, case.eval_id)}")
            continue
        if any(source not in results.content_sha256 for source in case.loaded_sources):
            failures.append(f"loaded source has no content hash: {(case.harness, case.eval_id)}")
        failures.extend(evaluate_case(case, evaluation))
    return failures
