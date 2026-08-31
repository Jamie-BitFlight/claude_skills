from __future__ import annotations

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from multiprocessing import get_context
from multiprocessing.synchronize import Barrier as ProcessBarrier
from pathlib import Path
from threading import Barrier, Thread
from unittest.mock import MagicMock

import pytest
from backlog_core import file_cache
from backlog_core.file_cache import CacheCheckpoint, FileCache, ReplayAcknowledgement, _ProviderSnapshotCheckpoint
from backlog_core.file_cache_state import (
    PendingMutation,
    _CacheState,
    _CacheStateStore,
    _content_mutation_key,
    _CorruptQueueEntry,
    _PendingWorkItemMutation,
    _RejectedMutation,
    _RejectedWorkItemMutation,
    _work_item_mutation_key,
)
from backlog_core.models import (
    BacklogItem,
    CacheStateCorruptError,
    ContentKind,
    ContentRecord,
    ContentRef,
    ContentUnavailableError,
    ContentWrite,
)
from ruamel.yaml import YAML


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


def test_acknowledge_work_items_skips_transaction_for_empty_key_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given: a durable work-item intent and a caller that acknowledges nothing
    cache = FileCache(tmp_path)
    cache._queue_work_item("#1", BacklogItem(title="One"))
    spy = MagicMock(wraps=cache._state.transaction)
    monkeypatch.setattr(cache._state, "transaction", spy)

    # When: acknowledgement is called with an empty key set (every reconcile without acks)
    cache._acknowledge_work_items(set())

    # Then: no lock/load/write cycle runs for a no-op acknowledgement
    spy.assert_not_called()


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


def test_reject_pending_is_a_noop_when_the_targeted_mutation_was_superseded(tmp_path: Path) -> None:
    """A stale idempotency key must not let reject_pending discard a superseding mutation.

    Regression test for a review finding on PR #3306: reject_pending() looked up the
    entry to move into `rejected` by `reference` alone. `queue_write()` deduplicates by
    reference -- a newer queue_write() call for the same reference replaces the older
    pending entry outright, so at most one pending entry per reference can ever exist.
    If a replay attempt for the superseded (older) mutation later fails, rejecting by
    reference alone would silently reject the newer, never-attempted mutation instead
    of the one that actually failed. reject_pending must match by idempotency_key, so
    it is inert once its target has already been superseded.
    """
    cache = FileCache(tmp_path)
    reference = _reference("#1")
    record = _record(reference, "before")
    first = cache.queue_write(record, ContentWrite(reference=reference, content="first", expected_revision="rev-1"))
    second = cache.queue_write(record, ContentWrite(reference=reference, content="second", expected_revision="rev-1"))
    assert cache.pending_mutations() == [second]

    cache.reject_pending(reference, first.idempotency_key, "stale replay failure")

    assert cache.pending_mutations() == [second]
    assert cache.rejected_mutations() == []


def test_reject_pending_moves_the_matching_mutation_by_idempotency_key(tmp_path: Path) -> None:
    """reject_pending still moves the correct mutation into `rejected` when it is current."""
    cache = FileCache(tmp_path)
    reference = _reference("#1")
    record = _record(reference, "before")
    mutation = cache.queue_write(record, ContentWrite(reference=reference, content="only", expected_revision="rev-1"))

    cache.reject_pending(reference, mutation.idempotency_key, "precondition failed")

    assert cache.pending_mutations() == []
    rejected = cache.rejected_mutations()
    assert len(rejected) == 1
    assert rejected[0].idempotency_key == mutation.idempotency_key
    assert rejected[0].reason == "precondition failed"


