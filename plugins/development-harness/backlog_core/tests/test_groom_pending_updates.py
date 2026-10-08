"""Public-boundary regression coverage for pending GitHub grooming writes."""

from __future__ import annotations

from threading import Barrier, Event, Lock, Thread
from typing import TYPE_CHECKING

import pytest

from backlog_core import operations
from backlog_core.backend_types import BacklogConfig
from backlog_core.backends.github_backend import GitHubBackend
from backlog_core.backends.memory_backend import InMemoryBackend
from backlog_core.file_cache import FileCache
from backlog_core.models import (
    BackendUnavailableError,
    BacklogError,
    BacklogItem,
    Entry,
    ReconcileRequest,
    ReconcileScope,
    Section,
)
from backlog_core.work_item_decisions import WorkItemDecisionContext

from ._fake_github import FakeGitHubHarness, make_harness

if TYPE_CHECKING:
    from pathlib import Path


class _RendezvousBackend(GitHubBackend):
    """Pause public groom calls after their real durable queue writes."""

    def __init__(self, harness: FakeGitHubHarness, cache_dir: Path) -> None:
        super().__init__(repo=harness.repo, cache=FileCache(cache_dir), contents=harness.contents)
        self._fetch_targeted_issues = harness.network.fetch_targeted_issues  # ty: ignore[invalid-assignment]
        self._expected_writes = 0
        self._queued_writes = 0
        self._queued = Event()
        self._release = Event()
        self._lock = Lock()
        self.offline = False

    def pause_after_writes(self, expected_writes: int) -> None:
        self._expected_writes = expected_writes
        self._queued_writes = 0
        self._queued.clear()
        self._release.clear()

    def put_work_item(self, item, repo: str = "", grooming_intent=None) -> None:  # type: ignore[no-untyped-def]
        super().put_work_item(item, repo, grooming_intent)
        with self._lock:
            self._queued_writes += 1
            if self._queued_writes == self._expected_writes:
                self._queued.set()
        if self._expected_writes:
            assert self._release.wait(timeout=5), "test did not release the queued grooming writes"

    def release(self) -> None:
        self._release.set()

    def reconcile(self, request: ReconcileRequest, *, snapshot=None):  # type: ignore[no-untyped-def]
        if self.offline:
            raise BackendUnavailableError("controlled offline reconciliation")
        return super().reconcile(request, snapshot=snapshot)


class _SharedPublication:
    def __init__(self) -> None:
        self.attempts = 0
        self.first_apply = Event()
        self.second_apply = Event()
        self.release_apply = Event()
        self.lock = Lock()


class _SharedCacheBackend(GitHubBackend):
    def __init__(
        self, harness: FakeGitHubHarness, cache_dir: Path, invocation_barrier: Barrier, publication: _SharedPublication
    ) -> None:
        super().__init__(repo=harness.repo, cache=FileCache(cache_dir), contents=harness.contents)
        self._fetch_targeted_issues = harness.network.fetch_targeted_issues  # ty: ignore[invalid-assignment]
        self._invocation_barrier = invocation_barrier
        self._publication = publication

    def reconcile(self, request: ReconcileRequest, *, snapshot=None):  # type: ignore[no-untyped-def]
        self._invocation_barrier.wait(timeout=5)
        return super().reconcile(request, snapshot=snapshot)

    def _apply_patches(self, patches, repo: str = ""):  # type: ignore[no-untyped-def]
        with self._publication.lock:
            self._publication.attempts += 1
            if self._publication.attempts == 1:
                self._publication.first_apply.set()
            else:
                self._publication.second_apply.set()
        assert self._publication.release_apply.wait(timeout=5), "test did not release provider apply"
        return super()._apply_patches(patches, repo)


@pytest.fixture
def harness(monkeypatch: pytest.MonkeyPatch) -> FakeGitHubHarness:
    return make_harness(monkeypatch, repo="owner/repo")


def _use_backend(monkeypatch: pytest.MonkeyPatch, backend: GitHubBackend) -> None:
    monkeypatch.setattr(operations, "get_config", lambda: BacklogConfig(backend=backend))


def _add_item(monkeypatch: pytest.MonkeyPatch, backend: GitHubBackend) -> str:
    _use_backend(monkeypatch, backend)
    added = operations.add_item(title="Concurrent grooming", description="base", priority="P1")
    reference = added["item_ref"]
    assert isinstance(reference, str)
    return reference


def _entries(item: BacklogItem, section_key: str) -> list[Entry]:
    section = item.sections[section_key]
    assert isinstance(section, Section)
    return section.entries


def _groom_in_threads(reference: str, repo: str, *updates: tuple[str, str]) -> tuple[list[BacklogError], list[Thread]]:
    failures: list[BacklogError] = []

    def groom(section: str, content: str) -> None:
        try:
            operations.groom_item(reference, section=section, content=content, repo=repo)
        except BacklogError as error:  # pragma: no cover - raised in the calling assertion
            failures.append(error)

    threads = [Thread(target=groom, args=update) for update in updates]
    for thread in threads:
        thread.start()
    return failures, threads


