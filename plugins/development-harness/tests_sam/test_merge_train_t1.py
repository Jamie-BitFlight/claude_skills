"""T1 public-seam tests for registered merge trains."""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
import sys
import types
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any, Generic, TypeVar

import pytest

if sys.platform == "win32":
    fcntl = types.ModuleType("fcntl")
    fcntl.LOCK_EX = 2
    fcntl.LOCK_NB = 4

    def unsupported_flock(*_args: object) -> None:
        raise OSError("fcntl.flock is unavailable on Windows")

    fcntl.flock = unsupported_flock
    sys.modules.setdefault("fcntl", fcntl)

from dh_core.ledger import store, transitions
from dh_core.merge_train import (
    DispatchMember,
    DispatchPlanDefinition,
    DispatchPlanSnapshot,
    DispatchReserved,
    HistoryQuery,
    HostAuthority,
    MergeQuery,
    MergeTrain,
    RegisterTrain,
    SourceGraphSnapshot,
)
from pydantic import ValidationError

T = TypeVar("T")


class Reader(Generic[T]):
    def __init__(self, value: T) -> None:
        self.value = value

    def read(self, _key: object) -> T:
        return self.value


def request() -> RegisterTrain:
    return RegisterTrain(plan_ref="dispatch-7", milestone=7, plan="P3798")


def windows_fcntl_bootstrap() -> str:
    """Return child-process setup for imports that only inspect non-locking surfaces."""
    return (
        "import sys, types; "
        "fcntl = types.ModuleType('fcntl'); "
        "fcntl.LOCK_EX = 2; fcntl.LOCK_NB = 4; "
        "fcntl.flock = lambda *_args: (_ for _ in ()).throw(OSError('fcntl unavailable on Windows')); "
        "sys.modules.setdefault('fcntl', fcntl); "
    )


def service(tmp_path: Path, *, host: str = "host-a") -> tuple[MergeTrain, sqlite3.Connection]:
    connection = store.open_ledger(tmp_path / "dh.db")
    transitions.create(
        connection,
        slug="3798",
        goal="test",
        plan_id="P3798",
        tasks=[
            {"id": "T1", "title": "T1", "github_issue": 101, "conflict_group": "shared"},
            {"id": "T2", "title": "T2", "github_issue": 102, "conflict_group": "shared"},
        ],
    )
    transitions.finalize(connection, "P3798")
    frozen = definition()
    dispatch_reader = Reader(
        DispatchPlanSnapshot(
            logical_id=frozen.logical_id, revision=frozen.revision, canonical_bytes=frozen.canonical_bytes()
        )
    )
    graph_reader = Reader(
        SourceGraphSnapshot(
            revision="github-1",
            milestone=frozen.milestone,
            integration_branch=frozen.integration_branch,
            baseline_sha=frozen.baseline_sha,
            members=frozen.members,
        )
    )
    return MergeTrain(connection, dispatch_reader, graph_reader, HostAuthority(authority_host_id=host)), connection


def definition() -> DispatchPlanDefinition:
    return DispatchPlanDefinition(
        logical_id="dispatch-7",
        revision="rev-1",
        milestone=7,
        plan="P3798",
        integration_branch="integration/runtime-integrity",
        baseline_sha="a" * 40,
        quality_gates=("uv run pytest",),
        members=(
            DispatchMember(issue=101, task="T1", role="maker", conflict_group="shared"),
            DispatchMember(issue=102, task="T2", role="checker", conflict_group="shared"),
        ),
    )


def test_f01_register_freezes_canonical_definition(tmp_path: Path) -> None:
    merge_train, connection = service(tmp_path)

    registered = merge_train.register(request())
    repeated = merge_train.register(request())

    assert registered.generation == 1
    assert registered.dispatch_plan_digest.startswith("sha256:")
    assert repeated.noop == "already-registered"
    assert len(store.events_of(connection, "P3798", kind="merge.train-registered")) == 1