def test_rejected_entry_is_cleared_once_a_superseding_write_is_acknowledged(tmp_path: Path) -> None:
    """A rejected entry must not survive past a later successful write for the same reference.

    Regression test for a review finding on PR #3306: discard_pending() clears both
    `state.pending` and `state.rejected` for a reference, but acknowledge_replay() only
    ever cleared `state.pending`. A reference whose earlier write was rejected (a genuine
    terminal conflict), then edited and replayed again successfully, left the stale
    rejected entry sitting in `rejected_mutations()` forever even though fresher content
    had since landed for that reference. The rejected entry is seeded directly through
    the durable state store here so this test exercises acknowledge_replay's own clearing
    behavior independent of reject_pending's call signature.
    """
    cache = FileCache(tmp_path)
    reference = _reference("#1")
    record = _record(reference, "before")
    cache.cache_content(record)
    stale_rejected_write = ContentWrite(reference=reference, content="rejected", expected_revision="rev-1")
    store = _CacheStateStore(tmp_path)
    store.transaction(
        lambda state: (
            state.model_copy(
                update={
                    "rejected": [
                        _RejectedMutation(
                            idempotency_key="stale-key", write=stale_rejected_write, reason="precondition failed"
                        )
                    ]
                }
            ),
            None,
        )
    )
    assert len(cache.rejected_mutations()) == 1

    retried = cache.queue_write(record, ContentWrite(reference=reference, content="retried", expected_revision="rev-1"))
    cache.acknowledge_replay([
        ReplayAcknowledgement(
            idempotency_key=retried.idempotency_key,
            record=_record(reference, "retried", revision="rev-2"),
            fingerprint="fp-2",
        )
    ])

    assert cache.rejected_mutations() == []


def test_get_content_surfaces_the_rejection_reason_for_a_rejected_reference(tmp_path: Path) -> None:
    """A caller reading content through get_content() must see why its write was dropped.

    Regression test for a review finding on PR #3306: `rejected_mutations()` is a
    private FileCache method absent from the logical ContentProvider interface, so a
    caller whose offline write was later rejected during replay had no way to learn
    about it through get_content() -- only a logger warning fired at replay time, which
    the original caller (a different call, possibly a different process) never sees.
    conflict_reason must be derived live from state.rejected, mirroring how `pending`
    is already derived live from state.pending.
    """
    cache = FileCache(tmp_path)
    reference = _reference("#1")
    record = _record(reference, "before")
    cache.cache_content(record)

    unrejected = cache.get_content(reference)
    assert unrejected.conflict_reason == ""

    mutation = cache.queue_write(record, ContentWrite(reference=reference, content="doomed", expected_revision="rev-1"))
    cache.reject_pending(reference, mutation.idempotency_key, "revision no longer matches")

    rejected_view = cache.get_content(reference)
    assert rejected_view.conflict_reason == "revision no longer matches"

    # A fresh write for the same reference supersedes the rejection (Fix 2 above);
    # get_content() must stop surfacing the stale reason once that happens.
    cache.queue_write(record, ContentWrite(reference=reference, content="retry", expected_revision="rev-1"))
    assert cache.get_content(reference).conflict_reason == ""


def _populated_cache_state() -> _CacheState:
    # A realistic mix of the nested models actually persisted to cache.json.
    # pending/pending_work_items keys are derived through the real formula
    # (not hardcoded) so they pass the idempotency-key self-consistency check
    # on load -- a hardcoded fake key would be dead-lettered as a hand-edit.
    artifact_ref = _reference("#1")
    plan_ref = ContentRef(kind=ContentKind.PLAN, name="P12.yaml")
    pending_write = ContentWrite(reference=artifact_ref, content="updated", expected_revision="rev-1")
    work_item = BacklogItem(title="Offline edit")
    return _CacheState(
        records=[
            _record(artifact_ref, "artifact body"),
            ContentRecord(reference=plan_ref, owner_reference="", content="plan body", revision="rev-2", stale=True),
        ],
        checkpoints=[CacheCheckpoint(reference=artifact_ref, revision="rev-1", fingerprint="fp-1")],
        pending=[PendingMutation(idempotency_key=_content_mutation_key(pending_write), write=pending_write)],
        pending_work_items=[
            _PendingWorkItemMutation(idempotency_key=_work_item_mutation_key("#1", work_item), key="#1", item=work_item)
        ],
        snapshot_checkpoint=_ProviderSnapshotCheckpoint(watermark="2026-08-12T01:00:00Z"),
    )