def _hold_common_base_selection(monkeypatch: pytest.MonkeyPatch, expected_calls: int = 2) -> tuple[Event, Event]:
    selected = Event()
    release = Event()
    lock = Lock()
    calls = 0
    original_select = WorkItemDecisionContext.select

    def select_common_base(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        nonlocal calls
        target = original_select(self, *args, **kwargs)
        with lock:
            calls += 1
            hold = calls <= expected_calls
            if calls == expected_calls:
                selected.set()
        if hold:
            assert release.wait(timeout=5), "test did not release common-base selection"
        return target

    monkeypatch.setattr(WorkItemDecisionContext, "select", select_common_base)
    return selected, release


def _release_and_join(backend: _RendezvousBackend, failures: list[BacklogError], threads: list[Thread]) -> None:
    backend.release()
    for thread in threads:
        thread.join(timeout=5)
        assert not thread.is_alive(), "grooming call did not finish"
    assert not failures


def test_stale_different_section_grooms_coalesce_and_reconcile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, harness: FakeGitHubHarness
) -> None:
    """Two stale public calls retain both section updates through a fresh reader."""
    writer = _RendezvousBackend(harness, tmp_path / "writer-cache")
    reference = _add_item(monkeypatch, writer)
    writer.pause_after_writes(2)
    selected, release_selection = _hold_common_base_selection(monkeypatch)

    failures, threads = _groom_in_threads(
        reference, harness.repo, ("Research", "FIRST_RESEARCH"), ("Decision", "SECOND_DECISION")
    )
    try:
        assert selected.wait(timeout=5), "both public grooming calls did not select the common base"
        release_selection.set()
        assert writer._queued.wait(timeout=5), "both public grooming calls did not reach the queue"

        pending = writer.pending_work_items(harness.repo)
        assert len(pending) == 1
        assert {entry.content for entry in _entries(pending[0], "research")} == {"FIRST_RESEARCH"}
        assert {entry.content for entry in _entries(pending[0], "unknown__decision")} == {"SECOND_DECISION"}
    finally:
        release_selection.set()
        _release_and_join(writer, failures, threads)
    assert writer.pending_work_items(harness.repo) == []

    reader = harness.new_backend(tmp_path / "reader-cache")
    reader.reconcile(ReconcileRequest(scope=ReconcileScope.TARGETED, repo=harness.repo, references=[reference]))
    persisted = reader.get_work_item(reference)
    assert {entry.content for entry in _entries(persisted, "research")} == {"FIRST_RESEARCH"}
    assert {entry.content for entry in _entries(persisted, "unknown__decision")} == {"SECOND_DECISION"}


def test_shared_cache_reconciliation_publishes_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, harness: FakeGitHubHarness
) -> None:
    """Separate backends sharing a cache acknowledge one combined provider mutation."""
    cache_dir = tmp_path / "shared-cache"
    writer = _RendezvousBackend(harness, cache_dir)
    reference = _add_item(monkeypatch, writer)
    writer.offline = True
    writer._expected_writes = 0
    operations.groom_item(reference, section="Research", content="FIRST_RESEARCH", repo=harness.repo)
    operations.groom_item(reference, section="Decision", content="SECOND_DECISION", repo=harness.repo)

    invocation_barrier = Barrier(3)
    publication = _SharedPublication()
    backends = [_SharedCacheBackend(harness, cache_dir, invocation_barrier, publication) for _ in range(2)]
    request = ReconcileRequest(scope=ReconcileScope.TARGETED, repo=harness.repo, references=[reference])
    failures: list[BacklogError] = []

    def reconcile(backend: _SharedCacheBackend) -> None:
        try:
            backend.reconcile(request)
        except BacklogError as error:
            failures.append(error)

    threads = [Thread(target=reconcile, args=(backend,)) for backend in backends]
    for thread in threads:
        thread.start()
    try:
        invocation_barrier.wait(timeout=5)
        assert publication.first_apply.wait(timeout=5), "no reconciliation reached provider apply"
        publication.second_apply.wait(timeout=1)
    finally:
        publication.release_apply.set()
        for thread in threads:
            thread.join(timeout=5)
            assert not thread.is_alive(), "reconciliation did not finish"
    assert not failures
    assert publication.attempts == 1
    assert writer.pending_work_items(harness.repo) == []

    reader = harness.new_backend(tmp_path / "reader-cache")
    reader.reconcile(request)
    persisted = reader.get_work_item(reference)
    assert {entry.content for entry in _entries(persisted, "research")} == {"FIRST_RESEARCH"}
    assert {entry.content for entry in _entries(persisted, "unknown__decision")} == {"SECOND_DECISION"}


