#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pydantic>=2.0",
#   "pytest",
#   "pytest-asyncio",
#   "pytest-cov",
#   "pytest-mock",
#   "pytest-xdist",
#   "typer",
# ]
# [tool.ty.environment]
# root = ["."]
# ///
"""Tests for the exhaustive review-cycle completion gate."""

from __future__ import annotations

import pytest

from pr_review_models import ReviewSnapshot
from pr_review_state import ReviewAuthorizationError, evaluate_review_complete
from pr_review_state_models import (
    ProviderInputIdentity,
    ReviewCapabilities,
    ReviewCycleState,
    calculate_snapshot_fingerprint,
)
from review_test_fixtures import (
    canonical_input as review_input,
    canonical_snapshot as snapshot,
    ready_cycle,
    snapshot_with_communication,
    state_for_input,
)


def test_review_complete_requires_provider_backed_per_input_lifecycle() -> None:
    snapshot_value = snapshot_with_communication()
    snapshot_value = snapshot_value.model_copy(update={"unresolved_count": 0, "outstanding_input_count": 0})
    cycle_value = ready_cycle().model_copy(
        update={
            "snapshot_fingerprint": snapshot_value.snapshot_fingerprint,
            "recheck_snapshot_fingerprint": snapshot_value.snapshot_fingerprint,
            "communication_states": {review_input().input_id: "completed"},
            "resolution_states": {review_input().input_id: "resolved"},
            "terminal_annotations": {review_input().input_id: "Implemented, verified, communicated, and resolved."},
        }
    )

    completed = evaluate_review_complete(snapshot_value, cycle_value)

    assert completed.cycle_state == "REVIEW_COMPLETE"
    assert completed.cycle_terminal == "review_complete"


def processed_codex_approval_state() -> tuple[ReviewSnapshot, ReviewCycleState]:
    """Return a fully assessed, communicated, and terminal Codex approval."""
    approval = review_input("github:reaction:99").model_copy(
        update={
            "provider_ids": ProviderInputIdentity(object_id="99"),
            "source_kind": "reaction",
            "kinds": {"approval"},
            "location": "top_level",
            "body": "+1",
            "stable_reference": "https://github.com/acme/widgets/pull/17",
            "provider_state": "approved",
            "capabilities": ReviewCapabilities(
                can_reply=False, can_resolve=False, can_comment=True, unavailable=["reply", "resolve"]
            ),
            "thread_id": None,
        }
    )
    assessment = (
        ready_cycle()
        .assessments[0]
        .model_copy(
            update={
                "input_id": approval.input_id,
                "semantic_kinds": {"approval"},
                "kind_assessment": "approval_assessed",
            }
        )
    )
    snapshot_value, cycle_value = state_for_input(approval, assessment)
    communicated = {approval.input_id}
    fingerprint = calculate_snapshot_fingerprint(
        snapshot_value.target,
        snapshot_value.head_revision,
        [approval],
        snapshot_value.completeness,
        revision_at=snapshot_value.revision_at,
        reviewability=snapshot_value.reviewability,
        provider_metadata=snapshot_value.provider_metadata,
        communicated_input_ids=communicated,
    )
    snapshot_value = snapshot_value.model_copy(
        update={
            "snapshot_fingerprint": fingerprint,
            "unresolved_count": 0,
            "outstanding_input_count": 0,
            "codex_approved": True,
            "communicated_input_ids": communicated,
        }
    )
    cycle_value = cycle_value.model_copy(
        update={
            "snapshot_fingerprint": fingerprint,
            "recheck_snapshot_fingerprint": fingerprint,
            "input_census": [approval.input_id],
            "clusters": [
                cycle_value.clusters[0].model_copy(
                    update={"input_ids": [approval.input_id], "resolution_policy": "unavailable"}
                )
            ],
            "communication_states": {approval.input_id: "completed"},
            "resolution_states": {approval.input_id: "unavailable"},
            "implementation_states": {approval.input_id: "not_required"},
            "terminal_annotations": {approval.input_id: "Approval assessed and communicated."},
        }
    )
    return snapshot_value, cycle_value


def test_review_complete_accepts_fully_processed_codex_approval() -> None:
    snapshot_value, cycle_value = processed_codex_approval_state()

    completed = evaluate_review_complete(snapshot_value, cycle_value)

    assert completed.cycle_state == "REVIEW_COMPLETE"


def test_review_complete_rejects_unassessed_codex_approval() -> None:
    snapshot_value, cycle_value = processed_codex_approval_state()
    cycle_value = cycle_value.model_copy(update={"assessments": []})

    with pytest.raises(ReviewAuthorizationError, match="assessment census"):
        evaluate_review_complete(snapshot_value, cycle_value)


