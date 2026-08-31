"""Atomic state storage for the provider-private file cache."""

from __future__ import annotations

import contextlib
import hashlib
import json
import logging
import os
import tempfile
from collections.abc import Callable, Iterator
from pathlib import Path
from threading import Lock
from typing import Final, TypeVar, cast

import pydantic
from pydantic import BaseModel, ConfigDict, Field
from ruamel.yaml import YAML, YAMLError

from .models import BacklogItem, CacheStateCorruptError, ContentRecord, ContentRef, ContentWrite

if os.name == "nt":
    import msvcrt
else:
    import fcntl

_STATE_FILE: Final = "cache.json"
_LEGACY_STATE_FILE: Final = "cache.yaml"
_LOCK_FILE: Final = "cache.lock"
_T = TypeVar("_T")
_THREAD_LOCKS: Final[dict[Path, Lock]] = {}
_THREAD_LOCKS_GUARD: Final = Lock()
_log = logging.getLogger(__name__)


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


class _ProviderSnapshotCheckpoint(BaseModel):
    model_config = ConfigDict(frozen=True)

    watermark: str = Field(min_length=1)


class _PendingWorkItemMutation(BaseModel):
    model_config = ConfigDict(frozen=True)

    idempotency_key: str
    key: str
    item: BacklogItem


class _RejectedMutation(BaseModel):
    """Durable provider mutation whose precondition can never be satisfied by retrying."""

    model_config = ConfigDict(frozen=True)

    idempotency_key: str
    write: ContentWrite
    reason: str


class _RejectedWorkItemMutation(BaseModel):
    """Durable work-item mutation whose idempotency_key doesn't match its own content.

    Mirrors :class:`_RejectedMutation` for the work-item queue -- inspectable
    and never replayed, but not destroyed. A mismatch is not proof of a
    hand-edit: an older plugin version reading an entry a newer version wrote
    silently drops any field it doesn't recognize (pydantic's default
    ``extra="ignore"``), which changes the recomputed hash for a perfectly
    legitimate entry too. Dropping outright would be silent data loss for
    that case; dead-lettering here keeps the entry recoverable either way.
    """

    model_config = ConfigDict(frozen=True)

    idempotency_key: str
    key: str
    item: BacklogItem
    reason: str


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
    rejected: list[_RejectedMutation] = Field(default_factory=list)
    pending_work_items: list[_PendingWorkItemMutation] = Field(default_factory=list)
    rejected_work_items: list[_RejectedWorkItemMutation] = Field(default_factory=list)
    snapshot_checkpoint: _ProviderSnapshotCheckpoint | None = None


# Fields whose loss discards a user's unreplayed offline write (logged at error,
# not warning) -- distinct from the other three fields, which are pure cache and
# regenerable from the provider.
_QUEUE_FIELDS: Final = frozenset({"pending", "pending_work_items"})


