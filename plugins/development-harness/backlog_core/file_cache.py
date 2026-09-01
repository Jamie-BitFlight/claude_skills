"""Private durable cache for remote-capable backlog providers."""

from __future__ import annotations

import contextlib
import os
import tempfile
import warnings
from collections.abc import Iterable
from io import StringIO
from pathlib import Path

from ruamel.yaml import YAML, YAMLError

from .file_cache_state import (
    CacheCheckpoint,
    PendingMutation,
    ReplayAcknowledgement,
    _CacheState,
    _CacheStateStore,
    _content_mutation_key,
    _CorruptQueueEntry,
    _PendingWorkItemMutation,
    _ProviderSnapshotCheckpoint,
    _RejectedMutation,
    _RejectedWorkItemMutation,
    _work_item_mutation_key,
)
from .models import BacklogItem, ContentRecord, ContentRef, ContentUnavailableError, ContentWrite, parse_issue_number
from .yaml_io import load_item, load_item_text, save_item


class LegacyMigrationError(ValueError):
    """Legacy item cannot be migrated without data loss."""


class FileCache:
    """Provider-private durable records, checkpoints, and offline writes."""

    def __init__(self, root: Path) -> None:
        """Initialize durable cache state beneath the provider-owned root."""
        self._root = root
        self._state = _CacheStateStore(root)

    def get_content(self, reference: ContentRef, *, stale: bool = False) -> ContentRecord:
        """Return cached content, distinguishing an offline miss from stale data.

        ``pending`` is derived live from the durable mutation queue
        (``state.pending``) rather than trusted from the stored record --
        that queue is the sole source of truth for whether a reference has
        unreplayed intent. See :meth:`_is_pending`. ``conflict_reason`` is
        likewise derived live from ``state.rejected`` -- this is the logical
        API surface a caller (possibly a different call than the one whose
        write was rejected) uses to discover a terminal replay conflict,
        since :meth:`reject_pending` only logs a warning at replay time.
        """
        state = self._load_state()
        for record in state.records:
            if record.reference == reference:
                return record.model_copy(
                    update={
                        "stale": stale,
                        "pending": self._is_pending(state, reference),
                        "conflict_reason": self._rejection_reason(state, reference),
                    }
                )
        raise ContentUnavailableError(str(reference.model_dump(mode="json")))

    def cache_content(self, record: ContentRecord, *, acknowledge_pending: bool = False) -> None:
        """Durably replace one provider-observed content record.

        A reference with a mutation still outstanding in the durable queue
        (``state.pending``) must survive routine online reads
        (``list_content``, ``get_content``) until that mutation is
        acknowledged -- otherwise a discovery read can silently clobber an
        unacknowledged write with older provider content. This method
        enforces that invariant directly, checked live against the queue, so
        every caller gets it for free instead of duplicating a guard clause.

        Args:
            record: The provider-observed content record to store. Its own
                ``pending`` field is ignored -- ``state.records`` never
                independently tracks pending status. The durable mutation
                queue (``state.pending``) is the sole source of truth, and
                every reader (:meth:`get_content`) recomputes ``pending``
                live from it. This method always normalises the stored
                record to ``pending=False`` so the on-disk cache never
                carries a second, potentially stale, copy of that fact.
            acknowledge_pending: Pass ``True`` only when this call itself is
                landing the authoritative write for ``record.reference`` (a
                direct foreground write that supersedes whatever was queued).
                Defaults to ``False`` so a routine cache-refresh read never
                overwrites a still-pending reference.
        """

        def replace(state: _CacheState) -> tuple[_CacheState, None]:
            if not acknowledge_pending and self._is_pending(state, record.reference):
                return state, None
            stored = record.model_copy(update={"pending": False})
            return state.model_copy(update={"records": self._replace_record(state.records, stored)}), None

        self._state.transaction(replace)

    def cache_content_many(self, records: Iterable[ContentRecord], *, acknowledge_pending: bool = False) -> int:
        """Durably replace many provider-observed content records in one transaction.

        Applies the same per-record pending-guard invariant as :meth:`cache_content`
        to every record, but performs a single locked read-modify-write for the
        whole batch instead of one transaction per record. A caller looping over
        ``cache_content`` pays a full state load, validate, and durable dump on
        every call -- O(n) work repeated n times. Folding the batch into one
        transaction collapses that to a single O(n) load/dump/fsync, and is
        strictly more durable than the loop it replaces: the batch either lands
        in full or not at all, where a mid-loop process death previously left a
        partially-refreshed cache.

        Args:
            records: Provider-observed content records to store.
            acknowledge_pending: Pass ``True`` only when this batch itself is
                landing the authoritative write for every reference in it.
                Defaults to ``False`` so a routine cache-refresh read never
                overwrites a still-pending reference.

        Returns:
            The count of records actually stored -- excludes records skipped
            because a pending mutation still owns that reference.
        """

        def replace(state: _CacheState) -> tuple[_CacheState, int]:
            current = state.records
            stored = 0
            for record in records:
                if not acknowledge_pending and self._is_pending(state, record.reference):
                    continue
                current = self._replace_record(current, record.model_copy(update={"pending": False}))
                stored += 1
            return state.model_copy(update={"records": current}), stored

        return self._state.transaction(replace)

    def queue_write(self, record: ContentRecord, write: ContentWrite) -> PendingMutation:
        """Atomically cache an offline write and append its deduplicated mutation.

        Returns:
            The stable pending mutation, whether newly appended or already queued.
        """

        def queue(state: _CacheState) -> tuple[_CacheState, PendingMutation]:
            prior = next((entry for entry in state.pending if entry.write.reference == write.reference), None)
            rebased = write.model_copy(
                update={
                    "expected_revision": prior.write.expected_revision if prior is not None else write.expected_revision
                }
            )
            mutation = PendingMutation(idempotency_key=_content_mutation_key(rebased), write=rebased)
            pending: list[PendingMutation] = []
            inserted = False
            for entry in state.pending:
                if entry.write.reference == write.reference:
                    if not inserted:
                        pending.append(mutation)
                        inserted = True
                else:
                    pending.append(entry)
            if not inserted:
                pending.append(mutation)
            owner_reference = record.owner_reference if write.owner_reference is None else write.owner_reference
            # "pending" is never stored True on the record itself -- the queue entry just
            # appended above is the sole durable fact; get_content() derives the flag live.
            cached = record.model_copy(
                update={
                    "reference": write.reference,
                    "owner_reference": owner_reference,
                    "content": write.content,
                    "pending": False,
                    "stale": False,
                }
            )
            # A prior rejection for this reference is moot the moment new intent is
            # queued for it -- mirrors discard_pending treating a rejected entry as
            # stale once superseded, and stops it from outliving a later successful write.
            rejected = [item for item in state.rejected if item.write.reference != write.reference]
            return (
                state.model_copy(
                    update={
                        "records": self._replace_record(state.records, cached),
                        "pending": pending,
                        "rejected": rejected,
                    }
                ),
                mutation,
            )

        return self._state.transaction(queue)

    def pending_mutations(self) -> list[PendingMutation]:
        """Return pending mutations in durable insertion order."""
        return list(self._load_state().pending)

    def rejected_mutations(self) -> list[_RejectedMutation]:
        """Return rejected mutations in durable insertion order."""
        return list(self._load_state().rejected)

    def discard_pending(self, reference: ContentRef) -> None:
        """Drop any queued or rejected mutation for a reference without touching cached content.

        Called after a direct online write for a reference lands successfully --
        that write already ran ahead of :meth:`pending_mutations` for the same
        reference (``put_content`` always calls ``replay_pending`` first), so a
        mutation still queued for it afterward is stale, superseded intent that
        must never be replayed against the fresher record it would land on top of.
        A rejected entry for the same reference is equally stale -- the newer
        write supersedes whatever precondition previously failed. No companion
        update to ``state.records`` is needed here: a stored record never
        independently tracks pending status, so removing the queue entry alone
        is sufficient -- the next :meth:`get_content` call derives
        ``pending=False`` from this queue's absence of an entry.
        """

        def discard(state: _CacheState) -> tuple[_CacheState, None]:
            remaining = [entry for entry in state.pending if entry.write.reference != reference]
            remaining_rejected = [entry for entry in state.rejected if entry.write.reference != reference]
            return state.model_copy(update={"pending": remaining, "rejected": remaining_rejected}), None

        self._state.transaction(discard)

    def reject_pending(self, reference: ContentRef, idempotency_key: str, reason: str) -> None:
        """Move the queued mutation matching ``idempotency_key`` out of ``pending`` into ``rejected``.

        Called when a replay attempt fails with a precondition error that
        retrying can never satisfy, so the mutation must stop occupying the
        unbounded-retry pending queue while still being retained for inspection.

        Matches by ``idempotency_key`` rather than ``reference`` alone: a newer
        ``queue_write`` call can replace the pending entry for a reference between
        when a replay attempt started and when it failed, and rejecting by
        reference alone would wrongly discard that newer, never-attempted
        mutation. A no-op when no pending entry matches the key -- the mutation
        that failed has already been superseded or otherwise handled.
        """

        def reject(state: _CacheState) -> tuple[_CacheState, None]:
            entry = next((item for item in state.pending if item.idempotency_key == idempotency_key), None)
            if entry is None:
                return state, None
            remaining = [item for item in state.pending if item.idempotency_key != idempotency_key]
            rejected = [
                *(item for item in state.rejected if item.write.reference != reference),
                _RejectedMutation(idempotency_key=entry.idempotency_key, write=entry.write, reason=reason),
            ]
            return state.model_copy(update={"pending": remaining, "rejected": rejected}), None

        self._state.transaction(reject)

    def _queue_work_item(self, key: str, item: BacklogItem) -> _PendingWorkItemMutation:
        mutation = _PendingWorkItemMutation(idempotency_key=_work_item_mutation_key(key, item), key=key, item=item)
        return self._state.transaction(
            lambda state: (
                state.model_copy(
                    update={
                        "pending_work_items": [
                            *(entry for entry in state.pending_work_items if entry.key != key),
                            mutation,
                        ]
                    }
                ),
                mutation,
            )
        )

    def _pending_work_item_mutations(self) -> list[_PendingWorkItemMutation]:
        return list(self._load_state().pending_work_items)

    def _rejected_work_item_mutations(self) -> list[_RejectedWorkItemMutation]:
        """Return work-item mutations dead-lettered for a key/content mismatch.

        See :meth:`_CacheStateStore._verify_queue_keys` -- a mismatch here is
        not proof of a hand-edit; a legitimate entry from a newer plugin
        version can trip it too, so these are preserved for inspection rather
        than replayed or discarded.
        """
        return list(self._load_state().rejected_work_items)

    def _corrupt_queue_entries(self) -> list[_CorruptQueueEntry]:
        """Return pending/pending_work_items entries that failed schema validation on load.

        See :meth:`_CacheStateStore._salvage_field` (``preserve=True``) --
        stored as raw payloads for manual recovery, since they never became
        typed models.
        """
        return list(self._load_state().corrupt_queue_entries)

    def _acknowledge_work_items(self, idempotency_keys: set[str]) -> None:
        if not idempotency_keys:
            return
        self._state.transaction(
            lambda state: (
                state.model_copy(
                    update={
                        "pending_work_items": [
                            entry for entry in state.pending_work_items if entry.idempotency_key not in idempotency_keys
                        ]
                    }
                ),
                None,
            )
        )

    def get_checkpoint(self, reference: ContentRef) -> CacheCheckpoint | None:
        """Return the last acknowledged checkpoint for a logical record."""
        for checkpoint in self._load_state().checkpoints:
            if checkpoint.reference == reference:
                return checkpoint
        return None

    def set_checkpoint(self, checkpoint: CacheCheckpoint) -> None:
        """Durably replace one provider checkpoint."""
        self._state.transaction(
            lambda state: (
                state.model_copy(
                    update={
                        "checkpoints": [
                            *(entry for entry in state.checkpoints if entry.reference != checkpoint.reference),
                            checkpoint,
                        ]
                    }
                ),
                None,
            )
        )

    def _get_snapshot_checkpoint(self) -> _ProviderSnapshotCheckpoint | None:
        return self._load_state().snapshot_checkpoint

    def _set_snapshot_checkpoint(self, checkpoint: _ProviderSnapshotCheckpoint) -> None:
        self._state.transaction(lambda state: (state.model_copy(update={"snapshot_checkpoint": checkpoint}), None))

    def acknowledge_replay(self, acknowledgements: list[ReplayAcknowledgement]) -> None:
        """Checkpoint only applied mutations while retaining all other queued work."""

        def acknowledge(state: _CacheState) -> tuple[_CacheState, None]:
            applied = {entry.idempotency_key: entry for entry in acknowledgements}
            acknowledged_keys = [entry.idempotency_key for entry in state.pending if entry.idempotency_key in applied]
            remaining = [entry for entry in state.pending if entry.idempotency_key not in acknowledged_keys]
            records = list(state.records)
            checkpoints = list(state.checkpoints)
            for key in acknowledged_keys:
                acknowledgement = applied[key]
                checkpoints = [entry for entry in checkpoints if entry.reference != acknowledgement.record.reference]
                checkpoints.append(
                    CacheCheckpoint(
                        reference=acknowledgement.record.reference,
                        revision=acknowledgement.record.revision,
                        fingerprint=acknowledgement.fingerprint,
                    )
                )
                # Only replace the cached record when no newer write was queued for this
                # reference after this acknowledgement was computed (a race guarded by
                # re-reading fresh state at the top of this transaction). "pending" is
                # forced False on every record stored in state.records -- it is never
                # independently trusted; get_content() derives it live from state.pending.
                if not any(entry.write.reference == acknowledgement.record.reference for entry in remaining):
                    record = acknowledgement.record.model_copy(update={"pending": False, "stale": False})
                    records = self._replace_record(records, record)
            return state.model_copy(update={"records": records, "checkpoints": checkpoints, "pending": remaining}), None

        self._state.transaction(acknowledge)

    def verify_legacy_item(self, source: Path) -> tuple[BacklogItem, list[str]]:
        """Parse a legacy item and verify its YAML representation without persisting it.

        Args:
            source: Legacy Markdown item to verify.

        Returns:
            The parsed item and its mismatched field names.

        Raises:
            ValueError: If the legacy YAML data cannot be parsed.
        """
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                item = load_item(source)
            reloaded = load_item_text(self._serialize_item(item), source.with_suffix(".yaml"))
        except YAMLError as exc:
            raise ValueError(str(exc)) from exc
        before = item.model_dump(exclude={"file_path", "skip"})
        after = reloaded.model_dump(exclude={"file_path", "skip"})
        return item, [key for key in before if before.get(key) != after.get(key)]

    def migrate_legacy_item(self, source: Path) -> Path:
        """Persist one verified legacy item as a YAML snapshot beside its source.

        Args:
            source: Legacy Markdown item to migrate.

        Returns:
            The written YAML path.

        Raises:
            ValueError: If the conversion cannot round-trip without data loss.
        """
        item, mismatches = self.verify_legacy_item(source)
        if mismatches:
            raise LegacyMigrationError(f"Mismatched fields: {mismatches}")
        destination = source.with_suffix(".yaml")
        try:
            save_item(item, destination)
            reloaded = load_item(destination)
        except YAMLError as exc:
            raise ValueError(str(exc)) from exc
        before = item.model_dump(exclude={"file_path", "skip"})
        after = reloaded.model_dump(exclude={"file_path", "skip"})
        if before != after:
            destination.unlink(missing_ok=True)
            mismatches = [key for key in before if before.get(key) != after.get(key)]
            raise LegacyMigrationError(
                f"Round-trip verification failed — .yaml removed. Mismatched fields: {mismatches}"
            )
        return destination

    def _load_item_snapshot(self, relative_path: Path) -> BacklogItem:
        return load_item(self._snapshot_path(relative_path))

    def _save_work_item_snapshot(self, key: str, item: BacklogItem) -> None:
        number = parse_issue_number(key)
        relative_path = Path("issues") / f"{number}.yaml" if number is not None else Path(key)
        if number is None and relative_path.suffix not in {".yaml", ".yml"}:
            relative_path = Path(f"{relative_path}.yaml")
        self._save_item_snapshot(item, relative_path)

    def _work_item_snapshots(self) -> list[tuple[str, BacklogItem]]:
        item_root = self._root / "items"
        if not item_root.exists():
            return []
        return [
            (relative.as_posix(), self._load_item_snapshot(relative))
            for relative in (path.relative_to(item_root) for path in sorted(item_root.rglob("*.yaml")))
        ]

    @staticmethod
    def _serialize_item(item: BacklogItem) -> str:
        output = StringIO()
        yaml = YAML(typ="rt")
        yaml.default_flow_style = False
        yaml.width = 2147483647
        yaml.dump(item.model_dump(exclude={"file_path", "skip"}), output)
        return output.getvalue()

    def _save_item_snapshot(self, item: BacklogItem, relative_path: Path) -> None:
        destination = self._snapshot_path(relative_path)
        destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        temporary: Path | None = None
        try:
            fd, temporary_name = tempfile.mkstemp(
                dir=destination.parent, prefix=f".{destination.name}.", suffix=".tmp.yaml"
            )
            temporary = Path(temporary_name)
            os.close(fd)
            save_item(item.model_copy(deep=True), temporary)
            Path(temporary).replace(destination)
        finally:
            if temporary is not None:
                with contextlib.suppress(FileNotFoundError):
                    temporary.unlink()

    def _snapshot_path(self, relative_path: Path) -> Path:
        destination = (self._root / "items" / relative_path).resolve()
        destination.relative_to((self._root / "items").resolve())
        return destination

    def _load_state(self) -> _CacheState:
        # load_after_migration(), not migrate-then-load as two calls: a
        # legacy-recreated cache.yaml (an older plugin copy queuing new
        # offline writes into a fresh file of its own) otherwise stays
        # invisible to every read accessor -- pending_mutations(),
        # get_content(), reconciliation's load_records() -- until some
        # unrelated transaction() happens to run and trigger migration as a
        # side effect. One lock acquisition also closes the race where a
        # second recreation lands in the gap between two separate calls.
        return self._state.load_after_migration()

    @staticmethod
    def _replace_record(records: list[ContentRecord], replacement: ContentRecord) -> list[ContentRecord]:
        return [*[record for record in records if record.reference != replacement.reference], replacement]

    @staticmethod
    def _is_pending(state: _CacheState, reference: ContentRef) -> bool:
        """Return whether the durable mutation queue still targets ``reference``.

        The queue (``state.pending``) is the single source of truth for
        whether a reference is pending. No stored ``ContentRecord.pending``
        flag is ever independently trusted; every record written into
        ``state.records`` is normalised to ``pending=False`` on write
        (:meth:`cache_content`, :meth:`queue_write`, :meth:`acknowledge_replay`)
        and this method recomputes the true value on every read. A reference
        moved to ``state.rejected`` by :meth:`reject_pending` is deliberately
        *not* pending here -- once a mutation's precondition can never be
        satisfied, a fresh online/legacy read is trusted again instead of
        being shadowed by the stale queued content forever.
        """
        return any(entry.write.reference == reference for entry in state.pending)

    @staticmethod
    def _rejection_reason(state: _CacheState, reference: ContentRef) -> str:
        """Return the reason a reference's mutation was terminally rejected, or "".

        Mirrors :meth:`_is_pending`: ``state.rejected`` is the sole source of
        truth, recomputed on every read rather than trusted from the stored
        record, so a reference cleared of its rejection (:meth:`queue_write`)
        stops surfacing a stale reason immediately.
        """
        entry = next((item for item in state.rejected if item.write.reference == reference), None)
        return entry.reason if entry is not None else ""
