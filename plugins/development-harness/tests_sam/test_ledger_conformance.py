"""Conformance tests driving ``dh_core.ledger`` through every ``ledger_spec.TRANSITIONS`` entry.

One parametrised case per specification entry, identified as ``<command>/<from_status>``. Each case
builds a ledger whose task sits in that entry's ``from_status``, runs the entry's command, and then
asserts one of two things the specification states:

* the first failing check's reason arrives as a :class:`dh_core.ledger.store.Refusal` carrying that
  code, and nothing was written; or
* every effect the entry names holds, every event it names was appended, its ``to_status`` was
  reached, and a fold of the append-only log reproduces the materialised row.

Nothing here is skipped: an entry with no scenario fails, so a transition the package does not
implement is a red test rather than a silent gap.

A second group at the foot of the file holds ``update --set`` to the same provenance statement
column by column: ``ledger_spec.COLUMNS`` gives ``tasks.status``, ``started``, ``completed`` and
``last_activity`` ``set_by`` lists that name the lifecycle events and not ``task.fields``, so an
``update`` may not move any of them.

The fold is the specification's own provenance statement run backwards. ``ledger_spec.COLUMNS``
says which event kinds set each column and ``ledger_spec.EVENTS`` says what each kind's payload
carries, so the log determines a column's value whenever the last event that set it declares the
column in its payload. Where the last setter does not carry the value — ``task.dispatched`` setting
``status``, ``lease.renewed`` setting ``expires`` — the log cannot reproduce it, and the test falls
back to the weaker statement the specification still makes: a column that changed must be named in
the ``set_by`` of an event the command appended.
"""

from __future__ import annotations

import contextlib
import json
import sqlite3
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

import pytest
from dh_core import ledger_spec as spec
from dh_core.ledger import port, store, transitions
from pydantic import BaseModel, ConfigDict, Field
from sam_schema.core.models import PlanState

if TYPE_CHECKING:  # pragma: no cover - typing only
    from collections.abc import Iterator, Mapping, Sequence
    from pathlib import Path

# ---------------------------------------------------------------------------
# Values read from the specification
# ---------------------------------------------------------------------------

NOT_STARTED = spec.Status.NOT_STARTED.value
IN_PROGRESS = spec.Status.IN_PROGRESS.value
COMPLETE = spec.Status.COMPLETE.value
BLOCKED = spec.Status.BLOCKED.value
DEFERRED = spec.Status.DEFERRED.value
SKIPPED = spec.Status.SKIPPED.value
FAILED = spec.Status.FAILED.value

STATUS_VALUES = {s.value for s in spec.Status}
REASON_KIND = {reason.code: reason.kind for reason in spec.REASONS}
DECLARED_PAYLOAD = {event.kind: set(event.payload) for event in spec.EVENTS}
STORED_COLUMNS: dict[str, list[spec.Column]] = store.TABLES
SET_BY: dict[tuple[str, str], set[str]] = {
    (column.table, column.name): set(column.set_by)
    for column in spec.COLUMNS
    if column.provenance is not spec.Provenance.DERIVED
}
TABLE_NAMES: tuple[str, ...] = tuple(STORED_COLUMNS)
FOLD_TABLES: tuple[str, ...] = ("plans", "tasks")
MAX_ATTEMPTS = next(entry.default for entry in spec.CONFIG if entry.key == "loop.max_attempts")

TTL = 60
"""The lease length every scenario dispatches with, so ``expires`` is checkable against it."""

MISSING = object()
"""Sentinel for a column the log cannot reproduce."""


# ---------------------------------------------------------------------------
# Snapshots of the whole database
# ---------------------------------------------------------------------------


class Snapshot(BaseModel):
    """Every materialised row and every logged event at one instant."""

    tables: dict[str, dict[str, dict[str, Any]]] = Field(default_factory=dict)
    events: list[dict[str, Any]] = Field(default_factory=list)


def select_all(conn: sqlite3.Connection, table: str) -> list[dict[str, Any]]:
    """Read every row of one table."""
    return store.rows_of(conn.execute(f"SELECT * FROM {table}"))


def row_key(table: str, row: Mapping[str, Any]) -> str:
    """Return one row's identity as a string, from the store's primary key."""
    return "|".join(str(row[name]) for name in store.PRIMARY_KEYS[table])


def task_key(plan: str, task: str) -> str:
    """Return the ``tasks`` key for one address."""
    return f"{plan}|{task}"


def row_plan(table: str, row: Mapping[str, Any]) -> str:
    """Return the plan a row belongs to."""
    return str(row["plan_id"]) if table == "plans" else str(row["plan"])


def row_task(table: str, row: Mapping[str, Any]) -> str | None:
    """Return the task a row belongs to, or None for a plan-scoped row."""
    if table == "tasks":
        return str(row["id"])
    if table == "sections":
        return str(row["task"])
    return None


