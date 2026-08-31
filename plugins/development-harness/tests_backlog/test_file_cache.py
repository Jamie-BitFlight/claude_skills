from __future__ import annotations

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
    _PendingWorkItemMutation,
    _RejectedMutation,
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

    # Then: the malformed entry is dropped, the valid one survives, nothing raises
    assert loaded.pending_work_items == [good_entry]


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

    # Then: the forged entry is dropped, the legitimate one survives
    assert loaded.pending_work_items == [good_entry]


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
