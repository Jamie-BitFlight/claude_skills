"""Retained RED tests for the certified T1 architecture amendment."""

from __future__ import annotations

import ast
import inspect
import json
import sqlite3
import sys
import types
from pathlib import Path

import pytest

if sys.platform == "win32":
    fcntl = types.ModuleType("fcntl")
    fcntl.LOCK_EX = 2
    fcntl.LOCK_NB = 4

    def unsupported_flock(*_args: object) -> None:
        raise OSError("fcntl.flock is unavailable on Windows")

    fcntl.flock = unsupported_flock
    sys.modules.setdefault("fcntl", fcntl)

from dh_core.ledger import port, store, transitions
from dh_core.merge_train import (
    DispatchMember,
    DispatchPlanDefinition,
    DispatchPlanSnapshot,
    DispatchReserved,
    HostAuthority,
    MergeTrain,
    RegisterTrain,
    SourceGraphSnapshot,
)
from pydantic import BaseModel, TypeAdapter, ValidationError


class DispatchPlans:
    def __init__(self, snapshot: DispatchPlanSnapshot) -> None:
        self.snapshot = snapshot

    def read(self, plan_ref: str) -> DispatchPlanSnapshot:
        assert plan_ref == "dispatch-7"
        return self.snapshot


class SourceGraph:
    def __init__(self, snapshot: SourceGraphSnapshot) -> None:
        self.snapshot = snapshot

    def read(self, milestone: int) -> SourceGraphSnapshot:
        assert milestone == 7
        return self.snapshot


def definition(*, no_group: bool = False) -> DispatchPlanDefinition:
    return DispatchPlanDefinition(
        logical_id="dispatch-7",
        revision="rev-1",
        milestone=7,
        plan="P3798",
        integration_branch="integration/runtime-integrity",
        baseline_sha="a" * 40,
        quality_gates=("uv run pytest",),
        members=(DispatchMember(issue=101, task="T1", role="maker", conflict_group=None if no_group else "shared"),),
    )


def snapshots(*, no_group: bool = False) -> tuple[DispatchPlanSnapshot, SourceGraphSnapshot]:
    frozen = definition(no_group=no_group)
    canonical = frozen.canonical_bytes()
    return (
        DispatchPlanSnapshot(logical_id=frozen.logical_id, revision=frozen.revision, canonical_bytes=canonical),
        SourceGraphSnapshot(
            revision="github:fixture-1",
            milestone=frozen.milestone,
            integration_branch=frozen.integration_branch,
            baseline_sha=frozen.baseline_sha,
            members=frozen.members,
        ),
    )


def service(
    tmp_path: Path, *, no_group: bool = False
) -> tuple[MergeTrain, sqlite3.Connection, DispatchPlans, SourceGraph]:
    connection = store.open_ledger(tmp_path / "dh.db")
    transitions.create(
        connection,
        slug="3798",
        goal="test",
        plan_id="P3798",
        base_sha="a" * 40,
        quality_gates=["uv run pytest"],
        tasks=[{"id": "T1", "title": "T1", "github_issue": 101, "conflict_group": None if no_group else "shared"}],
    )
    transitions.finalize(connection, "P3798")
    dispatch_snapshot, graph_snapshot = snapshots(no_group=no_group)
    plans = DispatchPlans(dispatch_snapshot)
    graph = SourceGraph(graph_snapshot)
    train = MergeTrain(connection, plans, graph, HostAuthority(authority_host_id="host-a"))
    return train, connection, plans, graph


def register(train: MergeTrain) -> None:
    train.register(RegisterTrain(plan_ref="dispatch-7", milestone=7, plan="P3798"))


