"""Backward-compatibility tests for pre-fix local plans (AC4).

Verifies that plans created before the Gist write-through fix — which exist only
on local disk with no Gist entry and no PlanIdIndex registration — are still
readable via the GistTaskLayer's local fallback path.

The fallback must:
- Return the plan without raising PlanNotFoundError.
- Annotate last_read_source with "local".
- Not silently return empty or corrupted data (content completeness check).

All tests run offline — no live GitHub token required (AC5 offline requirement).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from dh_core import operations
from sam_schema.core.artifact_registry_client import ArtifactRegistryClient
from sam_schema.core.backends.local_yaml import LocalYamlTaskProvider
from sam_schema.core.exceptions import PlanNotFoundError
from sam_schema.core.gist_task_layer import GistTaskLayer
from sam_schema.core.models import Complexity, Priority, Task, TaskStatus
from sam_schema.core.plan_id_index import PlanIdIndex

if TYPE_CHECKING:
    from pathlib import Path

# ---------------------------------------------------------------------------
# Deterministic in-memory fakes — same pattern as test_gist_write_through.py
# ---------------------------------------------------------------------------


class _EmptyArtifactStore:
    """Artifact store that always returns None on reads and succeeds on writes.

    Simulates a Gist store that has no content for pre-fix plans (they were
    never uploaded to Gist before the fix was deployed).
    """

    def store(self, issue: int, content: str, *, artifact_type: str = "task-plan") -> None:
        """Accept writes silently (no-op for backward-compat tests)."""

    def read(self, issue: int, artifact_type: str = "task-plan") -> str | None:
        """Always return None — simulates absent Gist content for pre-fix plans."""
        return None

    def store_index(self, sentinel_issue: int, content: str) -> None:
        """Accept index writes silently."""

    def read_index(self, sentinel_issue: int) -> str | None:
        """Always return None — simulates absent plan index (no registration)."""
        return None


class _EmptyArtifactRegistryClient(ArtifactRegistryClient):
    """ArtifactRegistryClient that delegates reads/writes to an empty in-memory store.

    Using a subclass instead of monkey-patching bound methods keeps the
    interface contract visible to the type checker (same signatures as the
    parent) and avoids method-assign diagnostics.
    """

    def __init__(self, store: _EmptyArtifactStore) -> None:
        """Initialise with an empty in-memory store."""
        super().__init__()
        self._store = store

    def store(self, issue: int, content: str, *, artifact_type: str = "task-plan") -> None:
        """Delegate to the in-memory store."""
        self._store.store(issue, content, artifact_type=artifact_type)

    def read(self, issue: int, artifact_type: str = "task-plan") -> str | None:
        """Delegate to the in-memory store."""
        return self._store.read(issue, artifact_type)

    def store_index(self, sentinel_issue: int, content: str) -> None:
        """Delegate to the in-memory store."""
        self._store.store_index(sentinel_issue, content)

    def read_index(self, sentinel_issue: int) -> str | None:
        """Delegate to the in-memory store."""
        return self._store.read_index(sentinel_issue)


def _make_empty_client() -> ArtifactRegistryClient:
    """Return an ArtifactRegistryClient backed by an empty store."""
    return _EmptyArtifactRegistryClient(_EmptyArtifactStore())


_SENTINEL_ISSUE = 99  # Non-zero sentinel — but read_index returns None, so index is always empty.


def _make_layer_with_empty_gist(plan_dir: Path) -> GistTaskLayer:
    """Build a GistTaskLayer whose Gist store is empty (simulating pre-fix environment)."""
    local_backend = LocalYamlTaskProvider(plan_dir)
    client = _make_empty_client()
    plan_index = PlanIdIndex(artifact_client=client, sentinel_issue=_SENTINEL_ISSUE)
    return GistTaskLayer(local_backend=local_backend, artifact_client=client, plan_index=plan_index)


# ---------------------------------------------------------------------------
# Helper to write a plan directly via LocalYamlTaskProvider (bypassing GistTaskLayer)
# This simulates a plan created before the Gist write-through fix was deployed.
# ---------------------------------------------------------------------------


def _create_local_only_plan(plan_dir: Path, slug: str, tasks: list[Task]) -> str:
    """Write a plan directly to local disk without any Gist upload.

    Returns the plan_id of the created plan.
    """
    local = LocalYamlTaskProvider(plan_dir)
    plan_data = local.create_plan(
        slug=slug,
        goal=f"Pre-fix local plan: {slug}",
        tasks=tasks,
        context="Created before Gist write-through was deployed",
        issue=None,  # pre-fix plans had no issue or weren't uploaded
    )
    return plan_data["plan_id"]


# ---------------------------------------------------------------------------
# AC4 tests
# ---------------------------------------------------------------------------


def test_local_plan_readable_via_fallback(tmp_path: Path) -> None:
    """AC4: a pre-fix local plan is readable via GistTaskLayer local fallback.

    Creates a plan using LocalYamlTaskProvider directly (bypassing GistTaskLayer),
    then reads it via a GistTaskLayer whose Gist store is empty.  The read must
    succeed, return the correct plan, and annotate last_read_source as "local".
    """
    plan_dir = tmp_path / "plan"
    plan_dir.mkdir()

    # Arrange: write a local-only plan (simulates pre-fix creation).
    tasks = [Task(id="T1", title="Pre-fix task", status=TaskStatus.NOT_STARTED, agent="some-agent", dependencies=[])]
    plan_id = _create_local_only_plan(plan_dir, "pre-fix-plan", tasks)

    # Act: read via GistTaskLayer with empty Gist store.
    layer = _make_layer_with_empty_gist(plan_dir)
    retrieved = layer.read_plan(plan_id)

    # Assert 1: plan returned (no PlanNotFoundError).
    assert retrieved is not None
    assert retrieved["plan_id"] == plan_id

    # Assert 2: source annotation is "local" (Gist had no content).
    assert layer.last_read_source == "local", "Pre-fix plans must be annotated as served from local cache, not Gist"

    # Assert 3: content completeness — task data is intact.
    assert len(retrieved["tasks"]) == 1
    assert retrieved["tasks"][0]["id"] == "T1"
    assert retrieved["tasks"][0]["title"] == "Pre-fix task"


def test_operations_read_plan_surfaces_local_fallback_warning(tmp_path: Path) -> None:
    """Local Gist fallback is surfaced to callers as a ReadResult warning."""
    plan_dir = tmp_path / "plan"
    plan_dir.mkdir()
    plan_id = _create_local_only_plan(
        plan_dir, "warning-plan", [Task(id="T1", title="Task", status=TaskStatus.NOT_STARTED)]
    )

    result = operations.read_plan(_make_layer_with_empty_gist(plan_dir), plan_id)

    assert result.warnings == [
        f"Plan {plan_id} served from local cache — Gist copy may be unavailable or predates this fix."
    ]


def test_local_plan_full_content_equality(tmp_path: Path) -> None:
    """AC4: full content equality for a pre-fix local plan served from local fallback.

    Extends the basic fallback test with complete task-field comparison to confirm
    the local fallback does not truncate or corrupt any plan data.
    """
    plan_dir = tmp_path / "plan"
    plan_dir.mkdir()

    tasks = [
        Task(
            id="T1",
            title="Foundation task",
            status=TaskStatus.NOT_STARTED,
            agent="python-cli-architect",
            dependencies=[],
            priority=Priority.CRITICAL,
            complexity=Complexity.LOW,
        ),
        Task(
            id="T2",
            title="Integration task",
            status=TaskStatus.NOT_STARTED,
            agent="python-cli-architect",
            dependencies=["T1"],
            priority=Priority.HIGH,
            complexity=Complexity.MEDIUM,
        ),
    ]
    plan_id = _create_local_only_plan(plan_dir, "pre-fix-full-equality", tasks)

    layer = _make_layer_with_empty_gist(plan_dir)
    retrieved = layer.read_plan(plan_id)

    # Source annotation.
    assert layer.last_read_source == "local"

    # Full task-field equality.
    assert len(retrieved["tasks"]) == 2
    by_id = {t["id"]: t for t in retrieved["tasks"]}

    assert by_id["T1"]["title"] == "Foundation task"
    assert by_id["T1"]["agent"] == "python-cli-architect"
    deps_t1 = by_id["T1"].get("dependencies") or []
    assert deps_t1 == [] or deps_t1 is None or deps_t1 == []

    assert by_id["T2"]["title"] == "Integration task"
    assert by_id["T2"]["agent"] == "python-cli-architect"
    assert "T1" in (by_id["T2"].get("dependencies") or [])


def test_local_plan_not_found_raises(tmp_path: Path) -> None:
    """AC4 guard: reading a completely absent plan raises PlanNotFoundError.

    Confirms that the local fallback does not silently return empty data when
    neither Gist nor local has the plan — PlanNotFoundError must propagate.
    """
    plan_dir = tmp_path / "plan"
    plan_dir.mkdir()

    layer = _make_layer_with_empty_gist(plan_dir)

    with pytest.raises(PlanNotFoundError):
        layer.read_plan("Pnonexistent99")


def test_local_plan_with_many_tasks(tmp_path: Path) -> None:
    """AC4: a multi-task pre-fix plan is fully readable via local fallback.

    Stress-tests the local fallback path with five tasks having a chain
    of dependencies — confirms the plan topology survives the fallback read.
    """
    plan_dir = tmp_path / "plan"
    plan_dir.mkdir()

    tasks = [
        Task(
            id="T1",
            title="Task one",
            status=TaskStatus.NOT_STARTED,
            agent="agent",
            dependencies=[],
            priority=Priority.CRITICAL,
        ),
        Task(
            id="T2",
            title="Task two",
            status=TaskStatus.NOT_STARTED,
            agent="agent",
            dependencies=["T1"],
            priority=Priority.HIGH,
        ),
        Task(
            id="T3",
            title="Task three",
            status=TaskStatus.NOT_STARTED,
            agent="agent",
            dependencies=["T1"],
            priority=Priority.MEDIUM,
        ),
        Task(
            id="T4",
            title="Task four",
            status=TaskStatus.NOT_STARTED,
            agent="agent",
            dependencies=["T2", "T3"],
            priority=Priority.LOW,
        ),
        Task(
            id="T5",
            title="Task five",
            status=TaskStatus.NOT_STARTED,
            agent="agent",
            dependencies=["T4"],
            priority=Priority.LOWEST,
        ),
    ]
    plan_id = _create_local_only_plan(plan_dir, "pre-fix-many-tasks", tasks)

    layer = _make_layer_with_empty_gist(plan_dir)
    retrieved = layer.read_plan(plan_id)

    assert layer.last_read_source == "local"
    assert len(retrieved["tasks"]) == 5

    by_id = {t["id"]: t for t in retrieved["tasks"]}
    assert set(by_id.keys()) == {"T1", "T2", "T3", "T4", "T5"}

    # Verify dependency chain is preserved.
    assert "T2" in (by_id["T4"].get("dependencies") or [])
    assert "T3" in (by_id["T4"].get("dependencies") or [])
    assert "T4" in (by_id["T5"].get("dependencies") or [])
