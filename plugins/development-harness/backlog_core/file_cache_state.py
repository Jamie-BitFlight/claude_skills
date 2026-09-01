"""Atomic state storage for the provider-private file cache."""

from __future__ import annotations

import contextlib
import hashlib
import json
import logging
import os
import tempfile
import time as _time
from collections.abc import Callable, Iterator
from pathlib import Path
from threading import Lock
from typing import Any, Final, TypeVar, cast

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


class _CorruptQueueEntry(BaseModel):
    """A pending/pending_work_items entry that failed schema validation on load.

    Stored as its raw, unvalidated payload -- unlike a key mismatch, a
    schema-invalid entry never became a typed model, so there is no
    well-formed object to preserve otherwise. The most likely cause is
    schema evolution (a model gaining a required field invalidates entries
    an older plugin version queued), not corruption, so the payload is very
    likely a perfectly good write that this version just can't parse yet --
    kept for manual recovery rather than silently discarded.
    """

    model_config = ConfigDict(frozen=True)

    field: str
    raw: Any
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
    corrupt_queue_entries: list[_CorruptQueueEntry] = Field(default_factory=list)
    snapshot_checkpoint: _ProviderSnapshotCheckpoint | None = None


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

    def load_after_migration(self) -> _CacheState:
        """Migrate the legacy file if needed, then load -- one lock acquisition, not two.

        ``load()`` itself stays read-only (see :meth:`_migrate_legacy_state_file`
        for why running migration there would deadlock), so a read accessor
        that enumerates the queue -- replay, reconciliation -- would otherwise
        see a legacy-recreated ``cache.yaml``'s entries only after some
        unrelated :meth:`transaction` happens to run first. Call this instead
        of :meth:`load` for that kind of read.

        Migration and the read that follows share one lock acquisition
        deliberately, not two separate calls: another process recreating
        ``cache.yaml`` in the gap between a migrate-then-release and a
        separate later load would be invisible to that load, the same race
        :meth:`transaction` already avoids by holding the lock across both.

        Returns:
            The state after any pending migration has been applied.
        """
        with self._lock():
            self._migrate_legacy_state_file()
            return self.load()

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

        ponytail: an older plugin copy that never observes this migration (a
        sequential downgrade, or two plugin versions sharing one ``~/.dh`` root
        concurrently) sees no ``cache.yaml``, takes ``cache.lock`` (never
        renamed, so both versions still exclude each other), and durably
        writes a fresh ``cache.yaml`` containing just its own new offline
        writes. The "both present" branch below merges that recreated file's
        pending/pending_work_items into cache.json's before superseding it, so
        that queued intent survives; records/checkpoints/snapshot_checkpoint
        from the legacy copy are still discarded on that path -- regenerable,
        so an accepted, narrower loss than before. Upgrade to a
        signed/versioned handoff if even that is ever observed as a problem.
        """
        if not self._legacy_state_path.exists():
            return
        if self._state_path.exists():
            self._merge_legacy_queue_entries_and_supersede()
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

    def _merge_legacy_queue_entries_and_supersede(self) -> None:
        """Merge a recreated legacy file's queue and dead-letter entries into cache.json, then supersede it.

        Called when both files exist. cache.json is authoritative for
        records/checkpoints/snapshot_checkpoint -- load() already prefers it,
        and the legacy copy's version of those is discarded here as
        regenerable. The five queue/dead-letter fields are different: an
        older plugin copy unaware of the rename could have written new
        offline mutations into a fresh cache.yaml of its own (see the
        ponytail note on :meth:`_migrate_legacy_state_file`), or its own read
        of that file could have dead-lettered an entry via the same
        :meth:`_verify_queue_keys`/:meth:`_salvage` this method itself calls.
        Superseding the file has a fixed target name -- a second occurrence
        of this scenario would silently overwrite the first ``.superseded``
        copy, so anything worth keeping has to be merged into cache.json now,
        not left for someone to notice the file before that happens. A legacy
        file too corrupt to parse at all can't be merged this way -- it gets
        a uniquely-named backup instead of the fixed ``.superseded`` name, so
        a second corrupt-legacy-file occurrence doesn't overwrite the first.
        """
        try:
            text = self._legacy_state_path.read_text(encoding="utf-8")
            raw = self._parse_relaxed(text, self._legacy_state_path)
            legacy_state = self._verify_queue_keys(self._salvage(raw, self._legacy_state_path), self._legacy_state_path)
        except CacheStateCorruptError as exc:
            unparsable_backup = self._legacy_state_path.with_name(
                f"{self._legacy_state_path.name}.corrupt.{_time.time_ns()}"
            )
            _log.error(
                "Cache state %s: could not read for merge before superseding, preserving as %s instead: %s",
                self._legacy_state_path,
                unparsable_backup,
                exc,
            )
            self._legacy_state_path.replace(unparsable_backup)
            return
        else:
            if (
                legacy_state.pending
                or legacy_state.pending_work_items
                or legacy_state.rejected
                or legacy_state.rejected_work_items
                or legacy_state.corrupt_queue_entries
            ):
                current = self.load()
                merged = self._merge_queue_state(current, legacy_state)
                if merged != current:
                    self._save(merged)
        superseded = self._legacy_state_path.with_name(self._legacy_state_path.name + ".superseded")
        self._legacy_state_path.replace(superseded)

    @staticmethod
    def _merge_queue_state(current: _CacheState, legacy: _CacheState) -> _CacheState:
        """Union all five queue/dead-letter fields from ``legacy`` into ``current``.

        ``rejected``/``rejected_work_items``/``corrupt_queue_entries`` are
        pure accumulated history -- duplicates across sources are harmless,
        so those three just union (deduped by ``idempotency_key``, or full
        equality for ``corrupt_queue_entries``, which has no key). pending
        and pending_work_items are different: ``queue_write()``/
        ``_queue_work_item()`` each maintain "at most one entry per
        reference/key" as an invariant, coalescing on every call within one
        process -- but that invariant says nothing about two *different*
        writes for the *same* reference arriving from two independently-
        evolved sources (current vs. a legacy file recreated by older code).
        Deduping only by ``idempotency_key`` would let both survive,
        breaking the invariant every other code path relies on and risking
        `replay_pending()` applying a stale entry after a newer one landed.
        current's entry wins on a shared reference/key; legacy's superseded
        entry is dead-lettered into rejected/rejected_work_items, not
        silently dropped. A final cross-check then removes any key left in
        both a pending list and its own terminal counterpart (current.pending
        holding a key legacy.rejected already has, or vice versa) -- the two
        per-field merges above only dedupe within one field, not across a
        queue and its terminal state, so the terminal classification wins.

        Returns:
            ``current``, with each of the five fields extended by whatever
            ``legacy`` holds that ``current`` doesn't already have.
        """

        def merged_by_key(current_entries: list[Any], legacy_entries: list[Any]) -> list[Any]:
            existing_keys = {entry.idempotency_key for entry in current_entries}
            return [
                *current_entries,
                *(entry for entry in legacy_entries if entry.idempotency_key not in existing_keys),
            ]

        pending, superseded_pending = _CacheStateStore._merge_pending_by_reference(current.pending, legacy.pending)
        pending_work_items, superseded_work_items = _CacheStateStore._merge_pending_work_items_by_key(
            current.pending_work_items, legacy.pending_work_items
        )
        rejected = [*merged_by_key(current.rejected, legacy.rejected), *superseded_pending]
        rejected_work_items = [
            *merged_by_key(current.rejected_work_items, legacy.rejected_work_items),
            *superseded_work_items,
        ]
        # A key can end up in both a pending list and its own terminal
        # counterpart: current.pending might hold a key legacy.rejected
        # already has (or vice versa) -- the two per-field merges above don't
        # cross-check between a queue and its own terminal state, only
        # within each one. The terminal state wins: replaying an entry
        # already classified terminal elsewhere risks a second, redundant
        # rejection once verification catches up.
        rejected_keys = {entry.idempotency_key for entry in rejected}
        pending = [entry for entry in pending if entry.idempotency_key not in rejected_keys]
        rejected_work_item_keys = {entry.idempotency_key for entry in rejected_work_items}
        pending_work_items = [
            entry for entry in pending_work_items if entry.idempotency_key not in rejected_work_item_keys
        ]
        return current.model_copy(
            update={
                "pending": pending,
                "pending_work_items": pending_work_items,
                "rejected": rejected,
                "rejected_work_items": rejected_work_items,
                "corrupt_queue_entries": [
                    *current.corrupt_queue_entries,
                    *(entry for entry in legacy.corrupt_queue_entries if entry not in current.corrupt_queue_entries),
                ],
            }
        )

    @staticmethod
    def _merge_pending_by_reference(
        current: list[PendingMutation], legacy: list[PendingMutation]
    ) -> tuple[list[PendingMutation], list[_RejectedMutation]]:
        """Union two pending-write queues, keeping at most one entry per reference.

        Returns:
            The merged queue (current's entries plus legacy's that don't
            collide by reference or idempotency_key), and a dead-lettered
            _RejectedMutation for each legacy entry superseded by a
            same-reference entry current already has.
        """
        existing_keys = {entry.idempotency_key for entry in current}
        # ContentRef isn't hashable (nested fields), so this stays a list
        # membership check rather than a set, unlike existing_keys above.
        existing_references = [entry.write.reference for entry in current]
        survivors = list(current)
        superseded: list[_RejectedMutation] = []
        for entry in legacy:
            if entry.idempotency_key in existing_keys:
                continue
            if entry.write.reference in existing_references:
                superseded.append(
                    _RejectedMutation(
                        idempotency_key=entry.idempotency_key,
                        write=entry.write,
                        reason="superseded by cache.json's entry for the same reference during legacy-file merge",
                    )
                )
                continue
            survivors.append(entry)
        return survivors, superseded

    @staticmethod
    def _merge_pending_work_items_by_key(
        current: list[_PendingWorkItemMutation], legacy: list[_PendingWorkItemMutation]
    ) -> tuple[list[_PendingWorkItemMutation], list[_RejectedWorkItemMutation]]:
        """Union two pending-work-item queues, keeping at most one entry per ``key``.

        Returns:
            The merged queue, and a dead-lettered _RejectedWorkItemMutation
            for each legacy entry superseded by a same-key entry current
            already has -- see :meth:`_merge_pending_by_reference` for why
            idempotency_key alone isn't enough here.
        """
        existing_keys = {entry.idempotency_key for entry in current}
        existing_work_keys = {entry.key for entry in current}
        survivors = list(current)
        superseded: list[_RejectedWorkItemMutation] = []
        for entry in legacy:
            if entry.idempotency_key in existing_keys:
                continue
            if entry.key in existing_work_keys:
                superseded.append(
                    _RejectedWorkItemMutation(
                        idempotency_key=entry.idempotency_key,
                        key=entry.key,
                        item=entry.item,
                        reason="superseded by cache.json's entry for the same key during legacy-file merge",
                    )
                )
                continue
            survivors.append(entry)
        return survivors, superseded

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

        records/checkpoints are different from the other four fields: those
        are pure cache, safely dropped and logged (:meth:`_salvage_field`
        with ``preserve=False``). pending/pending_work_items/rejected/
        rejected_work_items are all precious -- a schema-invalid entry there
        is more likely a legitimate write this version can't parse yet
        (schema evolution) than genuine corruption, including in the two
        terminal dead-letter buckets themselves (a stored ``rejected``/
        ``rejected_work_items`` entry is the only recovery record for
        whatever it holds; losing it too on a later load would be worse
        than the mismatch that put it there). :meth:`_salvage_field` with
        ``preserve=True`` preserves each one's raw payload in
        ``corrupt_queue_entries`` instead of dropping it. That field is the
        terminal fallback and isn't routed through the same path itself:
        its ``raw: Any`` member can't fail model validation, so there's
        nothing further to preserve it from.

        Returns:
            A state built only from entries that validated; malformed
            records/checkpoints entries are logged and dropped, malformed
            entries in the four precious fields are preserved in
            ``corrupt_queue_entries``.
        """
        # Runtime shape is guaranteed by _salvage_field's own
        # model.model_validate() calls; the casts below narrow the result back
        # for the type checker, which can't express that generically without an
        # overload per field. Driven by a loop rather than one named pair of
        # locals per field, to stay under ruff's too-many-locals limit.
        records = cast("list[ContentRecord]", self._salvage_field(raw, "records", ContentRecord, path)[0])
        checkpoints = cast("list[CacheCheckpoint]", self._salvage_field(raw, "checkpoints", CacheCheckpoint, path)[0])
        corrupt = cast(
            "list[_CorruptQueueEntry]", self._salvage_field(raw, "corrupt_queue_entries", _CorruptQueueEntry, path)[0]
        )
        survivors: dict[str, list[BaseModel]] = {}
        for field_name, model in (
            ("pending", PendingMutation),
            ("pending_work_items", _PendingWorkItemMutation),
            ("rejected", _RejectedMutation),
            ("rejected_work_items", _RejectedWorkItemMutation),
        ):
            entries, bad = self._salvage_field(raw, field_name, model, path, preserve=True)
            survivors[field_name] = entries
            corrupt.extend(bad)
        # Idempotency-key self-consistency is checked once, uniformly, in
        # _verify_queue_keys -- not here, so it also runs on states that took
        # the model_validate_json fast path (see _read).
        checkpoint = self._salvage_checkpoint(raw, path)
        return _CacheState(
            records=records,
            checkpoints=checkpoints,
            pending=cast("list[PendingMutation]", survivors["pending"]),
            rejected=cast("list[_RejectedMutation]", survivors["rejected"]),
            pending_work_items=cast("list[_PendingWorkItemMutation]", survivors["pending_work_items"]),
            rejected_work_items=cast("list[_RejectedWorkItemMutation]", survivors["rejected_work_items"]),
            corrupt_queue_entries=corrupt,
            snapshot_checkpoint=checkpoint,
        )

    @staticmethod
    def _salvage_field(
        raw: dict[str, object], field_name: str, model: type[BaseModel], path: Path, *, preserve: bool = False
    ) -> tuple[list[BaseModel], list[_CorruptQueueEntry]]:
        """Validate each entry of one field independently, per ``preserve``'s failure policy.

        ``preserve=False`` (records/checkpoints/corrupt_queue_entries -- pure
        cache, safe to drop): a malformed entry is logged at warning level and
        dropped; the second return element is always empty.

        ``preserve=True`` (pending/pending_work_items/rejected/
        rejected_work_items -- precious, losing one outright would discard
        something no longer recoverable elsewhere): a malformed entry is
        logged at error level and dead-lettered into a :class:`_CorruptQueueEntry`
        instead of being dropped.

        Returns:
            The entries that validated, and (``preserve=True`` only) a
            :class:`_CorruptQueueEntry` for each one that didn't -- or, if
            ``field_name`` itself isn't a list, a single such entry
            preserving the whole raw value rather than silently discarding
            the entire field. Always ``[]`` when ``preserve=False``.
        """
        value = raw.get(field_name, [])
        if not isinstance(value, list):
            if preserve:
                _log.error(
                    "Cache state %s: %r is not a list (%r) -- preserving as a single corrupt entry",
                    path,
                    field_name,
                    value,
                )
                return [], [_CorruptQueueEntry(field=field_name, raw=value, reason="value is not a list")]
            _log.warning("Cache state %s: %r is not a list (%r) -- dropping all entries", path, field_name, value)
            return [], []
        survivors: list[BaseModel] = []
        corrupt: list[_CorruptQueueEntry] = []
        for entry in value:
            try:
                survivors.append(model.model_validate(entry))
            except pydantic.ValidationError as exc:
                if preserve:
                    _log.error(
                        "Cache state %s: dead-lettering malformed %s entry (raw payload preserved): %s",
                        path,
                        field_name,
                        exc,
                    )
                    corrupt.append(_CorruptQueueEntry(field=field_name, raw=entry, reason=str(exc)))
                else:
                    _log.warning("Cache state %s: dropping malformed %s entry: %s", path, field_name, exc)
        return survivors, corrupt

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

        Known limitation, deliberately not fixed here: this is a one-way,
        permanent move. Once dead-lettered, an entry is never re-verified or
        automatically promoted back to pending/pending_work_items, even by a
        later load from a plugin version that could have recomputed a matching
        key. A false-positive version-skew entry is therefore preserved but
        not automatically delivered to the backend -- recoverable by manual
        inspection of rejected/rejected_work_items, not by anything automatic.
        Building real self-healing (re-verify on every load, with the
        version-detection and backoff that needs to not thrash) is the kind
        of provenance/recovery machinery already called out as deferred scope
        on backlog #2287, not a rider on this fix.

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
