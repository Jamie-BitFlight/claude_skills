from __future__ import annotations

from pathlib import Path

import pytest
from backlog_core.file_cache import CacheCheckpoint, FileCache, ReplayAcknowledgement
from backlog_core.models import ContentKind, ContentRecord, ContentRef, ContentUnavailableError, ContentWrite


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


def test_file_cache_distinguishes_stale_hit_from_unavailable_miss(tmp_path: Path) -> None:
    # Given: one cached provider record
    cache = FileCache(tmp_path)
    reference = _reference("#1")
    cache.cache_content(_record(reference, "cached"))

    # When: the provider is offline
    stale = cache.get_content(reference, stale=True)

    # Then: a hit is marked stale while a miss raises the explicit unavailable outcome
    assert stale.stale is True
    with pytest.raises(ContentUnavailableError):
        cache.get_content(_reference("#2"), stale=True)


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
