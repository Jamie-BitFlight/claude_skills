"""Normalize complete GitLab merge-request state into the public review schema."""

from __future__ import annotations

from collections.abc import Iterable

from pr_review_contracts import ChangeRequestTarget
from pr_review_gitlab_wire import GitLabAwardEmoji, GitLabDiscussion, GitLabNote, GitLabState, GitLabUser
from pr_review_models import (
    ProviderApprovalState,
    ProviderSystemEvent,
    Reviewability,
    ReviewProviderMetadata,
    ReviewSnapshot,
)
from pr_review_provider_text import reference_present
from pr_review_state_models import (
    InputKind,
    ProviderInputIdentity,
    ReviewActor,
    ReviewCapabilities,
    ReviewInput,
    SnapshotCompleteness,
    calculate_snapshot_fingerprint,
)

SURFACES = {"merge_request", "discussions", "notes", "approvals", "award_emoji", "versions", "identity"}


def actor(user: GitLabUser, state: GitLabState, *, reviewer: bool = False) -> ReviewActor:
    """Map only provider-observable identity and role facts.

    Args:
        user: Provider-observed GitLab user.
        state: Complete stable GitLab state.
        reviewer: Whether the source surface proves a reviewer role.

    Returns:
        A provider-neutral actor.
    """
    classification = "bot" if user.bot is True else "human" if user.bot is False else "unknown"
    if user.id == state.merge_request.author.id:
        role = "author"
    elif reviewer:
        role = "reviewer"
    else:
        role = "unknown"
    return ReviewActor(
        actor_id=str(user.id), login=user.username, display_name=user.name, classification=classification, role=role
    )


def note_reference(state: GitLabState, note: GitLabNote) -> str:
    """Build GitLab's stable merge-request note anchor.

    Args:
        state: Complete stable GitLab state.
        note: Atomic note whose stable URL is required.

    Returns:
        A stable note URL.
    """
    return f"{state.merge_request.web_url}#note_{note.id}"


def note_input(state: GitLabState, note: GitLabNote, *, discussion: GitLabDiscussion | None) -> ReviewInput | None:
    """Normalize one non-system note, preserving discussion mutation targets.

    Args:
        state: Complete stable GitLab state.
        note: Atomic provider note.
        discussion: Owning discussion, when the note was observed there.

    Returns:
        One canonical input, or ``None`` for a system note.
    """
    if note.system:
        return None
    position = note.position
    current_user = note.author.id == state.current_user.id
    threaded = discussion is not None and not discussion.individual_note
    resolved = note.resolved is True
    can_resolve = threaded and note.resolvable and not resolved
    relation = "unknown"
    if position is not None and position.head_sha is not None:
        relation = "current" if position.head_sha == state.merge_request.sha else "stale"
    path = None if position is None else position.new_path or position.old_path
    line = None if position is None else position.new_line or position.old_line
    discussion_id = discussion.id if discussion is not None else None
    return ReviewInput(
        input_id=f"gitlab:note:{note.id}",
        provider="gitlab",
        provider_ids=ProviderInputIdentity(
            object_id=str(note.id),
            reply_target_id=discussion_id if threaded else None,
            resolution_target_id=discussion_id if can_resolve else None,
        ),
        source_kind="discussion_note" if threaded else "individual_note",
        kinds={"comment"},
        location="inline" if position is not None else "top_level",
        direction="outbound" if current_user else "inbound",
        actor=actor(note.author, state),
        body=note.body,
        stable_reference=note_reference(state, note),
        created_at=note.created_at,
        updated_at=note.updated_at,
        revision_relation=relation,
        path=path,
        line=line,
        provider_state="resolved" if resolved else "open",
        capabilities=ReviewCapabilities(
            can_reply=threaded,
            can_resolve=can_resolve,
            can_comment=True,
            unavailable=[] if threaded else ["inline_reply", "provider_resolution"],
        ),
        thread_id=discussion_id,
        parent_id=str(discussion.notes[0].id) if discussion is not None and note != discussion.notes[0] else None,
    )


