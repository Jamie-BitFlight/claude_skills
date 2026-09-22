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
"""Tests for cross-provider snapshot and action-boundary consistency."""

from __future__ import annotations

import pytest

from pr_review_contracts import ChangeRequestTarget, ReplyAction, RepositoryTarget
from pr_review_models import ReviewSnapshot
from pr_review_state import ReviewAuthorizationError, authorize_action
from pr_review_state_models import ReviewCycleState, ReviewInput, calculate_snapshot_fingerprint
from review_test_fixtures import canonical_input, canonical_snapshot, ready_cycle


def state_for_snapshot(snapshot_value: ReviewSnapshot) -> tuple[ReviewSnapshot, ReviewCycleState]:
    """Bind a customized snapshot to matching cycle and fingerprint evidence."""
    item = snapshot_value.review_inputs[0]
    fingerprint = calculate_snapshot_fingerprint(
        snapshot_value.target,
        snapshot_value.head_revision,
        snapshot_value.review_inputs,
        snapshot_value.completeness,
        revision_at=snapshot_value.revision_at,
        reviewability=snapshot_value.reviewability,
        provider_metadata=snapshot_value.provider_metadata,
        communicated_input_ids=snapshot_value.communicated_input_ids,
    )
    snapshot_value = snapshot_value.model_copy(update={"snapshot_fingerprint": fingerprint})
    original_cycle = ready_cycle()
    assessment = original_cycle.assessments[0].model_copy(update={"input_id": item.input_id})
    cluster = original_cycle.clusters[0].model_copy(update={"input_ids": [item.input_id]})
    context = original_cycle.context.model_copy(update={"target": snapshot_value.target})
    cycle_value = original_cycle.model_copy(
        update={
            "context": context,
            "snapshot_fingerprint": fingerprint,
            "recheck_snapshot_fingerprint": fingerprint,
            "assessed_inputs": {item.input_id: item},
            "input_census": [item.input_id],
            "assessments": [assessment],
            "clusters": [cluster],
            "communication_states": {item.input_id: "pending"},
            "resolution_states": {item.input_id: "open"},
        }
    )
    return snapshot_value, cycle_value


@pytest.mark.parametrize(
    ("snapshot_value", "message"),
    [
        (
            canonical_snapshot().model_copy(update={"provider": "gitlab"}),
            "snapshot provider does not match target provider",
        ),
        (
            canonical_snapshot().model_copy(
                update={
                    "target": ChangeRequestTarget(
                        repository=RepositoryTarget(
                            provider="gitlab", hostname="gitlab.example", full_name="acme/widgets"
                        ),
                        number=17,
                    )
                }
            ),
            "snapshot provider does not match target provider",
        ),
        (
            canonical_snapshot().model_copy(
                update={"review_inputs": [canonical_input().model_copy(update={"provider": "gitlab"})]}
            ),
            "review input provider does not match snapshot provider",
        ),
        (
            canonical_snapshot().model_copy(
                update={"review_inputs": [canonical_input().model_copy(update={"input_id": "gitlab:note:42"})]}
            ),
            "canonical input id is outside the snapshot provider namespace",
        ),
        (
            canonical_snapshot().model_copy(update={"transport": "github_mcp"}),
            "snapshot transport does not match completeness transport",
        ),
        (
            canonical_snapshot().model_copy(
                update={
                    "transport": "gitlab_cli",
                    "completeness": canonical_snapshot().completeness.model_copy(update={"transport": "gitlab_cli"}),
                }
            ),
            "snapshot transport does not belong to snapshot provider",
        ),
    ],
)
def test_authorization_rejects_cross_provider_snapshot_evidence(snapshot_value: ReviewSnapshot, message: str) -> None:
    snapshot_value, cycle_value = state_for_snapshot(snapshot_value)

    with pytest.raises(ReviewAuthorizationError, match=message):
        authorize_action(
            snapshot_value, cycle_value, snapshot_value.review_inputs[0].input_id, ReplyAction(body="Done.")
        )


def test_github_watch_keeps_legacy_signals_when_canonical_history_exists() -> None:
    snapshot_value = canonical_snapshot().model_copy(
        update={"unresolved_count": 0, "unresponded_reviews": [], "codex_approved": False}
    )

    assert snapshot_value.review_inputs
    assert snapshot_value.has_outstanding_work() is False


@pytest.mark.parametrize(
    "changed_input",
    [
        canonical_input().model_copy(update={"body": "Materially edited after communication."}),
        canonical_input().model_copy(update={"provider_state": "resolved"}),
    ],
    ids=["edited-input", "resolved-state-transition"],
)
def test_watch_signal_compares_full_canonical_input_state(changed_input: ReviewInput) -> None:
    baseline = canonical_snapshot().model_copy(update={"unresolved_count": 0, "outstanding_input_count": 0})
    fingerprint = calculate_snapshot_fingerprint(
        baseline.target,
        baseline.head_revision,
        [changed_input],
        baseline.completeness,
        revision_at=baseline.revision_at,
        reviewability=baseline.reviewability,
        provider_metadata=baseline.provider_metadata,
        communicated_input_ids=baseline.communicated_input_ids,
    )
    changed = baseline.model_copy(update={"review_inputs": [changed_input], "snapshot_fingerprint": fingerprint})

    assert baseline.has_watch_signal(baseline.snapshot_fingerprint) is False
    assert changed.has_watch_signal(baseline.snapshot_fingerprint) is True


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
