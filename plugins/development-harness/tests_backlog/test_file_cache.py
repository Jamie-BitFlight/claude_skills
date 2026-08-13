from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from multiprocessing import get_context
from multiprocessing.synchronize import Barrier as ProcessBarrier
from pathlib import Path
from threading import Barrier, Thread

import pytest
from backlog_core import file_cache
from backlog_core.file_cache import CacheCheckpoint, FileCache, ReplayAcknowledgement, _ProviderSnapshotCheckpoint
from backlog_core.models import (
    BacklogItem,
    ContentKind,
    ContentRecord,
    ContentRef,
    ContentUnavailableError,
    ContentWrite,
)


def _reference(namespace: str, artifact_type: str = "research") -> ContentRef:
    return ContentRef(
        kind=ContentKind.ARTIFACT_CONTENT, namespace=namespace, artifact_type=artifact_type, name="report.md"
    )


def _record(reference: ContentRef, content: str, revision: str = "rev-1") -> ContentRecord:
    return ContentRecord(reference=reference, owner_reference=reference.namespace, content=content, revision=revision)


def _queue_write_in_process(root: str, namespace: str, start: ProcessBarrier) -> None:
    cache = FileCache(Path(root))
    reference = _reference(namespace)
    start.wait(timeout=20)
    cache.queue_write(
        _record(reference, f"{namespace} content"),
        ContentWrite(reference=reference, content=f"{namespace} content", expected_revision="rev-1"),
    )


def test_file_cache_round_trips_complete_content_reference_without_collision(tmp_path: Path) -> None:
    # Given: records that differ only by owner namespace or artifact type
    cache = FileCache(tmp_path)
    references = [_reference("#1"), _reference("#2"), _reference("#1", "verification")]

    # When: every record is cached and the cache is reopened
    for index, reference in enumerate(references):
        cache.cache_content(_record(reference, f"content-{index}"))
    reopened = FileCache(tmp_path)

    # Then: the complete references retain three distinct identities
    assert [reopened.get_content(reference).content for reference in references] == [
        "content-0",
        "content-1",
        "content-2",
    ]


def test_file_cache_round_trips_provider_snapshot_checkpoint(tmp_path: Path) -> None:
    # Given: a provider-owned cache with one acknowledged global snapshot
    cache = FileCache(tmp_path)

    # When: the checkpoint is stored and the cache is reopened
    cache._set_snapshot_checkpoint(_ProviderSnapshotCheckpoint(watermark="2026-08-12T01:00:00Z"))
    reopened = FileCache(tmp_path)

    # Then: the exact provider watermark remains durable
    assert reopened._get_snapshot_checkpoint() == _ProviderSnapshotCheckpoint(watermark="2026-08-12T01:00:00Z")


def test_file_cache_coalesces_work_item_intent_and_reopens_it(tmp_path: Path) -> None:
    # Given: two offline edits for one provider-linked work item
    cache = FileCache(tmp_path)
    first = BacklogItem(title="One", description="first")
    first.metadata.issue = "#1"
    second = first.model_copy(deep=True)
    second.description = "second"

    # When: both edits are queued and the cache is reopened
    cache._queue_work_item("#1", first)
    latest = cache._queue_work_item("#1", second)
    pending = FileCache(tmp_path)._pending_work_item_mutations()

    # Then: only the latest durable intent remains for idempotent replay
    assert pending == [latest]


def test_file_cache_acknowledges_work_item_by_idempotency_key(tmp_path: Path) -> None:
    # Given: one durable work-item intent
    cache = FileCache(tmp_path)
    mutation = cache._queue_work_item("#1", BacklogItem(title="One"))

    # When: the exact mutation identity is acknowledged
    cache._acknowledge_work_items({mutation.idempotency_key})

    # Then: the acknowledged entry is removed
    assert cache._pending_work_item_mutations() == []


