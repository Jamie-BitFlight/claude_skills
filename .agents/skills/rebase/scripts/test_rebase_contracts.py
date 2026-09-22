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
"""Focused plan-input and workflow-state contract checks."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from rebase_plan import RebasePlan
from rebase_states import StateKind, WorkflowState, workflow_state_definitions
from test_rebase_plan import valid_plan_data


def test_repository_without_instruction_file_records_completed_empty_search() -> None:
    """Accept an explicit instruction search whose candidates are all absent."""
    data = valid_plan_data()
    data["repository_instruction_search"] = [
        {"path": "AGENTS.md", "present": False},
        {"path": ".claude/CLAUDE.md", "present": False},
    ]
    data["repository_instruction_sources"] = []
    data["repository_preflights"] = []
    data["required_preflights"] = []

    plan = RebasePlan.model_validate(data)

    assert plan.repository_instruction_sources == []


def test_instruction_sources_must_match_search_evidence() -> None:
    """Reject invented or omitted repository instruction sources."""
    data = valid_plan_data()
    data["repository_instruction_sources"] = []

    with pytest.raises(ValidationError, match="instruction-search evidence"):
        RebasePlan.model_validate(data)


def test_workflow_state_source_includes_every_reviewed_state() -> None:
    """Keep one typed state vocabulary and transition contract."""
    definitions = workflow_state_definitions()

    assert WorkflowState.READY_TO_ANALYZE in definitions
    assert WorkflowState.BLOCKED_COMMAND_FAILED in definitions
    assert WorkflowState.BLOCKED_PREFLIGHT_FAILED in definitions
    assert WorkflowState.BLOCKED_UNRELATED_HISTORIES in definitions
    assert WorkflowState.NO_ACTIVE_REBASE in definitions
    assert WorkflowState.PLAN_INVALID in definitions
    assert all(state.kind in {StateKind.TRANSITION, StateKind.TERMINAL} for state in definitions.values())
    assert all(state.condition and state.next_action and state.artifact_policy for state in definitions.values())
    assert definitions[WorkflowState.PLAN_INVALID].kind is StateKind.TERMINAL
    assert "End this invocation" in definitions[WorkflowState.PLAN_INVALID].next_action
    assert definitions[WorkflowState.REPLAN_REF_DRIFT].kind is StateKind.TERMINAL
    assert "without recovery, plan, or replay" in definitions[WorkflowState.REPLAN_REF_DRIFT].artifact_policy
    assert "later invocation" in definitions[WorkflowState.REPLAN_REF_DRIFT].next_action


def test_validation_failure_freezes_history_until_a_new_authorized_plan() -> None:
    """Make failed replay verification a single-use terminal, not a reset-and-retry loop."""
    failed = workflow_state_definitions()[WorkflowState.REBASE_COMPLETE_VALIDATION_FAILED]

    assert "no further history mutation" in failed.next_action
    assert "explicit recovery decision" in failed.next_action
    assert "newly validated plan" in failed.next_action
    assert "rewritten branch" in failed.artifact_policy
    assert "recovery ref" in failed.artifact_policy
    assert "through the terminal" in failed.artifact_policy