def test_f03_raw_dispatch_refuses_registered_task_without_opening_attempt(tmp_path: Path) -> None:
    merge_train, connection = service(tmp_path)
    merge_train.register(request())

    with pytest.raises(store.Refusal, match="merge-dispatch-required"):
        transitions.dispatch(connection, "P3798", "T1")

    row = store.fetch_task(connection, "P3798", "T1")
    assert row["attempts"] == 0
    assert row["attempt_open"] == 0


def test_f03_registered_dispatch_reserves_conflict_group_atomically(tmp_path: Path) -> None:
    merge_train, _connection = service(tmp_path)
    merge_train.register(request())

    dispatched = merge_train.dispatch(DispatchReserved(plan="P3798", generation=1, task="T1"))
    with pytest.raises(store.Refusal, match="conflict-group-reserved"):
        merge_train.dispatch(DispatchReserved(plan="P3798", generation=1, task="T2"))

    assert dispatched.attempt == 1
    assert dispatched.role == "maker"
    status = merge_train.status(MergeQuery(plan="P3798"))
    assert status.reservations[0].model_dump() == {
        "plan": "P3798",
        "generation": 1,
        "conflict_group": "shared",
        "task": "T1",
        "attempt": 1,
        "role": "maker",
        "github_issue": 101,
        "active": True,
        "conclusion": None,
    }


def test_f24_host_marker_refuses_before_dispatch_mutation(tmp_path: Path) -> None:
    merge_train, connection = service(tmp_path)
    merge_train.register(request())
    wrong_host = MergeTrain(
        connection, merge_train.dispatch_plans, merge_train.source_graph, HostAuthority(authority_host_id="host-b")
    )

    with pytest.raises(store.Refusal, match="wrong-authority-host"):
        wrong_host.dispatch(DispatchReserved(plan="P3798", generation=1, task="T1"))

    assert store.fetch_task(connection, "P3798", "T1")["attempts"] == 0
    assert store.events_of(connection, "P3798", kind="merge.reserved") == []


def test_f01_registration_rejects_omitted_or_mismatched_resource(tmp_path: Path) -> None:
    merge_train, connection = service(tmp_path)
    mismatched_member = definition().members[0].model_copy(update={"conflict_group": "other"})
    merge_train.source_graph.value = merge_train.source_graph.value.model_copy(
        update={"members": (mismatched_member, definition().members[1])}
    )

    with pytest.raises(store.Refusal, match="dispatch-plan-disagreement"):
        merge_train.register(request())

    assert store.events_of(connection, "P3798", kind="merge.train-registered") == []


def test_f01_active_registration_rejects_changed_revision(tmp_path: Path) -> None:
    merge_train, connection = service(tmp_path)
    merge_train.register(request())
    changed = definition().model_copy(update={"baseline_sha": "b" * 40})
    merge_train.dispatch_plans.value = DispatchPlanSnapshot(
        logical_id=changed.logical_id, revision=changed.revision, canonical_bytes=changed.canonical_bytes()
    )
    merge_train.source_graph.value = merge_train.source_graph.value.model_copy(update={"baseline_sha": "b" * 40})

    with pytest.raises(store.Refusal, match="source-graph-stale"):
        merge_train.register(request())

    assert len(store.events_of(connection, "P3798", kind="merge.train-registered")) == 1


def test_f04_requests_forbid_caller_selected_storage_or_role() -> None:
    with pytest.raises(ValidationError):
        RegisterTrain.model_validate({
            "plan_ref": "dispatch-7",
            "milestone": 7,
            "plan": "P3798",
            "ledger_path": "/tmp/other.db",
        })
    with pytest.raises(ValidationError):
        DispatchReserved.model_validate({
            "plan": "P3798",
            "generation": 1,
            "task": "T1",
            "lock_path": "/tmp/lock",
            "role": "maker",
        })
    assert not hasattr(MergeTrain, "supersede")