def note_inputs(state: GitLabState) -> list[ReviewInput]:
    """Normalize discussions and add any notes missing from that endpoint.

    Args:
        state: Complete stable GitLab state.

    Returns:
        De-duplicated atomic note inputs.
    """
    normalized: list[ReviewInput] = []
    seen: set[int] = set()
    for discussion in state.discussions:
        for note in discussion.notes:
            seen.add(note.id)
            if item := note_input(state, note, discussion=discussion):
                normalized.append(item)
    normalized.extend(
        item for note in state.notes if note.id not in seen and (item := note_input(state, note, discussion=None))
    )
    return normalized


def approval_inputs(state: GitLabState) -> list[ReviewInput]:
    """Normalize only actor-backed approvals, never zero-required platform state.

    Args:
        state: Complete stable GitLab state.

    Returns:
        Actor-backed approval inputs.
    """
    inputs: list[ReviewInput] = []
    for approval in state.approvals.approved_by:
        user = approval.user
        inputs.append(
            ReviewInput(
                input_id=f"gitlab:approval:{user.id}",
                provider="gitlab",
                provider_ids=ProviderInputIdentity(object_id=str(user.id)),
                source_kind="merge_request_approval",
                kinds={"approval"},
                location="top_level",
                direction="outbound" if user.id == state.current_user.id else "inbound",
                actor=actor(user, state, reviewer=True),
                body="",
                stable_reference=f"{state.merge_request.web_url}#approval_{user.id}",
                created_at=None,
                updated_at=None,
                revision_relation="unknown",
                path=None,
                line=None,
                provider_state="approved",
                capabilities=ReviewCapabilities(
                    can_reply=False,
                    can_resolve=False,
                    can_comment=True,
                    unavailable=["inline_reply", "provider_resolution", "approval_timestamp"],
                ),
                thread_id=None,
                parent_id=None,
            )
        )
    return inputs


def award_kind(award: GitLabAwardEmoji) -> set[InputKind]:
    """Map explicit positive/negative award signals and retain other awards as comments.

    Args:
        award: Provider award emoji to classify.

    Returns:
        The canonical semantic kind set.
    """
    if award.name in {"thumbsup", "+1"}:
        return {"approval"}
    if award.name in {"thumbsdown", "-1"}:
        return {"rejection"}
    return {"comment"}


def award_inputs(state: GitLabState) -> list[ReviewInput]:
    """Normalize merge-request award signals as independently assessable inputs.

    Args:
        state: Complete stable GitLab state.

    Returns:
        Atomic award inputs.
    """
    return [
        ReviewInput(
            input_id=f"gitlab:award:{award.id}",
            provider="gitlab",
            provider_ids=ProviderInputIdentity(object_id=str(award.id)),
            source_kind="award_emoji",
            kinds=award_kind(award),
            location="top_level",
            direction="outbound" if award.user.id == state.current_user.id else "inbound",
            actor=actor(award.user, state, reviewer=award.name in {"thumbsup", "+1", "thumbsdown", "-1"}),
            body=award.name,
            stable_reference=f"{state.merge_request.web_url}#award_{award.id}",
            created_at=award.created_at,
            updated_at=award.updated_at,
            revision_relation="unknown",
            path=None,
            line=None,
            provider_state=award.name,
            capabilities=ReviewCapabilities(
                can_reply=False,
                can_resolve=False,
                can_comment=True,
                unavailable=["inline_reply", "provider_resolution"],
            ),
            thread_id=None,
            parent_id=None,
        )
        for award in state.awards
    ]


def ordered(inputs: Iterable[ReviewInput]) -> list[ReviewInput]:
    """Return a deterministic provider-independent sequence.

    Args:
        inputs: Normalized provider inputs.

    Returns:
        Inputs ordered by provider timestamp and canonical identity.
    """
    return sorted(inputs, key=lambda item: (item.created_at is None, item.created_at, item.input_id))


