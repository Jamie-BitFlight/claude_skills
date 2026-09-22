"""Retained RED tests for the certified T1 architecture amendment."""

from __future__ import annotations

import ast
import inspect
import json
import sqlite3
import sys
import types
from collections.abc import Iterator
from pathlib import Path
from threading import get_ident
from typing import Any

import pytest

if sys.platform == "win32":
    fcntl = types.ModuleType("fcntl")
    fcntl.LOCK_EX = 2
    fcntl.LOCK_NB = 4

    def unsupported_flock(*_args: object) -> None:
        raise OSError("fcntl.flock is unavailable on Windows")

    fcntl.flock = unsupported_flock
    sys.modules.setdefault("fcntl", fcntl)

from dh_core import ledger_spec
from dh_core.ledger import port, store, transitions
from dh_core.merge_train import (
    DispatchMember,
    DispatchPlanDefinition,
    DispatchPlanSnapshot,
    DispatchReserved,
    HostAuthority,
    MergeQuery,
    MergeTrain,
    RegisterTrain,
    SourceGraphSnapshot,
)
from pydantic import BaseModel, TypeAdapter, ValidationError


@pytest.fixture(autouse=True)
def close_test_ledgers(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Keep every test ledger alive until teardown, then close it explicitly."""
    owner_thread = get_ident()
    opened: list[tuple[int, sqlite3.Connection]] = []
    open_ledger = store.open_ledger

    def tracked_open_ledger(*args: Any, **kwargs: Any) -> sqlite3.Connection:
        connection = open_ledger(*args, **kwargs)
        opened.append((get_ident(), connection))
        return connection

    def close_all() -> None:
        for thread_id, connection in reversed(opened):
            if thread_id == owner_thread:
                connection.close()

    monkeypatch.setattr(store, "open_ledger", tracked_open_ledger)
    yield
    close_all()


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


class UnavailableDispatchPlans:
    def read(self, _plan_ref: str) -> DispatchPlanSnapshot:
        raise AssertionError("historical query read the dispatch-plan provider")


class UnavailableSourceGraph:
    def read(self, _milestone: int) -> SourceGraphSnapshot:
        raise AssertionError("historical query read the source-graph provider")


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


def merge_snapshot(connection: sqlite3.Connection) -> dict[str, list[dict[str, object]]]:
    return {
        table: store.rows_of(connection.execute(f"SELECT * FROM {table}"))
        for table in ("events", "merge_trains", "merge_dispatches", "merge_reservations")
    }


def replacement_source(*, route: str) -> port.PlanSource:
    if route == "import":
        return port.PlanSource(
            plan_id="P3798",
            milestone=7,
            source="fixture",
            revision="replace-judge-pending",
            tasks=[port.TaskSource(fields={"id": "T1", "title": "replacement", "github_issue": 101})],
        )
    return port.milestone_source(
        milestone_number=7,
        integration_branch="integration/runtime-integrity",
        base_sha="a" * 40,
        items=[port.MilestoneItem(issue=101, title="replacement", task_id="T1")],
        quality_gates=["uv run pytest"],
        plan_id="P3798",
    )


def corrupt_dispatch_authority(
    connection: sqlite3.Connection, *, field: str, event_value: object, row_value: object
) -> None:
    event = store.events_of(connection, "P3798", kind="merge.dispatch-bound")[0]
    if field == "task":
        connection.execute(
            "UPDATE events SET task = :value WHERE seq = :seq", {"value": event_value, "seq": event["seq"]}
        )
    else:
        payload = dict(event["payload"])
        payload[field] = event_value
        connection.execute(
            "UPDATE events SET payload = :payload WHERE seq = :seq",
            {"payload": json.dumps(payload), "seq": event["seq"]},
        )
    connection.execute(f"UPDATE merge_dispatches SET {field} = :value", {"value": row_value})


def corrupt_reservation_role(connection: sqlite3.Connection, role: str) -> None:
    event = store.events_of(connection, "P3798", kind="merge.reserved")[0]
    payload = dict(event["payload"])
    payload["role"] = role
    connection.execute(
        "UPDATE events SET payload = :payload WHERE seq = :seq", {"payload": json.dumps(payload), "seq": event["seq"]}
    )
    connection.execute("UPDATE merge_reservations SET role = :role", {"role": role})


def independent_dispatch_authority_findings(connection: sqlite3.Connection) -> list[str]:
    """Check binding events against literal retained definitions without production fold helpers."""
    registrations: dict[tuple[str, int], dict[str, tuple[object, ...]]] = {}
    attempts: dict[tuple[str, str], int] = {}
    findings: list[str] = []
    for event in store.all_events(connection):
        payload = event["payload"]
        assert isinstance(payload, dict)
        if event["kind"] == "task.dispatched":
            attempts[str(event["plan"]), str(event["task"])] = int(payload["attempt"])
        if event["kind"] == "merge.train-registered":
            definition_value = payload["definition"]
            assert isinstance(definition_value, dict)
            members = definition_value["members"]
            assert isinstance(members, list)
            registrations[str(event["plan"]), int(payload["generation"])] = {
                str(member["task"]): (int(member["issue"]), str(member["role"]), member.get("conflict_group"))
                for member in members
                if isinstance(member, dict)
            }
        if event["kind"] != "merge.dispatch-bound":
            continue
        members = registrations.get((str(event["plan"]), int(payload["generation"])), {})
        expected = members.get(str(event["task"]))
        actual = (int(payload["github_issue"]), str(payload["role"]), payload.get("conflict_group"))
        attempt = attempts.get((str(event["plan"]), str(event["task"])))
        if expected != actual or attempt != int(payload["attempt"]):
            findings.append("dispatch-binding-authority-mismatch")
    return findings


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


@pytest.mark.parametrize(
    ("column", "value"),
    [
        ("integration_branch", "integration/drift"),
        ("base_sha", "b" * 40),
        ("quality_gates", json.dumps(["uv run ty check"])),
    ],
)
def test_s1_registration_refuses_complete_ledger_plan_disagreement_without_mutation(
    tmp_path: Path, column: str, value: str
) -> None:
    train, connection, _, _ = service(tmp_path)
    connection.execute(f"UPDATE plans SET {column} = :value WHERE plan_id = 'P3798'", {"value": value})
    before = merge_snapshot(connection)

    with pytest.raises(store.Refusal, match="dispatch-plan-disagreement"):
        register(train)

    assert merge_snapshot(connection) == before


def test_s1_identical_registration_retry_after_dispatch_is_noop(tmp_path: Path) -> None:
    train, connection, _, _ = service(tmp_path)
    first = train.register(RegisterTrain(plan_ref="dispatch-7", milestone=7, plan="P3798"))
    train.dispatch(DispatchReserved(plan="P3798", generation=1, task="T1"))
    before = merge_snapshot(connection)

    repeated = train.register(RegisterTrain(plan_ref="dispatch-7", milestone=7, plan="P3798"))

    assert repeated.generation == first.generation
    assert repeated.registered_seq == first.registered_seq
    assert repeated.noop == "already-registered"
    assert merge_snapshot(connection) == before


def test_s1_identical_registration_retry_requires_original_host(tmp_path: Path) -> None:
    train, connection, plans, graph = service(tmp_path)
    register(train)
    other = MergeTrain(connection, plans, graph, HostAuthority(authority_host_id="host-b"))
    before = merge_snapshot(connection)

    with pytest.raises(store.Refusal, match="wrong-authority-host"):
        register(other)

    assert merge_snapshot(connection) == before


def test_s1_active_registration_refuses_dispatch_revision_only_drift(tmp_path: Path) -> None:
    train, connection, plans, _ = service(tmp_path)
    register(train)
    changed = definition().model_copy(update={"revision": "rev-2"})
    plans.snapshot = DispatchPlanSnapshot(
        logical_id=changed.logical_id, revision=changed.revision, canonical_bytes=changed.canonical_bytes()
    )
    before = merge_snapshot(connection)

    with pytest.raises(store.Refusal, match="dispatch-plan-stale"):
        register(train)

    assert merge_snapshot(connection) == before


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


@pytest.mark.parametrize("retaining_state", ["returned", "complete"])
def test_s2_reservation_retains_through_judge_intervals(tmp_path: Path, retaining_state: str) -> None:
    train, connection, _, _ = service(tmp_path)
    register(train)
    dispatched = train.dispatch(DispatchReserved(plan="P3798", generation=1, task="T1"))
    if retaining_state == "returned":
        transitions.settle(connection, "P3798", "T1", attempt=dispatched.attempt, return_text="done")
    else:
        transitions.state(connection, "P3798", "T1", new_status="complete", reason="review", force=True)

    result = train.validate(MergeQuery(plan="P3798"))

    assert result.valid, result.findings
    assert store.rows_of(connection.execute("SELECT active FROM merge_reservations")) == [{"active": 1}]


def test_s2_validate_reports_missing_group_reservation(tmp_path: Path) -> None:
    train, connection, _, _ = service(tmp_path)
    register(train)
    train.dispatch(DispatchReserved(plan="P3798", generation=1, task="T1"))
    connection.execute("DELETE FROM merge_reservations")

    result = train.validate(MergeQuery(plan="P3798"))

    assert "reservation-missing" in result.findings


def test_s2_merge_reserved_is_conditional_in_transition_spec() -> None:
    transition = next(item for item in ledger_spec.ALL_TRANSITIONS if item.command == "merge-dispatch")
    assert "merge.reserved" not in transition.events
    assert "merge.reserved" in transition.conditional_events


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


@pytest.mark.parametrize("route", ["import", "from-milestone"])
@pytest.mark.parametrize("retaining_state", ["returned", "complete-unaccepted"])
def test_f02_no_group_judge_pending_work_blocks_every_replacement_route(
    tmp_path: Path, route: str, retaining_state: str
) -> None:
    train, connection, _, _ = service(tmp_path, no_group=True)
    register(train)
    dispatched = train.dispatch(DispatchReserved(plan="P3798", generation=1, task="T1"))
    if retaining_state == "returned":
        transitions.settle(connection, "P3798", "T1", attempt=dispatched.attempt, return_text="judge me")
    else:
        transitions.state(connection, "P3798", "T1", new_status="complete", reason="judge me", force=True)
    before = merge_snapshot(connection)
    source = replacement_source(route=route)
    replace = port.import_plan if route == "import" else port.from_milestone

    with pytest.raises(store.Refusal, match="registered-plan-active"):
        replace(connection, source, replace=True)

    assert merge_snapshot(connection) == before


@pytest.mark.parametrize("disposition", ["accepted", "reclaimed", "failed"])
def test_f02_no_group_replacement_waits_for_final_disposition(tmp_path: Path, disposition: str) -> None:
    train, connection, _, _ = service(tmp_path, no_group=True)
    register(train)
    dispatched = train.dispatch(DispatchReserved(plan="P3798", generation=1, task="T1"))
    if disposition == "accepted":
        transitions.state(connection, "P3798", "T1", new_status="complete", reason="done", force=True)
        transitions.accept(connection, "P3798", "T1", force=True)
    elif disposition == "reclaimed":
        transitions.settle(connection, "P3798", "T1", attempt=dispatched.attempt, return_text="judge me")
        transitions.reclaim(connection, "P3798", "T1", reason="retry")
    else:
        transitions.state(connection, "P3798", "T1", new_status="failed", reason="terminal", force=True)

    port.import_plan(connection, replacement_source(route="import"), replace=True)

    train_row = store.rows_of(connection.execute("SELECT invalidated_seq FROM merge_trains"))[0]
    assert train_row["invalidated_seq"] is not None


@pytest.mark.parametrize(
    ("field", "value"),
    [("role", "checker"), ("github_issue", 999), ("generation", 2), ("attempt", 2), ("conflict_group", "copied-group")],
)
def test_f08_cross_copied_event_and_projection_reject_against_frozen_member(
    tmp_path: Path, field: str, value: object
) -> None:
    train, connection, _, _ = service(tmp_path, no_group=True)
    register(train)
    train.dispatch(DispatchReserved(plan="P3798", generation=1, task="T1"))
    corrupt_dispatch_authority(connection, field=field, event_value=value, row_value=value)

    assert independent_dispatch_authority_findings(connection) == ["dispatch-binding-authority-mismatch"]
    assert not train.validate(MergeQuery(plan="P3798")).valid
    with pytest.raises(LookupError, match="dispatch binding"):
        port.import_plan(connection, replacement_source(route="import"), replace=True)
    with pytest.raises(LookupError, match="dispatch binding"):
        store.rebuild(connection)
    with pytest.raises(store.Refusal, match="dispatch-binding-missing"):
        train.dispatch(DispatchReserved(plan="P3798", generation=1, task="T1"))


def test_f08_fold_rejects_cross_task_binding_event(tmp_path: Path) -> None:
    train, connection, _, _ = service(tmp_path, no_group=True)
    register(train)
    train.dispatch(DispatchReserved(plan="P3798", generation=1, task="T1"))
    events = store.all_events(connection)
    binding = next(event for event in events if event["kind"] == "merge.dispatch-bound")
    binding["task"] = "T2"

    with pytest.raises(LookupError, match="dispatch binding"):
        store.fold_events(events)


def test_f08_released_reservation_event_and_projection_cannot_cross_copy_role(tmp_path: Path) -> None:
    train, connection, _, _ = service(tmp_path)
    register(train)
    train.dispatch(DispatchReserved(plan="P3798", generation=1, task="T1"))
    transitions.state(connection, "P3798", "T1", new_status="blocked", reason="released", force=True)
    corrupt_reservation_role(connection, "checker")

    assert not train.validate(MergeQuery(plan="P3798")).valid
    assert not train.validate(MergeQuery(plan="P3798", generation=1)).valid
    with pytest.raises(LookupError, match="reservation"):
        store.rebuild(connection)


def test_f05_legal_released_reservation_history_survives_reacquisition_and_rebuild(tmp_path: Path) -> None:
    train, connection, _, _ = service(tmp_path)
    register(train)
    first = train.dispatch(DispatchReserved(plan="P3798", generation=1, task="T1"))
    transitions.state(connection, "P3798", "T1", new_status="blocked", reason="released", force=True)
    transitions.reclaim(connection, "P3798", "T1", reason="retry")
    second = train.dispatch(DispatchReserved(plan="P3798", generation=1, task="T1"))

    assert second.attempt == first.attempt + 1
    assert train.validate(MergeQuery(plan="P3798")).valid
    assert train.validate(MergeQuery(plan="P3798", generation=1)).valid
    store.rebuild(connection)
    assert train.validate(MergeQuery(plan="P3798")).valid
    assert train.validate(MergeQuery(plan="P3798", generation=1)).valid


def test_f25_mutation_subprocess_contract_is_bounded_and_classifies_timeout() -> None:
    runner_path = Path(__file__).with_name("run_merge_train_t1_mutations.py")
    tree = ast.parse(runner_path.read_text(encoding="utf-8"))
    run_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "run"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "subprocess"
    ]
    assert len(run_calls) == 1
    command = ast.unparse(run_calls[0].args[0])
    assert "BOUNDED_RUNNER" in command
    assert "--timeout-seconds" in command
    source = runner_path.read_text(encoding="utf-8")
    assert '"run_bounded.py"' in source
    assert "TIMEOUT_EXIT_CODE" in source
    assert "TIMEOUT" in source
    assert "completed.stdout" in source
    assert "completed.stderr" in source


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


def test_s3_fold_uses_typed_primary_key_order_for_generations(tmp_path: Path) -> None:
    train, connection, _, _ = service(tmp_path)
    register(train)
    event = store.events_of(connection, "P3798", kind="merge.train-registered")[0]
    events = []
    for sequence, generation in enumerate((10, 2, 1), start=100):
        copied = {**event, "seq": sequence, "payload": {**event["payload"], "generation": generation}}
        events.append(copied)

    folded = store.fold_events(events)

    assert [row["generation"] for row in folded["merge_trains"]] == [1, 2, 10]


def test_s3_fold_rejects_duplicate_registration_and_dual_terminal(tmp_path: Path) -> None:
    train, connection, _, _ = service(tmp_path)
    register(train)
    registered = store.events_of(connection, "P3798", kind="merge.train-registered")[0]
    duplicate = {**registered, "seq": int(registered["seq"]) + 1}
    with pytest.raises(LookupError, match="duplicates registered generation"):
        store.fold_events([registered, duplicate])

    superseded = {
        **registered,
        "seq": int(registered["seq"]) + 1,
        "kind": "merge.train-superseded",
        "payload": {"generation": 1},
    }
    invalidated = {
        **registered,
        "seq": int(registered["seq"]) + 2,
        "kind": "merge.train-invalidated",
        "payload": {"generation": 1, "reason": "replace", "replacement_source": "fixture", "replacement_revision": "2"},
    }
    with pytest.raises(LookupError, match="terminal generation"):
        store.fold_events([registered, superseded, invalidated])


def test_s4_explicit_history_is_provider_free_and_exposes_invalidation(tmp_path: Path) -> None:
    train, connection, _, _ = service(tmp_path)
    register(train)
    source = port.PlanSource(
        plan_id="P3798",
        milestone=7,
        integration_branch="integration/runtime-integrity",
        base_sha="a" * 40,
        quality_gates=["uv run pytest"],
        source="fixture",
        revision="replace-2",
        tasks=[port.TaskSource(fields={"id": "T1", "title": "replacement", "github_issue": 101})],
    )
    port.import_plan(connection, source, replace=True)

    train = MergeTrain(
        connection, UnavailableDispatchPlans(), UnavailableSourceGraph(), HostAuthority(authority_host_id="host-a")
    )

    page = train.status(MergeQuery(plan="P3798", generation=1))
    result = train.validate(MergeQuery(plan="P3798", generation=1))

    assert result.valid, result.findings
    assert page.train.invalidated_seq is not None
    assert page.train.invalidation_reason == "import:fixture:replace-2"
    assert page.train.replacement_source == "fixture"
    assert page.train.replacement_revision == "replace-2"