def test_f03_stale_generation_cannot_dispatch(tmp_path: Path) -> None:
    merge_train, connection = service(tmp_path)
    merge_train.register(request())

    with pytest.raises(store.Refusal, match="train-generation-stale"):
        merge_train.dispatch(DispatchReserved(plan="P3798", generation=2, task="T1"))

    assert store.fetch_task(connection, "P3798", "T1")["attempts"] == 0


def test_f03_schema_has_structural_active_group_uniqueness(tmp_path: Path) -> None:
    _, connection = service(tmp_path)
    indexes = store.rows_of(connection.execute("PRAGMA index_list(merge_reservations)"))

    active = next(index for index in indexes if index["name"] == "ux_merge_reservations_active_group")
    assert active["unique"] == 1
    assert active["partial"] == 1


def test_f05_terminal_transition_releases_exact_attempt_and_group_is_reusable(tmp_path: Path) -> None:
    merge_train, connection = service(tmp_path)
    merge_train.register(request())
    first = merge_train.dispatch(DispatchReserved(plan="P3798", generation=1, task="T1"))

    transitions.state(connection, "P3798", "T1", new_status="blocked", reason="terminal", force=True)
    second = merge_train.dispatch(DispatchReserved(plan="P3798", generation=1, task="T2"))
    reservations = merge_train.status(MergeQuery(plan="P3798")).reservations

    assert first.attempt == 1
    assert second.attempt == 1
    assert [(item.task, item.active, item.conclusion) for item in reservations] == [
        ("T1", False, "state:blocked"),
        ("T2", True, None),
    ]


def independent_reservation_fold(events: list[dict[str, object]]) -> list[tuple[object, ...]]:
    """Test-owned literal event fold with no production model or transition imports."""
    rows: dict[tuple[object, ...], tuple[object, ...]] = {}
    for event in events:
        payload = event["payload"]
        assert isinstance(payload, dict)
        key = (
            event["plan"],
            payload.get("generation"),
            payload.get("conflict_group"),
            event["task"],
            payload.get("attempt"),
        )
        if event["kind"] == "merge.reserved":
            rows[key] = (*key, payload["role"], payload["github_issue"], 1, None)
        elif event["kind"] == "merge.reservation-released":
            old = rows[key]
            rows[key] = (*old[:7], 0, payload["conclusion"])
    return [rows[key] for key in sorted(rows, key=str)]


def test_f18_rebuild_matches_independent_reservation_fold(tmp_path: Path) -> None:
    merge_train, connection = service(tmp_path)
    merge_train.register(request())
    merge_train.dispatch(DispatchReserved(plan="P3798", generation=1, task="T1"))
    transitions.state(connection, "P3798", "T1", new_status="blocked", reason="terminal", force=True)
    events = [event for event in store.events_of(connection, "P3798") if str(event["kind"]).startswith("merge.res")]
    expected = independent_reservation_fold(events)

    store.rebuild(connection)
    actual = store.rows_of(
        connection.execute(
            "SELECT plan, generation, conflict_group, task, attempt, role, github_issue, active, conclusion "
            "FROM merge_reservations ORDER BY plan, generation, conflict_group, task, attempt"
        )
    )

    assert [tuple(row.values()) for row in actual] == expected
    assert merge_train.validate(MergeQuery(plan="P3798")).valid


def test_f05_validate_reports_materialized_reservation_drift(tmp_path: Path) -> None:
    merge_train, connection = service(tmp_path)
    merge_train.register(request())
    merge_train.dispatch(DispatchReserved(plan="P3798", generation=1, task="T1"))
    connection.execute("UPDATE merge_reservations SET role = 'checker'")

    result = merge_train.validate(MergeQuery(plan="P3798"))

    assert not result.valid
    assert result.findings == ["merge_reservations-projection-drift"]


