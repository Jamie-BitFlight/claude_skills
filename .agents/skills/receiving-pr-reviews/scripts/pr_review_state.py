"""Pre-action gate for complete, current, exhaustively assessed review cycles."""

from __future__ import annotations

from pathlib import Path

from pr_review_contracts import ResolveAction, ReviewAction
from pr_review_models import ReviewSnapshot
from pr_review_state_models import (
    AuthorizedReviewAction,
    ReviewAssessment,
    ReviewCluster,
    ReviewCycleState,
    ReviewInput,
    calculate_snapshot_fingerprint,
)


class ReviewAuthorizationError(ValueError):
    """A review mutation was requested before the approved cycle gate passed."""


def load_snapshot(path: Path) -> ReviewSnapshot:
    """Load a canonical provider snapshot.

    Returns:
        The validated snapshot.
    """
    return ReviewSnapshot.model_validate_json(path.read_text(encoding="utf-8"))


def load_cycle(path: Path) -> ReviewCycleState:
    """Load serialized review-cycle evidence.

    Returns:
        The validated cycle state.
    """
    return ReviewCycleState.model_validate_json(path.read_text(encoding="utf-8"))


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ReviewAuthorizationError(message)


def _validate_snapshot_context(snapshot: ReviewSnapshot, cycle: ReviewCycleState) -> None:
    _require(snapshot.snapshot_complete and snapshot.completeness.complete, "snapshot is incomplete")
    _require(cycle.cycle_state == "READY_FOR_ACTION", "cycle state must be READY_FOR_ACTION")
    _require(cycle.context.target == snapshot.target, "cycle target does not match snapshot target")
    _require(
        cycle.context.revision == snapshot.head_revision and cycle.context.remote_head == snapshot.head_revision,
        "cycle revision does not match snapshot revision",
    )
    _require(
        cycle.snapshot_fingerprint == snapshot.snapshot_fingerprint,
        "cycle snapshot fingerprint does not match current snapshot",
    )
    calculated_fingerprint = calculate_snapshot_fingerprint(
        snapshot.target, snapshot.head_revision, snapshot.review_inputs, snapshot.completeness
    )
    _require(
        calculated_fingerprint == snapshot.snapshot_fingerprint,
        "snapshot fingerprint does not match canonical snapshot content",
    )


def _validate_cycle_coverage(
    snapshot: ReviewSnapshot, cycle: ReviewCycleState
) -> tuple[dict[str, ReviewInput], dict[str, ReviewAssessment], dict[str, ReviewCluster]]:
    inbound_ids = [item.input_id for item in snapshot.review_inputs if item.direction == "inbound"]
    inbound_set = set(inbound_ids)
    _require(
        len(inbound_ids) == len(inbound_set) and set(cycle.input_census) == inbound_set,
        "input census does not exactly cover inbound review inputs",
    )
    assessment_ids = [assessment.input_id for assessment in cycle.assessments]
    _require(
        len(assessment_ids) == len(set(assessment_ids)) and set(assessment_ids) == inbound_set,
        "assessment census does not exactly cover inbound review inputs",
    )
    cluster_members = [member for cluster in cycle.clusters for member in cluster.input_ids]
    _require(
        len(cluster_members) == len(set(cluster_members)) and set(cluster_members) == inbound_set,
        "cluster membership does not exactly cover inbound review inputs",
    )
    cluster_by_id = {cluster.cluster_id: cluster for cluster in cycle.clusters}
    _require(len(cluster_by_id) == len(cycle.clusters), "cluster ids must be unique")
    assignments_match = all(
        assessment.cluster_id in cluster_by_id and assessment.input_id in cluster_by_id[assessment.cluster_id].input_ids
        for assessment in cycle.assessments
    )
    _require(assignments_match, "assessment cluster assignment does not match cluster membership")
    required_unknowns = {unknown for assessment in cycle.assessments for unknown in assessment.unknowns}
    _require(
        required_unknowns.issubset(cycle.unknown_decisions),
        "every assessment unknown requires an explicit unknown decision",
    )
    _require(
        all(decision.strip() for decision in cycle.unknown_decisions.values()),
        "every unknown decision requires a resolution or clarification path",
    )
    return (
        {item.input_id: item for item in snapshot.review_inputs},
        {assessment.input_id: assessment for assessment in cycle.assessments},
        cluster_by_id,
    )


def authorize_action(
    snapshot: ReviewSnapshot, cycle: ReviewCycleState, input_id: str, action: ReviewAction
) -> AuthorizedReviewAction:
    """Validate every pre-action invariant and bind one authorized mutation.

    Returns:
        The action bound to its current target, revision, assessment, cluster, and input.
    """
    _validate_snapshot_context(snapshot, cycle)
    input_by_id, assessment_by_id, cluster_by_id = _validate_cycle_coverage(snapshot, cycle)
    _require(
        input_id in input_by_id and input_id in assessment_by_id, f"input {input_id!r} is not authorized by this cycle"
    )
    assessment = assessment_by_id[input_id]
    _require(
        not isinstance(action, ResolveAction) or assessment.disposition != "clarification_required",
        "clarification-required input must remain open",
    )
    _require(assessment.cluster_id in cluster_by_id, f"assessment cluster {assessment.cluster_id!r} has no plan")

    return AuthorizedReviewAction(
        target=snapshot.target,
        snapshot_fingerprint=snapshot.snapshot_fingerprint,
        revision=snapshot.head_revision,
        review_input=input_by_id[input_id],
        cluster_id=assessment.cluster_id,
        disposition=assessment.disposition,
        communication_plan=assessment.communication_plan,
        action=action,
    )
