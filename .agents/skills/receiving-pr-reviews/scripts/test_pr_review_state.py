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

from datetime import UTC, datetime

import pytest

from pr_review_github_normalize import review_inputs
from pr_review_models import (
    Author,
    ChangeRequestTarget,
    ReplyAction,
    RepositoryTarget,
    Reviewability,
    ReviewNode,
    ReviewSnapshot,
)
from pr_review_state import ReviewAuthorizationError, authorize_action
from pr_review_state_models import (
    ReviewActor,
    ReviewAssessment,
    ReviewCapabilities,
    ReviewCluster,
    ReviewContext,
    ReviewCycleState,
    ReviewInput,
    SnapshotCompleteness,
    calculate_snapshot_fingerprint,
)


def target() -> ChangeRequestTarget:
    """Return one stable target fixture."""
    return ChangeRequestTarget(
        repository=RepositoryTarget(provider="github", hostname="github.com", full_name="acme/widgets"), number=17
    )


def review_input(input_id: str = "github:review-comment:42") -> ReviewInput:
    """Return one inbound inline-comment fixture."""
    return ReviewInput(
        input_id=input_id,
        provider="github",
        provider_ids={"thread_id": "T1", "opening_comment_id": "42"},
        source_kind="review_comment",
        kinds={"comment"},
        location="inline",
        direction="inbound",
        actor=ReviewActor(actor_id="reviewer", login="reviewer", classification="human", role="reviewer"),
        body="Fix the shared invariant.",
        stable_reference="https://github.com/acme/widgets/pull/17#discussion_r42",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        updated_at=None,
        revision_relation="current",
        path="src/widget.py",
        line=12,
        provider_state="open",
        capabilities=ReviewCapabilities(can_reply=True, can_resolve=True, unavailable=[]),
        thread_id="T1",
        parent_id=None,
    )


def snapshot(*, complete: bool = True) -> ReviewSnapshot:
    """Return a canonical snapshot containing one review input."""
    item = review_input()
    completeness = SnapshotCompleteness(
        transport="github_cli",
        required_surfaces={"threads", "reviews", "comments", "reactions", "identity", "revision"},
        completed_surfaces={"threads", "reviews", "comments", "reactions", "identity", "revision"},
        truncated_input_ids=[] if complete else [item.input_id],
        unavailable_capabilities=[],
    )
    fingerprint = calculate_snapshot_fingerprint(target(), "abc123", [item], completeness)
    return ReviewSnapshot(
        provider="github",
        target=target(),
        transport="github_cli",
        snapshot_complete=complete,
        snapshot_fingerprint=fingerprint,
        head_revision="abc123",
        revision_at=datetime(2026, 1, 1, tzinfo=UTC),
        completeness=completeness,
        review_inputs=[item],
        assessments=[],
        clusters=[],
        cycle_state="ASSESSMENT_REQUIRED",
        reviews_count=0,
        reviews_with_body=[],
        unresponded_reviews=[],
        threads_count=1,
        unresolved=[],
        unresolved_count=1,
        codex_approved=False,
        codex_approval_equivalence="available",
        reviewability=Reviewability(is_draft=False, mergeable="MERGEABLE", merge_state_status="CLEAN", blockers=[]),
    )


def ready_cycle() -> ReviewCycleState:
    """Return a cycle satisfying every complete-set gate."""
    assessment = ReviewAssessment(
        input_id=review_input().input_id,
        validity="valid",
        relevance="relevant",
        evidence=["src/widget.py:12 demonstrates the invariant violation"],
        affected_scope=["src/widget.py"],
        verification_surface=["pytest tests/test_widget.py"],
        disposition="accepted_change",
        kind_assessment="not_applicable",
        semantic_kinds={"comment"},
        unknowns=[],
        cluster_id="cluster-1",
        communication_plan="Reply with the verified remote revision.",
    )
    cluster = ReviewCluster(
        cluster_id="cluster-1",
        input_ids=[review_input().input_id],
        shared_basis=["shared invariant"],
        explicit_singleton=True,
        systemic_outcome="Correct the invariant at its owning module.",
        evidence=["The owning module controls every affected call site."],
        verification_commands=["pytest tests/test_widget.py"],
        communication_plan="Reply with the verified remote revision.",
        resolution_policy="resolve_after_reply",
    )
    return ReviewCycleState(
        context=ReviewContext(
            repository_instructions="Follow AGENTS.md.",
            change_request_goal="Correct review handling.",
            changed_scope=["src/widget.py"],
            target=target(),
            remote_head="abc123",
            revision="abc123",
        ),
        snapshot_fingerprint=snapshot().snapshot_fingerprint,
        input_census=[review_input().input_id],
        assessments=[assessment],
        clusters=[cluster],
        unknown_decisions={},
        cycle_state="READY_FOR_ACTION",
    )


def test_shared_reply_action_does_not_require_github_comment_identifier() -> None:
    action = ReplyAction(body="Addressed systemically.")

    assert action.body == "Addressed systemically."


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

    normalized = review_inputs(reviews, own_login="agent", is_empty_codex=lambda _review: False)

    assert normalized[0].kinds == {"approval"}
    assert normalized[1].kinds == {"rejection"}


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