def _write_legacy_yaml(path: Path, state: _CacheState) -> None:
    yaml = YAML(typ="safe")
    yaml.default_flow_style = False
    with path.open("w", encoding="utf-8") as stream:
        yaml.dump(state.model_dump(mode="json"), stream)


def _write_new_json(path: Path, state: _CacheState) -> None:
    path.write_text(state.model_dump_json(), encoding="utf-8")


def test_load_reads_legacy_yaml_cache_file_with_full_fidelity(tmp_path: Path) -> None:
    # Given: a cache.yaml written the way every process wrote it before the
    # cache.json rename -- the legacy path, not the (now cache.json) accessor
    state = _populated_cache_state()
    store = _CacheStateStore(tmp_path)
    _write_legacy_yaml(store._legacy_state_path, state)

    # When: the store loads it (read-only -- no migration, no write)
    loaded = store.load()

    # Then: every record, checkpoint, pending mutation, and snapshot survives intact
    assert loaded == state
    assert not store._state_path.exists()


def test_load_reads_new_json_cache_file_with_full_fidelity(tmp_path: Path) -> None:
    # Given: a cache.json written by the store's own save path
    state = _populated_cache_state()
    store = _CacheStateStore(tmp_path)
    _write_new_json(store._state_path, state)

    # When: the store loads it
    loaded = store.load()

    # Then: every record, checkpoint, pending mutation, and snapshot survives intact
    assert loaded == state


def test_load_performs_no_writes(tmp_path: Path) -> None:
    # Given: a legacy-only root -- regression guard for the deadlock fix: load()
    # must never migrate or write, only transaction() may (see file_cache_state.py
    # _migrate_legacy_state_file's docstring for why doing it in load() deadlocks)
    state = _populated_cache_state()
    store = _CacheStateStore(tmp_path)
    _write_legacy_yaml(store._legacy_state_path, state)
    before = sorted(p.name for p in tmp_path.iterdir())

    # When: the store loads it
    store.load()

    # Then: the directory is untouched -- no cache.json, no cache.lock
    assert sorted(p.name for p in tmp_path.iterdir()) == before


def test_transaction_migrates_legacy_yaml_to_json(tmp_path: Path) -> None:
    # Given: a genuine legacy YAML cache.yaml (not JSON wearing the extension)
    state = _populated_cache_state()
    store = _CacheStateStore(tmp_path)
    _write_legacy_yaml(store._legacy_state_path, state)

    # When: a transaction runs (the only path that migrates)
    result = store.transaction(lambda s: (s, None))

    # Then: cache.json exists with identical content, cache.yaml is gone (superseded,
    # not deleted), and the transaction's own read saw the migrated state
    assert result is None
    assert store._state_path.exists()
    assert not store._legacy_state_path.exists()
    assert store._legacy_state_path.with_name("cache.yaml.superseded").exists()
    assert store.load() == state


def test_transaction_renames_already_json_legacy_file_without_rewriting(tmp_path: Path) -> None:
    # Given: a cache.yaml that's already JSON (written by code after the format
    # fix but before the rename) -- the json.loads-succeeds discriminator path
    state = _populated_cache_state()
    store = _CacheStateStore(tmp_path)
    _write_new_json(store._legacy_state_path, state)
    original_bytes = store._legacy_state_path.read_bytes()

    # When: a transaction runs
    store.transaction(lambda s: (s, None))

    # Then: renamed byte-for-byte, no ".superseded" leftover (nothing to supersede
    # -- the rename consumed the only copy), no rewrite occurred
    assert store._state_path.read_bytes() == original_bytes
    assert not store._legacy_state_path.exists()
    assert not store._legacy_state_path.with_name("cache.yaml.superseded").exists()


