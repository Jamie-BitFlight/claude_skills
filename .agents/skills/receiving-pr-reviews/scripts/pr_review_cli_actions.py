"""Shared preflight helpers for review mutation CLI commands."""

from __future__ import annotations

from pathlib import Path

from pr_review_contracts import ChangeRequestTarget, ReplyAction, ResolveAction, ReviewAction
from pr_review_models import ReviewSnapshot
from pr_review_provider import ProviderResponseError, ReviewProvider
from pr_review_state import (
    authorize_action,
    load_cycle,
    load_snapshot,
    record_completed_communication,
    record_completed_resolution,
)
from pr_review_state_models import AuthorizedReviewAction, ReviewCycleState


def load_current_snapshot(
    target: ChangeRequestTarget, snapshot_file: Path, *, provider: ReviewProvider, command_timeout: float | None
) -> ReviewSnapshot:
    """Refresh provider state and reject a stale caller-supplied snapshot.

    Args:
        target: Canonical command target.
        snapshot_file: Previously saved canonical snapshot JSON.
        provider: Selected provider used for the mandatory refresh.
        command_timeout: Positive caller-selected provider command bound.

    Returns:
        Fresh provider snapshot identical to the saved authorization identity.

    Raises:
        ProviderResponseError: If the saved target or snapshot identity is stale.
    """
    saved_snapshot = load_snapshot(snapshot_file)
    if saved_snapshot.target != target:
        raise ProviderResponseError("snapshot target does not match command target")
    snapshot = provider.snapshot(target, deadline=None, command_timeout=command_timeout)
    if (
        snapshot.target != saved_snapshot.target
        or snapshot.head_revision != saved_snapshot.head_revision
        or snapshot.snapshot_fingerprint != saved_snapshot.snapshot_fingerprint
    ):
        raise ProviderResponseError("saved review snapshot is no longer current")
    return snapshot


def authorized_action(
    target: ChangeRequestTarget,
    snapshot_file: Path,
    state_file: Path,
    input_id: str,
    action: ReviewAction,
    *,
    provider: ReviewProvider,
    command_timeout: float | None,
) -> tuple[AuthorizedReviewAction, ReviewCycleState]:
    """Load and validate one current pre-action gate.

    Args:
        target: Canonical command target.
        snapshot_file: Complete canonical snapshot JSON.
        state_file: Complete review-cycle JSON.
        input_id: Canonical inbound input selected for mutation.
        action: Provider-neutral mutation to authorize.
        provider: Selected provider used to refresh remote state before authorization.
        command_timeout: Positive caller-selected provider command bound.

    Returns:
        The action bound to validated evidence and the loaded cycle to update after success.
    """
    cycle = load_cycle(state_file)
    snapshot = load_current_snapshot(target, snapshot_file, provider=provider, command_timeout=command_timeout)
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
