"""Pre-action gate for complete, current, exhaustively assessed review cycles."""

from __future__ import annotations

from pathlib import Path

from pr_review_contracts import ReplyAction, ResolveAction, ReviewAction, TopLevelCommentAction
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

    Args:
        path: JSON snapshot file written by the fetch command.

    Returns:
        The validated snapshot.
    """
    return ReviewSnapshot.model_validate_json(path.read_text(encoding="utf-8"))


def load_cycle(path: Path) -> ReviewCycleState:
    """Load serialized review-cycle evidence.

    Args:
        path: JSON cycle-state file authored from the complete snapshot.

    Returns:
        The validated cycle state.
    """
    return ReviewCycleState.model_validate_json(path.read_text(encoding="utf-8"))


def require_authorization(condition: bool, message: str) -> None:
    """Raise the canonical authorization error when an invariant is false.

    Args:
        condition: Invariant result.
        message: Actionable failure text.

    Raises:
        ReviewAuthorizationError: If ``condition`` is false.
    """
    if not condition:
        raise ReviewAuthorizationError(message)


def validate_snapshot_context(snapshot: ReviewSnapshot, cycle: ReviewCycleState) -> None:
    """Validate current revision, fingerprint, recheck, and terminal evidence.

    Args:
        snapshot: Current complete provider snapshot.
        cycle: Serialized assessment and implementation evidence.
    """
    require_authorization(snapshot.snapshot_complete and snapshot.completeness.complete, "snapshot is incomplete")
    require_authorization(cycle.cycle_state == "READY_FOR_ACTION", "cycle state must be READY_FOR_ACTION")
    require_authorization(cycle.cycle_terminal == "action_pending", "cycle terminal must be action_pending")
    require_authorization(bool(cycle.implementation_evidence), "implementation evidence is required")
    require_authorization(bool(cycle.verification_evidence), "verification evidence is required")
    require_authorization(cycle.context.target == snapshot.target, "cycle target does not match snapshot target")
    require_authorization(
        cycle.context.revision == snapshot.head_revision and cycle.context.remote_head == snapshot.head_revision,
        "cycle revision does not match snapshot revision",
    )
    require_authorization(
        cycle.inspectable_revision == snapshot.head_revision, "inspectable revision does not match snapshot revision"
    )
    require_authorization(
        cycle.snapshot_fingerprint == snapshot.snapshot_fingerprint,
        "cycle snapshot fingerprint does not match current snapshot",
    )
    require_authorization(
        cycle.recheck_snapshot_fingerprint == snapshot.snapshot_fingerprint,
        "recheck snapshot fingerprint does not match current snapshot",
    )
    calculated_fingerprint = calculate_snapshot_fingerprint(
        snapshot.target, snapshot.head_revision, snapshot.review_inputs, snapshot.completeness
    )
    require_authorization(
        calculated_fingerprint == snapshot.snapshot_fingerprint,
        "snapshot fingerprint does not match canonical snapshot content",
    )


def validate_cycle_coverage(
    snapshot: ReviewSnapshot, cycle: ReviewCycleState
) -> tuple[dict[str, ReviewInput], dict[str, ReviewAssessment], dict[str, ReviewCluster]]:
    """Validate exhaustive, duplicate-free assessment and cluster coverage.

    Args:
        snapshot: Current complete provider snapshot.
        cycle: Serialized assessment and implementation evidence.

    Returns:
        Input, assessment, and cluster indexes after exhaustive validation.
    """
    inbound_ids = [item.input_id for item in snapshot.review_inputs if item.direction == "inbound"]
    inbound_set = set(inbound_ids)
    require_authorization(
        len(inbound_ids) == len(inbound_set)
        and len(cycle.input_census) == len(set(cycle.input_census))
        and set(cycle.input_census) == inbound_set,
        "input census does not exactly cover inbound review inputs",
    )
    assessment_ids = [assessment.input_id for assessment in cycle.assessments]
    require_authorization(
        len(assessment_ids) == len(set(assessment_ids)) and set(assessment_ids) == inbound_set,
        "assessment census does not exactly cover inbound review inputs",
    )
    cluster_members = [member for cluster in cycle.clusters for member in cluster.input_ids]
    require_authorization(
        len(cluster_members) == len(set(cluster_members)) and set(cluster_members) == inbound_set,
        "cluster membership does not exactly cover inbound review inputs",
    )
    cluster_by_id = {cluster.cluster_id: cluster for cluster in cycle.clusters}
    require_authorization(len(cluster_by_id) == len(cycle.clusters), "cluster ids must be unique")
    assignments_match = all(
        assessment.cluster_id in cluster_by_id and assessment.input_id in cluster_by_id[assessment.cluster_id].input_ids
        for assessment in cycle.assessments
    )
    require_authorization(assignments_match, "assessment cluster assignment does not match cluster membership")
    required_unknowns = {unknown for assessment in cycle.assessments for unknown in assessment.unknowns}
    require_authorization(
        required_unknowns.issubset(cycle.unknown_decisions),
        "every assessment unknown requires an explicit unknown decision",
    )
    require_authorization(
        all(decision.strip() for decision in cycle.unknown_decisions.values()),
        "every unknown decision requires a resolution or clarification path",
    )
    require_authorization(
        set(cycle.communication_states) == inbound_set, "communication states must exactly cover inbound review inputs"
    )
    require_authorization(
        set(cycle.resolution_states) == inbound_set, "resolution states must exactly cover inbound review inputs"
    )
    input_by_id = {item.input_id: item for item in snapshot.review_inputs}
    assessment_by_id = {assessment.input_id: assessment for assessment in cycle.assessments}
    for input_id in inbound_ids:
        review_input = input_by_id[input_id]
        assessment = assessment_by_id[input_id]
        required_fact_decisions = set()
        if review_input.revision_relation == "unknown":
            required_fact_decisions.add(f"revision_relation:{input_id}")
        if review_input.actor.classification == "unknown":
            required_fact_decisions.add(f"actor_classification:{input_id}")
        if review_input.actor.role == "unknown":
            required_fact_decisions.add(f"actor_role:{input_id}")
        require_authorization(
            required_fact_decisions.issubset(assessment.unknowns),
            f"assessment for {input_id!r} does not record every unknown provider fact",
        )
        added_kinds = assessment.semantic_kinds - review_input.kinds
        require_authorization(
            review_input.kinds.issubset(assessment.semantic_kinds) and added_kinds.issubset({"question"}),
            f"assessment kinds for {input_id!r} do not preserve normalized input kinds",
        )
        require_authorization(
            "question" not in added_kinds or "comment" in review_input.kinds,
            f"assessment for {input_id!r} can classify only a normalized comment as a question",
        )
        expected_kind_assessment = "not_applicable"
        if "rejection" in review_input.kinds:
            expected_kind_assessment = "rejection_assessed"
        elif "approval" in review_input.kinds:
            expected_kind_assessment = "approval_assessed"
        require_authorization(
            assessment.kind_assessment == expected_kind_assessment,
            f"kind assessment for {input_id!r} does not match approval/rejection semantics",
        )
    return (input_by_id, assessment_by_id, cluster_by_id)


def validate_action_state(
    review_input: ReviewInput,
    assessment: ReviewAssessment,
    cluster: ReviewCluster,
    cycle: ReviewCycleState,
    action: ReviewAction,
) -> None:
    """Validate capability, communication, and resolution state for one action.

    Args:
        review_input: Normalized input selected for mutation.
        assessment: Complete assessment for the input.
        cluster: Systemic plan containing the input.
        cycle: Current cycle evidence.
        action: Requested provider-neutral mutation.
    """
    input_id = review_input.input_id
    if isinstance(action, ReplyAction):
        require_authorization(cycle.resolution_states[input_id] == "open", "reply input resolution state must be open")
        require_authorization(review_input.capabilities.can_reply, "input does not support inline replies")
        require_authorization(cycle.communication_states[input_id] == "pending", "reply communication must be pending")
    elif isinstance(action, TopLevelCommentAction):
        require_authorization(
            cycle.resolution_states[input_id] in {"open", "unavailable"},
            "top-level input resolution state must be open or unavailable",
        )
        require_authorization(review_input.capabilities.can_comment, "input does not support top-level comments")
        require_authorization(
            cycle.communication_states[input_id] == "pending", "top-level communication must be pending"
        )
        require_authorization(
            review_input.stable_reference in action.references,
            "top-level communication must include the selected input stable reference",
        )
    elif isinstance(action, ResolveAction):
        require_authorization(
            cycle.resolution_states[input_id] == "open", "resolution input resolution state must be open"
        )
        require_authorization(review_input.capabilities.can_resolve, "input does not support resolution")
        require_authorization(
            cycle.communication_states[input_id] == "completed", "resolution requires completed communication"
        )
        require_authorization(
            cluster.resolution_policy == "resolve_after_reply", "cluster does not authorize resolution"
        )
        require_authorization(
            assessment.disposition != "clarification_required", "clarification-required input must remain open"
        )


def record_completed_communication(cycle: ReviewCycleState, input_id: str) -> ReviewCycleState:
    """Record transport-confirmed communication before authorizing resolution.

    Args:
        cycle: Current complete cycle state.
        input_id: Canonical input whose communication succeeded.

    Returns:
        A copied cycle with that input's communication marked completed.
    """
    require_authorization(input_id in cycle.communication_states, f"input {input_id!r} has no communication state")
    states = {**cycle.communication_states, input_id: "completed"}
    return cycle.model_copy(update={"communication_states": states})


def record_completed_resolution(cycle: ReviewCycleState, input_id: str) -> ReviewCycleState:
    """Record provider-confirmed resolution for one input.

    Args:
        cycle: Current complete cycle state.
        input_id: Canonical input whose resolution succeeded.

    Returns:
        A copied cycle with that input's resolution marked completed.
    """
    require_authorization(input_id in cycle.resolution_states, f"input {input_id!r} has no resolution state")
    states = {**cycle.resolution_states, input_id: "resolved"}
    return cycle.model_copy(update={"resolution_states": states})


def save_cycle(path: Path, cycle: ReviewCycleState) -> None:
    """Atomically persist transport-confirmed cycle progress.

    Args:
        path: Existing cycle-state path supplied by the mutation command.
        cycle: Updated validated cycle state.
    """
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(cycle.model_dump_json(indent=2), encoding="utf-8")
    temporary.replace(path)


def authorize_action(
    snapshot: ReviewSnapshot, cycle: ReviewCycleState, input_id: str, action: ReviewAction
) -> AuthorizedReviewAction:
    """Validate every pre-action invariant and bind one authorized mutation.

    Args:
        snapshot: Current complete provider snapshot.
        cycle: Complete assessment, implementation, verification, and communication evidence.
        input_id: Canonical inbound input selected for mutation.
        action: Provider-neutral action to authorize.

    Returns:
        The action bound to its current target, revision, assessment, cluster, and input.
    """
    validate_snapshot_context(snapshot, cycle)
    input_by_id, assessment_by_id, cluster_by_id = validate_cycle_coverage(snapshot, cycle)
    require_authorization(
        input_id in input_by_id and input_id in assessment_by_id, f"input {input_id!r} is not authorized by this cycle"
    )
    assessment = assessment_by_id[input_id]
    require_authorization(
        assessment.cluster_id in cluster_by_id, f"assessment cluster {assessment.cluster_id!r} has no plan"
    )
    cluster = cluster_by_id[assessment.cluster_id]
    validate_action_state(input_by_id[input_id], assessment, cluster, cycle, action)

    return AuthorizedReviewAction(
        target=snapshot.target,
        snapshot_fingerprint=snapshot.snapshot_fingerprint,
        revision=snapshot.head_revision,
        review_input=input_by_id[input_id],
        cluster_id=assessment.cluster_id,
        disposition=assessment.disposition,
        communication_plan=assessment.communication_plan,
        inspectable_revision=cycle.inspectable_revision,
        implementation_evidence=cycle.implementation_evidence,
        verification_evidence=cycle.verification_evidence,
        action=action,
    )