def test_f03_concurrent_dispatch_has_one_linearized_winner(tmp_path: Path) -> None:
    merge_train, connection = service(tmp_path)
    merge_train.register(request())
    database = tmp_path / "dh.db"
    connection.close()

    def dispatch(task_id: str) -> str:
        worker_connection = store.open_ledger(database)
        try:
            worker = MergeTrain(
                worker_connection,
                merge_train.dispatch_plans,
                merge_train.source_graph,
                HostAuthority(authority_host_id="host-a"),
            )
            worker.dispatch(DispatchReserved(plan="P3798", generation=1, task=task_id))
        except store.Refusal as exc:
            return exc.reason
        else:
            return "reserved"
        finally:
            worker_connection.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = sorted(executor.map(dispatch, ("T1", "T2")))

    assert outcomes == ["conflict-group-reserved", "reserved"]
    verify = store.open_ledger(database)
    assert verify.execute("SELECT COUNT(*) FROM merge_reservations WHERE active = 1").fetchone()[0] == 1
    assert verify.execute("SELECT COUNT(*) FROM events WHERE kind = 'task.dispatched'").fetchone()[0] == 1


def test_f03_reservation_failure_rolls_back_opened_attempt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    merge_train, connection = service(tmp_path)
    merge_train.register(request())
    append_event = store.append_event

    def fail_reservation(
        conn: sqlite3.Connection, *, kind: str, plan: str, task: str | None, payload: Mapping[str, Any], at: datetime
    ) -> int:
        if kind == "merge.reserved":
            raise RuntimeError("injected reservation failure")
        return append_event(conn, kind=kind, plan=plan, task=task, payload=payload, at=at)

    monkeypatch.setattr(store, "append_event", fail_reservation)

    with pytest.raises(RuntimeError, match="injected reservation failure"):
        merge_train.dispatch(DispatchReserved(plan="P3798", generation=1, task="T1"))

    row = store.fetch_task(connection, "P3798", "T1")
    assert row["attempts"] == 0
    assert row["attempt_open"] == 0
    assert store.events_of(connection, "P3798", kind="task.dispatched") == []
    assert store.events_of(connection, "P3798", kind="merge.reserved") == []


@pytest.mark.parametrize("order", [(0, 1), (1, 0)])
def test_f01_canonical_registration_is_member_order_independent(tmp_path: Path, order: list[int]) -> None:
    merge_train, connection = service(tmp_path / "-".join(str(item) for item in order))
    original = definition()
    permuted = original.model_copy(update={"members": tuple(original.members[index] for index in order)})

    merge_train.dispatch_plans.value = DispatchPlanSnapshot(
        logical_id=original.logical_id, revision=original.revision, canonical_bytes=original.canonical_bytes()
    )
    first = merge_train.register(request())
    merge_train.dispatch_plans.value = DispatchPlanSnapshot(
        logical_id=permuted.logical_id, revision=permuted.revision, canonical_bytes=permuted.canonical_bytes()
    )
    merge_train.source_graph.value = merge_train.source_graph.value.model_copy(update={"members": permuted.members})
    second = merge_train.register(request())

    assert second.noop == "already-registered"
    assert second.dispatch_plan_digest == first.dispatch_plan_digest
    assert len(store.events_of(connection, "P3798", kind="merge.train-registered")) == 1


def test_f02_concurrent_identical_registration_appends_once(tmp_path: Path) -> None:
    merge_train, connection = service(tmp_path)
    database = tmp_path / "dh.db"
    connection.close()

    def register_once(_: int) -> str:
        worker_connection = store.open_ledger(database)
        try:
            view = MergeTrain(
                worker_connection,
                merge_train.dispatch_plans,
                merge_train.source_graph,
                HostAuthority(authority_host_id="host-a"),
            ).register(request())
            return view.noop or "registered"
        finally:
            worker_connection.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = sorted(executor.map(register_once, (1, 2)))

    assert outcomes == ["already-registered", "registered"]
    verify = store.open_ledger(database)
    assert verify.execute("SELECT COUNT(*) FROM merge_trains").fetchone()[0] == 1
    assert verify.execute("SELECT COUNT(*) FROM events WHERE kind = 'merge.train-registered'").fetchone()[0] == 1


