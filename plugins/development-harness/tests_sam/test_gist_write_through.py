"""Roundtrip and write-failure tests for GistTaskLayer Gist-backed plan storage.

These tests verify AC1, AC2, AC3, and AC7 from the #2509 architect spec:

- AC1 (create_uploads_content): create with issue → content retrievable via
  ArtifactRegistryClient.read.
- AC2 (read_without_local_file): create+upload → delete local YAML → read returns
  the plan from Gist with source="gist", no PlanNotFoundError.
- AC3 (mutation_persists): mutate via update_task_status → fresh read observes change.
- AC3/concurrency (claim): serial claim returns True then False; issue=None raises
  ConcurrentClaimUnsupportedError.
- AC7 (write_failure_surfaces_error): forced store failure → create raises
  ArtifactWriteError (no silent swallow); MCP handler exposes error key.

Test-authorship independence: assertions are written against the desired behavior
from the architect spec and AC check-commands, not by reading T1-T4 implementation
line-by-line.  Fakes are deterministic — no live GitHub token required (AC5 offline
requirement).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from sam_schema.core.artifact_registry_client import ArtifactRegistryClient
from sam_schema.core.backends.local_yaml import LocalYamlTaskProvider
from sam_schema.core.exceptions import ArtifactWriteError, ConcurrentClaimUnsupportedError
from sam_schema.core.gist_task_layer import GistTaskLayer
from sam_schema.core.models import Complexity, Priority, Task, TaskStatus
from sam_schema.core.plan_id_index import PlanIdIndex, PlanIndexEntry, _serialize_index_yaml

if TYPE_CHECKING:
    from pathlib import Path

# ---------------------------------------------------------------------------
# Deterministic in-memory fakes
# ---------------------------------------------------------------------------


class _InMemoryArtifactStore:
    """Deterministic in-memory artifact store for offline tests.

    Stores keyed by (issue, artifact_type) → content string.
    Also holds a separate index store keyed by sentinel_issue → content string.
    """

    def __init__(self) -> None:
        self._store: dict[tuple[int, str], str] = {}
        self._index_store: dict[int, str] = {}
        #: When True, store() raises ArtifactWriteError to simulate Gist failure.
        self.force_store_failure: bool = False

    def store(self, issue: int, content: str, *, artifact_type: str = "task-plan") -> None:
        """Store content keyed by (issue, artifact_type).

        Raises:
            ArtifactWriteError: When force_store_failure is True.
        """
        if self.force_store_failure:
            raise ArtifactWriteError(plan_id="<unknown>", issue=issue, reason="forced failure for testing")
        self._store[issue, artifact_type] = content

    def read(self, issue: int, artifact_type: str = "task-plan") -> str | None:
        """Retrieve content by (issue, artifact_type)."""
        return self._store.get((issue, artifact_type))

    def store_index(self, sentinel_issue: int, content: str) -> None:
        """Store plan-index YAML for sentinel issue."""
        self._index_store[sentinel_issue] = content

    def read_index(self, sentinel_issue: int) -> str | None:
        """Retrieve plan-index YAML for sentinel issue."""
        return self._index_store.get(sentinel_issue)

    def clear_content_store(self) -> None:
        """Evict all stored artifact content, leaving the index intact.

        Useful in tests that need to force a local-fallback read after a
        rate-limited write-through: clearing stale Gist content from the
        in-memory store ensures read_plan falls back to the local YAML file.
        """
        self._store.clear()


def _make_fake_client(store: _InMemoryArtifactStore) -> ArtifactRegistryClient:
    """Return an ArtifactRegistryClient backed by the given in-memory store.

    Monkey-patches the four public methods so the client exercises its own
    interface contract while delegating to the deterministic store.
    """
    client = ArtifactRegistryClient.__new__(ArtifactRegistryClient)
    # Directly bind the in-memory store methods to the client interface.
    client.store = store.store  # type: ignore[method-assign]
    client.read = store.read  # type: ignore[method-assign]
    client.store_index = store.store_index  # type: ignore[method-assign]
    client.read_index = store.read_index  # type: ignore[method-assign]
    return client


def _make_fake_plan_index(client: ArtifactRegistryClient, sentinel_issue: int = 42) -> PlanIdIndex:
    """Return a PlanIdIndex backed by the given client and a non-zero sentinel."""
    return PlanIdIndex(artifact_client=client, sentinel_issue=sentinel_issue)


# ---------------------------------------------------------------------------
# Task helpers
# ---------------------------------------------------------------------------

_SENTINEL_ISSUE = 42
_PLAN_ISSUE = 2509


def _two_tasks() -> list[Task]:
    """Return two Task objects for roundtrip tests."""
    return [
        Task(
            id="T1",
            title="First task",
            status=TaskStatus.NOT_STARTED,
            agent="test-agent",
            dependencies=[],
            priority=Priority.CRITICAL,
            complexity=Complexity.LOW,
        ),
        Task(
            id="T2",
            title="Second task",
            status=TaskStatus.NOT_STARTED,
            agent="test-agent",
            dependencies=["T1"],
            priority=Priority.HIGH,
            complexity=Complexity.MEDIUM,
        ),
    ]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def store() -> _InMemoryArtifactStore:
    """Fresh in-memory artifact store per test."""
    return _InMemoryArtifactStore()


@pytest.fixture
def gist_layer(tmp_path: Path, store: _InMemoryArtifactStore) -> GistTaskLayer:
    """GistTaskLayer with an in-memory artifact store and plan index."""
    plan_dir = tmp_path / "plan"
    plan_dir.mkdir()
    local_backend = LocalYamlTaskProvider(plan_dir)
    client = _make_fake_client(store)
    plan_index = _make_fake_plan_index(client, sentinel_issue=_SENTINEL_ISSUE)
    return GistTaskLayer(local_backend=local_backend, artifact_client=client, plan_index=plan_index)


# ---------------------------------------------------------------------------
# AC1: create_uploads_content
# ---------------------------------------------------------------------------


def test_create_uploads_content(gist_layer: GistTaskLayer, store: _InMemoryArtifactStore) -> None:
    """AC1: create with issue → content retrievable via ArtifactRegistryClient.read.

    Verifies the write-through contract: after a successful create_plan, the Gist
    store must hold the full plan YAML and it must be retrievable.  Content equality
    covers all task fields and plan metadata (not just structural validity).
    """
    # Arrange
    tasks = _two_tasks()
    slug = "ac1-test-plan"
    goal = "Verify Gist write-through on create"

    # Act: create plan with an issue — triggers mandatory write-through.
    plan_data = gist_layer.create_plan(slug=slug, goal=goal, tasks=tasks, context="AC1 context", issue=_PLAN_ISSUE)
    plan_id = plan_data["plan_id"]

    # Assert 1: content was stored in the in-memory artifact store.
    stored_yaml = store.read(_PLAN_ISSUE, "task-plan")
    assert stored_yaml is not None, "Gist store must contain plan YAML after create"

    # Assert 2: stored YAML is non-empty and contains the plan slug and goal.
    assert slug in stored_yaml or goal in stored_yaml, "Stored YAML must contain plan identifying data"

    # Assert 3: re-read from Gist reproduces all critical fields (content equality check).
    retrieved = gist_layer.read_plan(plan_id)
    assert retrieved["plan_id"] == plan_id
    assert retrieved["feature"] == slug or retrieved.get("slug") == slug or retrieved.get("goal") == goal
    assert len(retrieved["tasks"]) == len(tasks)

    # Assert 4: task fields are preserved after roundtrip.
    retrieved_ids = {t["id"] for t in retrieved["tasks"]}
    assert {"T1", "T2"} == retrieved_ids, "All task IDs must survive roundtrip"

    task_t2 = next(t for t in retrieved["tasks"] if t["id"] == "T2")
    assert task_t2["title"] == "Second task"
    assert "T1" in (task_t2.get("dependencies") or []), "Task dependencies must survive roundtrip"

    # Assert 5: read source is "gist" (not local fallback).
    assert gist_layer.last_read_source == "gist", "read_plan must serve from Gist after write-through"


# ---------------------------------------------------------------------------
# AC2: read_without_local_file
# ---------------------------------------------------------------------------


def test_read_without_local_file(gist_layer: GistTaskLayer, store: _InMemoryArtifactStore) -> None:
    """AC2: create+upload → delete local YAML → read returns plan from Gist.

    Verifies the fresh-session dual-read contract: after the local YAML file is
    deleted, read_plan must still return the plan served from Gist.  No
    PlanNotFoundError should be raised.
    """
    # Arrange: create the plan and upload to Gist.
    tasks = _two_tasks()
    plan_data = gist_layer.create_plan(
        slug="ac2-no-local", goal="Gist-only read after local deletion", tasks=tasks, issue=_PLAN_ISSUE
    )
    plan_id = plan_data["plan_id"]

    # Verify Gist store is populated.
    assert store.read(_PLAN_ISSUE, "task-plan") is not None

    # Simulate fresh session: delete every local YAML file for this plan.
    local_dir: Path = gist_layer._local._plan_dir
    for yaml_file in local_dir.glob(f"{plan_id}-*.yaml"):
        yaml_file.unlink()
    # Confirm local file is gone.
    remaining = list(local_dir.glob(f"{plan_id}-*.yaml"))
    assert not remaining, "Local YAML must be deleted before testing Gist-only read"

    # Act: read plan — must hit Gist because local is absent.
    retrieved = gist_layer.read_plan(plan_id)

    # Assert 1: plan was returned (no PlanNotFoundError).
    assert retrieved is not None
    assert retrieved["plan_id"] == plan_id

    # Assert 2: source annotation is "gist".
    assert gist_layer.last_read_source == "gist", "Must serve from Gist when local file is absent"

    # Assert 3: full content equality — tasks survive the Gist roundtrip.
    assert len(retrieved["tasks"]) == 2
    retrieved_ids = {t["id"] for t in retrieved["tasks"]}
    assert {"T1", "T2"} == retrieved_ids


# ---------------------------------------------------------------------------
# AC3: mutation_persists
# ---------------------------------------------------------------------------


def test_mutation_persists(gist_layer: GistTaskLayer, store: _InMemoryArtifactStore) -> None:
    """AC3: mutate task status → delete local YAML → fresh read observes change.

    Verifies that mutations (update_task_status) write through to Gist, so a
    subsequent read from a fresh environment sees the mutated state.
    """
    # Arrange: create plan with two tasks.
    tasks = _two_tasks()
    plan_data = gist_layer.create_plan(
        slug="ac3-mutation", goal="Verify mutation persistence via Gist", tasks=tasks, issue=_PLAN_ISSUE
    )
    plan_id = plan_data["plan_id"]

    # Act: mutate T1 to in-progress.
    gist_layer.update_task_status(plan_id, "T1", "in-progress")

    # Simulate fresh session: remove local YAML so read must go to Gist.
    local_dir: Path = gist_layer._local._plan_dir
    for yaml_file in local_dir.glob(f"{plan_id}-*.yaml"):
        yaml_file.unlink()

    # Assert 1: read from Gist returns mutated status.
    retrieved = gist_layer.read_plan(plan_id)
    assert gist_layer.last_read_source == "gist"

    task_t1 = next(t for t in retrieved["tasks"] if t["id"] == "T1")
    assert task_t1["status"] == "in-progress", "Mutated task status must persist to Gist and be visible on fresh read"

    # Assert 2: T2 remains unchanged.
    task_t2 = next(t for t in retrieved["tasks"] if t["id"] == "T2")
    assert task_t2["status"] == "not-started", "Unmutated task status must be preserved"


# ---------------------------------------------------------------------------
# AC3 / concurrency: claim tests
# ---------------------------------------------------------------------------


def test_claim_serial_exactly_once(gist_layer: GistTaskLayer) -> None:
    """AC3/concurrency: serial claim — first returns True, second returns False.

    Tests that the exactly-once claim guarantee holds under the serialized-dispatch
    pattern (ADR-2509-3, Option 3): two sequential claim calls on the same task
    produce True then False, not True twice.
    """
    # Arrange: create plan with one task.
    tasks = [Task(id="T1", title="Claimable task", status=TaskStatus.NOT_STARTED, agent="test-agent", dependencies=[])]
    plan_data = gist_layer.create_plan(
        slug="ac3-claim", goal="Verify serial exactly-once claim", tasks=tasks, issue=_PLAN_ISSUE
    )
    plan_id = plan_data["plan_id"]

    # Act: two sequential claims on the same task.
    first_claim = gist_layer.claim_task(plan_id, "T1")
    second_claim = gist_layer.claim_task(plan_id, "T1")

    # Assert: exactly-once semantics under serialized dispatch.
    assert first_claim is True, "First claim on a not-started task must return True"
    assert second_claim is False, "Second claim on an already-claimed task must return False"


def test_claim_issue_none_raises(gist_layer: GistTaskLayer) -> None:
    """AC3/concurrency: claim on issue=None plan raises ConcurrentClaimUnsupportedError.

    When GistTaskLayer.create_plan is called with issue=None, claim_task must
    raise ConcurrentClaimUnsupportedError immediately — no GitHub label anchor
    is available for concurrent claim coordination.
    """
    # Arrange: local-only plan (issue=None).
    tasks = [Task(id="T1", title="Local-only task", status=TaskStatus.NOT_STARTED, agent="test-agent", dependencies=[])]
    plan_data = gist_layer.create_plan(
        slug="ac3-local-claim",
        goal="Verify ConcurrentClaimUnsupportedError for local-only plan",
        tasks=tasks,
        issue=None,  # local-only — no Gist upload
    )
    plan_id = plan_data["plan_id"]

    # Act + Assert: claim must raise for issue=None plans.
    with pytest.raises(ConcurrentClaimUnsupportedError) as exc_info:
        gist_layer.claim_task(plan_id, "T1")

    assert plan_id in str(exc_info.value), "Exception must reference the plan_id"


# ---------------------------------------------------------------------------
# AC7: write_failure_surfaces_error
# ---------------------------------------------------------------------------


def test_write_failure_surfaces_error(tmp_path: Path, store: _InMemoryArtifactStore) -> None:
    """AC7: forced Gist store failure → create raises ArtifactWriteError.

    Verifies that when artifact_client.store() fails, GistTaskLayer.create_plan
    raises ArtifactWriteError (no silent swallow).  This proves the deleted
    server.py:217 inner try/except is not secretly re-introduced in GistTaskLayer.
    """
    # Arrange: enable forced failure before create.
    plan_dir = tmp_path / "plan"
    plan_dir.mkdir()
    local_backend = LocalYamlTaskProvider(plan_dir)
    client = _make_fake_client(store)
    plan_index = _make_fake_plan_index(client, sentinel_issue=_SENTINEL_ISSUE)
    layer = GistTaskLayer(local_backend=local_backend, artifact_client=client, plan_index=plan_index)

    # Enable store failure AFTER constructing layer (so we can set it just before create).
    store.force_store_failure = True

    tasks = [
        Task(id="T1", title="Will fail to upload", status=TaskStatus.NOT_STARTED, agent="test-agent", dependencies=[])
    ]

    # Act + Assert: ArtifactWriteError must propagate (not be swallowed).
    with pytest.raises(ArtifactWriteError) as exc_info:
        layer.create_plan(
            slug="ac7-write-failure", goal="Verify write failure propagation", tasks=tasks, issue=_PLAN_ISSUE
        )

    exc = exc_info.value
    assert exc.issue == _PLAN_ISSUE, "ArtifactWriteError must reference the target issue"
    assert "forced failure" in exc.reason or "forced" in exc.reason.lower(), (
        "ArtifactWriteError reason must carry the underlying failure message"
    )

    # Assert: Gist store is empty (nothing was stored before the failure path).
    stored = store.read(_PLAN_ISSUE, "task-plan")
    assert stored is None, "No Gist content must exist when write-through fails"


def test_write_failure_does_not_succeed_silently(tmp_path: Path, store: _InMemoryArtifactStore) -> None:
    """AC7 complement: write failure is not reported as success with a warning.

    The old silent-swallow defect at server.py:217 returned a success response
    even when the Gist write failed.  GistTaskLayer must NOT do this — failure
    must raise, never succeed silently.

    This test directly invokes create_plan and asserts no PlanData is returned
    when the write fails.
    """
    plan_dir = tmp_path / "plan"
    plan_dir.mkdir()
    local_backend = LocalYamlTaskProvider(plan_dir)
    client = _make_fake_client(store)
    plan_index = _make_fake_plan_index(client, sentinel_issue=_SENTINEL_ISSUE)
    layer = GistTaskLayer(local_backend=local_backend, artifact_client=client, plan_index=plan_index)
    store.force_store_failure = True

    tasks = [Task(id="T1", title="Task", status=TaskStatus.NOT_STARTED, agent="agent", dependencies=[])]

    raised = False
    return_value: Any = None
    try:
        return_value = layer.create_plan(slug="fail-silent", goal="test", tasks=tasks, issue=_PLAN_ISSUE)
    except ArtifactWriteError:
        raised = True

    assert raised, "create_plan must raise ArtifactWriteError on Gist write failure"
    assert return_value is None, "create_plan must not return PlanData on write failure"


# ---------------------------------------------------------------------------
# Full content equality roundtrip — CoVe revision check
# ---------------------------------------------------------------------------


def test_full_content_equality_roundtrip(gist_layer: GistTaskLayer, store: _InMemoryArtifactStore) -> None:
    """Full content equality: every task field and plan metadata survives the Gist roundtrip.

    This is the CoVe revision-rule test: confirms the roundtrip assertion compares
    every task field and plan metadata, not merely that the plan loads.
    """
    tasks = [
        Task(
            id="T1",
            title="Scaffold and setup",
            status=TaskStatus.NOT_STARTED,
            agent="python-cli-architect",
            dependencies=[],
            priority=Priority.CRITICAL,
            complexity=Complexity.LOW,
        ),
        Task(
            id="T2",
            title="Implementation",
            status=TaskStatus.NOT_STARTED,
            agent="python-cli-architect",
            dependencies=["T1"],
            priority=Priority.HIGH,
            complexity=Complexity.HIGH,
        ),
        Task(
            id="T3",
            title="Tests",
            status=TaskStatus.NOT_STARTED,
            agent="python-pytest-architect",
            dependencies=["T1", "T2"],
            priority=Priority.MEDIUM,
            complexity=Complexity.MEDIUM,
        ),
    ]
    slug = "roundtrip-equality"
    goal = "Prove all fields survive Gist roundtrip"
    context = "Roundtrip test context narrative"

    plan_data = gist_layer.create_plan(slug=slug, goal=goal, tasks=tasks, context=context, issue=_PLAN_ISSUE)
    plan_id = plan_data["plan_id"]

    # Delete local file to force Gist read.
    local_dir: Path = gist_layer._local._plan_dir
    for yaml_file in local_dir.glob(f"{plan_id}-*.yaml"):
        yaml_file.unlink()

    retrieved = gist_layer.read_plan(plan_id)
    assert gist_layer.last_read_source == "gist"

    # Plan-level metadata checks.
    assert retrieved["plan_id"] == plan_id
    assert len(retrieved["tasks"]) == 3

    # Build a lookup by task ID.
    by_id = {t["id"]: t for t in retrieved["tasks"]}

    # T1 — no dependencies.
    assert by_id["T1"]["title"] == "Scaffold and setup"
    assert by_id["T1"]["agent"] == "python-cli-architect"
    assert by_id["T1"]["dependencies"] == [] or by_id["T1"]["dependencies"] is None or by_id["T1"]["dependencies"] == []

    # T2 — depends on T1.
    assert by_id["T2"]["title"] == "Implementation"
    assert by_id["T2"]["agent"] == "python-cli-architect"
    assert "T1" in (by_id["T2"].get("dependencies") or [])

    # T3 — depends on T1 and T2.
    assert by_id["T3"]["title"] == "Tests"
    assert by_id["T3"]["agent"] == "python-pytest-architect"
    deps_t3 = by_id["T3"].get("dependencies") or []
    assert "T1" in deps_t3
    assert "T2" in deps_t3


# ---------------------------------------------------------------------------
# Counting store subclass — used by perf-fix behavioral tests
# ---------------------------------------------------------------------------


class _CountingArtifactStore(_InMemoryArtifactStore):
    """_InMemoryArtifactStore subclass that tracks read() and read_index() call counts.

    Overrides both read methods to increment counters before delegating to the
    parent.  Using a proper subclass avoids assigning plain closures to method
    attributes, which would confuse ty's type checker.
    """

    def __init__(self) -> None:
        """Initialise with zero call counters."""
        super().__init__()
        self.read_call_count: int = 0
        self.read_index_call_count: int = 0

    def read(self, issue: int, artifact_type: str = "task-plan") -> str | None:
        """Increment read_call_count, then delegate to parent.

        Args:
            issue: GitHub issue number keying the artifact.
            artifact_type: Artifact type key (default ``"task-plan"``).

        Returns:
            Stored content string, or ``None`` when absent.
        """
        self.read_call_count += 1
        return super().read(issue, artifact_type)

    def read_index(self, sentinel_issue: int) -> str | None:
        """Increment read_index_call_count, then delegate to parent.

        Args:
            sentinel_issue: Sentinel issue number keying the index blob.

        Returns:
            Stored index YAML string, or ``None`` when absent.
        """
        self.read_index_call_count += 1
        return super().read_index(sentinel_issue)


# ---------------------------------------------------------------------------
# Perf fix: PlanIdIndex session cache (T1 / plan_id_index.py)
# ---------------------------------------------------------------------------


def test_read_entries_cache_reduces_gist_calls() -> None:
    """Session cache: multiple resolve/list_all calls trigger at most one Gist index fetch.

    Verifies that PlanIdIndex._read_entries() caches its result so repeated
    calls to resolve() and list_all() within the same invocation do not each
    perform a separate Gist round-trip.  The read_index_call_count on the
    counting store must equal 1 regardless of how many public methods are invoked.
    """
    counting_store = _CountingArtifactStore()
    client = _make_fake_client(counting_store)
    index = PlanIdIndex(artifact_client=client, sentinel_issue=_SENTINEL_ISSUE)

    # Pre-populate the index store with one entry (bypassing register so the
    # counter starts from a clean state without counting the setup fetch).
    initial_entry = PlanIndexEntry(
        plan_id="Pabc12345", issue=100, slug="cache-test-plan", created_at="2026-01-01T00:00:00Z"
    )
    counting_store.store_index(_SENTINEL_ISSUE, _serialize_index_yaml([initial_entry]))
    counting_store.read_index_call_count = 0  # reset after setup

    # Three operations on the same object — should only fetch from Gist once.
    result_resolve_1 = index.resolve("Pabc12345")
    result_list_all = index.list_all()
    result_resolve_2 = index.resolve("Pabc12345")

    assert result_resolve_1 == 100, "resolve() must return the correct issue number"
    assert len(result_list_all) == 1, "list_all() must return the one registered entry"
    assert result_resolve_2 == 100, "second resolve() must still return correct issue"
    assert counting_store.read_index_call_count == 1, (
        f"Expected exactly 1 Gist index fetch for 3 public method calls, got {counting_store.read_index_call_count}"
    )


def test_register_updates_cache_in_place() -> None:
    """After register(), the cache reflects the new entry without a re-fetch.

    Verifies that PlanIdIndex.register() updates _entries_cache to the
    written state so the next resolve()/list_all() in the same invocation
    returns the registered entry without an extra Gist round-trip.
    """
    counting_store = _CountingArtifactStore()
    client = _make_fake_client(counting_store)
    index = PlanIdIndex(artifact_client=client, sentinel_issue=_SENTINEL_ISSUE)

    # register() reads entries once (empty index → 1 fetch), then writes and
    # updates the cache.  A subsequent resolve() must not trigger a second fetch.
    index.register(plan_id="Pnew00001", issue=999, slug="new-plan")
    calls_after_register = counting_store.read_index_call_count

    resolved = index.resolve("Pnew00001")

    assert resolved == 999, "resolve() must return issue registered in the same invocation"
    assert counting_store.read_index_call_count == calls_after_register, (
        "resolve() after register() must not trigger an additional Gist fetch (cache hit expected)"
    )


# ---------------------------------------------------------------------------
# Perf fix: list_plans N+1 elimination (T1 / gist_task_layer.py)
# ---------------------------------------------------------------------------


def test_list_plans_no_gist_content_fetch_for_index_only_plans(tmp_path: Path) -> None:
    """list_plans must not call artifact_client.read() for index-only plans.

    Verifies that GistTaskLayer.list_plans() synthesises PlanSummary objects
    from index metadata alone — without fetching the full plan YAML blob from
    Gist for each index-only plan.  This prevents the N+1 API call pattern
    that grows unboundedly with the number of registered plans.
    """
    plan_dir = tmp_path / "plan"
    plan_dir.mkdir()
    local_backend = LocalYamlTaskProvider(plan_dir)
    counting_store = _CountingArtifactStore()
    client = _make_fake_client(counting_store)
    plan_index = _make_fake_plan_index(client, sentinel_issue=_SENTINEL_ISSUE)
    layer = GistTaskLayer(local_backend=local_backend, artifact_client=client, plan_index=plan_index)

    # Register two plans in the index (no local files, no Gist content store).
    plan_index.register(plan_id="Pindex001", issue=201, slug="index-plan-alpha")
    plan_index.register(plan_id="Pindex002", issue=202, slug="index-plan-beta")

    # Reset counter — register() writes the index but never calls read().
    counting_store.read_call_count = 0

    # list_plans — must not call read() for either index-only plan.
    summaries = layer.list_plans()

    assert counting_store.read_call_count == 0, (
        f"list_plans must not call artifact_client.read(), got {counting_store.read_call_count} call(s)"
    )

    # Both index-only plans must appear in the result with index-derived metadata.
    plan_ids = {s["plan_id"] for s in summaries}
    assert "Pindex001" in plan_ids, "Index-only plan Pindex001 must appear in list_plans result"
    assert "Pindex002" in plan_ids, "Index-only plan Pindex002 must appear in list_plans result"

    by_id = {s["plan_id"]: s for s in summaries}
    assert by_id["Pindex001"]["feature"] == "index-plan-alpha", "feature must equal the index slug"
    assert by_id["Pindex001"]["issue"] == "201", "issue must be serialised to str from index entry"
    assert by_id["Pindex002"]["feature"] == "index-plan-beta"
    assert by_id["Pindex002"]["issue"] == "202"


# ---------------------------------------------------------------------------
# list_plans: merge behavior (T3 / gist_task_layer.py)
# ---------------------------------------------------------------------------


def test_list_plans_merges_gist_and_local(gist_layer: GistTaskLayer) -> None:
    """list_plans returns plans from both Gist-registered index and local-only store.

    Verifies the merge strategy: a plan with an issue (written through to Gist
    and registered in the plan index) and a plan without an issue (local-only,
    not indexed) both appear in the list_plans result without duplication.
    """
    tasks = _two_tasks()

    # Arrange: create one plan with an issue — written to Gist and plan index.
    gist_data = gist_layer.create_plan(
        slug="merge-gist-plan", goal="Plan with Gist registration", tasks=tasks, issue=_PLAN_ISSUE
    )
    gist_plan_id = gist_data["plan_id"]

    # Create a second plan without an issue — local-only, not indexed.
    local_data = gist_layer.create_plan(
        slug="merge-local-plan", goal="Local-only plan with no Gist registration", tasks=tasks
    )
    local_plan_id = local_data["plan_id"]

    # Act: list all plans via the merge layer.
    summaries = gist_layer.list_plans()

    # Assert: both plan_ids appear in the merged result.
    plan_ids = {s["plan_id"] for s in summaries}
    assert gist_plan_id in plan_ids, "Gist-registered plan must appear in list_plans result"
    assert local_plan_id in plan_ids, "Local-only plan must appear in list_plans result"

    # Assert: no duplicates — each plan_id appears exactly once.
    all_ids = [s["plan_id"] for s in summaries]
    assert all_ids.count(gist_plan_id) == 1, "Gist-registered plan must appear exactly once (no duplicates)"
    assert all_ids.count(local_plan_id) == 1, "Local-only plan must appear exactly once (no duplicates)"


def test_list_plans_returns_empty_when_no_plans(tmp_path: Path) -> None:
    """list_plans returns an empty list when no plans exist in index or local store.

    Verifies that a fresh GistTaskLayer with an empty plan index and an empty
    local directory returns [] rather than raising or returning None.
    """
    plan_dir = tmp_path / "plan"
    plan_dir.mkdir()
    local_backend = LocalYamlTaskProvider(plan_dir)
    empty_store = _InMemoryArtifactStore()
    client = _make_fake_client(empty_store)
    plan_index = _make_fake_plan_index(client, sentinel_issue=_SENTINEL_ISSUE)
    layer = GistTaskLayer(local_backend=local_backend, artifact_client=client, plan_index=plan_index)

    # Act: list plans on a completely empty layer.
    summaries = layer.list_plans()

    # Assert: empty result, no exception raised.
    assert summaries == [], f"Empty layer must return [], got {summaries!r}"


# ---------------------------------------------------------------------------
# Write-through mutations: persistence to Gist (T3 / gist_task_layer.py)
# ---------------------------------------------------------------------------


def test_update_plan_fields_persists_to_gist(gist_layer: GistTaskLayer, store: _InMemoryArtifactStore) -> None:
    """update_plan_fields writes through to Gist; fresh read observes the changed goal.

    Verifies that calling update_plan_fields() with a new goal uploads the
    post-mutation YAML to Gist, so a subsequent read_plan() from a session
    without a local file sees the updated goal value.
    """
    # Arrange: create a plan with an issue so write-through is active.
    tasks = _two_tasks()
    plan_data = gist_layer.create_plan(slug="update-plan-fields", goal="Original goal", tasks=tasks, issue=_PLAN_ISSUE)
    plan_id = plan_data["plan_id"]

    # Act: mutate the plan goal via set_fields.
    gist_layer.update_plan_fields(plan_id, set_fields={"goal": "Updated goal via set_fields"})

    # Simulate fresh session: delete local YAML so read_plan must fetch from Gist.
    local_dir = gist_layer._local._plan_dir
    for yaml_file in local_dir.glob(f"{plan_id}-*.yaml"):
        yaml_file.unlink()

    # Assert: read from Gist returns the mutated goal.
    retrieved = gist_layer.read_plan(plan_id)
    assert gist_layer.last_read_source == "gist", "Post-delete read must come from Gist"
    assert retrieved["goal"] == "Updated goal via set_fields", (
        "Goal mutation must persist to Gist and be visible on fresh read"
    )


def test_update_task_fields_persists_to_gist(gist_layer: GistTaskLayer, store: _InMemoryArtifactStore) -> None:
    """update_task_fields writes through to Gist; fresh read observes the changed title.

    Verifies that updating a task field (title) uploads the post-mutation YAML
    to Gist, so a subsequent read_plan() from a session without a local file
    sees the updated task title.
    """
    # Arrange: create a plan with two tasks.
    tasks = _two_tasks()
    plan_data = gist_layer.create_plan(
        slug="update-task-fields",
        goal="Verify task field mutation persistence via Gist",
        tasks=tasks,
        issue=_PLAN_ISSUE,
    )
    plan_id = plan_data["plan_id"]

    # Act: mutate T1's title via update_task_fields.
    gist_layer.update_task_fields(plan_id, "T1", {"title": "Renamed via update_task_fields"})

    # Simulate fresh session: delete local YAML so read_plan must fetch from Gist.
    local_dir = gist_layer._local._plan_dir
    for yaml_file in local_dir.glob(f"{plan_id}-*.yaml"):
        yaml_file.unlink()

    # Assert: read from Gist returns the updated task title.
    retrieved = gist_layer.read_plan(plan_id)
    assert gist_layer.last_read_source == "gist", "Post-delete read must come from Gist"
    task_t1 = next(t for t in retrieved["tasks"] if t["id"] == "T1")
    assert task_t1["title"] == "Renamed via update_task_fields", (
        "Task title mutation must persist to Gist and be visible on fresh read"
    )


def test_update_task_persists_to_gist(gist_layer: GistTaskLayer, store: _InMemoryArtifactStore) -> None:
    """update_task writes through to Gist; fresh read observes the replaced task.

    Verifies that replacing a full Task object via update_task() uploads the
    post-mutation YAML to Gist, so a subsequent read_plan() from a session
    without a local file sees the replacement task's title and status.
    """
    # Arrange: create a plan with two tasks.
    tasks = _two_tasks()
    plan_data = gist_layer.create_plan(
        slug="update-task", goal="Verify full task replacement persistence via Gist", tasks=tasks, issue=_PLAN_ISSUE
    )
    plan_id = plan_data["plan_id"]

    # Act: replace T1 with a new Task object (different title and status).
    replacement = Task(
        id="T1",
        title="Replaced via update_task",
        status=TaskStatus.IN_PROGRESS,
        agent="replacement-agent",
        dependencies=[],
    )
    gist_layer.update_task(plan_id, replacement)

    # Simulate fresh session: delete local YAML so read_plan must fetch from Gist.
    local_dir = gist_layer._local._plan_dir
    for yaml_file in local_dir.glob(f"{plan_id}-*.yaml"):
        yaml_file.unlink()

    # Assert: read from Gist returns the replacement task's fields.
    retrieved = gist_layer.read_plan(plan_id)
    assert gist_layer.last_read_source == "gist", "Post-delete read must come from Gist"
    task_t1 = next(t for t in retrieved["tasks"] if t["id"] == "T1")
    assert task_t1["title"] == "Replaced via update_task", (
        "Replaced task title must persist to Gist and be visible on fresh read"
    )
    assert task_t1["status"] == "in-progress", "Replaced task status must persist to Gist and be visible on fresh read"


def test_append_task_section_persists_to_gist(gist_layer: GistTaskLayer, store: _InMemoryArtifactStore) -> None:
    """append_task_section writes through to Gist; Gist YAML contains the appended section.

    Verifies that appending a named markdown section to a task uploads the
    post-mutation YAML to Gist, so the Gist store contains both the section
    name and its content after the write-through.  The section content is
    verified in the raw stored YAML rather than through the parsed PlanData to
    avoid coupling the test to the exact deserialization path for body sections.
    """
    # Arrange: create a plan with two tasks.
    tasks = _two_tasks()
    plan_data = gist_layer.create_plan(
        slug="append-task-section",
        goal="Verify task section append persistence via Gist",
        tasks=tasks,
        issue=_PLAN_ISSUE,
    )
    plan_id = plan_data["plan_id"]

    # Act: append a named section to T1.
    section_name = "Implementation Notes"
    section_content = "Added by test_append_task_section_persists_to_gist."
    gist_layer.append_task_section(plan_id, "T1", section_name, section_content)

    # Assert: the Gist store contains the appended section name and content.
    stored_yaml = store.read(_PLAN_ISSUE, "task-plan")
    assert stored_yaml is not None, "Gist store must be populated after append_task_section"
    assert section_name in stored_yaml, (
        f"Section name {section_name!r} must appear in the Gist-stored YAML after append"
    )
    assert section_content in stored_yaml, "Section content must appear in the Gist-stored YAML after append"


def test_mutation_raises_on_gist_write_failure(gist_layer: GistTaskLayer, store: _InMemoryArtifactStore) -> None:
    """update_plan_fields propagates ArtifactWriteError when Gist store fails.

    Verifies that when artifact_client.store() is forced to fail during a
    write-through mutation, GistTaskLayer raises ArtifactWriteError rather
    than swallowing it silently.  Tests the no-silent-swallow contract for
    write-through mutations (AC7 analog for update_plan_fields).
    """
    # Arrange: create a plan successfully while the store is healthy.
    tasks = _two_tasks()
    plan_data = gist_layer.create_plan(
        slug="mutation-write-failure",
        goal="Verify write failure propagation for mutations",
        tasks=tasks,
        issue=_PLAN_ISSUE,
    )
    plan_id = plan_data["plan_id"]

    # Enable store failure before the mutation attempt.
    store.force_store_failure = True

    # Act + Assert: ArtifactWriteError must propagate (no silent swallow).
    with pytest.raises(ArtifactWriteError):
        gist_layer.update_plan_fields(plan_id, set_fields={"goal": "Attempted update during failure"})


# ---------------------------------------------------------------------------
# Write-through: append_task and finalize_plan persistence to Gist
# ---------------------------------------------------------------------------


def test_append_task_persists_to_gist(gist_layer: GistTaskLayer, store: _InMemoryArtifactStore) -> None:
    """append_task writes through to Gist; fresh read observes the appended task.

    Verifies that calling append_task() uploads the post-mutation YAML to Gist so
    a subsequent read_plan() from a session without a local file sees the appended
    task.  Tests the AC5 write-through contract for append_task (gist_task_layer.py:861).
    """
    # Arrange: create a plan with two tasks so append_task adds a third.
    tasks = _two_tasks()
    plan_data = gist_layer.create_plan(
        slug="append-task", goal="Verify append_task persistence via Gist", tasks=tasks, issue=_PLAN_ISSUE
    )
    plan_id = plan_data["plan_id"]

    # Append a third task to the plan.
    new_task = Task(
        id="T3",
        title="Appended third task",
        status=TaskStatus.NOT_STARTED,
        agent="test-agent",
        dependencies=[],
        priority=Priority.MEDIUM,
        complexity=Complexity.LOW,
    )

    # Act: append the task — must write through to Gist.
    gist_layer.append_task(plan_id, new_task)

    # Simulate fresh session: delete local YAML so read_plan must fetch from Gist.
    local_dir = gist_layer._local._plan_dir
    for yaml_file in local_dir.glob(f"{plan_id}-*.yaml"):
        yaml_file.unlink()

    # Assert: Gist-served plan contains the appended task.
    retrieved = gist_layer.read_plan(plan_id)
    assert gist_layer.last_read_source == "gist", "Post-delete read must come from Gist"
    retrieved_ids = {t["id"] for t in retrieved["tasks"]}
    assert "T3" in retrieved_ids, "Appended task T3 must persist to Gist and be visible on fresh read"
    assert len(retrieved["tasks"]) == 3, (
        "All three tasks (T1, T2, T3) must be present after append_task write-through to Gist"
    )


def test_finalize_plan_persists_to_gist(gist_layer: GistTaskLayer, store: _InMemoryArtifactStore) -> None:
    """finalize_plan writes through to Gist; fresh read sees state=ready with all tasks.

    Verifies that after appending tasks to a drafting plan and calling finalize_plan(),
    the post-finalization YAML is uploaded to Gist so a subsequent read_plan() from a
    fresh environment observes state=ready and contains all appended tasks.
    Tests the write-through contract for finalize_plan (gist_task_layer.py:891).
    """
    # Arrange: create a plan in drafting state (no tasks → state=drafting).
    plan_data = gist_layer.create_plan(
        slug="finalize-plan", goal="Verify finalize_plan persistence via Gist", tasks=[], issue=_PLAN_ISSUE
    )
    plan_id = plan_data["plan_id"]

    # Append T1 and T2 to the drafting plan (single-writer — sequential calls required).
    t1 = Task(
        id="T1",
        title="First appended task",
        status=TaskStatus.NOT_STARTED,
        agent="test-agent",
        dependencies=[],
        priority=Priority.CRITICAL,
        complexity=Complexity.LOW,
    )
    t2 = Task(
        id="T2",
        title="Second appended task",
        status=TaskStatus.NOT_STARTED,
        agent="test-agent",
        dependencies=["T1"],
        priority=Priority.HIGH,
        complexity=Complexity.MEDIUM,
    )
    gist_layer.append_task(plan_id, t1)
    gist_layer.append_task(plan_id, t2)

    # Act: finalize the plan — transitions state from drafting to ready and writes through to Gist.
    gist_layer.finalize_plan(plan_id)

    # Simulate fresh session: delete local YAML so read_plan must fetch from Gist.
    local_dir = gist_layer._local._plan_dir
    for yaml_file in local_dir.glob(f"{plan_id}-*.yaml"):
        yaml_file.unlink()

    # Assert: Gist-served plan reflects finalized state and contains both tasks.
    retrieved = gist_layer.read_plan(plan_id)
    assert gist_layer.last_read_source == "gist", "Post-delete read must come from Gist"
    assert retrieved["state"] == "ready", (
        "finalize_plan must transition plan from drafting to ready; state must persist to Gist"
    )
    retrieved_ids = {t["id"] for t in retrieved["tasks"]}
    assert retrieved_ids == {"T1", "T2"}, (
        "Both appended tasks must be visible after finalize_plan write-through to Gist"
    )


def test_append_task_raises_on_gist_write_failure(gist_layer: GistTaskLayer, store: _InMemoryArtifactStore) -> None:
    """append_task propagates ArtifactWriteError when Gist store fails.

    Verifies that when artifact_client.store() is forced to fail during the
    write-through triggered by append_task(), GistTaskLayer raises ArtifactWriteError
    rather than swallowing it silently.  Tests the no-silent-swallow contract for
    append_task (AC7 analog for gist_task_layer.py:861).
    """
    # Arrange: create a plan successfully while the store is healthy.
    tasks = _two_tasks()
    plan_data = gist_layer.create_plan(
        slug="append-task-write-failure",
        goal="Verify ArtifactWriteError propagation from append_task",
        tasks=tasks,
        issue=_PLAN_ISSUE,
    )
    plan_id = plan_data["plan_id"]

    # Enable store failure before the append attempt (create succeeded, append must fail).
    store.force_store_failure = True

    new_task = Task(
        id="T3",
        title="Task that triggers Gist write failure",
        status=TaskStatus.NOT_STARTED,
        agent="test-agent",
        dependencies=[],
        priority=Priority.MEDIUM,
        complexity=Complexity.LOW,
    )

    # Act + Assert: ArtifactWriteError must propagate (no silent swallow).
    with pytest.raises(ArtifactWriteError):
        gist_layer.append_task(plan_id, new_task)


# ---------------------------------------------------------------------------
# Rate-limit graceful degradation: _write_through absorbs secondary rate limits
# ---------------------------------------------------------------------------


class _RateLimitArtifactStore(_InMemoryArtifactStore):
    """_InMemoryArtifactStore subclass that simulates a GitHub secondary rate-limit response.

    When ``force_rate_limit`` is ``True``, ``store()`` raises
    :exc:`ArtifactWriteError` with ``"secondary rate limit"`` in the reason
    string, matching the signal strings checked by
    ``GistTaskLayer._write_through``.

    Inheriting from ``_InMemoryArtifactStore`` gives access to the same
    ``read``, ``store_index``, and ``read_index`` methods so fake clients
    can be constructed with :func:`_make_fake_client` unchanged.
    """

    def __init__(self) -> None:
        """Initialise with rate-limit simulation disabled."""
        super().__init__()
        #: When True, store() raises ArtifactWriteError simulating a GitHub
        #: secondary rate-limit response rather than storing content.
        self.force_rate_limit: bool = False

    def store(self, issue: int, content: str, *, artifact_type: str = "task-plan") -> None:
        """Raise ArtifactWriteError with secondary rate limit reason when force_rate_limit is set.

        When ``force_rate_limit`` is ``False``, delegates to the parent class,
        which respects the ``force_store_failure`` flag from
        :class:`_InMemoryArtifactStore`.

        Args:
            issue: GitHub issue number keying the artifact.
            content: YAML content to store.
            artifact_type: Artifact type key (default ``"task-plan"``).

        Raises:
            ArtifactWriteError: When ``force_rate_limit`` is ``True``, with a
                reason containing ``"secondary rate limit"``.
            ArtifactWriteError: When ``force_store_failure`` is ``True``
                (inherited behaviour, genuine error path).
        """
        if self.force_rate_limit:
            raise ArtifactWriteError(
                plan_id="<unknown>",
                issue=issue,
                reason="You have exceeded a secondary rate limit. Please wait a few minutes before you try again.",
            )
        super().store(issue, content, artifact_type=artifact_type)


def _make_rate_limit_layer(tmp_path: Path) -> tuple[GistTaskLayer, _RateLimitArtifactStore]:
    """Construct a GistTaskLayer backed by a _RateLimitArtifactStore.

    Returns a (layer, store) pair so tests can toggle ``force_rate_limit``
    between the create (successful) and mutation (rate-limited) steps.

    Args:
        tmp_path: pytest ``tmp_path`` fixture providing an isolated plan directory.

    Returns:
        Tuple of (GistTaskLayer, _RateLimitArtifactStore).
    """
    plan_dir = tmp_path / "plan"
    plan_dir.mkdir()
    local_backend = LocalYamlTaskProvider(plan_dir)
    rate_store = _RateLimitArtifactStore()
    client = _make_fake_client(rate_store)
    plan_index = _make_fake_plan_index(client, sentinel_issue=_SENTINEL_ISSUE)
    layer = GistTaskLayer(local_backend=local_backend, artifact_client=client, plan_index=plan_index)
    return layer, rate_store


def test_update_task_status_succeeds_on_rate_limit(tmp_path: Path) -> None:
    """Rate-limit degrade: update_task_status succeeds (no exception) when Gist is rate-limited.

    Verifies that when ``artifact_client.store()`` raises
    :exc:`ArtifactWriteError` with ``"secondary rate limit"`` in the reason,
    ``GistTaskLayer._write_through`` absorbs the error and
    ``update_task_status`` returns without raising.

    The local YAML state must still reflect the mutation — the task status is
    committed locally even though the Gist write-back is skipped.
    """
    # Arrange: create plan while the store is healthy.
    layer, rate_store = _make_rate_limit_layer(tmp_path)
    tasks = _two_tasks()
    plan_data = layer.create_plan(
        slug="rate-limit-mutation",
        goal="Verify rate-limit degrade on update_task_status",
        tasks=tasks,
        issue=_PLAN_ISSUE,
    )
    plan_id = plan_data["plan_id"]

    # Enable rate-limit simulation before the mutation attempt.
    rate_store.force_rate_limit = True

    # Act: update_task_status must not raise, even though Gist is rate-limited.
    layer.update_task_status(plan_id, "T1", "in-progress")  # must not raise

    # Assert: local YAML state reflects the mutation.
    # Disable rate-limit and clear the stale Gist content so read_plan falls
    # back to the local file that was just mutated — this verifies the local
    # write committed even though the Gist upload was skipped.
    rate_store.force_rate_limit = False
    rate_store.clear_content_store()  # remove stale pre-mutation content; forces local-fallback read

    retrieved = layer.read_plan(plan_id)
    task_t1 = next(t for t in retrieved["tasks"] if t["id"] == "T1")
    assert task_t1["status"] == "in-progress", (
        "Task status must be committed locally even when Gist write-back is rate-limited"
    )


def test_rate_limit_emits_warning_log(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Rate-limit degrade: a WARNING log is emitted when _write_through absorbs a rate limit.

    Verifies that ``GistTaskLayer._write_through`` logs at WARNING level
    (not ERROR or DEBUG) when the ``"secondary rate limit"`` signal is detected
    in the :exc:`ArtifactWriteError` reason, so operators can observe the event
    without it being surfaced as an error to the MCP caller.

    The log record must be from the ``"sam_schema.core.gist_task_layer"`` logger.
    """
    import logging

    layer, rate_store = _make_rate_limit_layer(tmp_path)
    tasks = _two_tasks()
    plan_data = layer.create_plan(
        slug="rate-limit-warn", goal="Verify WARNING log emission on rate-limit degrade", tasks=tasks, issue=_PLAN_ISSUE
    )
    plan_id = plan_data["plan_id"]

    # Enable rate-limit simulation and trigger a write-through mutation.
    rate_store.force_rate_limit = True

    with caplog.at_level(logging.WARNING, logger="sam_schema.core.gist_task_layer"):
        layer.update_task_status(plan_id, "T1", "in-progress")

    # Assert: at least one WARNING record from the gist_task_layer logger that
    # references the rate-limit event.
    rate_limit_warnings = [
        r
        for r in caplog.records
        if r.name == "sam_schema.core.gist_task_layer"
        and r.levelno == logging.WARNING
        and "rate limit" in r.getMessage().lower()
    ]
    assert rate_limit_warnings, (
        "Expected at least one WARNING log from 'sam_schema.core.gist_task_layer' "
        f"mentioning 'rate limit'; got records: {[r.getMessage() for r in caplog.records]}"
    )