def test_transaction_prefers_json_when_both_legacy_and_new_files_exist(tmp_path: Path) -> None:
    # Given: both cache.json and a stale cache.yaml present (e.g. post-downgrade-
    # then-upgrade)
    current_state = _populated_cache_state()
    store = _CacheStateStore(tmp_path)
    _write_new_json(store._state_path, current_state)
    stale_state = _CacheState()
    _write_legacy_yaml(store._legacy_state_path, stale_state)

    # When: a transaction runs
    store.transaction(lambda s: (s, None))

    # Then: cache.json (the real current state) wins; the stale cache.yaml is
    # superseded, not destroyed
    assert store.load() == current_state
    assert not store._legacy_state_path.exists()
    assert store._legacy_state_path.with_name("cache.yaml.superseded").exists()


def test_transaction_merges_queue_entries_from_a_legacy_file_recreated_by_older_code(tmp_path: Path) -> None:
    # Given: cache.json already exists (a newer version migrated once), but an
    # older plugin copy unaware of the rename later ran and wrote its own new
    # offline mutation into a fresh cache.yaml -- the concurrent-mixed-version
    # scenario named in _migrate_legacy_state_file's ponytail note
    store = _CacheStateStore(tmp_path)
    current_state = _populated_cache_state()
    _write_new_json(store._state_path, current_state)

    older_ref = _reference("#9")
    older_write = ContentWrite(reference=older_ref, content="queued by older code", expected_revision="rev-1")
    older_pending = PendingMutation(idempotency_key=_content_mutation_key(older_write), write=older_write)
    older_item = BacklogItem(title="Queued by older code")
    older_work_item = _PendingWorkItemMutation(
        idempotency_key=_work_item_mutation_key("#9", older_item), key="#9", item=older_item
    )
    legacy_state = _CacheState(pending=[older_pending], pending_work_items=[older_work_item])
    _write_legacy_yaml(store._legacy_state_path, legacy_state)

    # When: a transaction runs
    store.transaction(lambda s: (s, None))

    # Then: the older code's queued writes survive, merged into cache.json's
    # existing queue -- not silently discarded when cache.yaml is superseded
    loaded = store.load()
    assert older_pending in loaded.pending
    assert older_work_item in loaded.pending_work_items
    assert all(entry in loaded.pending for entry in current_state.pending)
    assert not store._legacy_state_path.exists()
    assert store._legacy_state_path.with_name("cache.yaml.superseded").exists()


def test_transaction_merges_dead_lettered_entries_from_a_recreated_legacy_file(tmp_path: Path) -> None:
    # Given: cache.json exists, and a legacy cache.yaml recreated by older
    # code holds not just a new pending write but also entries that the
    # legacy file's own load-time checks (_verify_queue_keys/_salvage) would
    # dead-letter -- a key mismatch, a schema failure. Superseding the file
    # unread would silently strand these in an inert renamed backup that a
    # second occurrence of this scenario could later overwrite.
    store = _CacheStateStore(tmp_path)
    current_state = _populated_cache_state()
    _write_new_json(store._state_path, current_state)

    write = ContentWrite(reference=_reference("#9"), content="rejected on the legacy side", expected_revision="rev-1")
    legacy_rejected = _RejectedMutation(idempotency_key="stale-key-1", write=write, reason="revision no longer matches")
    legacy_item = BacklogItem(title="Rejected on the legacy side")
    legacy_rejected_work_item = _RejectedWorkItemMutation(
        idempotency_key="stale-key-2", key="#9", item=legacy_item, reason="idempotency_key does not match its content"
    )
    legacy_corrupt = _CorruptQueueEntry(field="pending", raw={"idempotency_key": "x"}, reason="missing 'write'")
    legacy_state = _CacheState(
        rejected=[legacy_rejected],
        rejected_work_items=[legacy_rejected_work_item],
        corrupt_queue_entries=[legacy_corrupt],
    )
    _write_legacy_yaml(store._legacy_state_path, legacy_state)

    # When: a transaction runs
    store.transaction(lambda s: (s, None))

    # Then: all three dead-letter collections survive, merged into cache.json
    loaded = store.load()
    assert legacy_rejected in loaded.rejected
    assert legacy_rejected_work_item in loaded.rejected_work_items
    assert legacy_corrupt in loaded.corrupt_queue_entries
    assert all(entry in loaded.rejected for entry in current_state.rejected)