def test_t1_history_returns_complete_envelopes_with_caller_pagination(tmp_path: Path) -> None:
    merge_train, _ = service(tmp_path)
    merge_train.register(request())
    merge_train.dispatch(DispatchReserved(plan="P3798", generation=1, task="T1"))

    complete = merge_train.history(HistoryQuery(plan="P3798"))
    page = merge_train.history(HistoryQuery(plan="P3798", offset=1, limit=1))

    assert complete.total == 3
    assert complete.returned == 3
    assert set(complete.events[0]) == {"seq", "at", "kind", "plan", "task", "payload"}
    assert page.returned == 1
    assert page.total == 3


def test_f03_raw_cli_dispatch_refuses_registered_member_without_mutation() -> None:
    connection = store.open_ledger()
    transitions.create(
        connection,
        slug="cli",
        goal="guard raw dispatch",
        plan_id="Pcli",
        base_sha="1" * 40,
        tasks=[{"id": "T1", "title": "maker", "github_issue": 1, "conflict_group": "source"}],
    )
    cli_definition = DispatchPlanDefinition(
        logical_id="cli-plan",
        revision="one",
        milestone=7,
        plan="Pcli",
        integration_branch="integration/cli",
        baseline_sha="1" * 40,
        quality_gates=(),
        members=(DispatchMember(issue=1, task="T1", role="maker", conflict_group="source"),),
    )
    cli_dispatch = Reader(
        DispatchPlanSnapshot(logical_id="cli-plan", revision="one", canonical_bytes=cli_definition.canonical_bytes())
    )
    cli_graph = Reader(
        SourceGraphSnapshot(
            revision="github-cli",
            milestone=7,
            integration_branch="integration/cli",
            baseline_sha="1" * 40,
            members=cli_definition.members,
        )
    )
    MergeTrain(connection, cli_dispatch, cli_graph, HostAuthority(authority_host_id="cli-host")).register(
        RegisterTrain(plan_ref="cli-plan", milestone=7, plan="Pcli")
    )
    root = Path(__file__).parents[3]
    plugin = root / "plugins" / "development-harness"
    cli = plugin / "sam_schema" / "cli.py"
    arguments = ["plan", "dispatch", "--address", "Pcli/T1"]
    if sys.platform == "win32":
        script = windows_fcntl_bootstrap() + (
            f"import runpy; sys.argv = {[str(cli), *arguments]!r}; runpy.run_path({str(cli)!r}, run_name='__main__')"
        )
        command = [sys.executable, "-c", script]
    else:
        command = [
            sys.executable,
            str(root / "scripts" / "run_bounded.py"),
            "--timeout-seconds",
            "20",
            "--",
            sys.executable,
            str(cli),
            *arguments,
        ]

    completed = subprocess.run(
        command, cwd=root, env={**os.environ, "PYTHONPATH": str(plugin)}, capture_output=True, text=True, check=False
    )

    assert completed.returncode != 0
    assert "merge-dispatch-required" in completed.stderr
    assert store.fetch_task(connection, "Pcli", "T1")["attempts"] == 0


def test_f04_installed_plugin_request_schemas_expose_no_storage_identity(tmp_path: Path) -> None:
    root = Path(__file__).parents[3]
    installed = tmp_path / "installed-dh"
    shutil.copytree(root / "plugins" / "development-harness", installed)
    script = (windows_fcntl_bootstrap() if sys.platform == "win32" else "") + (
        "import json; from dh_core.merge_train import RegisterTrain, DispatchReserved; "
        "print(json.dumps(sorted(set(RegisterTrain.model_fields) | set(DispatchReserved.model_fields))))"
    )
    completed = subprocess.run(
        [
            sys.executable,
            str(root / "scripts" / "run_bounded.py"),
            "--timeout-seconds",
            "20",
            "--",
            sys.executable,
            "-c",
            script,
        ],
        cwd=installed,
        env={**os.environ, "PYTHONPATH": str(installed)},
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    fields = set(json.loads(completed.stdout))
    assert not fields & {"db", "database", "ledger_path", "lock_path", "path", "role"}