def provider_metadata(state: GitLabState) -> ReviewProviderMetadata:
    """Retain observable platform state outside the review-input census.

    Args:
        state: Complete stable GitLab state.

    Returns:
        Provider metadata for system events, approvals, and blocking discussions.
    """
    system_notes: dict[int, GitLabNote] = {}
    for discussion in state.discussions:
        system_notes.update({note.id: note for note in discussion.notes if note.system})
    system_notes.update({note.id: note for note in state.notes if note.system})
    return ReviewProviderMetadata(
        system_notes=[
            ProviderSystemEvent(id=str(note.id), body=note.body, created_at=note.created_at)
            for note in sorted(system_notes.values(), key=lambda value: (value.created_at, value.id))
        ],
        approval_state=ProviderApprovalState(
            approved=state.approvals.approved,
            approvals_required=state.approvals.approvals_required,
            approvals_left=state.approvals.approvals_left,
            approval_rules_left=state.approvals.approval_rules_left,
        ),
        blocking_discussions_resolved=state.merge_request.blocking_discussions_resolved,
    )


def communicated_inputs(inputs: list[ReviewInput]) -> set[str]:
    """Find inbound inputs quoted exactly by a later authenticated-actor note.

    Args:
        inputs: Complete normalized input census in stable order.

    Returns:
        Canonical inbound input IDs with provider-observed communication evidence.
    """
    outbound = [item for item in inputs if item.direction == "outbound"]
    return {
        item.input_id
        for item in inputs
        if item.direction == "inbound"
        and any(
            response.created_at is not None
            and (item.created_at is None or response.created_at >= item.created_at)
            and reference_present(response.body, item.stable_reference)
            for response in outbound
        )
    }


def normalize_state(state: GitLabState, target: ChangeRequestTarget) -> ReviewSnapshot:
    """Build one complete canonical GitLab snapshot.

    Args:
        state: Complete stable GitLab state.
        target: Canonical merge-request target.

    Returns:
        A complete provider-neutral review snapshot.
    """
    inputs = ordered([*note_inputs(state), *approval_inputs(state), *award_inputs(state)])
    completeness = SnapshotCompleteness(
        transport="gitlab_cli",
        required_surfaces=SURFACES,
        completed_surfaces=SURFACES,
        truncated_input_ids=[],
        unavailable_capabilities=["codex_approval_equivalence", "explicit_change_request_state"],
    )
    revision_at = max(version.created_at for version in state.versions)
    unresolved_threads = {
        item.thread_id
        for item in inputs
        if item.direction == "inbound" and item.capabilities.can_resolve and item.provider_state == "open"
    }
    blockers = []
    if state.merge_request.draft or state.merge_request.work_in_progress:
        blockers.append("draft")
    if state.merge_request.has_conflicts:
        blockers.append("conflicts")
    reviewability = Reviewability(
        is_draft=state.merge_request.draft or state.merge_request.work_in_progress,
        mergeable=state.merge_request.merge_status,
        merge_state_status=state.merge_request.detailed_merge_status,
        blockers=blockers,
    )
    metadata = provider_metadata(state)
    communicated = communicated_inputs(inputs)
    snapshot_fingerprint = calculate_snapshot_fingerprint(
        target,
        state.merge_request.sha,
        inputs,
        completeness,
        revision_at=revision_at,
        reviewability=reviewability,
        provider_metadata=metadata,
        communicated_input_ids=communicated,
    )
    return ReviewSnapshot(
        provider="gitlab",
        target=target,
        transport="gitlab_cli",
        snapshot_complete=True,
        snapshot_fingerprint=snapshot_fingerprint,
        head_revision=state.merge_request.sha,
        revision_at=revision_at,
        completeness=completeness,
        review_inputs=inputs,
        assessments=[],
        clusters=[],
        cycle_state="ASSESSMENT_REQUIRED",
        codex_approval_equivalence="unavailable",
        reviews_count=sum("approval" in item.kinds for item in inputs),
        threads_count=sum(
            not discussion.individual_note and any(not note.system for note in discussion.notes)
            for discussion in state.discussions
        ),
        unresolved_count=len(unresolved_threads),
        outstanding_input_count=sum(
            item.direction == "inbound" and item.provider_state != "resolved" and item.input_id not in communicated
            for item in inputs
        ),
        codex_approved=None,
        reviewability=reviewability,
        provider_metadata=metadata,
        communicated_input_ids=communicated,
    )
