from __future__ import annotations

from pathlib import Path

import backlog_core.models as _models
import pytest
from backlog_core.backend_protocol import set_config
from backlog_core.backend_types import BacklogConfig
from backlog_core.backends.github_backend import GitHubBackend
from backlog_core.backends.memory_backend import InMemoryBackend
from backlog_core.file_cache import FileCache
from backlog_core.models import (
    BackendUnavailableError,
    BacklogItem,
    BacklogItemMetadata,
    PatchResult,
    ProviderPatch,
    ProviderSnapshot,
    ReconcileRequest,
    ReconcileResult,
    ReconcileScope,
    Section,
)
from backlog_core.operations import (
    _handle_batch_groomed,
    _handle_update_groomed,
    list_items,
    pull_by_selector,
    pull_items,
    refresh_local_cache_from_github,
    sync_items,
)


class _SyncProviderStub(InMemoryBackend):
    requests: list[ReconcileRequest]
    result: ReconcileResult

    def __init__(self) -> None:
        super().__init__()
        self.requests = []
        self.result = ReconcileResult()

    def reconcile(self, request: ReconcileRequest) -> ReconcileResult:
        self.requests.append(request)
        return self.result

    def fetch_snapshot(self, request: ReconcileRequest) -> ProviderSnapshot:
        raise AssertionError(f"unexpected snapshot request: {request!r}")

    def apply_patches(self, patches: list[ProviderPatch]) -> list[PatchResult]:
        raise AssertionError(f"unexpected patches: {patches!r}")