def test_pending_mutations_sees_a_legacy_file_recreated_by_older_code_without_a_prior_write(tmp_path: Path) -> None:
    # Given: cache.json exists, and a legacy cache.yaml recreated by older
    # code holds a new offline write -- but no write of our own has happened
    # yet to trigger transaction()'s migration as a side effect
    cache_store = _CacheStateStore(tmp_path)
    current_state = _populated_cache_state()
    _write_new_json(cache_store._state_path, current_state)
    older_write = ContentWrite(reference=_reference("#9"), content="queued by older code", expected_revision="rev-1")
    older_pending = PendingMutation(idempotency_key=_content_mutation_key(older_write), write=older_write)
    _write_legacy_yaml(cache_store._legacy_state_path, _CacheState(pending=[older_pending]))

    # When: a plain read accessor is called first -- the shape of what
    # replay_pending()/reconcile() do before ever writing anything
    cache = FileCache(tmp_path)
    pending = cache.pending_mutations()

    # Then: the legacy entry is visible immediately, not only after some
    # unrelated write happens to trigger transaction()'s migration
    assert older_pending in pending
    assert not cache_store._legacy_state_path.exists()


def test_load_after_migration_migrates_and_reads_under_one_lock_acquisition(tmp_path: Path) -> None:
    # Given: a legacy-only root -- direct test of the combined method
    # FileCache._load_state() now uses instead of two separate calls
    # (ensure_migrated() then load()), which left a race window between them
    state = _populated_cache_state()
    store = _CacheStateStore(tmp_path)
    _write_legacy_yaml(store._legacy_state_path, state)

    # When: load_after_migration runs
    loaded = store.load_after_migration()

    # Then: migration happened and the returned state already reflects it --
    # a single call, not migrate-then-a-separate-read
    assert loaded == state
    assert store._state_path.exists()
    assert not store._legacy_state_path.exists()


