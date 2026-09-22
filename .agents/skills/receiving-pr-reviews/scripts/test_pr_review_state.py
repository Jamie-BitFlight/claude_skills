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
"""Tests for canonical review state and the pre-action authorization gate."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from pr_review_github_normalize import actor, review_inputs
from pr_review_models import Author, ReplyAction, ResolveAction, ReviewNode, ReviewSnapshot, TopLevelCommentAction
from pr_review_state import ReviewAuthorizationError, authorize_action, evaluate_review_complete
from pr_review_state_models import (
    ReviewActor,
    ReviewAssessment,
    ReviewCapabilities,
    ReviewCluster,
    ReviewCycleState,
    ReviewInput,
    calculate_snapshot_fingerprint,
)
from review_test_fixtures import (
    canonical_input as review_input,
    canonical_snapshot as snapshot,
    ready_cycle,
    snapshot_with_communication,
    state_for_input,
)


def test_shared_reply_action_does_not_require_github_comment_identifier() -> None:
    action = ReplyAction(body="Addressed systemically.")

    assert action.body == "Addressed systemically."


def test_review_input_rejects_advertised_mutation_without_typed_provider_target() -> None:
    payload = review_input().model_dump()
    payload["kinds"] = {"comment"}
    payload["provider_ids"] = {"object_id": "42"}

    with pytest.raises(ValidationError, match="reply_target_id"):
        ReviewInput.model_validate(payload)


def test_actor_classification_uses_provider_type_instead_of_login_guessing() -> None:
    untyped = actor(Author(login="service-bot"), pull_author_login=None, observed_role=None)
    typed = actor(
        Author.model_validate({"login": "service", "__typename": "Bot"}), pull_author_login=None, observed_role=None
    )

    assert untyped.classification == "unknown"
    assert typed.classification == "bot"


def test_authorize_action_binds_complete_current_cycle() -> None:
    authorized = authorize_action(snapshot(), ready_cycle(), review_input().input_id, ReplyAction(body="Done."))

    assert authorized.cycle_state == "READY_FOR_ACTION"
    assert authorized.review_input.input_id == review_input().input_id
    assert authorized.snapshot_fingerprint == snapshot().snapshot_fingerprint


@pytest.mark.parametrize(
    ("snapshot_value", "cycle_value", "message"),
    [
        (snapshot(complete=False), ready_cycle(), "snapshot is incomplete"),
        (snapshot(), ready_cycle().model_copy(update={"cycle_state": "ASSESSMENT_REQUIRED"}), "READY_FOR_ACTION"),
        (snapshot(), ready_cycle().model_copy(update={"assessments": []}), "assessment census"),
        (snapshot(), ready_cycle().model_copy(update={"clusters": []}), "cluster membership"),
        (snapshot(), ready_cycle().model_copy(update={"unknown_decisions": {"unknown-1": ""}}), "unknown decision"),
        (
            snapshot(),
            ready_cycle().model_copy(update={"input_census": [review_input().input_id, review_input().input_id]}),
            "input census",
        ),
        (snapshot(), ready_cycle().model_copy(update={"implementation_evidence": []}), "implementation evidence"),
        (snapshot(), ready_cycle().model_copy(update={"verification_evidence": []}), "verification evidence"),
    ],
)
def test_authorize_action_rejects_incomplete_cycle(
    snapshot_value: ReviewSnapshot, cycle_value: ReviewCycleState, message: str
) -> None:
    with pytest.raises(ReviewAuthorizationError, match=message):
        authorize_action(snapshot_value, cycle_value, review_input().input_id, ReplyAction(body="Done."))


def test_numeric_superset_reference_does_not_count_as_exact_review_reference() -> None:
    from pr_review_github_provider import render_top_level_body

    requested = "https://github.com/acme/widgets/pull/17#pullrequestreview-5"
    existing = "Addressed https://github.com/acme/widgets/pull/17#pullrequestreview-50"

    assert render_top_level_body(existing, [requested]) == f"{existing}\n\n{requested}"


def test_snapshot_fingerprint_survives_json_round_trip() -> None:
    original = snapshot()
    restored = ReviewSnapshot.model_validate_json(original.model_dump_json())

    assert restored.snapshot_fingerprint == calculate_snapshot_fingerprint(
        restored.target,
        restored.head_revision,
        restored.review_inputs,
        restored.completeness,
        revision_at=restored.revision_at,
        reviewability=restored.reviewability,
        provider_metadata=restored.provider_metadata,
        communicated_input_ids=restored.communicated_input_ids,
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


def test_authorization_requires_explicit_decisions_for_unknown_provider_facts() -> None:
    item = review_input().model_copy(
        update={
            "actor": ReviewActor(actor_id="reviewer", login="reviewer", classification="unknown", role="unknown"),
            "revision_relation": "unknown",
        }
    )
    assessment = ready_cycle().assessments[0].model_copy(update={"unknowns": []})
    snapshot_value, cycle_value = state_for_input(item, assessment)

    with pytest.raises(ReviewAuthorizationError, match="unknown provider fact"):
        authorize_action(snapshot_value, cycle_value, item.input_id, ReplyAction(body="Done."))


def test_authorization_requires_kind_assessment_to_match_approval_signal() -> None:
    item = review_input().model_copy(update={"kinds": {"approval"}})
    assessment = (
        ready_cycle()
        .assessments[0]
        .model_copy(update={"semantic_kinds": {"approval"}, "kind_assessment": "not_applicable"})
    )
    snapshot_value, cycle_value = state_for_input(item, assessment)

    with pytest.raises(ReviewAuthorizationError, match="approval/rejection semantics"):
        authorize_action(snapshot_value, cycle_value, item.input_id, ReplyAction(body="Done."))


def test_assessment_can_classify_a_normalized_comment_as_a_question() -> None:
    item = review_input()
    assessment = ready_cycle().assessments[0].model_copy(update={"semantic_kinds": {"comment", "question"}})
    snapshot_value, cycle_value = state_for_input(item, assessment)

    authorized = authorize_action(snapshot_value, cycle_value, item.input_id, ReplyAction(body="Answered."))

    assert authorized.review_input.input_id == item.input_id


def test_top_level_communication_accepts_truthful_unavailable_resolution_state() -> None:
    item = review_input().model_copy(
        update={
            "location": "top_level",
            "capabilities": ReviewCapabilities(
                can_reply=False, can_resolve=False, can_comment=True, unavailable=["reply", "resolve"]
            ),
            "provider_state": "COMMENTED",
            "thread_id": None,
        }
    )
    assessment = ready_cycle().assessments[0]
    snapshot_value, cycle_value = state_for_input(item, assessment)
    cycle_value = cycle_value.model_copy(
        update={
            "resolution_states": {item.input_id: "unavailable"},
            "clusters": [cycle_value.clusters[0].model_copy(update={"resolution_policy": "unavailable"})],
        }
    )

    authorized = authorize_action(
        snapshot_value,
        cycle_value,
        item.input_id,
        TopLevelCommentAction(body="Addressed.", references=[item.stable_reference]),
    )

    assert isinstance(authorized.action, TopLevelCommentAction)
    assert authorized.action.references == [item.stable_reference]


def test_top_level_communication_requires_selected_input_reference() -> None:
    item = review_input().model_copy(
        update={
            "location": "top_level",
            "capabilities": ReviewCapabilities(
                can_reply=False, can_resolve=False, can_comment=True, unavailable=["reply", "resolve"]
            ),
            "provider_state": "COMMENTED",
            "thread_id": None,
        }
    )
    snapshot_value, cycle_value = state_for_input(item, ready_cycle().assessments[0])
    cycle_value = cycle_value.model_copy(update={"resolution_states": {item.input_id: "unavailable"}})

    with pytest.raises(ReviewAuthorizationError, match="stable reference"):
        authorize_action(
            snapshot_value,
            cycle_value,
            item.input_id,
            TopLevelCommentAction(body="Addressed.", references=["https://example.invalid/another-input"]),
        )


def test_resolution_requires_capability_and_completed_communication() -> None:
    item = review_input().model_copy(
        update={
            "capabilities": ReviewCapabilities(
                can_reply=True, can_resolve=False, can_comment=True, unavailable=["resolve"]
            )
        }
    )
    snapshot_value, cycle_value = state_for_input(item, ready_cycle().assessments[0])
    cycle_value = cycle_value.model_copy(update={"communication_states": {item.input_id: "completed"}})

    with pytest.raises(ReviewAuthorizationError, match="does not support resolution"):
        authorize_action(snapshot_value, cycle_value, item.input_id, ResolveAction())


@pytest.mark.parametrize(("field", "value"), [("affected_scope", []), ("verification_surface", [])])
def test_assessment_rejects_empty_required_evidence_surfaces(field: str, value: list[str]) -> None:
    payload = ready_cycle().assessments[0].model_dump()
    payload[field] = value

    with pytest.raises(ValidationError):
        ReviewAssessment.model_validate(payload)


def test_cluster_rejects_empty_verification_commands() -> None:
    payload = ready_cycle().clusters[0].model_dump()
    payload["verification_commands"] = []

    with pytest.raises(ValidationError):
        ReviewCluster.model_validate(payload)


def test_gitlab_snapshot_accepts_unavailable_codex_equivalence_without_github_projection() -> None:
    original = snapshot()
    payload = {
        key: value
        for key, value in json.loads(original.model_dump_json()).items()
        if key
        not in {
            "reviews_count",
            "reviews_with_body",
            "unresponded_reviews",
            "threads_count",
            "unresolved",
            "unresolved_count",
            "reviewability",
        }
    }
    payload.update({
        "provider": "gitlab",
        "target": {
            "repository": {"provider": "gitlab", "hostname": "gitlab.example", "full_name": "acme/widgets"},
            "number": 17,
        },
        "transport": "gitlab_cli",
        "codex_approved": None,
        "codex_approval_equivalence": "unavailable",
    })
    payload["completeness"]["transport"] = "gitlab_cli"
    payload["review_inputs"][0]["provider"] = "gitlab"
    payload["review_inputs"][0]["input_id"] = "gitlab:note:42"

    parsed = ReviewSnapshot.model_validate_json(json.dumps(payload))

    assert parsed.codex_approved is None
    assert parsed.reviewability is None


def test_empty_body_approval_and_rejection_are_normalized_inputs() -> None:
    reviews = [
        ReviewNode(
            id="approved",
            author=Author(login="human-a"),
            state="APPROVED",
            body="",
            submittedAt=datetime(2026, 1, 1, tzinfo=UTC),
            lastEditedAt=None,
            url="https://example/review/1",
        ),
        ReviewNode(
            id="rejected",
            author=Author(login="human-b"),
            state="CHANGES_REQUESTED",
            body="",
            submittedAt=datetime(2026, 1, 1, tzinfo=UTC),
            lastEditedAt=None,
            url="https://example/review/2",
        ),
    ]

    normalized = review_inputs(
        reviews,
        own_login="agent",
        pull_author_login="author",
        head_revision="abc123",
        is_empty_codex=lambda _review: False,
    )

    assert normalized[0].kinds == {"approval"}
    assert normalized[1].kinds == {"rejection"}


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
