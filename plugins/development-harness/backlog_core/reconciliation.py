"""Provider-neutral snapshot reconciliation for persisted backlog items."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from typing import Literal, assert_never

from pydantic import BaseModel, Field

from .github_sync import merge_item, parse_issue_body, render_issue_body
from .models import (
    HEAD_FIELDS,
    TYPE_TO_LABEL,
    BacklogItem,
    PatchResult,
    ProviderItem,
    ProviderPatch,
    ProviderSnapshot,
    ReconcileRequest,
    ReconcileResult,
)
from .status_registry import STATUS_LABEL_PREFIX, pick_primary_status_label

#: Head fields whose D2 precedence is label-and-issue-state aware, resolved by
#: their own dedicated function below rather than the generic head-or-local
#: fallback every other HEAD_FIELDS member uses.
_SPECIALLY_RESOLVED_FIELDS = frozenset({"priority", "item_type", "status", "added"})
_GENERIC_HEAD_FIELDS = HEAD_FIELDS - _SPECIALLY_RESOLVED_FIELDS
_TERMINAL_STATUS_VALUES = frozenset({"done", "closed", "resolved"})
_LABEL_TO_TYPE: dict[str, str] = {label: name.capitalize() for name, label in TYPE_TO_LABEL.items()}

__all__ = [
    "ActionResult",
    "CacheAction",
    "LogicalCacheRecord",
    "ReconcileExecution",
    "ReconcileOutcome",
    "ReconcilePlan",
    "finalize_reconciliation",
    "provider_item_to_backlog_item",
    "reconcile_backlog",
    "synchronized_fingerprint",
]


class LogicalCacheRecord(BaseModel):
    """One backend-owned cache record identified without a filesystem path."""

    key: str
    item: BacklogItem
    #: True when *item* was taken from a queued mutation rather than a
    #: checkpointed provider snapshot (see github_work_items.load_records).
    #: Gates whether _candidate treats item.metadata's head fields as
    #: in-flight agent intent (D7) -- unset (False) for every record loaded
    #: from a snapshot alone.
    pending: bool = False


class CacheAction(BaseModel):
    """A logical cache mutation ordered around provider patch execution."""

    key: str
    kind: Literal["upsert", "unlink"] = "upsert"
    phase: Literal["before_provider", "checkpoint"] = "before_provider"
    record: LogicalCacheRecord
    requires_patch: str = ""
    reference: str = ""


class ReconcilePlan(BaseModel):
    """Deterministic cache and provider actions for one snapshot."""

    cache_actions: list[CacheAction] = Field(default_factory=list)
    provider_patches: list[ProviderPatch] = Field(default_factory=list)
    result: ReconcileResult = Field(default_factory=ReconcileResult)
    snapshot_checkpoint: str = ""
    dry_run: bool = False
    conflicted_references: list[str] = Field(default_factory=list)


class ActionResult(BaseModel):
    """Adapter-reported outcome for one cache action."""

    key: str
    phase: Literal["before_provider", "checkpoint"]
    status: Literal["applied", "error"]


class ReconcileExecution(BaseModel):
    """Durable outcomes reported after an adapter executes a plan.

    Attributes:
        cache_results: One outcome per cache action the adapter attempted.
        patch_results: One outcome per provider patch the adapter attempted
            to apply.  Absent when ``patches_skipped`` is True -- see that
            field.
        patches_skipped: True when the adapter deliberately never attempted
            ``plan.provider_patches`` at all (a fetch-only reconcile, e.g.
            ``ReconcileRequest.apply_local_patches=False``), as opposed to
            attempting them and some failing to produce a result. A queued
            local mutation this pass could not push is not, by itself, a
            failed reconciliation of everything else the pass *did*
            complete (the provider snapshot fetch and the local cache
            update) -- see ``finalize_reconciliation``.
    """

    cache_results: list[ActionResult] = Field(default_factory=list)
    patch_results: list[PatchResult] = Field(default_factory=list)
    patches_skipped: bool = False


class ReconcileOutcome(BaseModel):
    """Completed counts and the global snapshot-checkpoint decision."""

    result: ReconcileResult
    advance_snapshot_checkpoint: bool


def synchronized_fingerprint(item: BacklogItem) -> str:
    """Return the checkpoint hash for the provider-synchronized item projection."""
    projection = {
        "added": item.metadata.added,
        "description": item.description,
        "item_type": item.metadata.item_type,
        "priority": item.metadata.priority,
        "sections": item.sections,
        "status": item.metadata.status,
        "title": item.title,
    }
    payload = json.dumps(
        projection, default=lambda value: value.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def _normalized_body(body: str) -> str:
    return body.replace("\r\n", "\n").replace("\r", "\n")


def _mirrored_label_value(labels: Sequence[str], prefix: str, head_value: str) -> str:
    """Return the bare value from the single label under *prefix* that mirrors a head field.

    When several such labels are present (a data inconsistency -- normal
    writes through apply_patches's label mirror keep at most one), the label
    matching *head_value* wins, so a head value that was itself derived from
    labels round-trips instead of being overridden by list order. Falls back
    to the first label when none matches or no head value is supplied.

    Returns:
        The bare label value (e.g. ``"p1"``, ``"bug"``), or ``""`` when no
        label carries *prefix*.
    """
    matches = [label[len(prefix) :] for label in labels if label.startswith(prefix)]
    if not matches:
        return ""
    if len(matches) == 1 or not head_value:
        return matches[0]
    for match in matches:
        if match.lower() == head_value.lower():
            return match
    return matches[0]


def _label_priority(labels: Sequence[str], head_priority: str = "") -> str:
    """Return the priority a ``priority:`` label names, or ``""`` when none does.

    Issues created by ``create_issue_for_item`` carry priority only in this label;
    their body has no ``backlog-metadata`` block for ``parse_issue_body`` to read.
    """
    match = _mirrored_label_value(labels, "priority:", head_priority.lower() if head_priority else "")
    return match.upper() if match else ""


def _label_item_type(labels: Sequence[str], head_item_type: str = "") -> str:
    """Return the type a ``type:`` label names, or ``""`` when none does."""
    type_labels = [label for label in labels if label in _LABEL_TO_TYPE]
    if not type_labels:
        return ""
    head_label = TYPE_TO_LABEL.get(head_item_type.lower()) if head_item_type else None
    if len(type_labels) > 1 and head_label in type_labels:
        return _LABEL_TO_TYPE[head_label]
    return _LABEL_TO_TYPE[type_labels[0]]


def _resolve_priority(provider: ProviderItem, head_priority: str, body_priority: str) -> str:
    """Return the D2 priority: labels (head-preferring) > head (unless completed) > body block > ''.

    A head value of ``"completed"`` counts only while the issue is CLOSED.
    """
    is_closed = provider.state.lower() == "closed"
    if is_closed and head_priority.lower() == "completed":
        return head_priority
    label = _label_priority(provider.labels, head_priority)
    if label:
        return label
    if head_priority and head_priority.lower() != "completed":
        return head_priority
    return body_priority


def _resolve_item_type(provider: ProviderItem, head_item_type: str, body_item_type: str) -> str:
    """Return the D2 item_type: labels (head-preferring) > head > body block > 'Feature'."""
    label = _label_item_type(provider.labels, head_item_type)
    if label:
        return label
    if head_item_type:
        return head_item_type
    return body_item_type or "Feature"


def _resolve_status(provider: ProviderItem, head_status: str) -> str:
    """Return the D2 status: primary status label > head (non-terminal, non-open) > 'open'/'closed'."""
    if provider.state.lower() == "closed":
        return head_status if head_status.lower() in _TERMINAL_STATUS_VALUES else "closed"
    status_labels = [label for label in provider.labels if label.startswith(STATUS_LABEL_PREFIX)]
    primary = pick_primary_status_label(status_labels)
    if primary:
        return primary.removeprefix(STATUS_LABEL_PREFIX)
    if head_status and head_status.lower() not in _TERMINAL_STATUS_VALUES and head_status.lower() != "open":
        return head_status
    return "open"


def _resolve_added(head_added: str, body_added: str, created_at: str) -> str:
    """Return the D2 added: head > body block > the issue's createdAt date."""
    if head_added:
        return head_added
    if body_added:
        return body_added
    return created_at[:10] if created_at else ""


def _head_field_map(candidate: BacklogItem) -> dict[str, str]:
    """Return *candidate*'s full head-field map (see models.HEAD_FIELDS)."""
    return {name: str(getattr(candidate.metadata, name)) for name in HEAD_FIELDS}


def _compose(
    local: BacklogItem, provider: ProviderItem, body_item: BacklogItem, *, title: str | None = None
) -> BacklogItem:
    head_fields = provider.fields

    def _head_or_local(name: str) -> str:
        if head_fields is not None and name in head_fields:
            return head_fields[name]
        return str(getattr(local.metadata, name))

    head_priority = head_fields.get("priority", "") if head_fields is not None else ""
    head_item_type = head_fields.get("item_type", "") if head_fields is not None else ""
    head_status = head_fields.get("status", "") if head_fields is not None else ""
    head_added = head_fields.get("added", "") if head_fields is not None else ""

    metadata_updates: dict[str, object] = {name: _head_or_local(name) for name in _GENERIC_HEAD_FIELDS}
    metadata_updates.update({
        "added": _resolve_added(head_added, body_item.metadata.added, provider.created_at),
        "issue": provider.reference,
        "item_type": _resolve_item_type(provider, head_item_type, body_item.metadata.item_type),
        "labels": provider.labels,
        "priority": _resolve_priority(provider, head_priority, body_item.metadata.priority),
        "status": _resolve_status(provider, head_status),
        "updated_at": provider.revision,
    })
    metadata = local.metadata.model_copy(update=metadata_updates)
    return BacklogItem(
        title=provider.title if title is None else title,
        reference=local.reference,
        description=body_item.description,
        sections=body_item.sections,
        metadata=metadata,
    )


def provider_item_to_backlog_item(provider: ProviderItem) -> BacklogItem:
    """Convert one normalized provider item into the logical work-item model.

    Returns:
        Parsed logical work item carrying provider-owned fields.
    """
    parsed = parse_issue_body(provider.body)
    return _compose(BacklogItem(reference=provider.reference), provider, parsed)


def _checkpoint(item: BacklogItem, revision: str) -> BacklogItem:
    metadata = item.metadata.model_copy(
        update={"sync_fingerprint": synchronized_fingerprint(item), "updated_at": revision}
    )
    return BacklogItem(
        title=item.title,
        reference=item.reference,
        description=item.description,
        sections=item.sections,
        metadata=metadata,
    )


def _merged_title(local: BacklogItem, remote: BacklogItem, baseline: str) -> str:
    """Return the provider's title when local never edited it, else keep local's.

    Substitutes ``local.title`` into the remote projection and checks whether
    that hypothetical fingerprint reproduces ``baseline``. A match proves the
    only thing distinguishing ``remote`` from ``baseline`` was its title, so
    ``local`` never touched the title and the remote rename is safe to accept.
    A remote-side change to any other field breaks the substitution even when
    local's title is untouched -- that case falls back to ``local.title`` and
    surfaces as a conflict instead of silently discarding the remote change.
    """
    if not baseline:
        return local.title
    probe = remote.model_copy(update={"title": local.title})
    return remote.title if synchronized_fingerprint(probe) == baseline else local.title


def _pending_head_fields(local: BacklogItem, remote: BacklogItem, head_fields: dict[str, str] | None) -> dict[str, str]:
    """Return the D7 candidate head-field map for a record carrying pending intent.

    Starts from the local (in-flight) value for every head field. For
    priority, item_type and status only: when the local value still equals
    the raw head value, the agent never touched that field, so the
    remote-composed value is taken instead -- this is what absorbs a human
    label edit made while the mutation was queued. Every other head field
    always keeps the local value, so an in-flight plan/topic/etc. write is
    never clobbered by a head that has not caught up with it yet (see design
    R2 -- this is a last-writer-wins choice, not a merge).
    """
    resolved: dict[str, str] = {}
    for name in HEAD_FIELDS:
        local_value = str(getattr(local.metadata, name))
        if name in _SPECIALLY_RESOLVED_FIELDS:
            head_value = head_fields.get(name, "") if head_fields is not None else ""
            resolved[name] = str(getattr(remote.metadata, name)) if local_value == head_value else local_value
        else:
            resolved[name] = local_value
    return resolved


def _candidate(
    local: BacklogItem, provider: ProviderItem, request: ReconcileRequest, *, pending: bool = False
) -> tuple[BacklogItem, ProviderPatch | None]:
    remote_body = parse_issue_body(provider.body, existing=local)
    remote = _compose(local, provider, remote_body)
    baseline = local.metadata.sync_fingerprint
    local_changed = not baseline or synchronized_fingerprint(local) != baseline
    remote_changed = not baseline or synchronized_fingerprint(remote) != baseline
    if request.force:
        candidate = remote
    elif local_changed and remote_changed:
        merged_title = _merged_title(local, remote, baseline)
        candidate = _compose(local, provider, merge_item(local, remote_body), title=merged_title)
    elif remote_changed:
        candidate = remote
    else:
        candidate = _compose(local, provider, local, title=local.title)
    if pending:
        # D7: a record carrying pending intent resolves its head fields from
        # local-vs-head divergence, not purely from the body/fingerprint
        # merge branch above (which only ever governs title/description/
        # sections -- see synchronized_fingerprint's projection).
        candidate = candidate.model_copy(
            update={
                "metadata": candidate.metadata.model_copy(update=_pending_head_fields(local, remote, provider.fields))
            }
        )
    rendered = render_issue_body(candidate, original_body=provider.body)
    patch_fields = _head_field_map(candidate)
    body_changed = _normalized_body(rendered) != _normalized_body(provider.body)
    head_fields_changed = pending and patch_fields != (provider.fields or {})
    if not body_changed and not head_fields_changed:
        return candidate, None
    return candidate, ProviderPatch(
        provider_id=provider.provider_id,
        reference=provider.reference,
        expected_revision=provider.revision,
        body=rendered,
        fields=patch_fields,
    )


def _action(
    key: str,
    item: BacklogItem,
    *,
    phase: Literal["before_provider", "checkpoint"] = "before_provider",
    requires_patch: str = "",
    kind: Literal["upsert", "unlink"] = "upsert",
    reference: str = "",
) -> CacheAction:
    return CacheAction(
        key=key,
        kind=kind,
        phase=phase,
        record=LogicalCacheRecord(key=key, item=item),
        requires_patch=requires_patch,
        reference=reference or item.metadata.issue,
    )


def _plan_item(
    record: LogicalCacheRecord | None, provider: ProviderItem, request: ReconcileRequest, plan: ReconcilePlan
) -> None:
    if record is None:
        if provider.exists:
            item = _checkpoint(provider_item_to_backlog_item(provider), provider.revision)
            plan.cache_actions.append(_action(provider.reference, item))
            plan.result.changed_references.append(provider.reference)
        return
    local = record.item
    if not provider.exists:
        metadata = local.metadata.model_copy(update={"issue": "", "sync_fingerprint": "", "updated_at": ""})
        unlinked = BacklogItem(
            title=local.title,
            reference=local.reference,
            description=local.description,
            sections=local.sections,
            metadata=metadata,
        )
        plan.cache_actions.append(_action(record.key, unlinked, kind="unlink", reference=local.metadata.issue))
        plan.result.changed_references.append(provider.reference)
        return
    candidate, patch = _candidate(local, provider, request, pending=record.pending)
    if candidate.title != provider.title:
        if candidate != local:
            plan.cache_actions.append(_action(record.key, candidate))
        if patch is not None:
            plan.provider_patches.append(patch)
        plan.result.conflicts += 1
        plan.result.changed_references.append(provider.reference)
        plan.conflicted_references.append(provider.reference)
        if request.include_diff and patch is not None:
            plan.result.diffs[provider.reference] = (
                f"{_normalized_body(provider.body)}\n---\n{_normalized_body(patch.body)}"
            )
        return
    if patch is None:
        plan.result.no_ops += 1
        checkpointed = _checkpoint(candidate, provider.revision)
        if checkpointed != local:
            plan.cache_actions.append(_action(record.key, checkpointed))
            plan.result.changed_references.append(provider.reference)
        return
    if candidate != local:
        plan.cache_actions.append(_action(record.key, candidate))
    plan.provider_patches.append(patch)
    plan.cache_actions.append(
        _action(
            record.key, _checkpoint(candidate, provider.revision), phase="checkpoint", requires_patch=provider.reference
        )
    )
    plan.result.changed_references.append(provider.reference)
    if request.include_diff:
        plan.result.diffs[provider.reference] = (
            f"{_normalized_body(provider.body)}\n---\n{_normalized_body(patch.body)}"
        )


def reconcile_backlog(
    records: Sequence[LogicalCacheRecord], snapshot: ProviderSnapshot, request: ReconcileRequest
) -> ReconcilePlan:
    """Classify logical cache records against a normalized provider snapshot.

    Returns:
        Ordered logical cache and provider actions.
    """
    result = ReconcileResult(fetched_pages=snapshot.pages_fetched, fetched_items=len(snapshot.items))
    plan = ReconcilePlan(result=result, snapshot_checkpoint=snapshot.sync_started_at, dry_run=request.dry_run)
    local_by_reference = {record.item.metadata.issue: record for record in records if record.item.metadata.issue}
    for provider_item in snapshot.items:
        _plan_item(local_by_reference.get(provider_item.reference), provider_item, request, plan)
    plan.result.changed_references = list(dict.fromkeys(plan.result.changed_references))
    if request.dry_run:
        plan.cache_actions = []
        plan.provider_patches = []
    return plan


def _account_for_patch_outcomes(
    plan: ReconcilePlan, execution: ReconcileExecution, result: ReconcileResult
) -> set[str]:
    """Fold each planned patch's outcome into *result* and report which applied.

    Split out of :func:`finalize_reconciliation` to keep that function's
    branch count under the project's complexity ceiling; this loop is the
    only place a planned patch's per-status accounting happens.

    A patch in ``plan.provider_patches`` with no matching entry in
    ``execution.patch_results`` counts as ``result.skipped_patches`` when
    ``execution.patches_skipped`` is True (a fetch-only reconcile that never
    attempted it), and as ``result.failures`` otherwise (an attempted patch
    the provider never returned an outcome for). Only ``failures`` gates
    ``advance_snapshot_checkpoint`` -- an intentionally skipped patch must not
    block the checkpoint from advancing over the snapshot fetch and cache
    update this pass did complete, while an unexplained missing outcome
    still must.

    Args:
        plan: The reconciliation plan whose ``provider_patches`` are being scored.
        execution: The adapter's durable outcomes for this pass.
        result: Mutated in place with each patch's outcome.

    Returns:
        The references of patches whose status was ``"applied"`` -- the
        checkpoint cache actions gate on this set.
    """
    patch_results = {patch.reference: patch for patch in execution.patch_results}
    applied_patches: set[str] = set()
    for patch in plan.provider_patches:
        patch_result = patch_results.get(patch.reference)
        if patch_result is None:
            if execution.patches_skipped:
                # Never attempted -- a fetch-only reconcile intentionally
                # never called _apply_patches (see ReconcileExecution's
                # patches_skipped docstring). Distinct from "attempted and
                # the provider never returned an outcome for it", which stays
                # a genuine failure below.
                result.skipped_patches += 1
            else:
                result.failures += 1
            continue
        result.patch_results.append(patch_result)
        match patch_result.status:
            case "applied":
                result.provider_patches += 1
                applied_patches.add(patch.reference)
            case "conflict":
                result.conflicts += 1
            case "error":
                result.failures += 1
            case unreachable:
                assert_never(unreachable)
    return applied_patches


def finalize_reconciliation(plan: ReconcilePlan, execution: ReconcileExecution) -> ReconcileOutcome:
    """Convert durable adapter outcomes into counts and checkpoint eligibility.

    See :func:`_account_for_patch_outcomes` for how a planned patch missing
    from ``execution.patch_results`` is scored as a skip versus a failure.

    Returns:
        Completed outcome counts and the global checkpoint decision.
    """
    result = plan.result.model_copy(deep=True)
    applied_patches = _account_for_patch_outcomes(plan, execution, result)
    cache_results = {(action.key, action.phase): action for action in execution.cache_results}
    updated_keys: set[str] = set()
    eligible_actions = [
        action for action in plan.cache_actions if not action.requires_patch or action.requires_patch in applied_patches
    ]
    for action in eligible_actions:
        action_result = cache_results.get((action.key, action.phase))
        if action_result is None:
            result.failures += 1
            continue
        match action_result.status:
            case "applied":
                updated_keys.add(action.key)
                if action.kind == "unlink":
                    result.deleted_provider_items += 1
            case "error":
                result.failures += 1
            case unreachable:
                assert_never(unreachable)
    result.local_updates = len(updated_keys)
    return ReconcileOutcome(result=result, advance_snapshot_checkpoint=not plan.dry_run and result.failures == 0)
