"""Private durable cache for remote-capable backlog providers."""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Final

from pydantic import BaseModel, ConfigDict, Field
from ruamel.yaml import YAML

from .models import BacklogItem, ContentRecord, ContentRef, ContentUnavailableError, ContentWrite
from .yaml_io import load_item, save_item

_STATE_FILE: Final = "cache.yaml"


class PendingMutation(BaseModel):
    """Durable provider mutation awaiting acknowledgement."""

    model_config = ConfigDict(frozen=True)

    idempotency_key: str
    write: ContentWrite


class CacheCheckpoint(BaseModel):
    """Last provider revision and fingerprint acknowledged for content."""

    model_config = ConfigDict(frozen=True)

    reference: ContentRef
    revision: str
    fingerprint: str


class ReplayAcknowledgement(BaseModel):
    """Applied provider mutation and its resulting checkpoint."""

    model_config = ConfigDict(frozen=True)

    idempotency_key: str
    record: ContentRecord
    fingerprint: str


class _CacheState(BaseModel):
    model_config = ConfigDict(frozen=True)

    records: list[ContentRecord] = Field(default_factory=list)
    checkpoints: list[CacheCheckpoint] = Field(default_factory=list)
    pending: list[PendingMutation] = Field(default_factory=list)


class FileCache:
    """Provider-private durable records, checkpoints, and offline writes."""

    def __init__(self, root: Path) -> None:
        """Initialize durable cache state beneath the provider-owned root."""
        self._root = root
        self._state_path = root / _STATE_FILE

    def get_content(self, reference: ContentRef, *, stale: bool = False) -> ContentRecord:
        """Return cached content, distinguishing an offline miss from stale data."""
        state = self._load_state()
        for record in state.records:
            if record.reference == reference:
                return record.model_copy(update={"stale": stale})
        raise ContentUnavailableError(str(reference.model_dump(mode="json")))

    def cache_content(self, record: ContentRecord) -> None:
        """Durably replace one provider-observed content record."""
        state = self._load_state()
        self._save_state(state.model_copy(update={"records": self._replace_record(state.records, record)}))

    def queue_write(self, record: ContentRecord, write: ContentWrite) -> PendingMutation:
        """Atomically cache an offline write and append its deduplicated mutation.

        Returns:
            The stable pending mutation, whether newly appended or already queued.
        """
        payload = json.dumps(write.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        mutation = PendingMutation(idempotency_key=hashlib.sha256(payload.encode()).hexdigest(), write=write)
        state = self._load_state()
        pending = (
            state.pending
            if mutation.idempotency_key in {entry.idempotency_key for entry in state.pending}
            else [*state.pending, mutation]
        )
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
        self._save_state(
            state.model_copy(update={"records": self._replace_record(state.records, cached), "pending": pending})
        )
        return mutation

    def pending_mutations(self) -> list[PendingMutation]:
        """Return pending mutations in durable insertion order."""
        return list(self._load_state().pending)

    def get_checkpoint(self, reference: ContentRef) -> CacheCheckpoint | None:
        """Return the last acknowledged checkpoint for a logical record."""
        for checkpoint in self._load_state().checkpoints:
            if checkpoint.reference == reference:
                return checkpoint
        return None

    def set_checkpoint(self, checkpoint: CacheCheckpoint) -> None:
        """Durably replace one provider checkpoint."""
        state = self._load_state()
        checkpoints = [entry for entry in state.checkpoints if entry.reference != checkpoint.reference]
        self._save_state(state.model_copy(update={"checkpoints": [*checkpoints, checkpoint]}))

    def acknowledge_replay(self, acknowledgements: list[ReplayAcknowledgement]) -> None:
        """Checkpoint only applied mutations while retaining all other queued work."""
        state = self._load_state()
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
        self._save_state(
            state.model_copy(update={"records": records, "checkpoints": checkpoints, "pending": remaining})
        )

    def _load_item_snapshot(self, relative_path: Path) -> BacklogItem:
        return load_item(self._snapshot_path(relative_path))

    def _save_item_snapshot(self, item: BacklogItem, relative_path: Path) -> None:
        destination = self._snapshot_path(relative_path)
        destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        temporary = destination.with_name(f".{destination.name}.tmp.yaml")
        try:
            save_item(item.model_copy(deep=True), temporary)
            Path(temporary).replace(destination)
        finally:
            with contextlib.suppress(FileNotFoundError):
                temporary.unlink()

    def _snapshot_path(self, relative_path: Path) -> Path:
        destination = (self._root / "items" / relative_path).resolve()
        destination.relative_to((self._root / "items").resolve())
        return destination

    def _load_state(self) -> _CacheState:
        if not self._state_path.exists():
            return _CacheState()
        yaml = YAML(typ="safe")
        with self._state_path.open(encoding="utf-8") as stream:
            return _CacheState.model_validate(yaml.load(stream))

    def _save_state(self, state: _CacheState) -> None:
        self._root.mkdir(mode=0o700, parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self._root, suffix=".tmp", delete=False
            ) as stream:
                temporary_path = Path(stream.name)
                yaml = YAML(typ="safe")
                yaml.default_flow_style = False
                yaml.dump(state.model_dump(mode="json"), stream)
                stream.flush()
                os.fsync(stream.fileno())
            Path(temporary_path).replace(self._state_path)
            temporary_path = None
        finally:
            if temporary_path is not None:
                with contextlib.suppress(FileNotFoundError):
                    temporary_path.unlink()

    @staticmethod
    def _replace_record(records: list[ContentRecord], replacement: ContentRecord) -> list[ContentRecord]:
        return [*[record for record in records if record.reference != replacement.reference], replacement]
