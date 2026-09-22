"""Shared preflight helpers for review mutation CLI commands."""

from __future__ import annotations

from pathlib import Path

from pr_review_contracts import ChangeRequestTarget, ReplyAction, ResolveAction, ReviewAction
from pr_review_models import ReviewSnapshot
from pr_review_provider import ProviderResponseError
from pr_review_state import (
    authorize_action,
    load_cycle,
    load_snapshot,
    record_completed_communication,
    record_completed_resolution,
)
from pr_review_state_models import AuthorizedReviewAction, ReviewCycleState


def authorized_action(
    target: ChangeRequestTarget, snapshot_file: Path, state_file: Path, input_id: str, action: ReviewAction
) -> tuple[AuthorizedReviewAction, ReviewCycleState]:
    """Load and validate one current pre-action gate.

    Args:
        target: Canonical command target.
        snapshot_file: Complete canonical snapshot JSON.
        state_file: Complete review-cycle JSON.
        input_id: Canonical inbound input selected for mutation.
        action: Provider-neutral mutation to authorize.

    Returns:
        The action bound to validated evidence and the loaded cycle to update after success.
    """
    snapshot = load_snapshot(snapshot_file)
    cycle = load_cycle(state_file)
    if snapshot.target != target:
        raise ProviderResponseError("snapshot target does not match command target")
    return authorize_action(snapshot, cycle, input_id, action), cycle


def authorize_reply_and_resolve(
    snapshot: ReviewSnapshot, cycle: ReviewCycleState, input_id: str, body: str
) -> tuple[AuthorizedReviewAction, AuthorizedReviewAction, ReviewCycleState]:
    """Preflight both halves of a combined mutation without provider calls.

    Args:
        snapshot: Current complete provider snapshot.
        cycle: Current complete review cycle.
        input_id: Canonical inline input selected for both actions.
        body: Evidence-bearing reply body.

    Returns:
        Authorized reply, authorized resolution, and simulated completed state.
    """
    reply_action = authorize_action(snapshot, cycle, input_id, ReplyAction(body=body))
    simulated = record_completed_communication(cycle, input_id)
    resolve_action = authorize_action(snapshot, simulated, input_id, ResolveAction())
    return reply_action, resolve_action, record_completed_resolution(simulated, input_id)