def _content_mutation_key(write: ContentWrite) -> str:
    """Reproducible idempotency key for a queued content write.

    Shared by :meth:`FileCache.queue_write` (derivation) and
    :meth:`_CacheStateStore._verify_queue_keys` (self-consistency check on
    load) so the formula lives in exactly one place.

    Returns:
        The hex-encoded sha256 digest of the write's canonical JSON.
    """
    payload = json.dumps(write.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def _work_item_mutation_key(key: str, item: BacklogItem) -> str:
    """Reproducible idempotency key for a queued work-item mutation.

    Shared by :meth:`FileCache._queue_work_item` (derivation) and
    :meth:`_CacheStateStore._verify_queue_keys` (self-consistency check on load).

    Returns:
        The hex-encoded sha256 digest of the key and the item's canonical JSON.
    """
    payload = json.dumps(item.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(f"{key}:{payload}".encode()).hexdigest()


class _CacheStateStore:
    """Serialize state transactions across threads and processes."""

    def __init__(self, root: Path) -> None:
        self._root = root
        self._state_path = root / _STATE_FILE
        self._legacy_state_path = root / _LEGACY_STATE_FILE

    def load(self) -> _CacheState:
        """Return the current state, salvaging what it can from a damaged file.

        Read-only -- never migrates or writes. A legacy-only root is read
        straight from ``cache.yaml`` without touching disk; migration only runs
        from :meth:`transaction`, which already holds the write lock (see
        :meth:`_migrate_legacy_state_file` for why doing it here would deadlock).
        """
        path = self._state_path if self._state_path.exists() else self._legacy_state_path
        if not path.exists():
            return _CacheState()
        return self._read(path)

    def _read(self, path: Path) -> _CacheState:
        text = path.read_text(encoding="utf-8")
        try:
            state = _CacheState.model_validate_json(text)
        except pydantic.ValidationError:
            raw = self._parse_relaxed(text, path)
            state = self._salvage(raw, path)
        # Runs on every load, not only the salvage branch above: a hand-edited
        # entry with a fabricated-but-syntactically-valid idempotency_key is
        # structurally complete, so it passes model_validate_json's fast path
        # without ever touching _salvage. The self-consistency check is a
        # semantic property pydantic's schema validation can't express.
        return self._verify_queue_keys(state, path)

    def transaction(self, transform: Callable[[_CacheState], tuple[_CacheState, _T]]) -> _T:
        with self._lock():
            self._migrate_legacy_state_file()
            state, result = transform(self.load())
            self._save(state)
        return result

    @contextlib.contextmanager
    def _lock(self) -> Iterator[None]:
        self._root.mkdir(mode=0o700, parents=True, exist_ok=True)
        with _THREAD_LOCKS_GUARD:
            thread_lock = _THREAD_LOCKS.setdefault(self._root.resolve(), Lock())
        with thread_lock:
            lock_fd = os.open(str(self._root / _LOCK_FILE), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
            try:
                if os.name == "nt":
                    msvcrt.locking(lock_fd, msvcrt.LK_LOCK, 1)
                else:
                    fcntl.flock(lock_fd, fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    if os.name == "nt":
                        msvcrt.locking(lock_fd, msvcrt.LK_UNLCK, 1)
                    else:
                        fcntl.flock(lock_fd, fcntl.LOCK_UN)
            finally:
                os.close(lock_fd)

    def _migrate_legacy_state_file(self) -> None:
        """Move a pre-rename ``cache.yaml`` onto ``cache.json``.

        Must only be called while already holding ``_lock()`` (from
        :meth:`transaction`) -- doing this from :meth:`load` would self-deadlock:
        ``_THREAD_LOCKS`` holds a non-reentrant ``threading.Lock``, and ``_lock()``
        opens a fresh fd each call, so a second ``flock(LOCK_EX)`` in the same
        process also blocks. Idempotent and self-healing: a crash mid-migration
        leaves ``cache.yaml`` in place, which :meth:`load` still reads, and the
        next transaction retries.

        ponytail: accepts a narrow, deliberate loss -- an older plugin copy that
        never observes this migration (a sequential downgrade, or two plugin
        versions sharing one ``~/.dh`` root concurrently) sees no ``cache.yaml``,
        takes ``cache.lock`` (never renamed, so both versions still exclude each
        other), and durably writes a fresh empty state. ``records``/``checkpoints``
        just cost a full resync; the real loss is any unreplayed
        ``pending``/``pending_work_items`` queued before that point. Upgrade to a
        signed/versioned handoff if this is ever observed in practice.
        """
        if not self._legacy_state_path.exists():
            return
        if self._state_path.exists():
            # Both present (e.g. post-downgrade-then-upgrade): cache.json is
            # authoritative -- load() already prefers it. Supersede the stale
            # legacy file so it stops looking like something safe to hand-edit,
            # without reading or altering its content.
            superseded = self._legacy_state_path.with_name(self._legacy_state_path.name + ".superseded")
            self._legacy_state_path.replace(superseded)
            return
        text = self._legacy_state_path.read_text(encoding="utf-8")
        try:
            json.loads(text)
        except json.JSONDecodeError:
            # Genuine legacy YAML: parse, salvage what validates, write as JSON,
            # then supersede (not delete) the original -- no data destroyed, no
            # longer named like something safe to hand-edit.
            raw = self._parse_yaml(text, self._legacy_state_path)
            state = self._verify_queue_keys(self._salvage(raw, self._legacy_state_path), self._legacy_state_path)
            self._save(state)
            superseded = self._legacy_state_path.with_name(self._legacy_state_path.name + ".superseded")
            self._legacy_state_path.replace(superseded)
        else:
            # Already JSON, just wearing the old extension. Rename with no
            # rewrite: _CacheState uses pydantic's default extra="ignore", so a
            # parse-and-rewrite would silently drop any field a newer plugin
            # version wrote that this version doesn't know about yet.
            self._legacy_state_path.replace(self._state_path)

    @staticmethod
    def _parse_yaml(text: str, path: Path) -> dict[str, object]:
        try:
            raw = YAML(typ="safe").load(text)
        except YAMLError as exc:
            raise CacheStateCorruptError(f"Cache state file is not valid YAML: {path}") from exc
        if not isinstance(raw, dict):
            raise CacheStateCorruptError(f"Cache state file did not parse to a mapping: {path}")
        return raw

    @staticmethod
    def _parse_relaxed(text: str, path: Path) -> dict[str, object]:
        """Parse a state file that failed strict JSON-schema validation.

        Returns:
            The parsed mapping, ready for per-entry salvage.

        Raises:
            CacheStateCorruptError: The text is neither valid JSON nor valid
                YAML, or it parses to something other than a mapping.
        """
        try:
            raw = json.loads(text)
        except json.JSONDecodeError:
            return _CacheStateStore._parse_yaml(text, path)
        if not isinstance(raw, dict):
            raise CacheStateCorruptError(f"Cache state file did not parse to a mapping: {path}")
        return raw

    def _salvage(self, raw: dict[str, object], path: Path) -> _CacheState:
        """Validate each entry of a partially-malformed state dict independently.

        Drops individual malformed entries instead of failing the whole load --
        a hand-edit or a schema change from an older plugin version should cost
        one entry, not the entire durable cache. The two most likely causes of a
        single bad entry in an otherwise-valid document: a hand-edit (bypassing
        this store's normal write path), or schema evolution (a model gaining a
        required field invalidates entries queued by an older plugin version).
        Whole-document corruption (e.g. truncation) never reaches this method --
        it fails earlier, in :meth:`_parse_relaxed`, with a typed error, because
        per-entry salvage cannot help when the document itself doesn't parse.

        Returns:
            A state built only from entries that validated; malformed ones are
            logged and dropped.
        """
        # Runtime shape is guaranteed by _salvage_list's own model.model_validate()
        # call; the casts below narrow it back for the type checker, which can't
        # express that generically without an overload per field.
        records = cast("list[ContentRecord]", self._salvage_list(raw, "records", ContentRecord, path))
        checkpoints = cast("list[CacheCheckpoint]", self._salvage_list(raw, "checkpoints", CacheCheckpoint, path))
        pending = cast("list[PendingMutation]", self._salvage_list(raw, "pending", PendingMutation, path))
        rejected = cast("list[_RejectedMutation]", self._salvage_list(raw, "rejected", _RejectedMutation, path))
        pending_work_items = cast(
            "list[_PendingWorkItemMutation]",
            self._salvage_list(raw, "pending_work_items", _PendingWorkItemMutation, path),
        )
        rejected_work_items = cast(
            "list[_RejectedWorkItemMutation]",
            self._salvage_list(raw, "rejected_work_items", _RejectedWorkItemMutation, path),
        )
        # Idempotency-key self-consistency is checked once, uniformly, in
        # _verify_queue_keys -- not here, so it also runs on states that took
        # the model_validate_json fast path (see _read).
        checkpoint = self._salvage_checkpoint(raw, path)
        return _CacheState(
            records=records,
            checkpoints=checkpoints,
            pending=pending,
            rejected=rejected,
            pending_work_items=pending_work_items,
            rejected_work_items=rejected_work_items,
            snapshot_checkpoint=checkpoint,
        )

    @staticmethod
    def _salvage_list(raw: dict[str, object], field_name: str, model: type[BaseModel], path: Path) -> list[BaseModel]:
        value = raw.get(field_name, [])
        log = _log.error if field_name in _QUEUE_FIELDS else _log.warning
        if not isinstance(value, list):
            log("Cache state %s: %r is not a list (%r) -- dropping all entries", path, field_name, value)
            return []
        survivors: list[BaseModel] = []
        for entry in value:
            try:
                survivors.append(model.model_validate(entry))
            except pydantic.ValidationError as exc:
                log("Cache state %s: dropping malformed %s entry: %s", path, field_name, exc)
        return survivors

    @staticmethod
    def _salvage_checkpoint(raw: dict[str, object], path: Path) -> _ProviderSnapshotCheckpoint | None:
        value = raw.get("snapshot_checkpoint")
        if value is None:
            return None
        try:
            return _ProviderSnapshotCheckpoint.model_validate(value)
        except pydantic.ValidationError as exc:
            # A lost watermark just forces a full resync -- warning, not error;
            # the cache is regenerable, unlike a dropped offline write.
            _log.warning("Cache state %s: dropping malformed snapshot_checkpoint: %s", path, exc)
            return None

    @staticmethod
    def _verify_queue_keys(state: _CacheState, path: Path) -> _CacheState:
        """Dead-letter any pending/pending_work_items entry whose key doesn't match its content.

        Runs on every load (both the model_validate_json fast path and the
        _salvage path) and during migration, before a legacy file's converted
        content is saved -- not folded into _salvage, because a structurally
        complete but forged entry never fails schema validation and would
        otherwise skip this check entirely. rejected/rejected_work_items entries
        are exempt from the check themselves: they're inert inspection records,
        never replayed, so a stale key there is harmless.

        A mismatch moves the entry to rejected/rejected_work_items instead of
        deleting it -- it is not proof of a hand-edit. An older plugin version
        reading an entry a newer version wrote silently drops any field it
        doesn't recognize (pydantic's default extra="ignore"), which changes
        the recomputed hash for a perfectly legitimate entry too. Dropping
        outright would be silent data loss for that case; dead-lettering keeps
        the entry recoverable and inspectable either way.

        Returns:
            ``state``, or a copy with the inconsistent entries moved to the
            corresponding rejected list.
        """
        pending: list[PendingMutation] = []
        rejected = list(state.rejected)
        for entry in state.pending:
            expected = _content_mutation_key(entry.write)
            if _CacheStateStore._key_is_consistent(path, "pending", entry.idempotency_key, expected):
                pending.append(entry)
            else:
                rejected.append(
                    _RejectedMutation(
                        idempotency_key=entry.idempotency_key,
                        write=entry.write,
                        reason="idempotency_key does not match its content",
                    )
                )
        pending_work_items: list[_PendingWorkItemMutation] = []
        rejected_work_items = list(state.rejected_work_items)
        for wi_entry in state.pending_work_items:
            expected = _work_item_mutation_key(wi_entry.key, wi_entry.item)
            if _CacheStateStore._key_is_consistent(path, "pending_work_items", wi_entry.idempotency_key, expected):
                pending_work_items.append(wi_entry)
            else:
                rejected_work_items.append(
                    _RejectedWorkItemMutation(
                        idempotency_key=wi_entry.idempotency_key,
                        key=wi_entry.key,
                        item=wi_entry.item,
                        reason="idempotency_key does not match its content",
                    )
                )
        if (
            pending == state.pending
            and pending_work_items == state.pending_work_items
            and rejected == state.rejected
            and rejected_work_items == state.rejected_work_items
        ):
            return state
        return state.model_copy(
            update={
                "pending": pending,
                "pending_work_items": pending_work_items,
                "rejected": rejected,
                "rejected_work_items": rejected_work_items,
            }
        )

    @staticmethod
    def _key_is_consistent(path: Path, field_name: str, stored_key: str, expected_key: str) -> bool:
        """Self-consistency check: does a queue entry's key match its own content?

        A key mismatch does not by itself prove a hand-edit -- see
        :meth:`_verify_queue_keys` for why a legitimate, version-skewed entry
        can trip this too. Either way the entry is dead-lettered, not trusted
        for replay, by the caller.

        Returns:
            True if the entry's key matches its own content, False otherwise
            (also logs the mismatch at error level).
        """
        if stored_key == expected_key:
            return True
        _log.error(
            "Cache state %s: dead-lettering %s entry %s -- idempotency_key does not match its content",
            path,
            field_name,
            stored_key,
        )
        return False

    def _save(self, state: _CacheState) -> None:
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self._root, suffix=".tmp", delete=False
            ) as stream:
                temporary_path = Path(stream.name)
                stream.write(state.model_dump_json())
                stream.flush()
                os.fsync(stream.fileno())
            temporary_path.replace(self._state_path)
            temporary_path = None
        finally:
            if temporary_path is not None:
                with contextlib.suppress(FileNotFoundError):
                    temporary_path.unlink()