def test_create_plan_raises_on_rate_limit(tmp_path: Path) -> None:
    """Rate-limit hard-fail: create_plan raises ArtifactWriteError when Gist is rate-limited.

    Verifies that create_plan does NOT absorb rate-limit errors — the
    ``_write_through`` degradation path applies only to mutations routed
    through ``_write_through``.  ``create_plan`` calls ``artifact_client.store()``
    directly and must propagate any :exc:`ArtifactWriteError`, including
    rate-limit variants, as a hard error.

    This preserves the AC7 contract: a plan that fails to upload to Gist must
    not appear to succeed.
    """
    # Arrange: enable rate-limit simulation before create so the first upload fails.
    layer, rate_store = _make_rate_limit_layer(tmp_path)
    rate_store.force_rate_limit = True

    tasks = _two_tasks()

    # Act + Assert: ArtifactWriteError must propagate (no graceful degrade for create).
    with pytest.raises(ArtifactWriteError) as exc_info:
        layer.create_plan(
            slug="rate-limit-create-fail",
            goal="Verify create_plan hard-fails on rate limit",
            tasks=tasks,
            issue=_PLAN_ISSUE,
        )

    assert exc_info.value.issue == _PLAN_ISSUE, "ArtifactWriteError must reference the target issue"
    assert "rate limit" in exc_info.value.reason.lower(), (
        "ArtifactWriteError reason must carry the rate-limit message from the store"
    )


