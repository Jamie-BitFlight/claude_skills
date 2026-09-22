#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pydantic>=2.0",
#   "pytest",
#   "pytest-asyncio",
#   "pytest-cov",
#   "pytest-xdist",
# ]
# [tool.ty.environment]
# root = ["."]
# ///
"""Canonical schema and evidence-isolation checks for skill evaluations."""

from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from pr_review_models import ReviewSnapshot
from pr_review_state import load_snapshot
from pr_review_state_models import calculate_snapshot_fingerprint

SKILL_ROOT = Path(__file__).resolve().parents[1]
EVALS_PATH = SKILL_ROOT / "evals/evals.json"
EVAL_FILES = SKILL_ROOT / "evals/files"
ATTACHED_EVAL_IDS = {1, 2, 4, 5, 6, 7, 8, 9, 13}
REQUIRED_EVAL_TAGS = {
    "github-activation",
    "gitlab-activation",
    "negative-activation",
    "mixed-census",
    "question",
    "approval-only",
    "rejection",
    "bot-summary",
    "shared-cause",
    "stale-input",
    "incomplete-pagination",
    "mutation-authorization",
    "unavailable-capability",
    "new-input",
    "quiet-watch",
}
ANSWER_KEY_FIELDS = {
    "assessment",
    "assessed_inputs",
    "cluster",
    "communication",
    "communication_plan",
    "communication_states",
    "complete_cycle",
    "cycle_terminal",
    "disposition",
    "expected_projection",
    "focused_question",
    "implementation",
    "implementation_evidence",
    "implementation_states",
    "input_census",
    "kind_assessment",
    "missing_fact",
    "observed_transitions",
    "recheck",
    "resolution",
    "resolution_states",
    "semantic_kinds",
    "systemic_outcome",
    "terminal_annotations",
    "unknown_decisions",
    "verification",
    "verification_evidence",
}


def eval_inventory() -> list[dict[str, Any]]:
    """Load the grader-owned scenario inventory."""
    payload = json.loads(EVALS_PATH.read_text(encoding="utf-8"))
    assert payload["skill_name"] == "receiving-pr-reviews"
    return payload["evals"]


def nested_keys(value: object) -> Iterator[str]:
    """Yield every object key without truncating nested fixture evidence."""
    if isinstance(value, dict):
        for key, nested in value.items():
            yield key
            yield from nested_keys(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from nested_keys(nested)


def test_instruction_evals_have_unique_ids_and_required_scenarios() -> None:
    evals = eval_inventory()
    ids = [case["id"] for case in evals]
    tags = {tag for case in evals for tag in case["tags"]}

    assert ids == list(range(1, 16))
    assert len(ids) == len(set(ids))
    assert tags >= REQUIRED_EVAL_TAGS
    assert all(case["expectations"] for case in evals)


def test_each_attached_scenario_declares_only_its_own_snapshot() -> None:
    evals = eval_inventory()
    declarations = Counter(path for case in evals for path in case["files"])
    declared_files = set(declarations)
    actual_files = {path.relative_to(SKILL_ROOT).as_posix() for path in EVAL_FILES.glob("*.json")}

    assert declared_files == actual_files
    assert all(count == 1 for count in declarations.values())
    for case in evals:
        expected = [f"evals/files/case-{case['id']:02d}-snapshot.json"] if case["id"] in ATTACHED_EVAL_IDS else []
        assert case["files"] == expected
        prompt_paths = re.findall(r"evals/files/[a-z0-9-]+\.json", case["prompt"])
        assert prompt_paths == expected


@pytest.mark.parametrize("relative_path", sorted({path for case in eval_inventory() for path in case["files"]}))
def test_declared_snapshot_passes_canonical_read_only_boundary(relative_path: str) -> None:
    path = SKILL_ROOT / relative_path
    text = path.read_text(encoding="utf-8")
    payload = json.loads(text)
    snapshot = ReviewSnapshot.model_validate_json(text)

    assert load_snapshot(path) == snapshot
    assert ReviewSnapshot.model_validate(payload, strict=False) == snapshot
    assert set(payload).issubset(ReviewSnapshot.model_fields)
    assert snapshot.snapshot_complete is True
    assert snapshot.completeness.complete is True
    assert snapshot.cycle_state == "ASSESSMENT_REQUIRED"
    assert snapshot.assessments == []
    assert snapshot.clusters == []
    assert all(item.direction == "inbound" for item in snapshot.review_inputs)
    assert snapshot.outstanding_input_count == len(snapshot.review_inputs)
    assert snapshot.snapshot_fingerprint == calculate_snapshot_fingerprint(
        snapshot.target,
        snapshot.head_revision,
        snapshot.review_inputs,
        snapshot.completeness,
        revision_at=snapshot.revision_at,
        reviewability=snapshot.reviewability,
        provider_metadata=snapshot.provider_metadata,
        communicated_input_ids=snapshot.communicated_input_ids,
    )


def test_attached_snapshots_contain_no_answers_or_cross_scenario_inputs() -> None:
    input_sets: list[set[str]] = []
    targets: set[tuple[str, int]] = set()

    for case in eval_inventory():
        for relative_path in case["files"]:
            payload = json.loads((SKILL_ROOT / relative_path).read_text(encoding="utf-8"))
            snapshot = load_snapshot(SKILL_ROOT / relative_path)
            leaked_fields = set(nested_keys(payload)) & ANSWER_KEY_FIELDS
            assert leaked_fields == set()
            input_ids = {item.input_id for item in snapshot.review_inputs}
            assert input_ids
            assert all(input_ids.isdisjoint(other) for other in input_sets)
            input_sets.append(input_ids)
            target = (snapshot.provider, snapshot.target.number)
            assert target not in targets
            targets.add(target)


def test_rejection_fixture_retains_only_observed_provider_schema_facts() -> None:
    snapshot = load_snapshot(EVAL_FILES / "case-07-snapshot.json")

    assert snapshot.reviews_count == 2
    assert [review.id for review in snapshot.reviews_with_body] == ["702"]
    assert [review.state for review in snapshot.unresponded_reviews] == ["CHANGES_REQUESTED"]
    assert {item.input_id for item in snapshot.review_inputs} == {"github:review:701", "github:review:702"}
    assert all(item.provider_state == "CHANGES_REQUESTED" for item in snapshot.review_inputs)
    assert snapshot.assessments == []
    assert snapshot.clusters == []


def test_shared_cause_fixture_supplies_raw_decision_evidence_without_answers() -> None:
    snapshot = load_snapshot(EVAL_FILES / "case-09-snapshot.json")

    assert {item.input_id for item in snapshot.review_inputs} == {
        "github:thread:901",
        "github:thread:902",
        "github:thread:903",
    }
    assert {item.path for item in snapshot.review_inputs} == {
        "src/github_adapter.py",
        "src/gitlab_adapter.py",
        "tests/test_request_boundary.py",
    }
    assert all("RequestBoundary" in item.body for item in snapshot.review_inputs)
    assert snapshot.assessments == []
    assert snapshot.clusters == []


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