def test_f01_registration_reads_authoritative_sources_and_records_identities(tmp_path: Path) -> None:
    train, connection, _, _ = service(tmp_path)

    registered = train.register(RegisterTrain(plan_ref="dispatch-7", milestone=7, plan="P3798"))

    assert registered.dispatch_plan_revision == "rev-1"
    assert registered.source_graph_revision == "github:fixture-1"
    assert registered.source_graph_digest.startswith("sha256:")
    payload = store.events_of(connection, "P3798", kind="merge.train-registered")[0]["payload"]
    assert payload["source_graph_revision"] == "github:fixture-1"
    assert set(RegisterTrain.model_fields) == {"plan_ref", "milestone", "plan"}


def test_f01_dispatch_refuses_changed_authority_source_before_mutation(tmp_path: Path) -> None:
    train, connection, plans, _ = service(tmp_path)
    register(train)
    plans.snapshot = plans.snapshot.model_copy(update={"revision": "rev-2"})

    with pytest.raises(store.Refusal, match="dispatch-plan-stale"):
        train.dispatch(DispatchReserved(plan="P3798", generation=1, task="T1"))

    assert store.fetch_task(connection, "P3798", "T1")["attempts"] == 0


def test_f01_registration_refuses_dispatch_and_source_graph_disagreement(tmp_path: Path) -> None:
    train, connection, _, graph = service(tmp_path)
    graph.snapshot = graph.snapshot.model_copy(
        update={"members": (definition().members[0].model_copy(update={"issue": 999}),)}
    )

    with pytest.raises(store.Refusal, match="dispatch-plan-disagreement"):
        register(train)

    assert store.events_of(connection, "P3798", kind="merge.train-registered") == []


def test_f03_f08_no_group_attempt_gets_exact_dispatch_binding(tmp_path: Path) -> None:
    train, connection, _, _ = service(tmp_path, no_group=True)
    register(train)

    dispatched = train.dispatch(DispatchReserved(plan="P3798", generation=1, task="T1"))
    repeated = train.dispatch(DispatchReserved(plan="P3798", generation=1, task="T1"))

    assert repeated.noop == "already-dispatched"
    assert store.rows_of(connection.execute("SELECT * FROM merge_dispatches")) == [
        {
            "plan": "P3798",
            "generation": 1,
            "task": "T1",
            "attempt": dispatched.attempt,
            "role": "maker",
            "github_issue": 101,
            "conflict_group": None,
            "dispatch_seq": store.events_of(connection, "P3798", kind="merge.dispatch-bound")[0]["seq"],
        }
    ]


def test_f03_f08_registration_refuses_preexisting_open_attempt(tmp_path: Path) -> None:
    train, connection, _, _ = service(tmp_path, no_group=True)
    transitions.dispatch(connection, "P3798", "T1")

    with pytest.raises(store.Refusal, match="preexisting-open-attempt"):
        register(train)


def test_f03_f08_deleted_binding_cannot_authorize_open_attempt(tmp_path: Path) -> None:
    train, connection, _, _ = service(tmp_path, no_group=True)
    register(train)
    train.dispatch(DispatchReserved(plan="P3798", generation=1, task="T1"))
    connection.execute("DELETE FROM merge_dispatches")

    with pytest.raises(store.Refusal, match="dispatch-binding-missing"):
        train.dispatch(DispatchReserved(plan="P3798", generation=1, task="T1"))


def test_f02_import_replace_invalidates_inactive_registration(tmp_path: Path) -> None:
    train, connection, _, _ = service(tmp_path)
    register(train)
    source = port.PlanSource(
        plan_id="P3798",
        milestone=7,
        integration_branch="integration/runtime-integrity",
        base_sha="a" * 40,
        quality_gates=["uv run pytest"],
        source="fixture",
        revision="replace-1",
        tasks=[port.TaskSource(fields={"id": "T1", "title": "changed", "github_issue": 999})],
    )

    port.import_plan(connection, source, replace=True)

    row = store.rows_of(connection.execute("SELECT * FROM merge_trains"))[0]
    assert row["invalidated_seq"] is not None
    assert row["invalidation_reason"] == "import:fixture:replace-1"
    with pytest.raises(store.Refusal, match="merge-train-not-registered"):
        train.dispatch(DispatchReserved(plan="P3798", generation=1, task="T1"))