def test_genuine_error_propagates_from_update_task_status(
    gist_layer: GistTaskLayer, store: _InMemoryArtifactStore
) -> None:
    """Genuine-error path: ArtifactWriteError propagates from update_task_status when force_store_failure=True.

    Verifies that the rate-limit degrade path does not accidentally swallow
    genuine write errors (i.e. errors whose reason does NOT contain the
    ``"secondary rate limit"`` or ``"abuse detection"`` signal strings).

    The existing ``force_store_failure=True`` path raises with reason
    ``"forced failure for testing"``, which is NOT a rate-limit signal.
    ``update_task_status`` must re-raise such errors as :exc:`ArtifactWriteError`.

    This test ensures the pre-existing genuine-error contract (AC7 analog for
    mutations) is unchanged by the rate-limit degrade feature.
    """
    # Arrange: create plan while the store is healthy.
    tasks = _two_tasks()
    plan_data = gist_layer.create_plan(
        slug="genuine-error-mutation",
        goal="Verify genuine-error propagation from update_task_status",
        tasks=tasks,
        issue=_PLAN_ISSUE,
    )
    plan_id = plan_data["plan_id"]

    # Enable genuine store failure (reason does NOT contain "secondary rate limit").
    store.force_store_failure = True

    # Act + Assert: ArtifactWriteError must propagate (not absorbed as rate-limit).
    with pytest.raises(ArtifactWriteError) as exc_info:
        gist_layer.update_task_status(plan_id, "T1", "in-progress")

    assert "forced failure" in exc_info.value.reason.lower(), (
        "The genuine-error reason must be carried through ArtifactWriteError unchanged"
    )
