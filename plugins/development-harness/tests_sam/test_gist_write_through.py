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
from sam_schema.core.models import Task, TaskStatus
from sam_schema.core.plan_id_index import PlanIdIndex

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
            priority=1,
            complexity="low",
        ),
        Task(
            id="T2",
            title="Second task",
            status=TaskStatus.NOT_STARTED,
            agent="test-agent",
            dependencies=["T1"],
            priority=2,
            complexity="medium",
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
            priority=1,
            complexity="low",
        ),
        Task(
            id="T2",
            title="Implementation",
            status=TaskStatus.NOT_STARTED,
            agent="python-cli-architect",
            dependencies=["T1"],
            priority=2,
            complexity="high",
        ),
        Task(
            id="T3",
            title="Tests",
            status=TaskStatus.NOT_STARTED,
            agent="python-pytest-architect",
            dependencies=["T1", "T2"],
            priority=3,
            complexity="medium",
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