def test_f02_replace_refuses_active_registered_attempt(tmp_path: Path) -> None:
    train, connection, _, _ = service(tmp_path)
    register(train)
    train.dispatch(DispatchReserved(plan="P3798", generation=1, task="T1"))
    source = port.PlanSource(plan_id="P3798", milestone=7, source="fixture", revision="replace-1")

    with pytest.raises(store.Refusal, match="registered-plan-active"):
        port.import_plan(connection, source, replace=True)


@pytest.mark.parametrize(
    ("model", "value"),
    [
        (DispatchMember, {"issue": "101", "task": "T1", "role": "maker"}),
        (RegisterTrain, {"plan_ref": "dispatch-7", "milestone": "7", "plan": "P3798"}),
        (DispatchReserved, {"plan": "P3798", "generation": "1", "task": "T1"}),
    ],
)
def test_f04_f19_requests_reject_wrong_scalar_types(model: type[BaseModel], value: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        model.model_validate(value)


def test_f22_t1_exposes_no_callable_supersession_or_mcp_dispatch() -> None:
    import dh_core.merge_train as merge_train
    from sam_schema.core.action_models import PlanActionConfig

    assert not hasattr(MergeTrain, "supersede")
    assert not hasattr(merge_train, "SupersedeTrain")
    schema = json.dumps(TypeAdapter(PlanActionConfig).json_schema(), sort_keys=True)
    assert '"dispatch"' not in schema


def test_f03_f22_dynamic_dispatch_adapter_and_direct_writer_inventory() -> None:
    from dh_core import ledger
    from dh_core.ledger import commands
    from sam_schema import sam_plan

    assert ledger.dispatch is transitions.dispatch
    assert commands.COMMAND_FUNCTIONS["dispatch"] is transitions.dispatch
    assert "ledger.dispatch(" in inspect.getsource(sam_plan.dispatch)

    plugin = Path(__file__).parents[1]
    writers: list[tuple[str, str]] = []
    for path in sorted((plugin / "dh_core").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            writers.extend(
                (path.relative_to(plugin).as_posix(), getattr(node.func, "id", getattr(node.func, "attr", "")))
                for keyword in node.keywords
                if keyword.arg == "kind"
                and isinstance(keyword.value, ast.Constant)
                and keyword.value.value == "task.dispatched"
            )
    writers = [writer for writer in writers if writer[1] in {"append", "append_event"}]
    assert {path for path, _ in writers} == {"dh_core/ledger/transitions.py"}
    assert [name for _, name in writers] == ["append", "append"]


def test_f18_independent_fold_reconstructs_registration_invalidation_and_binding(tmp_path: Path) -> None:
    train, connection, _, _ = service(tmp_path, no_group=True)
    register(train)
    train.dispatch(DispatchReserved(plan="P3798", generation=1, task="T1"))
    events = store.events_of(connection, "P3798")
    folded: dict[str, list[tuple[object, ...]]] = {"trains": [], "dispatches": []}
    for event in events:
        payload = event["payload"]
        assert isinstance(payload, dict)
        if event["kind"] == "merge.train-registered":
            folded["trains"].append((event["plan"], payload["generation"], payload["source_graph_revision"]))
        if event["kind"] == "merge.dispatch-bound":
            folded["dispatches"].append((
                event["plan"],
                payload["generation"],
                event["task"],
                payload["attempt"],
                payload["role"],
            ))

    store.rebuild(connection)

    assert folded == {"trains": [("P3798", 1, "github:fixture-1")], "dispatches": [("P3798", 1, "T1", 1, "maker")]}
    assert connection.execute("SELECT COUNT(*) FROM merge_trains").fetchone()[0] == 1
    assert connection.execute("SELECT COUNT(*) FROM merge_dispatches").fetchone()[0] == 1
