"""Provider-neutral snapshot reconciliation for persisted backlog items."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from typing import Literal, assert_never

from pydantic import BaseModel, Field

from .github_sync import merge_item, parse_issue_body, render_issue_body
from .models import (
    BacklogItem,
    PatchResult,
    ProviderItem,
    ProviderPatch,
    ProviderSnapshot,
    ReconcileRequest,
    ReconcileResult,
)

__all__ = [
    "ActionResult",
    "CacheAction",
    "LogicalCacheRecord",
    "ReconcileExecution",
    "ReconcileOutcome",
    "ReconcilePlan",
    "finalize_reconciliation",
    "reconcile_backlog",
    "synchronized_fingerprint",
]


class LogicalCacheRecord(BaseModel):
    """One backend-owned cache record identified without a filesystem path."""

    key: str
    item: BacklogItem


class CacheAction(BaseModel):
    """A logical cache mutation ordered around provider patch execution."""

    key: str
    kind: Literal["upsert", "unlink"] = "upsert"
    phase: Literal["before_provider", "checkpoint"] = "before_provider"
    record: LogicalCacheRecord
    requires_patch: str = ""


class ReconcilePlan(BaseModel):
    """Deterministic cache and provider actions for one snapshot."""

    cache_actions: list[CacheAction] = Field(default_factory=list)
    provider_patches: list[ProviderPatch] = Field(default_factory=list)
    result: ReconcileResult = Field(default_factory=ReconcileResult)
    snapshot_checkpoint: str = ""
    dry_run: bool = False


class ActionResult(BaseModel):
    """Adapter-reported outcome for one cache action."""

    key: str
    phase: Literal["before_provider", "checkpoint"]
    status: Literal["applied", "error"]


class ReconcileExecution(BaseModel):
    """Durable outcomes reported after an adapter executes a plan."""

    cache_results: list[ActionResult] = Field(default_factory=list)
    patch_results: list[PatchResult] = Field(default_factory=list)


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
    }
    payload = json.dumps(
        projection, default=lambda value: value.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def _normalized_body(body: str) -> str:
    return body.replace("\r\n", "\n").replace("\r", "\n")


def _compose(local: BacklogItem, provider: ProviderItem, body_item: BacklogItem) -> BacklogItem:
    metadata = local.metadata.model_copy(
        update={
            "added": body_item.metadata.added,
            "issue": provider.reference,
            "item_type": body_item.metadata.item_type,
            "labels": provider.labels,
            "priority": body_item.metadata.priority,
            "status": provider.state.lower(),
            "updated_at": provider.revision,
        }
    )
    return BacklogItem(
        title=provider.title, description=body_item.description, sections=body_item.sections, metadata=metadata
    )


def _new_local_item(provider: ProviderItem) -> BacklogItem:
    parsed = parse_issue_body(provider.body)
    return _compose(BacklogItem(), provider, parsed)


def _checkpoint(item: BacklogItem, revision: str) -> BacklogItem:
    metadata = item.metadata.model_copy(
        update={"sync_fingerprint": synchronized_fingerprint(item), "updated_at": revision}
    )
    return BacklogItem(title=item.title, description=item.description, sections=item.sections, metadata=metadata)


def _candidate(
    local: BacklogItem, provider: ProviderItem, request: ReconcileRequest
) -> tuple[BacklogItem, ProviderPatch | None]:
    remote_body = parse_issue_body(provider.body, existing=local)
    remote = _compose(local, provider, remote_body)
    baseline = local.metadata.sync_fingerprint
    local_changed = not baseline or synchronized_fingerprint(local) != baseline
    remote_changed = not baseline or synchronized_fingerprint(remote_body) != baseline
    if request.force:
        candidate = remote
    elif local_changed and remote_changed:
        candidate = _compose(local, provider, merge_item(local, remote_body))
    elif remote_changed:
        candidate = remote
    else:
        candidate = _compose(local, provider, local)
    rendered = render_issue_body(candidate, original_body=provider.body)
    if _normalized_body(rendered) == _normalized_body(provider.body):
        return candidate, None
    return candidate, ProviderPatch(
        provider_id=provider.provider_id,
        reference=provider.reference,
        expected_revision=provider.revision,
        body=rendered,
    )


def _action(
    key: str,
    item: BacklogItem,
    *,
    phase: Literal["before_provider", "checkpoint"] = "before_provider",
    requires_patch: str = "",
    kind: Literal["upsert", "unlink"] = "upsert",
) -> CacheAction:
    return CacheAction(
        key=key, kind=kind, phase=phase, record=LogicalCacheRecord(key=key, item=item), requires_patch=requires_patch
    )


def _plan_item(
    record: LogicalCacheRecord | None, provider: ProviderItem, request: ReconcileRequest, plan: ReconcilePlan
) -> None:
    if record is None:
        if provider.exists:
            item = _checkpoint(_new_local_item(provider), provider.revision)
            plan.cache_actions.append(_action(provider.reference, item))
            plan.result.changed_references.append(provider.reference)
        return
    local = record.item
    if not provider.exists:
        metadata = local.metadata.model_copy(update={"issue": "", "sync_fingerprint": "", "updated_at": ""})
        unlinked = BacklogItem(
            title=local.title, description=local.description, sections=local.sections, metadata=metadata
        )
        plan.cache_actions.append(_action(record.key, unlinked, kind="unlink"))
        plan.result.changed_references.append(provider.reference)
        return
    candidate, patch = _candidate(local, provider, request)
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


def finalize_reconciliation(plan: ReconcilePlan, execution: ReconcileExecution) -> ReconcileOutcome:
    """Convert durable adapter outcomes into counts and checkpoint eligibility.

    Returns:
        Completed outcome counts and the global checkpoint decision.
    """
    result = plan.result.model_copy(deep=True)
    patch_results = {patch.reference: patch for patch in execution.patch_results}
    applied_patches: set[str] = set()
    for patch in plan.provider_patches:
        patch_result = patch_results.get(patch.reference)
        if patch_result is None:
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
