"""Shared canonical review-state fixtures for provider and orchestration tests."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pr_review_contracts import ChangeRequestTarget, RepositoryTarget
from pr_review_models import Reviewability, ReviewSnapshot
from pr_review_state_models import (
    ProviderInputIdentity,
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


def review_target() -> ChangeRequestTarget:
    """Return one stable GitHub target."""
    return ChangeRequestTarget(
        repository=RepositoryTarget(provider="github", hostname="github.com", full_name="acme/widgets"), number=17
    )


def canonical_input(input_id: str = "github:review-comment:42") -> ReviewInput:
    """Return one inbound inline comment."""
    return ReviewInput(
        input_id=input_id,
        provider="github",
        provider_ids=ProviderInputIdentity(object_id="42", reply_target_id="42", resolution_target_id="T1"),
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
        capabilities=ReviewCapabilities(can_reply=True, can_resolve=True, can_comment=True, unavailable=[]),
        thread_id="T1",
        parent_id=None,
    )


def canonical_snapshot(*, complete: bool = True) -> ReviewSnapshot:
    """Return a snapshot containing one canonical input."""
    item = canonical_input()
    completeness = SnapshotCompleteness(
        transport="github_cli",
        required_surfaces={"threads", "reviews", "comments", "reactions", "identity", "revision"},
        completed_surfaces={"threads", "reviews", "comments", "reactions", "identity", "revision"},
        truncated_input_ids=[] if complete else [item.input_id],
        unavailable_capabilities=[],
    )
    fingerprint = calculate_snapshot_fingerprint(review_target(), "abc123", [item], completeness)
    return ReviewSnapshot(
        provider="github",
        target=review_target(),
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
    item = canonical_input()
    assessment = ReviewAssessment(
        input_id=item.input_id,
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
        input_ids=[item.input_id],
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
            target=review_target(),
            remote_head="abc123",
            revision="abc123",
        ),
        snapshot_fingerprint=canonical_snapshot().snapshot_fingerprint,
        input_census=[item.input_id],
        assessments=[assessment],
        clusters=[cluster],
        unknown_decisions={},
        implementation_evidence=["Commit abc123 contains the systemic correction."],
        verification_evidence=["pytest tests/test_widget.py passed at abc123."],
        inspectable_revision="abc123",
        recheck_snapshot_fingerprint=canonical_snapshot().snapshot_fingerprint,
        communication_states={item.input_id: "pending"},
        resolution_states={item.input_id: "open"},
        cycle_terminal="action_pending",
        cycle_state="READY_FOR_ACTION",
    )


def write_ready_files(directory: Path) -> tuple[Path, Path]:
    """Write current snapshot and cycle JSON files.

    Returns:
        Snapshot and state paths.
    """
    snapshot_path = directory / "snapshot.json"
    state_path = directory / "state.json"
    snapshot_path.write_text(canonical_snapshot().model_dump_json())
    state_path.write_text(ready_cycle().model_dump_json())
    return snapshot_path, state_path