def test_file_cache_lists_work_item_snapshots_by_stable_key(tmp_path: Path) -> None:
    # Given: snapshots persisted beneath separate private cache directories
    cache = FileCache(tmp_path)
    cache._save_work_item_snapshot("#12", BacklogItem(title="Issue snapshot"))
    cache._save_work_item_snapshot("plans/P12.yaml", BacklogItem(title="Plan snapshot"))

    # When: the provider reloads its durable snapshots
    snapshots = FileCache(tmp_path)._work_item_snapshots()

    # Then: it receives ordered logical keys and typed work items, never paths
    assert [(key, item.title) for key, item in snapshots] == [
        ("issues/12.yaml", "Issue snapshot"),
        ("plans/P12.yaml", "Plan snapshot"),
    ]


def test_file_cache_reopens_opaque_snapshot_key_with_yaml_suffix(tmp_path: Path) -> None:
    # Given: an opaque provider key and an item whose backend reference is meaningful
    cache = FileCache(tmp_path)
    item = BacklogItem(title="Opaque snapshot", reference="ece.37")

    # When: the snapshot is saved and loaded by a fresh cache instance
    cache._save_work_item_snapshot("ece.37", item)
    snapshots = FileCache(tmp_path)._work_item_snapshots()

    # Then: the opaque key is discoverable and the item's reference survives
    assert [(key, snapshot.reference) for key, snapshot in snapshots] == [("ece.37.yaml", "ece.37")]


def test_file_cache_concurrent_snapshot_writes_keep_unique_temps_and_complete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given: two writers forced to finish serialisation before either replaces one destination
    caches = [FileCache(tmp_path), FileCache(tmp_path)]
    save_barrier = Barrier(2)
    original_save_item = file_cache.save_item

    def synchronized_save_item(item: BacklogItem, path: Path) -> None:
        original_save_item(item, path)
        save_barrier.wait(timeout=5)

    monkeypatch.setattr(file_cache, "save_item", synchronized_save_item)

    # When: both cache instances persist the same logical snapshot concurrently
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(cache._save_work_item_snapshot, "issues/12.yaml", BacklogItem(title=title))
            for cache, title in zip(caches, ("first", "second"), strict=True)
        ]
        for future in futures:
            future.result()

    # Then: the destination is one complete valid snapshot, with last-writer-wins semantics
    snapshots = FileCache(tmp_path)._work_item_snapshots()
    assert len(snapshots) == 1
    assert snapshots[0][0] == "issues/12.yaml"
    assert snapshots[0][1].title in {"first", "second"}


def test_file_cache_distinguishes_stale_hit_from_unavailable_miss(tmp_path: Path) -> None:
    # Given: one cached provider record
    cache = FileCache(tmp_path)
    reference = _reference("#1")
    cache.cache_content(_record(reference, "cached"))

    # When: the provider is offline
    stale = cache.get_content(reference, stale=True)

    # Then: a hit is marked stale while a miss raises the explicit unavailable outcome
    assert stale.stale is True
    with pytest.raises(ContentUnavailableError) as exc_info:
        cache.get_content(_reference("#2"), stale=True)
    assert type(exc_info.value) is ContentUnavailableError


def test_queue_write_is_atomic_when_state_replacement_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Given: a durable cached record and a replacement failure
    cache = FileCache(tmp_path)
    reference = _reference("#1")
    cache.cache_content(_record(reference, "before"))

    def fail_replace(source: Path, destination: Path) -> None:
        raise OSError("injected replacement failure")

    monkeypatch.setattr("backlog_core.file_cache_state.os.replace", fail_replace)

    # When: an offline write tries to replace the record and append its queue entry
    with pytest.raises(OSError, match="injected replacement failure"):
        cache.queue_write(
            _record(reference, "after"), ContentWrite(reference=reference, content="after", expected_revision="rev-1")
        )

    # Then: neither half of the transaction becomes durable
    reopened = FileCache(tmp_path)
    assert reopened.get_content(reference).content == "before"
    assert reopened.pending_mutations() == []


def test_duplicate_idempotency_key_is_queued_once(tmp_path: Path) -> None:
    # Given: the same logical write submitted twice
    cache = FileCache(tmp_path)
    reference = _reference("#1")
    write = ContentWrite(reference=reference, content="after", owner_reference="#1", expected_revision="rev-1")
    mismatched_record = _record(reference, "caller-mismatch").model_copy(update={"owner_reference": "caller-mismatch"})

    # When: the provider queues both submissions
    first = cache.queue_write(mismatched_record, write)
    cached_after_first_submission = cache.get_content(reference)
    second = cache.queue_write(_record(reference, "after"), write)

    # Then: its stable key and durable queue entry are deduplicated
    assert first.idempotency_key == second.idempotency_key
    assert cache.pending_mutations() == [first]
    assert (cached_after_first_submission.content, cached_after_first_submission.owner_reference) == (
        write.content,
        write.owner_reference,
    )