def test_unparsable_legacy_file_gets_a_unique_backup_not_the_shared_superseded_name(tmp_path: Path) -> None:
    # Given: cache.json exists, and cache.yaml is neither valid JSON nor YAML
    # -- can't be read to merge its queued writes, unlike the other
    # both-files-present tests above
    store = _CacheStateStore(tmp_path)
    current_state = _populated_cache_state()
    _write_new_json(store._state_path, current_state)
    store._legacy_state_path.write_text("{[", encoding="utf-8")

    # When: a transaction runs
    store.transaction(lambda s: (s, None))

    # Then: preserved under a unique name, not the fixed .superseded target
    assert not store._legacy_state_path.exists()
    assert not store._legacy_state_path.with_name("cache.yaml.superseded").exists()
    backups = list(tmp_path.glob("cache.yaml.corrupt.*"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "{["


def test_a_second_unparsable_legacy_file_does_not_overwrite_the_first_backup(tmp_path: Path) -> None:
    # Given: one unparsable legacy file already migrated (backed up) once
    store = _CacheStateStore(tmp_path)
    current_state = _populated_cache_state()
    _write_new_json(store._state_path, current_state)
    store._legacy_state_path.write_text("{[ first corrupt file", encoding="utf-8")
    store.transaction(lambda s: (s, None))
    first_backups = list(tmp_path.glob("cache.yaml.corrupt.*"))
    assert len(first_backups) == 1

    # When: an older process recreates cache.yaml, itself unparsable, and a
    # second transaction migrates it
    store._legacy_state_path.write_text("{[ second corrupt file", encoding="utf-8")
    store.transaction(lambda s: (s, None))

    # Then: both backups survive -- the second didn't overwrite the first
    backups = {path: path.read_text(encoding="utf-8") for path in tmp_path.glob("cache.yaml.corrupt.*")}
    assert len(backups) == 2
    assert "{[ first corrupt file" in backups.values()
    assert "{[ second corrupt file" in backups.values()


def test_migration_leaves_lock_and_snapshot_items_untouched(tmp_path: Path) -> None:
    # Given: a legacy cache.yaml alongside the lock file and a per-item snapshot
    state = _populated_cache_state()
    store = _CacheStateStore(tmp_path)
    _write_legacy_yaml(store._legacy_state_path, state)
    (tmp_path / "cache.lock").touch()
    items_dir = tmp_path / "items"
    items_dir.mkdir()
    (items_dir / "issues" / "12.yaml").parent.mkdir(parents=True)
    (items_dir / "issues" / "12.yaml").write_text("title: kept\n", encoding="utf-8")

    # When: a transaction runs
    store.transaction(lambda s: (s, None))

    # Then: the lock file is never renamed (it's what gives old and new plugin
    # copies mutual exclusion) and per-item snapshots are untouched
    assert (tmp_path / "cache.lock").exists()
    assert (items_dir / "issues" / "12.yaml").read_text(encoding="utf-8") == "title: kept\n"


def test_migration_is_serialized_across_threads(tmp_path: Path) -> None:
    # Given: a legacy cache.yaml and several threads racing to be the one that migrates it
    state = _populated_cache_state()
    store = _CacheStateStore(tmp_path)
    _write_legacy_yaml(store._legacy_state_path, state)
    start = Barrier(5)

    def run() -> None:
        start.wait()
        store.transaction(lambda s: (s, None))

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(run) for _ in range(4)]
        start.wait()
        for future in futures:
            future.result()

    # Then: exactly one migration happened -- no data lost, no leftover legacy file
    assert store.load() == state
    assert not store._legacy_state_path.exists()
    assert store._legacy_state_path.with_name("cache.yaml.superseded").exists()


def test_save_writes_content_parseable_as_plain_json(tmp_path: Path) -> None:
    # Given: a populated state persisted through the store's own save path
    state = _populated_cache_state()
    store = _CacheStateStore(tmp_path)
    store._save(state)

    # Then: the state file is actually named cache.json now (the direct
    # regression guard for the rename -- nothing else in this suite asserts
    # the filename), and its raw bytes parse as plain JSON, not YAML
    assert store._state_path.name == "cache.json"
    raw_text = store._state_path.read_text(encoding="utf-8")
    json.loads(raw_text)


def test_empty_state_round_trips_through_save_and_load(tmp_path: Path) -> None:
    # Given: the default empty cache state
    state = _CacheState()
    store = _CacheStateStore(tmp_path)

    # When: it is saved and reloaded
    store._save(state)
    loaded = store.load()

    # Then: it comes back identical
    assert loaded == state


def test_load_returns_empty_state_when_file_is_missing(tmp_path: Path) -> None:
    # Given: a cache root with neither cache.json nor cache.yaml written yet
    store = _CacheStateStore(tmp_path)

    # When: the store loads it
    loaded = store.load()

    # Then: it is an empty state, not an error
    assert loaded == _CacheState()


def test_load_raises_typed_error_for_file_that_is_neither_json_nor_yaml(tmp_path: Path) -> None:
    # Given: a cache.json that parses as neither JSON nor YAML
    store = _CacheStateStore(tmp_path)
    store._state_path.write_text("{[", encoding="utf-8")

    # When/Then: loading raises the typed error, not a raw ruamel.yaml.YAMLError
    with pytest.raises(CacheStateCorruptError):
        store.load()


def test_load_raises_typed_error_for_file_that_parses_to_a_non_mapping(tmp_path: Path) -> None:
    # Given: a cache.json that's valid YAML (a plain scalar) but not a mapping
    store = _CacheStateStore(tmp_path)
    store._state_path.write_text("just a garbage string, not a mapping", encoding="utf-8")

    # When/Then: loading raises rather than silently discarding the on-disk state
    with pytest.raises(CacheStateCorruptError):
        store.load()


def test_load_salvages_valid_entries_when_one_pending_work_item_is_malformed(tmp_path: Path) -> None:
    # Given: a state dict with one schema-valid pending_work_items entry and one
    # that's missing a required field
    state = _populated_cache_state()
    good_entry = state.pending_work_items[0]
    raw = json.loads(state.model_dump_json())
    raw["pending_work_items"].append({"idempotency_key": "whatever", "key": "#2"})  # missing "item"
    store = _CacheStateStore(tmp_path)
    store._state_path.write_text(json.dumps(raw), encoding="utf-8")

    # When: the store loads it
    loaded = store.load()

    # Then: the malformed entry is removed from pending_work_items (it never
    # became a valid model), the valid one survives, nothing raises -- and the
    # malformed entry's raw payload is preserved in corrupt_queue_entries
    # rather than silently lost (see the version-skew test below for why:
    # "missing a required field" is exactly what schema evolution looks like)
    assert loaded.pending_work_items == [good_entry]
    assert len(loaded.corrupt_queue_entries) == 1
    preserved = loaded.corrupt_queue_entries[0]
    assert preserved.field == "pending_work_items"
    assert preserved.raw == {"idempotency_key": "whatever", "key": "#2"}


def test_load_preserves_raw_payload_when_a_newer_version_adds_a_required_field(tmp_path: Path) -> None:
    # Given: a pending entry written by a newer plugin version whose schema
    # gained a required field this version's PendingMutation doesn't have --
    # the strongest real justification for per-entry salvage in the first
    # place. Missing-required-field is indistinguishable at validation time
    # from any other malformed entry, so this exercises the same code path
    # as a hand-edit -- the point is that it's preserved either way.
    store = _CacheStateStore(tmp_path)
    raw = json.loads(_CacheState().model_dump_json())
    raw["pending"] = [
        {
            "idempotency_key": "whatever-the-newer-version-computed",
            "write": {"reference": {"kind": "plan", "namespace": "", "artifact_type": "", "name": "P1.yaml"}},
            "a_required_field_from_a_future_version": "unknown to this reader",
        }
    ]
    store._state_path.write_text(json.dumps(raw), encoding="utf-8")

    # When: this (older) version loads it
    loaded = store.load()

    # Then: not silently lost -- the raw entry survives for manual recovery
    assert loaded.pending == []
    assert len(loaded.corrupt_queue_entries) == 1
    assert loaded.corrupt_queue_entries[0].field == "pending"
    assert loaded.corrupt_queue_entries[0].raw == raw["pending"][0]


def test_load_dead_letters_pending_entry_with_mismatched_idempotency_key(tmp_path: Path) -> None:
    # Given: a state dict with one legitimate pending_work_items entry and one
    # that's schema-valid but whose idempotency_key doesn't match its own
    # content -- the shape of the hand-edit incident this check exists for
    state = _populated_cache_state()
    good_entry = state.pending_work_items[0]
    forged_item = BacklogItem(title="Hand-edited entry")
    raw = json.loads(state.model_dump_json())
    raw["pending_work_items"].append({
        "idempotency_key": "not-the-real-hash",
        "key": "#2",
        "item": json.loads(forged_item.model_dump_json()),
    })
    store = _CacheStateStore(tmp_path)
    store._state_path.write_text(json.dumps(raw), encoding="utf-8")

    # When: the store loads it
    loaded = store.load()

    # Then: the forged entry is dead-lettered (not deleted, not replayed), the
    # legitimate one survives untouched
    assert loaded.pending_work_items == [good_entry]
    assert len(loaded.rejected_work_items) == 1
    dead_lettered = loaded.rejected_work_items[0]
    assert dead_lettered.idempotency_key == "not-the-real-hash"
    assert dead_lettered.key == "#2"
    assert dead_lettered.reason == "idempotency_key does not match its content"


def test_load_dead_letters_pending_entry_from_version_skew_not_just_hand_edits(tmp_path: Path) -> None:
    # Given: a pending entry whose key was computed by a NEWER plugin version
    # that included a field this version's ContentWrite model doesn't know
    # about -- pydantic's default extra="ignore" silently drops that field on
    # load, so re-deriving the key from the (now-lossy) parsed model produces
    # a different hash than the writer's, even though the entry is legitimate
    reference = _reference("#1")
    write = ContentWrite(reference=reference, content="from a newer version", expected_revision="rev-1")
    raw_write = json.loads(write.model_dump_json())
    raw_write["field_added_by_a_future_version"] = "unknown to this reader"
    payload = json.dumps(raw_write, sort_keys=True, separators=(",", ":"))
    key_from_newer_version = hashlib.sha256(payload.encode()).hexdigest()
    raw_state = json.loads(_CacheState().model_dump_json())
    raw_state["pending"] = [{"idempotency_key": key_from_newer_version, "write": raw_write}]
    store = _CacheStateStore(tmp_path)
    store._state_path.write_text(json.dumps(raw_state), encoding="utf-8")

    # When: this (older) version loads it
    loaded = store.load()

    # Then: not silently lost -- dead-lettered for inspection, not deleted
    assert loaded.pending == []
    assert len(loaded.rejected) == 1
    assert loaded.rejected[0].idempotency_key == key_from_newer_version
    assert loaded.rejected[0].write.content == "from a newer version"


def test_load_preserves_a_stored_rejected_entry_that_fails_schema_validation(tmp_path: Path) -> None:
    # Given: a stored rejected entry (already the terminal recovery record for
    # a prior key mismatch) that itself fails schema validation on this load
    # -- e.g. its nested ContentWrite gained a required field on a later
    # version. Routed through _salvage_list before this fix, it would have
    # been silently dropped -- losing the only remaining copy of what it held.
    good_state = _populated_cache_state()
    raw = json.loads(good_state.model_dump_json())
    raw["rejected"] = [{"idempotency_key": "whatever", "write": {"reference": {}}}]  # missing "reason", malformed ref
    store = _CacheStateStore(tmp_path)
    store._state_path.write_text(json.dumps(raw), encoding="utf-8")

    # When: the store loads it
    loaded = store.load()

    # Then: not silently lost -- preserved as a corrupt_queue_entries record
    assert loaded.rejected == []
    corrupt = [entry for entry in loaded.corrupt_queue_entries if entry.field == "rejected"]
    assert len(corrupt) == 1
    assert corrupt[0].raw == raw["rejected"][0]


def test_load_preserves_a_malformed_non_list_queue_field_as_a_single_corrupt_entry(tmp_path: Path) -> None:
    # Given: pending_work_items itself is not a list at all (e.g. corrupted to
    # a bare string) -- a coarser failure than one bad entry within the list
    store = _CacheStateStore(tmp_path)
    raw = json.loads(_CacheState().model_dump_json())
    raw["pending_work_items"] = "not-a-list-at-all"
    store._state_path.write_text(json.dumps(raw), encoding="utf-8")

    # When: the store loads it
    loaded = store.load()

    # Then: the whole raw value is preserved, not silently discarded
    assert loaded.pending_work_items == []
    corrupt = [entry for entry in loaded.corrupt_queue_entries if entry.field == "pending_work_items"]
    assert len(corrupt) == 1
    assert corrupt[0].raw == "not-a-list-at-all"


def test_load_does_not_key_check_rejected_entries(tmp_path: Path) -> None:
    # Given: a rejected entry with a stale key from before its mutation was
    # queue_write-superseded -- rejected entries are inert inspection records,
    # never replayed, so they're exempt from the self-consistency check
    reference = _reference("#1")
    write = ContentWrite(reference=reference, content="rejected", expected_revision="rev-1")
    state = _CacheState(
        rejected=[_RejectedMutation(idempotency_key="stale-key", write=write, reason="revision no longer matches")]
    )
    store = _CacheStateStore(tmp_path)
    store._save(state)

    # When: the store loads it
    loaded = store.load()

    # Then: the rejected entry survives despite the mismatched key
    assert loaded == state


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
