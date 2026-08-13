from __future__ import annotations

from pathlib import Path

import pytest
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

    monkeypatch.setattr("backlog_core.file_cache.os.replace", fail_replace)

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