def test_review_complete_rejects_new_codex_approval() -> None:
    snapshot_value, cycle_value = processed_codex_approval_state()
    new_approval = snapshot_value.review_inputs[0].model_copy(
        update={"input_id": "github:reaction:100", "provider_ids": ProviderInputIdentity(object_id="100")}
    )
    review_inputs = [*snapshot_value.review_inputs, new_approval]
    fingerprint = calculate_snapshot_fingerprint(
        snapshot_value.target,
        snapshot_value.head_revision,
        review_inputs,
        snapshot_value.completeness,
        revision_at=snapshot_value.revision_at,
        reviewability=snapshot_value.reviewability,
        provider_metadata=snapshot_value.provider_metadata,
        communicated_input_ids=snapshot_value.communicated_input_ids,
    )
    snapshot_value = snapshot_value.model_copy(
        update={"review_inputs": review_inputs, "snapshot_fingerprint": fingerprint}
    )
    cycle_value = cycle_value.model_copy(update={"recheck_snapshot_fingerprint": fingerprint})

    with pytest.raises(ReviewAuthorizationError, match="input census"):
        evaluate_review_complete(snapshot_value, cycle_value)


def test_review_complete_rejects_changed_codex_approval() -> None:
    snapshot_value, cycle_value = processed_codex_approval_state()
    changed_approval = snapshot_value.review_inputs[0].model_copy(update={"body": "+1 after reassessment requested"})
    fingerprint = calculate_snapshot_fingerprint(
        snapshot_value.target,
        snapshot_value.head_revision,
        [changed_approval],
        snapshot_value.completeness,
        revision_at=snapshot_value.revision_at,
        reviewability=snapshot_value.reviewability,
        provider_metadata=snapshot_value.provider_metadata,
        communicated_input_ids=snapshot_value.communicated_input_ids,
    )
    snapshot_value = snapshot_value.model_copy(
        update={"review_inputs": [changed_approval], "snapshot_fingerprint": fingerprint}
    )
    cycle_value = cycle_value.model_copy(update={"recheck_snapshot_fingerprint": fingerprint})

    with pytest.raises(ReviewAuthorizationError, match="changed since assessment"):
        evaluate_review_complete(snapshot_value, cycle_value)


def test_review_complete_rejects_provider_snapshot_with_outstanding_work() -> None:
    snapshot_value = snapshot_with_communication()
    cycle_value = ready_cycle().model_copy(
        update={
            "snapshot_fingerprint": snapshot_value.snapshot_fingerprint,
            "recheck_snapshot_fingerprint": snapshot_value.snapshot_fingerprint,
            "communication_states": {review_input().input_id: "completed"},
            "resolution_states": {review_input().input_id: "resolved"},
            "terminal_annotations": {review_input().input_id: "Caller claims the input is resolved."},
        }
    )

    with pytest.raises(ReviewAuthorizationError, match="provider snapshot has outstanding work"):
        evaluate_review_complete(snapshot_value, cycle_value)


def test_review_complete_rejects_input_changed_after_assessment() -> None:
    original = snapshot_with_communication().model_copy(update={"unresolved_count": 0, "outstanding_input_count": 0})
    changed = review_input().model_copy(update={"body": "A materially different concern after assessment."})
    changed_fingerprint = calculate_snapshot_fingerprint(
        original.target,
        original.head_revision,
        [changed],
        original.completeness,
        revision_at=original.revision_at,
        reviewability=original.reviewability,
        provider_metadata=original.provider_metadata,
        communicated_input_ids=original.communicated_input_ids,
    )
    final_snapshot = original.model_copy(
        update={"review_inputs": [changed], "snapshot_fingerprint": changed_fingerprint}
    )
    cycle_value = ready_cycle().model_copy(
        update={
            "recheck_snapshot_fingerprint": changed_fingerprint,
            "communication_states": {review_input().input_id: "completed"},
            "resolution_states": {review_input().input_id: "resolved"},
            "terminal_annotations": {review_input().input_id: "Caller claims the input is unchanged."},
        }
    )

    with pytest.raises(ReviewAuthorizationError, match="changed since assessment"):
        evaluate_review_complete(final_snapshot, cycle_value)


def test_review_complete_rejects_caller_only_communication_claim() -> None:
    snapshot_value = snapshot().model_copy(update={"unresolved_count": 0, "outstanding_input_count": 0})
    cycle_value = ready_cycle().model_copy(
        update={
            "communication_states": {review_input().input_id: "completed"},
            "resolution_states": {review_input().input_id: "resolved"},
            "terminal_annotations": {review_input().input_id: "Claimed complete."},
        }
    )

    with pytest.raises(ReviewAuthorizationError, match="provider-backed communication"):
        evaluate_review_complete(snapshot_value, cycle_value)


def test_review_complete_requires_per_input_implementation_and_annotation() -> None:
    snapshot_value = snapshot_with_communication().model_copy(
        update={"unresolved_count": 0, "outstanding_input_count": 0}
    )
    cycle_value = ready_cycle().model_copy(
        update={
            "snapshot_fingerprint": snapshot_value.snapshot_fingerprint,
            "recheck_snapshot_fingerprint": snapshot_value.snapshot_fingerprint,
            "communication_states": {review_input().input_id: "completed"},
            "resolution_states": {review_input().input_id: "resolved"},
            "implementation_states": {review_input().input_id: "pending"},
            "terminal_annotations": {},
        }
    )

    with pytest.raises(ReviewAuthorizationError, match="implementation state"):
        evaluate_review_complete(snapshot_value, cycle_value)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