def test_partial_replay_checkpoints_applied_entry_and_retains_the_rest(tmp_path: Path) -> None:
    # Given: two durable pending writes
    cache = FileCache(tmp_path)
    first_ref = _reference("#1")
    second_ref = _reference("#2")
    first = cache.queue_write(
        _record(first_ref, "first"), ContentWrite(reference=first_ref, content="first", expected_revision="rev-1")
    )
    second = cache.queue_write(
        _record(second_ref, "second"), ContentWrite(reference=second_ref, content="second", expected_revision="rev-1")
    )

    # When: only the first mutation is acknowledged by the provider
    cache.acknowledge_replay([
        ReplayAcknowledgement(
            idempotency_key=first.idempotency_key,
            record=_record(first_ref, "first", revision="rev-2"),
            fingerprint="fp-2",
        )
    ])

    # Then: the applied checkpoint advances and every unapplied entry remains queued
    assert cache.pending_mutations() == [second]
    assert cache.get_checkpoint(first_ref) == CacheCheckpoint(reference=first_ref, revision="rev-2", fingerprint="fp-2")
    assert cache.get_content(first_ref).pending is False
    assert cache.get_content(second_ref).pending is True


def test_file_cache_serializes_concurrent_instances_and_reopens_valid_state(tmp_path: Path) -> None:
    # Given: two cache instances that begin independent state transactions together
    first = FileCache(tmp_path)
    second = FileCache(tmp_path)
    references = [_reference("#1"), _reference("#2")]
    start = Barrier(3)

    def update(cache: FileCache, reference: ContentRef, title: str) -> None:
        start.wait()
        cache.queue_write(
            _record(reference, f"{title} content"),
            ContentWrite(reference=reference, content=f"{title} content", expected_revision="rev-1"),
        )
        cache._queue_work_item(reference.namespace, BacklogItem(title=title))
        cache.set_checkpoint(CacheCheckpoint(reference=reference, revision="rev-2", fingerprint=f"{title}-fp"))

    threads = [
        Thread(target=update, args=(cache, reference, f"item-{index}"))
        for index, (cache, reference) in enumerate(zip([first, second], references, strict=True), start=1)
    ]

    # When: both instances update records, queues, and checkpoints concurrently
    for thread in threads:
        thread.start()
    start.wait()
    for thread in threads:
        thread.join(timeout=5)

    # Then: reopening parses the atomic state and retains every independent update
    assert not any(thread.is_alive() for thread in threads)
    reopened = FileCache(tmp_path)
    assert sorted(mutation.write.reference.model_dump_json() for mutation in reopened.pending_mutations()) == sorted(
        reference.model_dump_json() for reference in references
    )
    assert {mutation.key for mutation in reopened._pending_work_item_mutations()} == {"#1", "#2"}
    assert [reopened.get_checkpoint(reference) for reference in references] == [
        CacheCheckpoint(reference=references[0], revision="rev-2", fingerprint="item-1-fp"),
        CacheCheckpoint(reference=references[1], revision="rev-2", fingerprint="item-2-fp"),
    ]


def test_file_cache_serializes_process_writers(tmp_path: Path) -> None:
    # Given: two separate Python processes with the same cache root
    context = get_context("spawn")
    start = context.Barrier(3)
    namespaces = ["#1", "#2"]
    processes = [
        context.Process(target=_queue_write_in_process, args=(str(tmp_path), namespace, start))
        for namespace in namespaces
    ]

    # When: both processes cross a barrier before starting their transactions
    for process in processes:
        process.start()
    start.wait(timeout=20)
    for process in processes:
        process.join(timeout=20)

    # Then: the cross-process lock retains both durable writes
    assert [process.exitcode for process in processes] == [0, 0]
    assert (
        sorted(mutation.write.reference.namespace for mutation in FileCache(tmp_path).pending_mutations()) == namespaces
    )
