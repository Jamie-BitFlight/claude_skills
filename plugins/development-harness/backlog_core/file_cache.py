"""Private durable cache for remote-capable backlog providers."""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import tempfile
import warnings
from io import StringIO
from pathlib import Path

from ruamel.yaml import YAML, YAMLError

from .file_cache_state import (
    CacheCheckpoint,
    PendingMutation,
    ReplayAcknowledgement,
    _CacheState,
    _CacheStateStore,
    _PendingWorkItemMutation,
    _ProviderSnapshotCheckpoint,
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
        """Return cached content, distinguishing an offline miss from stale data."""
        state = self._load_state()
        for record in state.records:
            if record.reference == reference:
                return record.model_copy(update={"stale": stale})
        raise ContentUnavailableError(str(reference.model_dump(mode="json")))

    def cache_content(self, record: ContentRecord, *, acknowledge_pending: bool = False) -> None:
        """Durably replace one provider-observed content record.

        A cached record already marked ``pending`` represents a queued mutation
        whose content and ``pending`` flag must survive routine online reads
        (``list_content``, ``get_content``) until that mutation is acknowledged
        -- otherwise a discovery read can silently clobber an unacknowledged
        write with older provider content. This method enforces that invariant
        directly so every caller gets it for free instead of duplicating a
        guard clause.

        Args:
            record: The provider-observed content record to store.
            acknowledge_pending: Pass ``True`` only when this call itself is
                landing the authoritative write for ``record.reference`` (a
                direct foreground write that supersedes whatever was queued).
                Defaults to ``False`` so a routine cache-refresh read never
                overwrites a still-pending reference.
        """

        def replace(state: _CacheState) -> tuple[_CacheState, None]:
            existing = next((entry for entry in state.records if entry.reference == record.reference), None)
            if existing is not None and existing.pending and not acknowledge_pending:
                return state, None
            return state.model_copy(update={"records": self._replace_record(state.records, record)}), None

        self._state.transaction(replace)

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
            payload = json.dumps(rebased.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
            mutation = PendingMutation(idempotency_key=hashlib.sha256(payload.encode()).hexdigest(), write=rebased)
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
            cached = record.model_copy(
                update={
                    "reference": write.reference,
                    "owner_reference": owner_reference,
                    "content": write.content,
                    "pending": True,
                    "stale": False,
                }
            )
            return (
                state.model_copy(update={"records": self._replace_record(state.records, cached), "pending": pending}),
                mutation,
            )

        return self._state.transaction(queue)

    def pending_mutations(self) -> list[PendingMutation]:
        """Return pending mutations in durable insertion order."""
        return list(self._load_state().pending)

    def discard_pending(self, reference: ContentRef) -> bool:
        """Drop any queued mutation for a reference without touching cached content.

        Called after a direct online write for a reference lands successfully --
        that write already ran ahead of :meth:`pending_mutations` for the same
        reference (``put_content`` always calls ``replay_pending`` first), so a
        mutation still queued for it afterward is stale, superseded intent that
        must never be replayed against the fresher record it would land on top of.

        Returns:
            ``True`` if a queued mutation for ``reference`` was found and
            removed, ``False`` if nothing was queued for it.
        """

        def discard(state: _CacheState) -> tuple[_CacheState, bool]:
            remaining = [entry for entry in state.pending if entry.write.reference != reference]
            return state.model_copy(update={"pending": remaining}), len(remaining) != len(state.pending)

        return self._state.transaction(discard)

    def _queue_work_item(self, key: str, item: BacklogItem) -> _PendingWorkItemMutation:
        payload = json.dumps(item.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        mutation = _PendingWorkItemMutation(
            idempotency_key=hashlib.sha256(f"{key}:{payload}".encode()).hexdigest(), key=key, item=item
        )
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

    def _acknowledge_work_items(self, idempotency_keys: set[str]) -> None:
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
        return self._state.load()

    @staticmethod
    def _replace_record(records: list[ContentRecord], replacement: ContentRecord) -> list[ContentRecord]:
        return [*[record for record in records if record.reference != replacement.reference], replacement]
