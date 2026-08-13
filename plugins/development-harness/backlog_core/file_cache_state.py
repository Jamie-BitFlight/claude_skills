"""Atomic state storage for the provider-private file cache."""

from __future__ import annotations

import contextlib
import os
import tempfile
from collections.abc import Callable, Iterator
from pathlib import Path
from threading import Lock
from typing import Final, TypeVar

from pydantic import BaseModel, ConfigDict, Field
from ruamel.yaml import YAML

from .models import BacklogItem, ContentRecord, ContentRef, ContentWrite

if os.name == "nt":
    import msvcrt
else:
    import fcntl

_STATE_FILE: Final = "cache.yaml"
_LOCK_FILE: Final = "cache.lock"
_T = TypeVar("_T")
_THREAD_LOCKS: Final[dict[Path, Lock]] = {}
_THREAD_LOCKS_GUARD: Final = Lock()


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
    pending_work_items: list[_PendingWorkItemMutation] = Field(default_factory=list)
    snapshot_checkpoint: _ProviderSnapshotCheckpoint | None = None


class _CacheStateStore:
    """Serialize state transactions across threads and processes."""

    def __init__(self, root: Path) -> None:
        self._root = root
        self._state_path = root / _STATE_FILE

    def load(self) -> _CacheState:
        if not self._state_path.exists():
            return _CacheState()
        yaml = YAML(typ="safe")
        with self._state_path.open(encoding="utf-8") as stream:
            return _CacheState.model_validate(yaml.load(stream))

    def transaction(self, transform: Callable[[_CacheState], tuple[_CacheState, _T]]) -> _T:
        with self._lock():
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

    def _save(self, state: _CacheState) -> None:
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
            temporary_path.replace(self._state_path)
            temporary_path = None
        finally:
            if temporary_path is not None:
                with contextlib.suppress(FileNotFoundError):
                    temporary_path.unlink()