def test_default_same_section_grooms_append_and_explicit_target_replaces(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, harness: FakeGitHubHarness
) -> None:
    """Default stale writes append, while an explicit entry target still replaces."""
    writer = _RendezvousBackend(harness, tmp_path / "writer-cache")
    reference = _add_item(monkeypatch, writer)
    writer.pause_after_writes(2)
    selected, release_selection = _hold_common_base_selection(monkeypatch)

    failures, threads = _groom_in_threads(
        reference, harness.repo, ("Research", "FIRST_SAME"), ("Research", "SECOND_SAME")
    )
    try:
        assert selected.wait(timeout=5), "both public grooming calls did not select the common base"
        release_selection.set()
        assert writer._queued.wait(timeout=5), "both public grooming calls did not reach the queue"
        pending_entries = _entries(writer.pending_work_items(harness.repo)[0], "research")
        assert {entry.content for entry in pending_entries} == {"FIRST_SAME", "SECOND_SAME"}
        assert len({entry.id for entry in pending_entries}) == 2
    finally:
        release_selection.set()
        _release_and_join(writer, failures, threads)
    reader = harness.new_backend(tmp_path / "reader-cache")
    reader.reconcile(ReconcileRequest(scope=ReconcileScope.TARGETED, repo=harness.repo, references=[reference]))
    first_id = next(
        entry.id for entry in _entries(reader.get_work_item(reference), "research") if entry.content == "FIRST_SAME"
    )

    replacement = _RendezvousBackend(harness, tmp_path / "replacement-cache")
    _use_backend(monkeypatch, replacement)
    replacement.pause_after_writes(1)
    failures: list[BacklogError] = []

    def replace_target() -> None:
        try:
            operations.groom_item(
                reference, section="Research", content="REPLACED", entry_id=first_id, repo=harness.repo
            )
        except BacklogError as error:  # pragma: no cover - raised in the calling assertion
            failures.append(error)

    thread = Thread(target=replace_target)
    thread.start()
    try:
        assert replacement._queued.wait(timeout=5), "targeted replacement did not reach the queue"
        pending = replacement.pending_work_items(harness.repo)
        assert {entry.content for entry in _entries(pending[0], "research")} == {"REPLACED", "SECOND_SAME"}
    finally:
        _release_and_join(replacement, failures, [thread])


def test_regular_full_item_writes_still_replace_pending_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, harness: FakeGitHubHarness
) -> None:
    """The grooming coalescer does not alter ordinary full-item replacement."""
    writer = _RendezvousBackend(harness, tmp_path / "writer-cache")
    reference = _add_item(monkeypatch, writer)
    writer._expected_writes = 0

    first = writer.get_work_item(reference)
    first.description = "FIRST_FULL_WRITE"
    writer.put_work_item(first)
    second = writer.get_work_item(reference)
    second.description = "SECOND_FULL_WRITE"
    writer.put_work_item(second)

    pending = writer.pending_work_items(harness.repo)
    assert len(pending) == 1
    assert pending[0].description == "SECOND_FULL_WRITE"


def test_mark_groomed_keeps_pending_groomed_section(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, harness: FakeGitHubHarness
) -> None:
    """A stale metadata follow-up preserves the preceding pending grooming write."""
    writer = _RendezvousBackend(harness, tmp_path / "writer-cache")
    reference = _add_item(monkeypatch, writer)
    writer.offline = True
    writer._expected_writes = 0

    operations.groom_item(
        reference, section="Research", content="PRESERVE_WITH_STATUS", mark_groomed=True, repo=harness.repo
    )

    pending = writer.pending_work_items(harness.repo)
    assert len(pending) == 1
    assert {entry.content for entry in _entries(pending[0], "research")} == {"PRESERVE_WITH_STATUS"}
    assert pending[0].metadata.status == "groomed"


def test_append_precedes_entry_target_for_public_grooming(monkeypatch: pytest.MonkeyPatch) -> None:
    """append=True preserves the target and adds a new entry through groom_item."""
    backend = InMemoryBackend()
    item = BacklogItem(
        title="Append precedence",
        reference="append-precedence",
        sections={"research": Section(entries=[Entry(id="old", content="OLD")])},
    )
    backend.put_work_item(item)
    monkeypatch.setattr(operations, "get_config", lambda: BacklogConfig(backend=backend))

    operations.groom_item(item.reference, section="Research", content="NEW", entry_id="old", append=True)

    entries = _entries(backend.get_work_item(item.reference), "research")
    assert {entry.content for entry in entries} == {"OLD", "NEW"}
    assert len({entry.id for entry in entries}) == 2


def test_replace_section_precedes_entry_target_for_public_grooming(monkeypatch: pytest.MonkeyPatch) -> None:
    """replace_section=True strikes existing entries and appends a live replacement."""
    backend = InMemoryBackend()
    item = BacklogItem(
        title="Replace precedence",
        reference="replace-precedence",
        sections={"research": Section(entries=[Entry(id="old", content="OLD")])},
    )
    backend.put_work_item(item)
    monkeypatch.setattr(operations, "get_config", lambda: BacklogConfig(backend=backend))

    operations.groom_item(
        item.reference, section="Research", content="NEW", entry_id="old", replace_section=True, reason="superseded"
    )

    entries = _entries(backend.get_work_item(item.reference), "research")
    assert [entry.content for entry in entries if not entry.struck] == ["NEW"]
    assert all(entry.struck for entry in entries if entry.content == "OLD")
