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
"""A delivered clarification is not a completed review disposition."""

from __future__ import annotations

from typing import Literal

import pytest

from pr_review_contracts import ChangeRequestTarget, RepositoryTarget, TopLevelCommentAction
from pr_review_models import ReviewSnapshot
from pr_review_state import ReviewAuthorizationError, authorize_action, evaluate_review_complete
from pr_review_state_models import (
    ProviderInputIdentity,
    ReviewCapabilities,
    ReviewCycleState,
    calculate_snapshot_fingerprint,
)
from review_test_fixtures import canonical_input, canonical_snapshot, ready_cycle


def communicated_cycle(
    provider: Literal["github", "gitlab"], *, inline: bool = False
) -> tuple[ReviewSnapshot, ReviewCycleState]:
    """Build provider-shaped terminal delivery evidence, separate from disposition."""
    original = canonical_snapshot()
    target = ChangeRequestTarget(
        repository=RepositoryTarget(provider=provider, hostname=f"{provider}.com", full_name="acme/widgets"), number=17
    )
    item = canonical_input().model_copy(
        update={
            "input_id": f"{provider}:comment:42",
            "provider": provider,
            "provider_ids": ProviderInputIdentity(
                object_id="42", reply_target_id="42" if inline else None, resolution_target_id="T1" if inline else None
            ),
            "source_kind": "review_comment" if inline else "issue_comment",
            "location": "inline" if inline else "top_level",
            "provider_state": "resolved" if inline else "open",
            "stable_reference": f"https://{provider}.com/acme/widgets/requests/17#comment-42",
            "capabilities": ReviewCapabilities(
                can_reply=inline,
                can_resolve=inline,
                can_comment=True,
                unavailable=[] if inline else ["reply", "resolve"],
            ),
            "thread_id": "T1" if inline else None,
        }
    )
    completeness = original.completeness.model_copy(update={"transport": f"{provider}_cli"})
    communicated = {item.input_id}
    fingerprint = calculate_snapshot_fingerprint(
        target,
        original.head_revision,
        [item],
        completeness,
        revision_at=original.revision_at,
        reviewability=original.reviewability,
        provider_metadata=original.provider_metadata,
        communicated_input_ids=communicated,
    )
    snapshot = original.model_copy(
        update={
            "provider": provider,
            "target": target,
            "transport": f"{provider}_cli",
            "completeness": completeness,
            "review_inputs": [item],
            "snapshot_fingerprint": fingerprint,
            "communicated_input_ids": communicated,
            "unresolved_count": 0,
            "outstanding_input_count": 0,
        }
    )
    cycle = ready_cycle()
    assessment = cycle.assessments[0].model_copy(
        update={
            "input_id": item.input_id,
            "validity": "unknown",
            "disposition": "clarification_required",
            "unknowns": ["required-behavior"],
            "communication_plan": "Ask which behavior the stakeholder requires.",
        }
    )
    cycle = cycle.model_copy(
        update={
            "context": cycle.context.model_copy(update={"target": target}),
            "input_census": [item.input_id],
            "assessed_inputs": {item.input_id: item},
            "assessments": [assessment],
            "clusters": [
                cycle.clusters[0].model_copy(
                    update={
                        "input_ids": [item.input_id],
                        "resolution_policy": "leave_open" if inline else "unavailable",
                    }
                )
            ],
            "unknown_decisions": {"required-behavior": "Question sent; awaiting stakeholder response."},
            "snapshot_fingerprint": fingerprint,
            "recheck_snapshot_fingerprint": fingerprint,
            "communication_states": {item.input_id: "completed"},
            "resolution_states": {item.input_id: "resolved" if inline else "unavailable"},
            "implementation_states": {item.input_id: "not_required"},
            "terminal_annotations": {item.input_id: "Question delivered; no answer received."},
        }
    )
    # Exercise the serialized model boundary used by complete-cycle, not model_copy alone.
    return (
        ReviewSnapshot.model_validate_json(snapshot.model_dump_json()),
        ReviewCycleState.model_validate_json(cycle.model_dump_json()),
    )


@pytest.mark.parametrize("provider", ["github", "gitlab"])
@pytest.mark.parametrize("inline", [False, True], ids=["unresolvable-top-level", "externally-resolved-inline"])
def test_clarification_remains_nonterminal_after_delivery(provider: Literal["github", "gitlab"], inline: bool) -> None:
    """Zero provider backlog and a sent question do not answer the pending question."""
    snapshot, cycle = communicated_cycle(provider, inline=inline)
    before = cycle.model_dump_json()

    with pytest.raises(ReviewAuthorizationError, match="clarification"):
        evaluate_review_complete(snapshot, cycle)

    assert cycle.model_dump_json() == before


@pytest.mark.parametrize("provider", ["github", "gitlab"])
@pytest.mark.parametrize("disposition", ["accepted_change", "no_change", "superseded"])
def test_resolved_disposition_can_complete(provider: Literal["github", "gitlab"], disposition: str) -> None:
    """Completed dispositions retain the existing completion path after reassessment."""
    snapshot, cycle = communicated_cycle(provider)
    cycle = cycle.model_copy(
        update={
            "assessments": [
                cycle.assessments[0].model_copy(
                    update={"validity": "valid", "disposition": disposition, "unknowns": []}
                )
            ],
            "unknown_decisions": {},
            "implementation_states": {
                cycle.input_census[0]: "completed" if disposition == "accepted_change" else "not_required"
            },
        }
    )
    cycle = ReviewCycleState.model_validate_json(cycle.model_dump_json())

    assert evaluate_review_complete(snapshot, cycle).cycle_state == "REVIEW_COMPLETE"


@pytest.mark.parametrize("provider", ["github", "gitlab"])
def test_clarification_question_can_still_be_authorized(provider: Literal["github", "gitlab"]) -> None:
    """The terminal guard must not block communicating the clarification itself."""
    snapshot, cycle = communicated_cycle(provider)
    item = snapshot.review_inputs[0]
    cycle = cycle.model_copy(update={"communication_states": {item.input_id: "pending"}})
    action = TopLevelCommentAction(body="Which behavior is required?", references=[item.stable_reference])

    authorized = authorize_action(snapshot, cycle, item.input_id, action)

    assert authorized.disposition == "clarification_required"
    assert authorized.action == action


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
