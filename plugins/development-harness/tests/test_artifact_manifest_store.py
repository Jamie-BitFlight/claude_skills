from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Lock

from backlog_core.artifact_manifest_store import register_manifest_entry
from backlog_core.backends.memory_backend import InMemoryBackend
from backlog_core.models import (
    ArtifactEntry,
    ArtifactManifest,
    ArtifactType,
    ContentKind,
    ContentRecord,
    ContentRef,
    ContentWrite,
)


class _ConcurrentInitialReadBackend(InMemoryBackend):
    def __init__(self) -> None:
        super().__init__()
        self._initial_reads = Barrier(2, timeout=5)
        self._initial_writes = Barrier(2, timeout=5)
        self._read_count = 0
        self._write_count = 0
        self._read_lock = Lock()
        self.writes: list[ContentWrite] = []

    def get_content(self, reference: ContentRef) -> ContentRecord:
        with self._read_lock:
            is_initial_read = self._read_count < 2
            self._read_count += 1
        if is_initial_read and reference.kind == ContentKind.ARTIFACT_MANIFEST:
            self._initial_reads.wait()
        return super().get_content(reference)

    def put_content(self, request: ContentWrite) -> ContentRecord:
        with self._read_lock:
            is_initial_write = self._write_count < 2
            self._write_count += 1
        self.writes.append(request)
        if is_initial_write:
            self._initial_writes.wait()
        return super().put_content(request)


def test_concurrent_initial_manifest_registration_uses_create_only_and_retries() -> None:
    provider = _ConcurrentInitialReadBackend()
    reference = ContentRef(kind=ContentKind.ARTIFACT_MANIFEST, namespace="42", name="manifest")
    entries = [
        ArtifactEntry(artifact_type=ArtifactType.ARCHITECT, artifact_id="one.md"),
        ArtifactEntry(artifact_type=ArtifactType.RESEARCH, artifact_id="two.md"),
    ]

    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(lambda entry: register_manifest_entry(provider, reference, 42, entry), entries))

    persisted = ArtifactManifest.model_validate_json(provider.get_content(reference).content)
    assert {(entry.artifact_type, entry.artifact_id) for entry in persisted.artifacts} == {
        (entry.artifact_type, entry.artifact_id) for entry in entries
    }
    assert [write.create_only for write in provider.writes[:2]] == [True, True]
    assert provider.writes[2].expected_revision
