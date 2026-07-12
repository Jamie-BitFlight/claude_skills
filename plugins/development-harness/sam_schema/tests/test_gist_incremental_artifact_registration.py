"""AC5/AC6 coverage for #2658: sam_plan incremental artifact registration.

This file lives in the beads-scoped ``sam_schema/tests/`` directory because
AC5 and AC6 of #2658 literally require coverage under this path (the plan's
requirements name this exact file location).

The fixture stack below (``_InMemoryArtifactStore``, ``_make_fake_client``,
``_make_fake_plan_index``, the ``store`` fixture, and the ``gist_layer``
fixture) is an intentionally MINIMAL, INDEPENDENT duplicate of the fixtures
in ``tests_sam/test_gist_write_through.py`` (ADR-1) -- it is a copy, not an
import. Both copies must be updated in lockstep whenever the
``GistTaskLayer`` / ``ArtifactRegistryClient`` interface changes. This
duplication is an accepted, documented trade-off in exchange for keeping
this file's fixture stack independently readable and self-contained.

Test-to-AC mapping:

- ``test_incremental_plan_registers_finalized_task_plan_artifact`` closes AC5:
  proves the incremental path (``create(tasks=[], issue=N)`` ->
  ``append_task`` x2 -> ``finalize_plan``) registers a FINALIZED task-plan
  artifact (``state == "ready"`` with both appended tasks present), not the
  empty drafting skeleton captured at ``create_plan(tasks=[])`` time.
- ``test_finalize_plan_is_idempotent_on_second_call`` closes AC6: proves a
  second ``finalize_plan`` call on an already-finalized plan raises no
  exception and performs zero additional ``store()`` calls (content-hash
  dedup in ``GistTaskLayer._write_through``), leaving stored content
  byte-identical.

Known coverage gap -- documented, not silently absent elsewhere: ``_make_fake_client``
returns a ``_FakeArtifactRegistryClient`` subclass that overrides ``store``/``read``/
``store_index``/``read_index`` to delegate to the in-memory store, so neither this
file nor ``tests_sam/test_gist_write_through.py`` exercises the REAL
``ArtifactRegistryClient.store()`` ``entry_exists`` idempotency guard
(``artifact_registry_client.py`` lines 117-157) -- the override replaces that
method's body entirely. That guard is independently covered by
``tests_backlog/test_artifact_registry.py::test_register_same_type_and_path_updates_in_place``.
A future reader should not mistake "not exercised by AC6" for "not tested
anywhere" -- it is tested at the real-client layer in that other file.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from sam_schema.core.artifact_registry_client import ArtifactRegistryClient
from sam_schema.core.backends.local_yaml import LocalYamlTaskProvider
from sam_schema.core.gist_task_layer import GistTaskLayer
from sam_schema.core.models import Complexity, PlanState, Priority, Task, TaskStatus
from sam_schema.core.plan_id_index import PlanIdIndex

if TYPE_CHECKING:
    from pathlib import Path

# ---------------------------------------------------------------------------
# Deterministic in-memory fakes (minimal, independent duplicate -- ADR-1)
# ---------------------------------------------------------------------------

_SENTINEL_ISSUE = 42
_PLAN_ISSUE = 2658


class _InMemoryArtifactStore:
    """Deterministic in-memory artifact store for offline tests.

    Stores keyed by (issue, artifact_type) -> content string. Also holds a
    separate index store keyed by sentinel_issue -> content string.

    Extended with a ``store_call_count`` invocation-count spy (AC6
    requirement): incremented at the top of ``store()`` so tests can detect
    whether a second ``finalize_plan`` call triggered a redundant Gist
    upload. Dict-size checks on ``_store`` cannot detect this because
    ``store()`` overwrites the same ``(issue, artifact_type)`` key on every
    call -- the dict never grows even when ``store()`` is invoked repeatedly.
    """

    def __init__(self) -> None:
        self._store: dict[tuple[int, str], str] = {}
        self._index_store: dict[int, str] = {}
        #: AC6 spy -- incremented at the top of store(), regardless of outcome.
        self.store_call_count: int = 0

    def store(self, issue: int, content: str, *, artifact_type: str = "task-plan") -> None:
        """Store content keyed by (issue, artifact_type)."""
        self.store_call_count += 1
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


class _FakeArtifactRegistryClient(ArtifactRegistryClient):
    """ArtifactRegistryClient subclass that delegates I/O to an in-memory store.

    Overrides the four public methods directly instead of monkey-patching
    bound methods onto an instance -- avoids ``# type: ignore[method-assign]``
    suppressions, which require documented user approval per
    ``.claude/rules/linting-exceptions.md`` and were not approved here.
    """

    def __init__(self, store: _InMemoryArtifactStore) -> None:
        super().__init__(provider=None)
        self._fake_store = store

    def store(self, issue: int, content: str, *, artifact_type: str = "task-plan") -> None:
        self._fake_store.store(issue, content, artifact_type=artifact_type)

    def read(self, issue: int, artifact_type: str = "task-plan") -> str | None:
        return self._fake_store.read(issue, artifact_type)

    def store_index(self, sentinel_issue: int, content: str) -> None:
        self._fake_store.store_index(sentinel_issue, content)

    def read_index(self, sentinel_issue: int) -> str | None:
        return self._fake_store.read_index(sentinel_issue)


def _make_fake_client(store: _InMemoryArtifactStore) -> ArtifactRegistryClient:
    """Return an ArtifactRegistryClient backed by the given in-memory store."""
    return _FakeArtifactRegistryClient(store)


def _make_fake_plan_index(client: ArtifactRegistryClient, sentinel_issue: int = _SENTINEL_ISSUE) -> PlanIdIndex:
    """Return a PlanIdIndex backed by the given client and a non-zero sentinel."""
    return PlanIdIndex(artifact_client=client, sentinel_issue=sentinel_issue)


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
# AC5: incremental path registers a FINALIZED task-plan artifact
# ---------------------------------------------------------------------------


def test_incremental_plan_registers_finalized_task_plan_artifact(
    gist_layer: GistTaskLayer, store: _InMemoryArtifactStore
) -> None:
    """AC5: create(tasks=[])->append_task x2->finalize registers a FINALIZED artifact.

    Verifies that the incremental drafting path -- creating a plan with an
    empty task list, appending tasks one at a time, then finalizing -- ends
    with the Gist-served artifact reflecting the FINALIZED plan (state
    "ready" with both appended tasks), not the empty ``tasks: []`` drafting
    skeleton captured at ``create_plan`` time.
    """
    # Arrange + Act: incremental path -- create empty drafting plan, append
    # two tasks one at a time (single-writer, sequential calls), finalize.
    plan_data = gist_layer.create_plan(
        slug="incremental-artifact-registration",
        goal="Verify incremental plan path registers a finalized task-plan artifact",
        tasks=[],
        issue=_PLAN_ISSUE,
    )
    plan_id = plan_data["plan_id"]

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
    gist_layer.finalize_plan(plan_id)

    # Force a Gist-only read: delete the local YAML so read_plan cannot serve
    # from a surviving local file -- content must come from the artifact store.
    local_dir: Path = gist_layer.local.plan_dir
    for yaml_file in local_dir.glob(f"{plan_id}-*.yaml"):
        yaml_file.unlink()

    # Act: read the plan back. Must not raise PlanNotFoundError.
    retrieved = gist_layer.read_plan(plan_id)

    # Assert 2: content came from the artifact store, not a surviving local file.
    assert gist_layer.last_read_source == "gist", (
        "read_plan must serve the finalized plan from the Gist store after the "
        "local YAML was deleted -- a 'local' source here means the test setup "
        "did not force a Gist-only read"
    )

    # Assert 3: retrieved state is "ready" -- the FINALIZED content, not the
    # "drafting" state captured when create_plan(tasks=[]) ran.
    assert retrieved["state"] == PlanState.READY, (
        f"Retrieved plan state must be {PlanState.READY!r}; got {retrieved['state']!r}. "
        "A 'drafting' state here means finalize_plan's state transition did not "
        "persist to the Gist-stored artifact."
    )

    # Assert 4: both appended tasks are present -- not the empty drafting skeleton.
    retrieved_ids = {t["id"] for t in retrieved["tasks"]}
    assert retrieved_ids == {"T1", "T2"}, (
        f"Retrieved tasks must be {{'T1', 'T2'}}; got {retrieved_ids!r}. A failure here "
        "indicates a regression back to the empty tasks: [] drafting skeleton registered "
        "at create_plan(tasks=[], issue=...) time, instead of the finalized task list."
    )

    # Assert 5: the raw fake store also holds the uploaded content directly.
    assert store.read(_PLAN_ISSUE, "task-plan") is not None, (
        "Raw artifact store must contain uploaded task-plan content after the incremental path"
    )


# ---------------------------------------------------------------------------
# AC6: finalize_plan is idempotent on a second call
# ---------------------------------------------------------------------------


def test_finalize_plan_is_idempotent_on_second_call(gist_layer: GistTaskLayer, store: _InMemoryArtifactStore) -> None:
    """AC6: a second finalize_plan call on an already-ready plan is a no-op.

    Verifies that calling ``finalize_plan`` a second time on a plan that is
    already in the "ready" state raises no exception, performs zero
    additional ``store()`` calls (the content-hash dedup guard in
    ``GistTaskLayer._write_through`` must recognise the unchanged YAML and
    skip the redundant upload), and leaves the stored content byte-identical.

    FALSIFICATION GATE (architect spec section 6, Q2): if the
    ``store_call_count`` assertion below fails, this is empirical evidence
    that the content-hash dedup guard did NOT skip the redundant upload --
    a real idempotency defect in ``gist_task_layer.py:_write_through``, not
    a test authoring error. Per task instructions, such a failure must be
    reported as STATUS: BLOCKED rather than patched around here.
    """
    # Arrange: create a drafting plan, append one task, then finalize once.
    plan_data = gist_layer.create_plan(
        slug="idempotent-finalize",
        goal="Verify finalize_plan is idempotent on a second call",
        tasks=[],
        issue=_PLAN_ISSUE,
    )
    plan_id = plan_data["plan_id"]

    t1 = Task(
        id="T1",
        title="Only appended task",
        status=TaskStatus.NOT_STARTED,
        agent="test-agent",
        dependencies=[],
        priority=Priority.CRITICAL,
        complexity=Complexity.LOW,
    )
    gist_layer.append_task(plan_id, t1)

    # First finalize: transitions drafting -> ready and uploads to Gist.
    gist_layer.finalize_plan(plan_id)

    count_after_first = store.store_call_count
    content_after_first = store.read(_PLAN_ISSUE, "task-plan")

    # Sanity check: the first finalize must have actually produced stored
    # content before asserting the second finalize is a no-op -- otherwise a
    # broken first finalize (writing nothing) would make the "no growth"
    # assertion below vacuously true (0 == 0, None == None) and silently mask
    # the real regression it's meant to catch.
    assert count_after_first > 0, (
        "First finalize_plan call must have invoked store() at least once; "
        "count_after_first=0 would make the idempotency assertion below meaningless"
    )
    assert content_after_first is not None, (
        "First finalize_plan call must have produced stored task-plan content; "
        "content_after_first=None would make the idempotency assertion below meaningless"
    )

    # Act: second finalize_plan call on the now-ready plan. Must not raise --
    # deliberately NOT wrapped in pytest.raises so an uncaught exception here
    # fails the test naturally.
    gist_layer.finalize_plan(plan_id)

    # Assert 7 (primary AC6 assertion / falsification gate): zero additional
    # store() calls were made by the second finalize.
    assert store.store_call_count == count_after_first, (
        "FALSIFICATION GATE: the second finalize_plan call added a store() invocation "
        f"(count_after_first={count_after_first}, count_after_second={store.store_call_count}). "
        "This means the content-hash dedup guard in GistTaskLayer._write_through did NOT "
        "skip the redundant upload -- report STATUS: BLOCKED, do not patch this test."
    )

    # Assert 8: stored content is byte-identical -- nothing silently overwritten.
    assert store.read(_PLAN_ISSUE, "task-plan") == content_after_first, (
        "Stored task-plan content must be byte-identical after the second, no-op finalize_plan call"
    )

    # Assert 9: plan state is still "ready" after the second (no-op) finalize.
    retrieved = gist_layer.read_plan(plan_id)
    assert retrieved["state"] == PlanState.READY, (
        f"Plan state must remain {PlanState.READY!r} after the second finalize_plan call; got {retrieved['state']!r}"
    )
