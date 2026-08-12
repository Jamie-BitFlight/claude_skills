"""Provider-neutral snapshot reconciliation for persisted backlog items."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable

from .backend_types import SyncProvider
from .github_sync import merge_item, parse_issue_body, render_issue_body
from .models import (
    BacklogItem,
    PatchResult,
    ProviderItem,
    ProviderPatch,
    ReconcileRequest,
    ReconcileResult,
    ReconcileScope,
    get_backlog_dir,
)
from .parsing import parse_backlog, title_to_slug
from .yaml_io import save_item

__all__ = ["reconcile_backlog", "synchronized_fingerprint"]


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
    payload = json.dumps(projection, default=lambda value: value.model_dump(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def _normalized_body(body: str) -> str:
    return body.replace("\r\n", "\n").replace("\r", "\n")


def _with_provider_fields(local: BacklogItem, provider: ProviderItem, body_item: BacklogItem) -> BacklogItem:
    metadata = local.metadata.model_copy(
        update={
            "issue": provider.reference,
            "labels": provider.labels,
            "status": provider.state.lower(),
            "updated_at": provider.revision,
        }
    )
    data = body_item.model_dump()
    data.update({"title": provider.title, "metadata": metadata, "file_path": local.file_path, "section": local.section})
    return BacklogItem.model_validate(data)


def _persist(item: BacklogItem, result: ReconcileResult) -> None:
    save_item(item)
    result.local_updates += 1
    result.changed_references.append(item.metadata.issue)
    result.file_paths[item.metadata.issue] = item.file_path


def _selected(items: Iterable[BacklogItem], request: ReconcileRequest) -> list[BacklogItem]:
    if request.scope not in {ReconcileScope.LINKED, ReconcileScope.TARGETED}:
        return list(items)
    references = set(request.references)
    return [item for item in items if item.metadata.issue in references]


def _new_local_item(provider: ProviderItem) -> BacklogItem:
    parsed = parse_issue_body(provider.body)
    local = BacklogItem(title=provider.title, description=parsed.description, sections=parsed.sections)
    return _with_provider_fields(local, provider, parsed)


def _write_new_item(item: BacklogItem, result: ReconcileResult) -> None:
    item.file_path = str(get_backlog_dir() / f"p1-{title_to_slug(item.title)}.yaml")
    item.metadata.sync_fingerprint = synchronized_fingerprint(item)
    _persist(item, result)


def _checkpoint(item: BacklogItem, revision: str) -> BacklogItem:
    metadata = item.metadata.model_copy(
        update={"sync_fingerprint": synchronized_fingerprint(item), "updated_at": revision}
    )
    data = item.model_dump()
    data.update({"metadata": metadata, "file_path": item.file_path, "section": item.section})
    return BacklogItem.model_validate(data)


def _apply_patches(provider: SyncProvider, patches: list[ProviderPatch]) -> dict[str, PatchResult]:
    return {result.reference: result for result in provider.apply_patches(patches)}


def _candidate_patch(
    local: BacklogItem, provider: ProviderItem, request: ReconcileRequest
) -> tuple[BacklogItem, ProviderPatch | None]:
    remote = _with_provider_fields(local, provider, parse_issue_body(provider.body, existing=local))
    baseline = local.metadata.sync_fingerprint
    local_changed = not baseline or synchronized_fingerprint(local) != baseline
    remote_changed = not baseline or synchronized_fingerprint(remote) != baseline
    candidate = remote if request.force else local
    if not request.force and local_changed and remote_changed:
        candidate = _with_provider_fields(local, provider, merge_item(local, remote))
    elif not request.force and remote_changed and not local_changed:
        candidate = remote
    elif not request.force and local_changed and not remote_changed:
        candidate = _with_provider_fields(local, provider, local)
    rendered = render_issue_body(candidate, original_body=provider.body)
    if _normalized_body(rendered) == _normalized_body(provider.body):
        return candidate, None
    return candidate, ProviderPatch(
        provider_id=provider.provider_id,
        reference=provider.reference,
        expected_revision=provider.revision,
        body=rendered,
    )


def _reconcile_observed_item(
    local: BacklogItem | None, provider: ProviderItem, request: ReconcileRequest, result: ReconcileResult
) -> tuple[BacklogItem, ProviderPatch] | None:
    if local is None:
        if provider.exists and not request.dry_run:
            _write_new_item(_new_local_item(provider), result)
        return None
    if not provider.exists:
        if not request.dry_run:
            local.metadata.issue = ""
            local.metadata.sync_fingerprint = ""
            local.metadata.updated_at = ""
            _persist(local, result)
        result.deleted_provider_items += 1
        return None
    candidate, patch = _candidate_patch(local, provider, request)
    if patch is not None:
        return candidate, patch
    result.no_ops += 1
    if not request.dry_run:
        _persist(_checkpoint(candidate, provider.revision), result)
    return None


def reconcile_backlog(provider: SyncProvider, request: ReconcileRequest) -> ReconcileResult:
    """Reconcile local backlog items with one normalized provider snapshot.

    Returns:
        Completed reconciliation outcomes.
    """
    result = ReconcileResult()
    try:
        snapshot = provider.fetch_snapshot(request)
    except (OSError, RuntimeError, ValueError):
        result.failures += 1
        return result

    result.fetched_pages = snapshot.pages_fetched
    result.fetched_items = len(snapshot.items)
    local_items = _selected(parse_backlog(), request)
    local_by_reference = {item.metadata.issue: item for item in local_items if item.metadata.issue}
    pending: list[tuple[BacklogItem, ProviderPatch]] = []

    for provider_item in snapshot.items:
        pending_item = _reconcile_observed_item(
            local_by_reference.pop(provider_item.reference, None), provider_item, request, result
        )
        if pending_item is not None:
            pending.append(pending_item)

    if request.dry_run or not pending:
        return result

    patch_results = _apply_patches(provider, [patch for _, patch in pending])
    for candidate, patch in pending:
        patch_result = patch_results.get(patch.reference)
        if patch_result is None:
            result.failures += 1
            continue
        result.patch_results.append(patch_result)
        match patch_result.status:
            case "applied":
                result.provider_patches += 1
                _persist(_checkpoint(candidate, patch_result.revision), result)
            case "conflict":
                result.conflicts += 1
            case "error":
                result.failures += 1
    return result