def read_events(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Read the whole log, oldest first, with each payload decoded."""
    rows = store.rows_of(conn.execute("SELECT seq, kind, plan, task, payload FROM events ORDER BY seq"))
    for row in rows:
        raw = row["payload"]
        row["payload"] = json.loads(raw) if isinstance(raw, str) else raw
    return rows


def snapshot(conn: sqlite3.Connection) -> Snapshot:
    """Capture every row and every event."""
    tables = {table: {row_key(table, row): row for row in select_all(conn, table)} for table in TABLE_NAMES}
    return Snapshot(tables=tables, events=read_events(conn))


def appended_events(before: Snapshot, after: Snapshot) -> list[dict[str, Any]]:
    """Return the events appended between two snapshots."""
    return after.events[len(before.events) :]


def baseline(table: str) -> dict[str, Any]:
    """Return the row a table's DDL defaults describe, for a row that did not exist before."""
    values: dict[str, Any] = {}
    for column in STORED_COLUMNS[table]:
        if store.nullable(column):
            values[column.name] = None
        else:
            values[column.name] = 0 if store.affinity(column) == store.INTEGER else ""
    return values


# ---------------------------------------------------------------------------
# What the specification says the log carries
# ---------------------------------------------------------------------------


def assert_payload_shape(events: Sequence[Mapping[str, Any]]) -> None:
    """Every appended event carries exactly the payload ``ledger_spec.EVENTS`` declares."""
    for event in events:
        kind = str(event["kind"])
        assert kind in DECLARED_PAYLOAD, f"{kind} is not an event kind in ledger_spec.EVENTS"
        assert set(event["payload"]) == DECLARED_PAYLOAD[kind], (
            f"{kind} payload {sorted(event['payload'])} but ledger_spec declares {sorted(DECLARED_PAYLOAD[kind])}"
        )


def setters_for(events: Sequence[Mapping[str, Any]], table: str, name: str, plan: str, task: str | None) -> list[Any]:
    """Return the events that ``ledger_spec.COLUMNS`` says may set one row's column."""
    kinds = SET_BY[table, name]
    return [
        event
        for event in events
        if event["kind"] in kinds
        and event["plan"] == plan
        and (event["task"] is None or task is None or event["task"] == task)
    ]


def assert_provenance(before: Snapshot, after: Snapshot, events: Sequence[Mapping[str, Any]]) -> None:
    """Every column that changed is named in the ``set_by`` of an event this command appended."""
    for table in TABLE_NAMES:
        default = baseline(table)
        for key, row in after.tables[table].items():
            prior = before.tables[table].get(key, default)
            for name, value in row.items():
                if value == prior.get(name):
                    continue
                matched = setters_for(events, table, name, row_plan(table, row), row_task(table, row))
                assert matched, (
                    f"{table}.{name} changed to {value!r} on {key} but no appended event "
                    f"of {sorted(SET_BY[table, name])} names it"
                )


def folded_value(events: Sequence[Mapping[str, Any]], table: str, name: str, plan: str, task: str | None) -> Any:
    """Fold the log for one column, or return :data:`MISSING` when the log cannot reproduce it."""
    value: Any = MISSING
    for event in setters_for(events, table, name, plan, task):
        kind = str(event["kind"])
        payload = event["payload"]
        declared = DECLARED_PAYLOAD[kind]
        if "changed" in declared:
            changed = payload.get("changed") or {}
            if isinstance(changed, dict) and name in changed:
                value = store.encode(changed[name])
            continue
        if name in declared:
            assert name in payload, f"{kind} declares {name} in its payload but the appended event omits it"
            value = store.encode(payload[name])
            continue
        value = MISSING
    return value


def assert_fold(after: Snapshot) -> None:
    """A fold of the log reproduces every materialised value the log's payloads carry."""
    for table in FOLD_TABLES:
        for key, row in after.tables[table].items():
            plan, task = row_plan(table, row), row_task(table, row)
            for column in STORED_COLUMNS[table]:
                value = folded_value(after.events, table, column.name, plan, task)
                if value is MISSING:
                    continue
                assert row[column.name] == value, (
                    f"folding the log gives {table}.{column.name} = {value!r} on {key}, "
                    f"but the row holds {row[column.name]!r}"
                )


# ---------------------------------------------------------------------------
# The case a scenario builds, and the values its checkers read
# ---------------------------------------------------------------------------


class Verify(BaseModel):
    """What an effect checker reads: the ledger, the two snapshots, and what the run returned."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    conn: sqlite3.Connection
    plan: str
    task: str
    before: Snapshot
    after: Snapshot
    result: Any = None
    extras: list[Any] = Field(default_factory=list)
    started: datetime
    ended: datetime


class Case(BaseModel):
    """One arranged ledger, the run that exercises a transition, and what to assert about it."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    conn: sqlite3.Connection
    plan: str = ""
    task: str = ""
    run: Callable[[], Any]
    extra: list[Callable[[], Any]] = Field(default_factory=list)
    refusal: str = ""
    noop: str = ""
    events: tuple[str, ...] = ()
    status: str = ""
    effects: dict[str, Callable[[Verify], None]] = Field(default_factory=dict)
    why: str = ""
    """Why the run emits fewer events than the entry lists; required when it does."""
    quiet: Callable[[], Any] | None = None
    """A call that passes every check of an entry that names no effect and no event."""


def after_task(verify: Verify, task: str | None = None) -> dict[str, Any]:
    """Return one task row from the after snapshot."""
    return verify.after.tables["tasks"][task_key(verify.plan, task or verify.task)]


def before_task(verify: Verify, task: str | None = None) -> dict[str, Any]:
    """Return one task row from the before snapshot."""
    return verify.before.tables["tasks"][task_key(verify.plan, task or verify.task)]


def after_plan(verify: Verify, plan: str | None = None) -> dict[str, Any]:
    """Return one plan row from the after snapshot."""
    return verify.after.tables["plans"][plan or verify.plan]


def column_is(name: str, expected: Any) -> Callable[[Verify], None]:
    """Assert one task column holds a literal value."""

    def check(verify: Verify) -> None:
        assert after_task(verify)[name] == expected, f"tasks.{name}"

    return check


def column_unchanged(name: str) -> Callable[[Verify], None]:
    """Assert one task column is what it was before the run."""

    def check(verify: Verify) -> None:
        assert after_task(verify)[name] == before_task(verify)[name], f"tasks.{name}"

    return check


def column_recent(name: str) -> Callable[[Verify], None]:
    """Assert one task column holds an instant inside the run."""

    def check(verify: Verify) -> None:
        moment = store.moment(after_task(verify)[name])
        assert moment is not None, f"tasks.{name} is null"
        assert verify.started <= moment <= verify.ended, f"tasks.{name} = {moment} outside the run"

    return check


def expires_one_ttl_on(ttl: int) -> Callable[[Verify], None]:
    """Assert ``expires`` is one lease length past the activity the transition recorded."""

    def check(verify: Verify) -> None:
        row = after_task(verify)
        activity, deadline = store.moment(row["last_activity"]), store.moment(row["expires"])
        assert activity is not None
        assert deadline is not None
        assert deadline == activity + timedelta(seconds=ttl), f"expires {deadline} is not {ttl}s past {activity}"

    return check


def first_renewed_is_now() -> Callable[[Verify], None]:
    """Assert ``first_renewed`` took the renewal instant, having been null."""

    def check(verify: Verify) -> None:
        row = after_task(verify)
        assert before_task(verify)["first_renewed"] is None, "first_renewed was already set"
        assert row["first_renewed"] == row["last_activity"], "first_renewed is not the renewal instant"

    return check


def cascade_to(*skipped: str) -> Callable[[Verify], None]:
    """Assert the cascade skipped exactly these dependents, each with its ``cascade`` reason."""

    def check(verify: Verify) -> None:
        assert list(verify.result.cascaded) == list(skipped), f"cascaded {verify.result.cascaded}"
        for dependent in skipped:
            assert after_task(verify, dependent)["status"] == SKIPPED
            reason = transitions.latest_state_reason(verify.conn, verify.plan, dependent)
            assert reason == transitions.cascade_code(verify.task), f"{dependent} reason {reason}"

    return check


def reversal_to(*restored: str) -> Callable[[Verify], None]:
    """Assert the reversal returned exactly these dependents to not-started."""

    def check(verify: Verify) -> None:
        assert list(verify.result.reversed_tasks) == list(restored), f"reversed {verify.result.reversed_tasks}"
        for dependent in restored:
            assert after_task(verify, dependent)["status"] == NOT_STARTED
            reason = transitions.latest_state_reason(verify.conn, verify.plan, dependent)
            assert reason == transitions.reversal_code(verify.task), f"{dependent} reason {reason}"

    return check


def status_only(expected: str) -> Callable[[Verify], None]:
    """Assert the addressed task reached a status and no other task moved."""

    def check(verify: Verify) -> None:
        assert after_task(verify)["status"] == expected
        for key, row in verify.after.tables["tasks"].items():
            if key == task_key(verify.plan, verify.task):
                continue
            assert row["status"] == verify.before.tables["tasks"][key]["status"], f"{key} moved"

    return check


# ---------------------------------------------------------------------------
# Building a ledger and reaching a status
# ---------------------------------------------------------------------------


def ledger(tmp_path: Path) -> sqlite3.Connection:
    """Open a ledger in a temporary directory."""
    return store.open_ledger(tmp_path / store.DATABASE_NAME)


def one_task() -> list[dict[str, Any]]:
    """Return a single task definition."""
    return [{"id": "T1", "title": "first"}]


def two_tasks() -> list[dict[str, Any]]:
    """Return a task and a dependent, so a cascade has somewhere to go."""
    return [{"id": "T1", "title": "first"}, {"id": "T2", "title": "second", "dependencies": ["T1"]}]


def make_plan(conn: sqlite3.Connection, tasks: Sequence[Mapping[str, Any]] = ()) -> str:
    """Create a plan and return its id."""
    return str(transitions.create(conn, slug="feature", goal="goal", tasks=list(tasks)).plan)


def add_reports(conn: sqlite3.Connection, plan: str, task: str, attempt: int) -> None:
    """Append every report section for one attempt, so the report check passes."""
    for name in spec.REPORT_SECTIONS:
        transitions.update(conn, plan, task, attempt=attempt, section=name, section_content="body")


def dispatch_task(conn: sqlite3.Connection, plan: str, task: str = "T1") -> int:
    """Dispatch one task and return the attempt it opened."""
    return int(transitions.dispatch(conn, plan, task, ttl_seconds=TTL).attempt or 0)


def reach(conn: sqlite3.Connection, plan: str, status: str, task: str = "T1") -> None:
    """Move a task from not-started into one of the specification's statuses."""
    if status == NOT_STARTED:
        return
    if status in {DEFERRED, SKIPPED}:
        transitions.state(conn, plan, task, new_status=status, reason="orchestrator")
        return
    attempt = dispatch_task(conn, plan, task)
    if status == IN_PROGRESS:
        return
    if status == COMPLETE:
        add_reports(conn, plan, task, attempt)
        transitions.finish(conn, plan, task, attempt=attempt, result=COMPLETE)
        return
    transitions.finish(conn, plan, task, attempt=attempt, result=status)


def attempts_of(conn: sqlite3.Connection, plan: str, task: str = "T1") -> int:
    """Return a task's current attempt number."""
    return int(store.fetch_task(conn, plan, task)["attempts"] or 0)


def arranged(tmp_path: Path, status: str, tasks: Sequence[Mapping[str, Any]] = ()) -> tuple[Any, str]:
    """Open a ledger holding one plan whose T1 sits in a status."""
    conn = ledger(tmp_path)
    plan = make_plan(conn, tasks or one_task())
    reach(conn, plan, status)
    return conn, plan


# ---------------------------------------------------------------------------
# The scenario registry
# ---------------------------------------------------------------------------

SCENARIOS: dict[tuple[str, str], Callable[[Path], Case]] = {}


def register(command: str, from_status: str) -> Callable[[Callable[[Path], Case]], Callable[[Path], Case]]:
    """Register the scenario for one ``ledger_spec.TRANSITIONS`` entry."""

    def decorate(builder: Callable[[Path], Case]) -> Callable[[Path], Case]:
        SCENARIOS[command, from_status] = builder
        return builder

    return decorate


# --- dispatch ---------------------------------------------------------------


@register("dispatch", NOT_STARTED)
def dispatch_open(tmp_path: Path) -> Case:
    conn, plan = arranged(tmp_path, NOT_STARTED)
    worktree = str(tmp_path / "worktree")
    return Case(
        conn=conn,
        plan=plan,
        task="T1",
        run=lambda: transitions.dispatch(conn, plan, "T1", ttl_seconds=TTL, worktree=worktree),
        events=("task.dispatched",),
        status=IN_PROGRESS,
        effects={
            "attempts": column_is("attempts", 1),
            "attempt_open": column_is("attempt_open", 1),
            "ttl_seconds": column_is("ttl_seconds", TTL),
            "worktree": column_is("worktree", worktree),
            "expires": expires_one_ttl_on(TTL),
            "first_renewed": column_is("first_renewed", None),
            "started": column_recent("started"),
            "last_activity": column_recent("last_activity"),
            "result": column_is("result", None),
            "note": column_is("note", None),
            "settled": column_is("settled", 0),
            "return_text": column_is("return_text", None),
            "completed": column_is("completed", None),
        },
    )


def dispatch_refusal(status: str, code: str) -> Callable[[Path], Case]:
    """Build the scenario for a ``dispatch`` entry that cannot open an attempt."""

    def build(tmp_path: Path) -> Case:
        conn, plan = arranged(tmp_path, status)
        return Case(conn=conn, plan=plan, task="T1", run=lambda: transitions.dispatch(conn, plan, "T1"), refusal=code)

    return build


for _status, _code in (
    (IN_PROGRESS, "leased"),
    (COMPLETE, "not-ready"),
    (BLOCKED, "not-ready"),
    (DEFERRED, "not-ready"),
    (SKIPPED, "not-ready"),
    (FAILED, "not-ready"),
):
    SCENARIOS["dispatch", _status] = dispatch_refusal(_status, _code)


# --- read -------------------------------------------------------------------


@register("read", IN_PROGRESS)
def read_renews(tmp_path: Path) -> Case:
    conn, plan = arranged(tmp_path, IN_PROGRESS)
    return Case(
        conn=conn,
        plan=plan,
        task="T1",
        run=lambda: transitions.read(conn, plan, "T1", attempt=1),
        events=("lease.renewed",),
        effects={
            "expires": expires_one_ttl_on(TTL),
            "last_activity": column_recent("last_activity"),
            "first_renewed": first_renewed_is_now(),
        },
    )


def stale_attempt_refusal(status: str, call: Callable[[sqlite3.Connection, str, int], Any]) -> Callable[[Path], Case]:
    """Build the scenario for an entry whose first check is ``stale-attempt``."""

    def build(tmp_path: Path) -> Case:
        conn, plan = arranged(tmp_path, status)
        current = attempts_of(conn, plan)
        return Case(
            conn=conn,
            plan=plan,
            task="T1",
            run=lambda: call(conn, plan, current + 1),
            refusal="stale-attempt",
            quiet=lambda: call(conn, plan, current),
        )

    return build


def read_call(conn: sqlite3.Connection, plan: str, attempt: int) -> Any:
    return transitions.read(conn, plan, "T1", attempt=attempt)


def renew_call(conn: sqlite3.Connection, plan: str, attempt: int) -> Any:
    return transitions.renew(conn, plan, "T1", attempt=attempt)


def finish_call(conn: sqlite3.Connection, plan: str, attempt: int) -> Any:
    return transitions.finish(conn, plan, "T1", attempt=attempt, result=COMPLETE)


def settle_call(conn: sqlite3.Connection, plan: str, attempt: int) -> Any:
    return transitions.settle(conn, plan, "T1", attempt=attempt, return_text="returned")


for _status in (NOT_STARTED, COMPLETE, BLOCKED, DEFERRED, SKIPPED, FAILED):
    SCENARIOS["read", _status] = stale_attempt_refusal(_status, read_call)
    SCENARIOS["renew", _status] = stale_attempt_refusal(_status, renew_call)
    SCENARIOS["finish", _status] = stale_attempt_refusal(_status, finish_call)


for _status in (NOT_STARTED, DEFERRED, SKIPPED):
    SCENARIOS["settle", _status] = stale_attempt_refusal(_status, settle_call)


# --- update -----------------------------------------------------------------


def section_appended(name: str, attempt: int, content: str) -> Callable[[Verify], None]:
    """Assert one section row landed with the attempt tag the transition names."""

    def sections_of(snap: Snapshot, task: str) -> list[dict[str, Any]]:
        return [row for row in snap.tables["sections"].values() if row["task"] == task]

    def check(verify: Verify) -> None:
        rows = sections_of(verify.after, verify.task)
        assert len(rows) == len(sections_of(verify.before, verify.task)) + 1, "one section row per --append-section"
        matching = [row for row in rows if row["name"] == name]
        assert matching, f"no section named {name}"
        assert matching[-1]["attempt"] == attempt, "the section is not tagged with tasks.attempts"
        assert matching[-1]["content"] == content

    return check


@register("update", IN_PROGRESS)
def update_in_progress(tmp_path: Path) -> Case:
    conn, plan = arranged(tmp_path, IN_PROGRESS)
    return Case(
        conn=conn,
        plan=plan,
        task="T1",
        run=lambda: transitions.update(
            conn, plan, "T1", attempt=1, section="Notes", section_content="body", values={"title": "renamed"}
        ),
        extra=[lambda: transitions.update(conn, plan, values={"description": "plan text"})],
        events=("task.section", "task.fields", "plan.fields", "lease.renewed"),
        effects={
            "sections": section_appended("Notes", 1, "body"),
            "task model fields": column_is("title", "renamed"),
            "expires": expires_one_ttl_on(TTL),
            "last_activity": column_recent("last_activity"),
            "first_renewed": first_renewed_is_now(),
        },
    )


def update_fields_only(status: str) -> Callable[[Path], Case]:
    """Build the ``update`` scenario for a task that holds no open attempt."""

    def build(tmp_path: Path) -> Case:
        conn, plan = arranged(tmp_path, status)
        return Case(
            conn=conn,
            plan=plan,
            task="T1",
            run=lambda: transitions.update(conn, plan, "T1", values={"title": "renamed"}),
            extra=[lambda: transitions.update(conn, plan, values={"description": "plan text"})],
            events=("task.fields", "plan.fields"),
            effects={"task model fields": column_is("title", "renamed")},
        )

    return build


for _status in (NOT_STARTED, COMPLETE, BLOCKED, DEFERRED, SKIPPED, FAILED):
    SCENARIOS["update", _status] = update_fields_only(_status)


# --- renew ------------------------------------------------------------------


@register("renew", IN_PROGRESS)
def renew_in_progress(tmp_path: Path) -> Case:
    conn, plan = arranged(tmp_path, IN_PROGRESS)
    return Case(
        conn=conn,
        plan=plan,
        task="T1",
        run=lambda: transitions.renew(conn, plan, "T1", attempt=1),
        events=("lease.renewed",),
        effects={
            "expires": expires_one_ttl_on(TTL),
            "last_activity": column_recent("last_activity"),
            "first_renewed": first_renewed_is_now(),
        },
    )


# --- finish -----------------------------------------------------------------


@register("finish", IN_PROGRESS)
def finish_failed(tmp_path: Path) -> Case:
    conn, plan = arranged(tmp_path, NOT_STARTED, two_tasks())
    dispatch_task(conn, plan)
    return Case(
        conn=conn,
        plan=plan,
        task="T1",
        run=lambda: transitions.finish(conn, plan, "T1", attempt=1, result=FAILED, note="gates red"),
        events=("task.finished", "task.state"),
        status=FAILED,
        effects={
            "attempt_open": column_is("attempt_open", 0),
            "result": column_is("result", FAILED),
            "note": column_is("note", "gates red"),
            "completed": column_is("completed", None),
            "status": cascade_to("T2"),
        },
    )


# --- settle -----------------------------------------------------------------


@register("settle", IN_PROGRESS)
def settle_in_progress(tmp_path: Path) -> Case:
    conn, plan = arranged(tmp_path, IN_PROGRESS)
    return Case(
        conn=conn,
        plan=plan,
        task="T1",
        run=lambda: transitions.settle(conn, plan, "T1", attempt=1, return_text="harness said so"),
        events=("task.settled",),
        effects={
            "settled": column_is("settled", 1),
            "return_text": column_is("return_text", "harness said so"),
            "attempt_open": column_is("attempt_open", 0),
        },
    )


def settle_closed(status: str) -> Callable[[Path], Case]:
    """Build the ``settle`` scenario for a task whose attempt is already closed."""

    def build(tmp_path: Path) -> Case:
        conn, plan = arranged(tmp_path, status)
        attempt = attempts_of(conn, plan)
        return Case(
            conn=conn,
            plan=plan,
            task="T1",
            run=lambda: transitions.settle(conn, plan, "T1", attempt=attempt, return_text="harness said so"),
            events=("task.settled",),
            effects={"settled": column_is("settled", 1), "return_text": column_is("return_text", "harness said so")},
        )

    return build


for _status in (COMPLETE, FAILED, BLOCKED):
    SCENARIOS["settle", _status] = settle_closed(_status)


# --- accept -----------------------------------------------------------------


@register("accept", COMPLETE)
def accept_complete(tmp_path: Path) -> Case:
    conn, plan = arranged(tmp_path, COMPLETE)
    return Case(
        conn=conn,
        plan=plan,
        task="T1",
        run=lambda: transitions.accept(conn, plan, "T1", note="judged"),
        events=("task.accepted",),
        effects={"accepted": column_is("accepted", 1)},
    )


@register("accept", IN_PROGRESS)
def accept_returned(tmp_path: Path) -> Case:
    conn, plan = arranged(tmp_path, IN_PROGRESS)
    add_reports(conn, plan, "T1", 1)
    transitions.settle(conn, plan, "T1", attempt=1, return_text="harness returned")
    return Case(
        conn=conn,
        plan=plan,
        task="T1",
        run=lambda: transitions.accept(conn, plan, "T1", note="judged"),
        events=("task.state", "task.accepted"),
        status=COMPLETE,
        effects={"completed": column_recent("completed"), "accepted": column_is("accepted", 1)},
    )


def accept_refusal(status: str) -> Callable[[Path], Case]:
    """Build the ``accept`` scenario for a task that is not complete and not returned."""

    def build(tmp_path: Path) -> Case:
        conn, plan = arranged(tmp_path, status)
        return Case(
            conn=conn, plan=plan, task="T1", run=lambda: transitions.accept(conn, plan, "T1"), refusal="not-complete"
        )

    return build


for _status in (NOT_STARTED, FAILED, BLOCKED, DEFERRED, SKIPPED):
    SCENARIOS["accept", _status] = accept_refusal(_status)


# --- reclaim ----------------------------------------------------------------


@register("reclaim", NOT_STARTED)
def reclaim_already_open(tmp_path: Path) -> Case:
    conn, plan = arranged(tmp_path, NOT_STARTED)
    return Case(
        conn=conn,
        plan=plan,
        task="T1",
        run=lambda: transitions.reclaim(conn, plan, "T1", reason="send back"),
        noop="already-open",
    )


def reclaim_effects(allowed: int, restored: Callable[[Verify], None]) -> dict[str, Callable[[Verify], None]]:
    """Return the checkers for every effect the ``reclaim`` entry names."""
    return {
        "attempts_allowed": column_is("attempts_allowed", allowed),
        "attempt_open": column_is("attempt_open", 0),
        "result": column_is("result", None),
        "note": column_is("note", None),
        "settled": column_is("settled", 0),
        "return_text": column_is("return_text", None),
        "completed": column_is("completed", None),
        "accepted": column_is("accepted", 0),
        "response": column_is("response", "read this first"),
        "status": restored,
    }


NO_TASK_STATE = "task.state rows only for the reversal, which applies when from_status is failed"


@register("reclaim", IN_PROGRESS)
def reclaim_returned(tmp_path: Path) -> Case:
    conn, plan = arranged(tmp_path, IN_PROGRESS)
    transitions.settle(conn, plan, "T1", attempt=1, return_text="harness returned")
    return Case(
        conn=conn,
        plan=plan,
        task="T1",
        run=lambda: transitions.reclaim(conn, plan, "T1", reason="send back", response="read this first"),
        events=("task.reclaimed",),
        status=NOT_STARTED,
        effects=reclaim_effects(MAX_ATTEMPTS, status_only(NOT_STARTED)),
        why=NO_TASK_STATE,
    )


@register("reclaim", COMPLETE)
def reclaim_complete(tmp_path: Path) -> Case:
    conn, plan = arranged(tmp_path, COMPLETE)
    return Case(
        conn=conn,
        plan=plan,
        task="T1",
        run=lambda: transitions.reclaim(
            conn, plan, "T1", reason="judge said no", response="read this first", more_attempts=True
        ),
        events=("task.reclaimed",),
        status=NOT_STARTED,
        effects=reclaim_effects(MAX_ATTEMPTS * 2, status_only(NOT_STARTED)),
        why=NO_TASK_STATE,
    )


@register("reclaim", BLOCKED)
def reclaim_needs_input(tmp_path: Path) -> Case:
    conn, plan = arranged(tmp_path, IN_PROGRESS)
    transitions.finish(conn, plan, "T1", attempt=1, result=transitions.NEEDS_INPUT)
    return Case(
        conn=conn,
        plan=plan,
        task="T1",
        run=lambda: transitions.reclaim(conn, plan, "T1", reason="answered", response="read this first"),
        events=("task.reclaimed",),
        status=NOT_STARTED,
        effects=reclaim_effects(MAX_ATTEMPTS + 1, status_only(NOT_STARTED)),
        why=NO_TASK_STATE,
    )


def reclaim_untouched(status: str) -> Callable[[Path], Case]:
    """Build the ``reclaim`` scenario for a task the orchestrator set aside without a runner."""

    def build(tmp_path: Path) -> Case:
        conn, plan = arranged(tmp_path, status)
        return Case(
            conn=conn,
            plan=plan,
            task="T1",
            run=lambda: transitions.reclaim(conn, plan, "T1", reason="back on", response="read this first"),
            events=("task.reclaimed",),
            status=NOT_STARTED,
            effects=reclaim_effects(MAX_ATTEMPTS, status_only(NOT_STARTED)),
            why=NO_TASK_STATE,
        )

    return build


for _status in (DEFERRED, SKIPPED):
    SCENARIOS["reclaim", _status] = reclaim_untouched(_status)


@register("reclaim", FAILED)
def reclaim_failed(tmp_path: Path) -> Case:
    conn, plan = arranged(tmp_path, NOT_STARTED, two_tasks())
    dispatch_task(conn, plan)
    transitions.finish(conn, plan, "T1", attempt=1, result=FAILED)
    return Case(
        conn=conn,
        plan=plan,
        task="T1",
        run=lambda: transitions.reclaim(conn, plan, "T1", reason="try again", response="read this first"),
        events=("task.reclaimed", "task.state"),
        status=NOT_STARTED,
        effects=reclaim_effects(MAX_ATTEMPTS, reversal_to("T2")),
    )


# --- state ------------------------------------------------------------------


def state_effects(
    accepted: Callable[[Verify], None], completed: Callable[[Verify], None], status: Callable[[Verify], None]
) -> dict[str, Callable[[Verify], None]]:
    """Return the checkers for every effect the ``state`` entry names."""
    return {
        "attempt_open": column_is("attempt_open", 0),
        "accepted": accepted,
        "completed": completed,
        "status": status,
    }


@register("state", NOT_STARTED)
def state_not_started(tmp_path: Path) -> Case:
    conn, plan = arranged(tmp_path, NOT_STARTED, two_tasks())
    return Case(
        conn=conn,
        plan=plan,
        task="T1",
        run=lambda: transitions.state(conn, plan, "T1", new_status=FAILED, reason="abandoned"),
        events=("task.state",),
        status=FAILED,
        effects=state_effects(column_is("accepted", 0), column_is("completed", None), cascade_to("T2")),
    )


@register("state", IN_PROGRESS)
def state_in_progress(tmp_path: Path) -> Case:
    conn, plan = arranged(tmp_path, NOT_STARTED, two_tasks())
    dispatch_task(conn, plan)
    return Case(
        conn=conn,
        plan=plan,
        task="T1",
        run=lambda: transitions.state(conn, plan, "T1", new_status=FAILED, reason="abandoned", force=True),
        events=("task.state",),
        status=FAILED,
        effects=state_effects(column_is("accepted", 0), column_is("completed", None), cascade_to("T2")),
    )


@register("state", COMPLETE)
def state_complete(tmp_path: Path) -> Case:
    conn, plan = arranged(tmp_path, COMPLETE)
    transitions.accept(conn, plan, "T1")
    return Case(
        conn=conn,
        plan=plan,
        task="T1",
        run=lambda: transitions.state(conn, plan, "T1", new_status=DEFERRED, reason="parked", force=True),
        events=("task.state",),
        status=DEFERRED,
        effects=state_effects(column_is("accepted", 0), column_unchanged("completed"), status_only(DEFERRED)),
    )


@register("state", BLOCKED)
def state_blocked(tmp_path: Path) -> Case:
    conn, plan = arranged(tmp_path, IN_PROGRESS)
    add_reports(conn, plan, "T1", 1)
    transitions.finish(conn, plan, "T1", attempt=1, result=BLOCKED)
    return Case(
        conn=conn,
        plan=plan,
        task="T1",
        run=lambda: transitions.state(conn, plan, "T1", new_status=COMPLETE, reason="done by hand"),
        events=("task.state",),
        status=COMPLETE,
        effects=state_effects(column_is("accepted", 0), column_recent("completed"), status_only(COMPLETE)),
    )


@register("state", DEFERRED)
def state_deferred(tmp_path: Path) -> Case:
    conn, plan = arranged(tmp_path, DEFERRED)
    return Case(
        conn=conn,
        plan=plan,
        task="T1",
        run=lambda: transitions.state(conn, plan, "T1", new_status=SKIPPED, reason="dropped"),
        events=("task.state",),
        status=SKIPPED,
        effects=state_effects(column_is("accepted", 0), column_is("completed", None), status_only(SKIPPED)),
    )


@register("state", SKIPPED)
def state_skipped(tmp_path: Path) -> Case:
    conn, plan = arranged(tmp_path, NOT_STARTED, two_tasks())
    transitions.state(conn, plan, "T1", new_status=SKIPPED, reason="dropped")
    return Case(
        conn=conn,
        plan=plan,
        task="T1",
        run=lambda: transitions.state(conn, plan, "T1", new_status=FAILED, reason="abandoned"),
        events=("task.state",),
        status=FAILED,
        effects=state_effects(column_is("accepted", 0), column_is("completed", None), cascade_to("T2")),
    )


@register("state", FAILED)
def state_failed(tmp_path: Path) -> Case:
    conn, plan = arranged(tmp_path, FAILED)
    return Case(
        conn=conn,
        plan=plan,
        task="T1",
        run=lambda: transitions.state(conn, plan, "T1", new_status=BLOCKED, reason="waiting on a person"),
        events=("task.state",),
        status=BLOCKED,
        effects=state_effects(column_is("accepted", 0), column_unchanged("completed"), status_only(BLOCKED)),
    )


# --- plan-scoped ------------------------------------------------------------


@register("create", spec.ANY)
def create_plan(tmp_path: Path) -> Case:
    conn = ledger(tmp_path)

    def plans_row(verify: Verify) -> None:
        created = str(verify.result.plan)
        assert [key for key in verify.after.tables["plans"] if key == created] == [created]
        drafting = str(verify.extras[0].plan)
        assert after_plan(verify, drafting)["state"] == PlanState.DRAFTING.value

    def tasks_rows(verify: Verify) -> None:
        created, drafting = str(verify.result.plan), str(verify.extras[0].plan)
        rows = verify.after.tables["tasks"]
        assert [key for key in rows if rows[key]["plan"] == created] == [task_key(created, "T1")]
        assert not [key for key in rows if rows[key]["plan"] == drafting]

    return Case(
        conn=conn,
        run=lambda: transitions.create(conn, slug="one", goal="goal", tasks=one_task()),
        extra=[lambda: transitions.create(conn, slug="two", goal="goal")],
        events=("plan.created", "task.added"),
        effects={"plans": plans_row, "tasks": tasks_rows},
    )


@register("append-task", spec.ANY)
def append_one_task(tmp_path: Path) -> Case:
    conn = ledger(tmp_path)
    plan = make_plan(conn)

    def tasks_row(verify: Verify) -> None:
        row = after_task(verify)
        assert row["attempts"] == 0
        assert row["attempts_allowed"] == MAX_ATTEMPTS
        assert row["accepted"] == 0
        assert row["attempt_open"] == 0

    return Case(
        conn=conn,
        plan=plan,
        task="T1",
        run=lambda: transitions.append_task(conn, plan, task_id="T1", task_title="first"),
        events=("task.added",),
        effects={"tasks": tasks_row},
    )


@register("finalize", spec.ANY)
def finalize_plan(tmp_path: Path) -> Case:
    conn = ledger(tmp_path)
    plan = make_plan(conn)

    def state_ready(verify: Verify) -> None:
        assert after_plan(verify)["state"] == PlanState.READY.value

    return Case(
        conn=conn,
        plan=plan,
        run=lambda: transitions.finalize(conn, plan),
        events=("plan.fields",),
        effects={"state": state_ready},
    )


@register("archive", spec.ANY)
def archive_plan(tmp_path: Path) -> Case:
    conn, plan = arranged(tmp_path, IN_PROGRESS)

    def archived_now(verify: Verify) -> None:
        moment = store.moment(after_plan(verify)["archived"])
        assert moment is not None
        assert verify.started <= moment <= verify.ended

    def every_attempt_closed(verify: Verify) -> None:
        rows = [row for row in verify.after.tables["tasks"].values() if row["plan"] == verify.plan]
        assert rows
        assert all(row["attempt_open"] == 0 for row in rows)

    return Case(
        conn=conn,
        plan=plan,
        task="T1",
        run=lambda: transitions.archive(conn, plan, reason="superseded"),
        events=("plan.archived",),
        effects={"archived": archived_now, "attempt_open": every_attempt_closed},
    )


def import_source(revision: str) -> port.PlanSource:
    """Build a plan source carrying one task with attempts, acceptance and a section."""
    return port.PlanSource(
        plan_id="Pimported",
        fields={"feature": "imported", "goal": "carry a plan in"},
        tasks=[
            port.TaskSource(
                fields={"id": "T1", "title": "first", "status": COMPLETE},
                attempts=2,
                attempts_allowed=MAX_ATTEMPTS,
                accepted=1,
                sections=[port.SectionSource(name="Notes", content="body")],
            )
        ],
        source="content",
        revision=revision,
    )


@register("import", spec.ANY)
def import_a_plan(tmp_path: Path) -> Case:
    conn = ledger(tmp_path)

    def rows_from_source(verify: Verify) -> None:
        assert after_plan(verify)["feature"] == "imported"
        row = after_task(verify)
        assert row["attempt_open"] == 0
        assert row["attempts"] == 2
        assert row["accepted"] == 1
        sections = [s for s in verify.after.tables["sections"].values() if s["plan"] == verify.plan]
        assert [s["attempt"] for s in sections] == [0]

    def cursor_written(verify: Verify) -> None:
        cursor = port.read_cursor(verify.conn, verify.plan, port.CONTENT_TARGET)
        assert cursor is not None
        assert cursor["revision"] == "r2"
        assert cursor["projection_hash"] == "hash-two"

    return Case(
        conn=conn,
        plan="Pimported",
        task="T1",
        run=lambda: port.import_plan(conn, import_source("r1"), projection_hash="hash-one"),
        extra=[lambda: port.import_plan(conn, import_source("r2"), replace=True, projection_hash="hash-two")],
        events=("plan.created", "plan.replaced", "task.imported", "plan.imported"),
        effects={"plans, tasks, sections": rows_from_source, "export_cursors": cursor_written},
    )


class RecordingStore:
    """A :class:`dh_core.ledger.port.ProjectionStore` that keeps the projection in memory."""

    def __init__(self) -> None:
        """Start with nothing written."""
        self.written: dict[str, dict[str, Any]] = {}
        self.revision = "revision-1"

    def read(self, plan: str) -> dict[str, Any] | None:
        """Return the projection this store holds for a plan."""
        return self.written.get(plan)

    def write(self, plan: str, content: Mapping[str, Any], *, expected_revision: str = "") -> str:
        """Record a projection and return the revision assigned to it."""
        del expected_revision
        self.written[plan] = dict(content)
        return self.revision


@register("export", spec.ANY)
def export_a_plan(tmp_path: Path) -> Case:
    conn = ledger(tmp_path)
    port.import_plan(conn, import_source("r1"), projection_hash="hash-one")
    target = RecordingStore()

    def cursor_written(verify: Verify) -> None:
        cursor = port.read_cursor(verify.conn, verify.plan, port.CONTENT_TARGET)
        exported = next(event for event in verify.after.events if event["kind"] == "plan.exported")
        assert cursor is not None
        assert cursor["last_seq"] == exported["payload"]["last_seq"], "the cursor and its event disagree"
        assert cursor["last_seq"] <= store.last_seq(verify.conn, verify.plan)
        assert cursor["revision"] == target.revision
        assert cursor["projection_hash"] == port.projection_hash(port.projection(verify.conn, verify.plan))

    return Case(
        conn=conn,
        plan="Pimported",
        run=lambda: port.export_plan(conn, "Pimported", projection_store=target),
        events=("plan.exported",),
        effects={"export_cursors": cursor_written},
    )


def milestone_plan() -> port.PlanSource:
    """Build the plan one milestone item describes."""
    return port.milestone_source(
        milestone_number=7,
        integration_branch="milestone-7",
        base_sha="0123456789abcdef",
        items=[
            port.MilestoneItem(
                issue=11,
                title="first",
                task_id="T1",
                acceptance_criteria="gates green",
                verification_steps="run the gates",
                conflict_group="core",
            )
        ],
        quality_gates=["uv run pytest"],
    )


@register("from-milestone", spec.ANY)
def plan_from_milestone(tmp_path: Path) -> Case:
    conn = ledger(tmp_path)

    def plans_row(verify: Verify) -> None:
        row = after_plan(verify)
        assert row["milestone"] == 7
        assert row["integration_branch"] == "milestone-7"
        assert row["base_sha"] == "0123456789abcdef"
        assert json.loads(str(row["quality_gates"])) == ["uv run pytest"]

    def tasks_row(verify: Verify) -> None:
        row = after_task(verify)
        assert row["github_issue"] == 11
        assert row["conflict_group"] == "core"
        assert row["acceptance_criteria"] == "gates green"
        assert row["verification_steps"] == "run the gates"

    return Case(
        conn=conn,
        plan="P7",
        task="T1",
        run=lambda: port.from_milestone(conn, milestone_plan()),
        extra=[lambda: port.from_milestone(conn, milestone_plan(), replace=True)],
        events=("plan.created", "plan.replaced", "task.added"),
        effects={"plans": plans_row, "tasks": tasks_row},
    )


# ---------------------------------------------------------------------------
# The conformance test
# ---------------------------------------------------------------------------

ENTRY_IDS = [f"{entry.command}/{entry.from_status}" for entry in spec.TRANSITIONS]


def assert_refused(case: Case, entry: spec.Transition, before: Snapshot) -> None:
    """A refusal names one of the entry's checks and writes nothing."""
    assert case.refusal in {check.reason for check in entry.checks}, (
        f"{case.refusal} is not a check of {entry.command}/{entry.from_status}"
    )
    assert REASON_KIND[case.refusal] is spec.ReasonKind.REFUSAL
    with pytest.raises(store.Refusal) as raised:
        case.run()
    assert raised.value.reason == case.refusal
    assert snapshot(case.conn) == before, "a refusal changed the ledger"
    if case.quiet is None:
        return
    assert not entry.effects, "an entry with effects needs them asserted, not a quiet run"
    assert not entry.events, "an entry with events needs them asserted, not a quiet run"
    case.quiet()
    assert snapshot(case.conn) == before, "the entry names no effect and no event, but the command wrote one"


def assert_declined(case: Case, entry: spec.Transition, before: Snapshot) -> None:
    """A no-op names its reason on the result and writes nothing."""
    assert REASON_KIND[case.noop] is spec.ReasonKind.NOOP
    assert case.noop == entry.noop or case.noop in {check.reason for check in entry.checks}
    result = case.run()
    assert result.noop == case.noop
    assert snapshot(case.conn) == before, "a no-op changed the ledger"


def assert_events(case: Case, entry: spec.Transition, events: Sequence[Mapping[str, Any]]) -> None:
    """The run appended the entry's events, and nothing the entry does not list."""
    appended = {str(event["kind"]) for event in events}
    assert appended <= set(entry.events), f"appended {sorted(appended - set(entry.events))} the entry does not list"
    assert appended == set(case.events), f"appended {sorted(appended)}, expected {sorted(case.events)}"
    if appended != set(entry.events):
        assert case.why, (
            f"{entry.command}/{entry.from_status} lists {sorted(set(entry.events) - appended)} "
            "which this run does not emit, and the scenario says nothing about why"
        )
        assert case.why in entry.note, "the reason given is not the entry's own note"


def assert_to_status(case: Case, entry: spec.Transition, before: Snapshot, after: Snapshot) -> None:
    """The task reached the status the entry names, or kept the one it had."""
    key = task_key(case.plan, case.task)
    if not entry.to_status:
        if case.task and key in before.tables["tasks"]:
            assert after.tables["tasks"][key]["status"] == before.tables["tasks"][key]["status"]
        return
    assert case.status, "the entry names a to_status and the scenario does not"
    assert after.tables["tasks"][key]["status"] == case.status
    if entry.to_status == "--new-status":
        assert case.status in STATUS_VALUES
    elif entry.to_status in STATUS_VALUES:
        assert case.status == entry.to_status
    else:
        assert case.status in entry.to_status, f"{case.status} is not in {entry.to_status!r}"


def assert_effects(case: Case, entry: spec.Transition, verify: Verify) -> None:
    """Every effect the entry names has a checker, and every checker holds."""
    named = {effect.column for effect in entry.effects}
    assert set(case.effects) == named, f"effects {sorted(case.effects)} against the entry's {sorted(named)}"
    for check in case.effects.values():
        check(verify)


@pytest.mark.parametrize("entry", spec.TRANSITIONS, ids=ENTRY_IDS)
def test_transition_conforms_to_spec(entry: spec.Transition, tmp_path: Path) -> None:
    builder = SCENARIOS.get((entry.command, entry.from_status))
    assert builder is not None, f"no scenario drives {entry.command}/{entry.from_status}"
    case = builder(tmp_path)
    before = snapshot(case.conn)
    if case.refusal:
        assert_refused(case, entry, before)
        return
    if case.noop:
        assert_declined(case, entry, before)
        return
    started = store.now()
    result = case.run()
    extras = [run() for run in case.extra]
    ended = store.now()
    after = snapshot(case.conn)
    events = appended_events(before, after)
    plan = case.plan or str(result.plan)
    verify = Verify(
        conn=case.conn,
        plan=plan,
        task=case.task,
        before=before,
        after=after,
        result=result,
        extras=extras,
        started=started,
        ended=ended,
    )
    assert_payload_shape(events)
    assert_events(case, entry, events)
    assert_to_status(case, entry, before, after)
    assert_effects(case, entry, verify)
    assert_provenance(before, after, events)
    assert_fold(after)


# ---------------------------------------------------------------------------
# update --set writes only the columns task.fields sets
# ---------------------------------------------------------------------------

TASK_FIELDS_EVENT = "task.fields"
"""The event kind the ``update`` transition appends for ``--set`` on a task."""

NOT_SET_BY_TASK_FIELDS: tuple[str, ...] = tuple(
    sorted(
        column.name
        for column in spec.COLUMNS
        if column.table == "tasks"
        and column.provenance is not spec.Provenance.DERIVED
        and TASK_FIELDS_EVENT not in column.set_by
    )
)
"""Every stored ``tasks`` column ``ledger_spec.COLUMNS`` says ``task.fields`` does not set."""

PROBES: dict[str, Any] = {
    "status": spec.Status.COMPLETE.value,
    "started": "2020-01-01T00:00:00",
    "completed": "2020-01-01T00:00:00",
    "last_activity": "2020-01-01T00:00:00",
    "plan": "Pother",
    "conflict_group": "G",
    "attempts": 9,
    "attempts_allowed": 9,
    "accepted": 1,
    "attempt_open": 1,
    "ttl_seconds": 99,
    "worktree": "/tmp/elsewhere",
    "expires": "2020-01-01T00:00:00",
    "first_renewed": "2020-01-01T00:00:00",
    "result": "complete",
    "note": "note",
    "settled": 1,
    "return_text": "text",
    "response": "response",
}
"""A value to try writing into each column, differing from the value a fresh task holds."""


@pytest.fixture
def set_conn(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    """Open a ledger in a temporary directory and close it afterwards.

    Args:
        tmp_path: pytest's per-test directory.

    Yields:
        An open connection with the schema present.
    """
    connection = store.open_ledger(tmp_path / store.DATABASE_NAME)
    try:
        yield connection
    finally:
        connection.close()


@pytest.fixture
def set_plan(set_conn: sqlite3.Connection) -> str:
    """Create a plan holding one not-started task.

    Args:
        set_conn: An open ledger connection.

    Returns:
        The plan id.
    """
    return str(transitions.create(set_conn, slug="feature", goal="goal", tasks=[{"id": "T1", "title": "first"}]).plan)


def test_probe_covers_every_column_outside_task_fields() -> None:
    """Every column the specification keeps out of ``task.fields`` has a probe value."""
    assert set(NOT_SET_BY_TASK_FIELDS) <= set(PROBES)


@pytest.mark.parametrize("column", NOT_SET_BY_TASK_FIELDS)
def test_update_set_does_not_write_a_column_task_fields_never_sets(
    set_conn: sqlite3.Connection, set_plan: str, column: str
) -> None:
    """``update --set`` leaves every column ``task.fields`` is not declared to set unchanged."""
    before = store.fetch_task(set_conn, set_plan, "T1")[column]
    probe = PROBES[column]
    assert before != probe, f"the probe for tasks.{column} does not differ from the stored value"
    with contextlib.suppress(ValueError):
        transitions.update(set_conn, set_plan, "T1", values={column: probe})
    after = store.fetch_task(set_conn, set_plan, "T1")[column]
    assert after == before, (
        f"update --set {column}={probe!r} wrote tasks.{column}, but ledger_spec.COLUMNS declares it "
        f"set_by {sorted(next(c for c in spec.COLUMNS if c.table == 'tasks' and c.name == column).set_by)}, "
        f"which does not include {TASK_FIELDS_EVENT}"
    )


def test_update_set_status_does_not_bypass_the_state_machine(set_conn: sqlite3.Connection, set_plan: str) -> None:
    """A task reaches complete only through an event ``ledger_spec.COLUMNS`` names for the column."""
    result = transitions.update(set_conn, set_plan, "T1", values={"status": spec.Status.COMPLETE.value})
    assert result.events == [TASK_FIELDS_EVENT]
    row = store.fetch_task(set_conn, set_plan, "T1")
    setters = set(next(c for c in spec.COLUMNS if c.table == "tasks" and c.name == "status").set_by)
    assert TASK_FIELDS_EVENT not in setters
    assert row["status"] == spec.Status.NOT_STARTED.value, (
        "update --set status=complete moved the task to complete while appending only task.fields, "
        "so no report check, lease check or cascade ran and no event in "
        f"{sorted(setters)} explains the column's value"
    )


def test_update_set_names_the_columns_it_would_not_write(set_conn: sqlite3.Connection, set_plan: str) -> None:
    """The names ``task.fields`` does not set come back on the result rather than passing silently."""
    result = transitions.update(set_conn, set_plan, "T1", values={"title": "renamed", "status": COMPLETE})
    assert result.changed == {"title": "renamed"}
    assert result.unsettable == ["status"]