@pytest.fixture
def sync_provider(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> _SyncProviderStub:
    backlog_dir = tmp_path / "backlog"
    backlog_dir.mkdir()
    monkeypatch.setattr(
        _models, "_config", _models.BacklogConfig(repo_root=tmp_path, backlog_dir=backlog_dir, default_repo="")
    )
    provider = _SyncProviderStub()
    set_config(BacklogConfig(backend=provider))
    return provider


@pytest.mark.parametrize(("fetched_items", "expected_progress"), [(3, [(3, 3)]), (0, [(0, 0)])])
def test_refresh_wrapper_maps_label_and_progress(
    sync_provider, monkeypatch: pytest.MonkeyPatch, fetched_items: int, expected_progress: list[tuple[int, int | None]]
) -> None:
    sync_provider.result = ReconcileResult(fetched_items=fetched_items, local_updates=2, deleted_provider_items=1)
    progress: list[tuple[int, int | None]] = []

    result = refresh_local_cache_from_github(
        label="review", progress_callback=lambda done, total: progress.append((done, total))
    )

    assert sync_provider.requests == [ReconcileRequest(scope=ReconcileScope.INCREMENTAL, label="review")]
    assert progress == expected_progress
    assert result["refreshed"] == 2
    assert result["reconciled"] == 1


@pytest.mark.parametrize(
    ("full_refresh", "scope"), [(False, ReconcileScope.INCREMENTAL), (True, ReconcileScope.INITIAL)]
)
def test_label_refresh_does_not_forward_unfiltered_cached_references(sync_provider, full_refresh, scope) -> None:
    # Given: a cached issue that may not carry the requested label
    sync_provider.put_work_item(_linked_item("#11"))

    # When: a label-scoped refresh is requested
    refresh_local_cache_from_github(label="review", full_refresh=full_refresh)

    # Then: the provider receives the label query without targeted fallbacks
    assert sync_provider.requests == [ReconcileRequest(scope=scope, label="review")]


def test_unscoped_refresh_forwards_cached_references(sync_provider) -> None:
    # Given: a cached issue available for an unscoped refresh
    sync_provider.put_work_item(_linked_item("#11"))

    # When: an unscoped refresh is requested
    refresh_local_cache_from_github()

    # Then: existing targeted fallback behavior remains intact
    assert sync_provider.requests == [ReconcileRequest(scope=ReconcileScope.INCREMENTAL, references=["#11"])]


def test_list_wrapper_forwards_label_to_reconciliation(sync_provider) -> None:
    # Given: a GitHub-backed list restricted to one label
    list_items(from_github=True, label="review")

    # Then: its refresh uses the same typed snapshot filter
    assert sync_provider.requests == [ReconcileRequest(scope=ReconcileScope.INCREMENTAL, label="review")]


def _linked_item(reference: str = "#7") -> BacklogItem:
    return BacklogItem(
        title="Wrapper item",
        section="P2",
        file_path="/tmp/wrapper-item.yaml",
        metadata=BacklogItemMetadata(issue=reference),
    )


def test_sync_wrapper_reconciles_linked_items(sync_provider, monkeypatch: pytest.MonkeyPatch) -> None:
    # Given: a linked item after missing-issue creation
    item = _linked_item()
    monkeypatch.setattr(sync_provider, "list_work_items", lambda: [item])
    monkeypatch.setattr("backlog_core.operations.sync_create_missing_issues", lambda *args, **kwargs: {"created": 3})
    sync_provider.result = ReconcileResult(provider_patches=2)

    # When: explicit sync runs
    result = sync_items(dry_run=True)

    # Then: its stable output maps provider patches and forwards dry-run scope
    request = sync_provider.requests[0]
    assert request.scope == ReconcileScope.LINKED
    assert request.references == ["#7"]
    assert request.dry_run is True
    assert result["created"] == 3
    assert result["pushed"] == 2
    assert result["dry_run"] is True


def test_bulk_pull_wrapper_maps_linked_reconciliation(sync_provider, monkeypatch: pytest.MonkeyPatch) -> None:
    # Given: one linked local item and a completed reconciliation
    monkeypatch.setattr(sync_provider, "list_work_items", lambda: [_linked_item()])
    sync_provider.result = ReconcileResult(local_updates=1, failures=1, diffs={"#7": "body diff"})

    # When: the bulk pull requests forceful diff reconciliation
    result = pull_items(dry_run=True, force=True, diff=True)

    # Then: existing response keys preserve the reconciled values
    request = sync_provider.requests[0]
    assert request.scope == ReconcileScope.LINKED
    assert request.references == ["#7"]
    assert request.dry_run is True
    assert request.force is True
    assert request.include_diff is True
    assert result["pulled"] == 1
    assert result["skipped"] == 1
    assert result["total"] == 1
    assert result["diff"] == "body diff"


def test_selector_pull_wrapper_reconciles_one_target(sync_provider, monkeypatch: pytest.MonkeyPatch) -> None:
    # Given: a target reconciliation result with an updated local path
    sync_provider.result = ReconcileResult(file_paths={"#7": "/tmp/wrapper-item.yaml"}, diffs={"#7": "target diff"})

    # When: a direct issue selector is pulled
    result = pull_by_selector("#7", diff=True)

    # Then: exactly the selected reference is reconciled and returned
    request = sync_provider.requests[0]
    assert request.scope == ReconcileScope.TARGETED
    assert request.references == ["#7"]
    assert request.include_diff is True
    assert result["file_path"] == "/tmp/wrapper-item.yaml"
    assert result["diff"] == "target diff"


def test_grooming_persists_before_targeted_reconciliation(sync_provider) -> None:
    # Given: a linked item owned by a remote-capable provider
    item = _linked_item()
    sync_provider.put_work_item(item)
    events: list[str] = []
    original_put = sync_provider.put_work_item

    def record_put(updated: BacklogItem) -> None:
        events.append("put")
        original_put(updated)

    def record_reconcile(request: ReconcileRequest) -> ReconcileResult:
        events.append("reconcile")
        sync_provider.requests.append(request)
        return ReconcileResult()

    sync_provider.put_work_item = record_put
    sync_provider.reconcile = record_reconcile

    # When: one grooming section is changed
    _handle_update_groomed(item, "First step", "Plan", repo="unused")

    # Then: the provider-owned record is durable before one targeted reconcile
    assert events == ["put", "reconcile"]
    assert sync_provider.requests[-1] == ReconcileRequest(scope=ReconcileScope.TARGETED, references=["#7"])


def test_batch_grooming_reconciles_once(sync_provider) -> None:
    # Given: a linked item and two grooming mutations in one batch
    item = _linked_item()
    sync_provider.put_work_item(item)

    # When: both sections are persisted
    written = _handle_batch_groomed(item, {"Plan": "First", "Research": "Second"}, repo="unused")

    # Then: one targeted reconciliation covers the complete backend-owned mutation
    assert written == ["Plan", "Research"]
    assert sync_provider.requests == [ReconcileRequest(scope=ReconcileScope.TARGETED, references=["#7"])]


def test_local_grooming_uses_native_storage_without_sync(monkeypatch: pytest.MonkeyPatch) -> None:
    # Given: a cache-free local provider whose network delegate must not be called
    provider = InMemoryBackend()
    item = _linked_item("#9")
    provider.put_work_item(item)
    set_config(BacklogConfig(backend=provider))
    monkeypatch.setattr("backlog_core.operations.try_get_github", lambda *args, **kwargs: pytest.fail("network used"))

    # When: grooming mutates the item
    _handle_update_groomed(item, "Native only", "Plan", repo="unused")

    # Then: the native record contains the change without a sync capability or cache
    stored_section = next(iter(provider.get_work_item("#9").sections.values()))
    assert isinstance(stored_section, Section)
    assert stored_section.entries[-1].content == "Native only"
    assert not hasattr(provider, "_cache")


def test_operations_exposes_no_direct_grooming_sync_helpers() -> None:
    import backlog_core.operations as operations

    assert not hasattr(operations, "_write_groomed_to_github")
    assert not hasattr(operations, "sync_push_groomed_content")
    assert not hasattr(operations, "_build_groomed_update_list")
    assert not hasattr(operations, "_dispatch_issue_body_updates")


def test_offline_github_grooming_queues_one_pending_mutation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Given: one cached linked item whose GitHub provider is offline
    cache = FileCache(tmp_path / "github-cache")
    item = _linked_item("#12")
    item.reference = "#12"
    cache._save_item_snapshot(item, Path("issues/12.yaml"))
    backend = GitHubBackend(cache=cache)
    set_config(BacklogConfig(backend=backend))
    monkeypatch.setattr(backend, "get_github", lambda *args, **kwargs: (_ for _ in ()).throw(BackendUnavailableError()))

    # When: grooming writes through the configured backend
    _handle_update_groomed(item, "Durable offline", "Plan", repo="unused")

    # Then: one complete work-item mutation remains queued for reconciliation
    pending = cache._pending_work_item_mutations()
    assert len(pending) == 1
    stored_section = next(iter(pending[0].item.sections.values()))
    assert isinstance(stored_section, Section)
    assert stored_section.entries[-1].content == "Durable offline"
