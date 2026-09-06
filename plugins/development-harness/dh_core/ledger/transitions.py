"""One function per mutating command of :mod:`dh_core.ledger_spec`.

Each function implements the ``ledger_spec.TRANSITIONS`` entry that matches the addressed row's
current status: it evaluates that entry's checks in order, honouring each check's ``unless``
clause, and then applies the entry's effects and appends its events inside a single transaction.
A check whose reason is a ``ReasonKind.REFUSAL`` raises :class:`dh_core.ledger.store.Refusal`; a
check whose reason is a ``ReasonKind.NOOP`` returns that code on
:attr:`TransitionResult.noop` without touching the database.

``import``, ``export`` and ``from-milestone`` are not here; they live in ``dh_core/ledger/port.py``.
``validate``, ``list``, ``status`` and ``ready`` have no ``TRANSITIONS`` entry because they only
read.

Nothing in this module prints, formats or imports a CLI framework. Every value that the
specification names is read from ``ledger_spec`` at import time rather than copied, including the
statuses, the reason kinds, the ``--new-status`` and ``--result`` vocabularies, the report section
names, the dependency-satisfying statuses and the configuration defaults.

Every instant a transition writes is sampled inside ``store.transaction``, after its
``BEGIN IMMEDIATE`` has taken the write lock. The wait for another writer's lock can be as long as
``store.BUSY_TIMEOUT_MS``, and an instant sampled before that wait would be subtracted from the
lease the transition then writes: ``dispatch``'s ``expires = now + ttl_seconds`` and
``_renew_effects``' same expression would hand back a deadline that had already passed, leaving
``tasks.expired`` true the moment the attempt was granted.

Collaborating modules, written alongside this one:

``dh_core.ledger.store``
    ``Refusal(reason)``, the exception carrying one ``ledger_spec`` reason code;
    ``transaction(conn)``, a context manager running ``BEGIN IMMEDIATE`` and committing or rolling
    back; and ``append_event(conn, kind=..., plan=..., task=..., payload=...)``, which appends one
    ``events`` row. ``store`` also owns opening the database — this module opens nothing and is
    always handed a live connection — and owns the shared conventions this module imports rather
    than restates: ``now``, ``timestamp``, ``rows_of``, ``json_list``, ``fetch_task``,
    ``fetch_plan`` and ``plan_tasks``.

``dh_core.ledger.derive``
    the derived columns of ``ledger_spec.COLUMNS``: ``returned``, ``stale`` and ``renew_by``, which
    the checks and the ``renew`` result need, and ``READY_PREDICATE``, the one implementation of
    ``tasks.ready``, which ``DISPATCH_SQL`` composes into its WHERE clause. Derived values are
    never recomputed here.

The ``events`` table is read directly for one purpose: the cascade reason lives only in the
``task.state`` payload, because ``ledger_spec.COLUMNS`` does not fold it into ``tasks.reason``.
That read assumes the columns ``seq``, ``kind``, ``plan``, ``task`` and a JSON ``payload``.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any, NoReturn

from pydantic import BaseModel, Field
from sam_schema.core.models import Plan, PlanState, Task

from dh_core import ledger_spec
from dh_core.ledger import derive, store
from dh_core.ledger.store import (
    fetch_plan,
    fetch_task,
    insert_statement,
    json_list,
    now,
    plan_tasks,
    rows_of,
    timestamp,
)

if TYPE_CHECKING:  # pragma: no cover - typing only
    import sqlite3
    from collections.abc import Mapping, Sequence

# ---------------------------------------------------------------------------
# Values read from the specification
# ---------------------------------------------------------------------------

NOT_STARTED = store.NOT_STARTED
IN_PROGRESS = store.IN_PROGRESS
COMPLETE = store.COMPLETE
FAILED = store.FAILED
DEFERRED = store.DEFERRED
SKIPPED = store.SKIPPED

REASON_KINDS: dict[str, ledger_spec.ReasonKind] = {reason.code: reason.kind for reason in ledger_spec.REASONS}
"""Every reason code the specification defines, with the kind that decides raise versus return."""

SUCCESSFUL_DEPENDENCY: tuple[str, ...] = derive.SUCCESSFUL_DEPENDENCY
"""Statuses that satisfy a dependency without acceptance; ``derive`` binds them into the SQL."""

EVENT_KINDS: frozenset[str] = frozenset(event.kind for event in ledger_spec.EVENTS)
"""Every event kind the specification declares; :func:`append` refuses any other."""


STATE_TARGETS: tuple[str, ...] = store.flag_vocabulary("state", "--new-status")
"""The statuses ``state --new-status`` accepts; anything else is ``status-invalid``."""

FINISH_RESULTS: tuple[str, ...] = store.FINISH_RESULTS
"""The values ``finish --result`` accepts."""

RESULT_STATUS: dict[str, str] = store.RESULT_STATUS
"""``finish --result`` to resulting status; ``store`` owns it because the fold of ``task.finished``
needs it too, and that payload carries the result rather than the status."""

NEEDS_INPUT: str = next(value for value in FINISH_RESULTS if value not in {s.value for s in ledger_spec.Status})
"""The one ``finish --result`` value that is not a status: the question that does not spend an attempt."""

CONFIG_DEFAULTS: dict[str, int] = store.CONFIG_DEFAULTS
DEFAULT_TTL_SECONDS: int = store.DEFAULT_TTL_SECONDS
DEFAULT_MAX_ATTEMPTS: int = store.DEFAULT_MAX_ATTEMPTS

TASK_COLUMNS: tuple[str, ...] = (
    *ledger_spec.TASK_MODEL_FIELDS,
    "plan",
    "conflict_group",
    "attempts",
    "attempts_allowed",
    "accepted",
    "attempt_open",
    "ttl_seconds",
    "worktree",
    "expires",
    "first_renewed",
    "result",
    "note",
    "settled",
    "return_text",
    "response",
)
"""Every column of ``tasks``, model fields first, as ``ledger_spec.COLUMNS`` declares them."""


def stored_columns(table: str) -> tuple[str, ...]:
    """Return every column ``ledger_spec.COLUMNS`` materialises for one table.

    Args:
        table: The table name.

    Returns:
        The names of its non-derived columns, in specification order.
    """
    return tuple(
        column.name
        for column in ledger_spec.COLUMNS
        if column.table == table and column.provenance is not ledger_spec.Provenance.DERIVED
    )


def columns_set_by(table: str, kind: str) -> tuple[str, ...]:
    """Return the columns of one table whose fold ``ledger_spec.COLUMNS`` says one event kind sets.

    Args:
        table: The table name.
        kind: The event kind, as ``ledger_spec.EVENTS`` names it.

    Returns:
        The names of the columns carrying that kind in ``set_by``, in specification order.
    """
    return tuple(column.name for column in ledger_spec.COLUMNS if column.table == table and kind in column.set_by)


TASK_FIELD_COLUMNS: tuple[str, ...] = columns_set_by("tasks", "task.fields")
"""The ``tasks`` columns ``update --set`` may write.

The ``update`` transition appends ``task.fields`` and nothing else that touches ``tasks``, so its
"task model fields, per --set" effect reaches exactly the columns whose ``set_by`` names that kind.
``status``, ``started``, ``completed`` and ``last_activity`` are declared ``Provenance.EVENT`` with
``set_by`` lists that name the lifecycle events instead, so they are not here: a task moves through
them by ``dispatch``, ``finish``, ``state``, ``reclaim`` or ``accept``, never by ``--set``.
"""

PLAN_FIELD_COLUMNS: tuple[str, ...] = columns_set_by("plans", "plan.fields")
"""The ``plans`` columns ``update --set`` and ``finalize`` may write, read the same way."""


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------


class TransitionResult(BaseModel):
    """What one transition did, for a caller that renders it.

    A ``noop`` code means the transition declined without appending anything. ``status`` is the
    resulting task status when the transition changed it, and ``None`` when it did not.
    ``changed`` carries what the transition actually wrote, and ``unsettable`` the ``--set`` names
    it declined to write because no event it appends sets that column.
    """

    command: str
    plan: str | None = None
    task: str | None = None
    noop: str | None = None
    status: str | None = None
    attempt: int | None = None
    renew_by: datetime | None = None
    events: list[str] = Field(default_factory=list)
    cascaded: list[str] = Field(default_factory=list)
    reversed_tasks: list[str] = Field(default_factory=list)
    changed: dict[str, Any] = Field(default_factory=dict)
    unsettable: list[str] = Field(default_factory=list)
    row: dict[str, Any] | None = None
    sections: list[dict[str, Any]] = Field(default_factory=list)


def refuse(code: str) -> NoReturn:
    """Raise the store's refusal for a reason code.

    Args:
        code: A ``ledger_spec.REASONS`` code of kind ``REFUSAL``.

    Raises:
        Refusal: Always.
        ValueError: When the code is not a refusal in the specification.
    """
    if REASON_KINDS.get(code) is not ledger_spec.ReasonKind.REFUSAL:
        msg = f"{code} is not a refusal in ledger_spec.REASONS"
        raise ValueError(msg)
    raise store.Refusal(code)


def declined(command: str, code: str, plan: str | None = None, task: str | None = None) -> TransitionResult:
    """Build the result of a transition that stopped on a no-op reason.

    Args:
        command: The command name.
        code: A ``ledger_spec.REASONS`` code of kind ``NOOP``.
        plan: The addressed plan, when there is one.
        task: The addressed task, when there is one.

    Returns:
        A result carrying the code and no effects.

    Raises:
        ValueError: When the code is not a no-op in the specification.
    """
    if REASON_KINDS.get(code) is not ledger_spec.ReasonKind.NOOP:
        msg = f"{code} is not a noop in ledger_spec.REASONS"
        raise ValueError(msg)
    return TransitionResult(command=command, plan=plan, task=task, noop=code)


def outcome_code(code: str) -> str:
    """Return an outcome reason code after checking the specification defines it that way.

    Args:
        code: A ``ledger_spec.REASONS`` code of kind ``OUTCOME``.

    Returns:
        The same code.

    Raises:
        ValueError: When the code is not an outcome in the specification.
    """
    if REASON_KINDS.get(code) is not ledger_spec.ReasonKind.OUTCOME:
        msg = f"{code} is not an outcome in ledger_spec.REASONS"
        raise ValueError(msg)
    return code


RETURNED_COMPLETE: str = outcome_code("returned-complete")
"""The reason ``accept`` records when it completes a returned task before accepting it."""


def append(
    conn: sqlite3.Connection, *, kind: str, plan: str, task: str | None, payload: Mapping[str, Any], at: datetime
) -> None:
    """Append one event through the store, after checking the kind against the specification.

    Args:
        conn: An open ledger connection, inside the caller's transaction.
        kind: An event kind from ``ledger_spec.EVENTS``.
        plan: The plan the event belongs to.
        task: The task the event belongs to, or None for a plan-scoped event.
        payload: The event payload.
        at: The instant this transition sampled inside its transaction, which the log records as
            ``events.at`` and the fold reads every ``ledger_spec.INSTANT_COLUMNS`` value out of.

    Raises:
        ValueError: When the kind is not one the specification declares.
    """
    if kind not in EVENT_KINDS:
        msg = f"{kind} is not an event kind in ledger_spec.EVENTS"
        raise ValueError(msg)
    store.append_event(conn, kind=kind, plan=plan, task=task, payload=dict(payload), at=at)


# ---------------------------------------------------------------------------
# Small reads that refuse
# ---------------------------------------------------------------------------
#
# The row reads, the JSON decode and the time conventions live in ``store``; imported above.
# What stays here is the reads that end in a refusal, which is this module's business.


def plan_archived(conn: sqlite3.Connection, plan: str) -> bool:
    """Report whether a plan carries an ``archived`` datetime.

    Args:
        conn: An open ledger connection.
        plan: The plan id.

    Returns:
        True when ``plans.archived`` is set.
    """
    return fetch_plan(conn, plan)["archived"] is not None


def require_unarchived(conn: sqlite3.Connection, plan: str) -> None:
    """Refuse with ``archived`` when the plan is archived.

    Args:
        conn: An open ledger connection.
        plan: The plan id.
    """
    if plan_archived(conn, plan):
        refuse("archived")


def sections_of(conn: sqlite3.Connection, plan: str, task: str) -> list[dict[str, Any]]:
    """Read every section row of one task, oldest attempt first.

    Args:
        conn: An open ledger connection.
        plan: The plan id.
        task: The task id.

    Returns:
        The section rows, ordered by attempt then insertion order.
    """
    return rows_of(
        conn.execute(
            "SELECT plan, task, name, attempt, content, seq FROM sections "
            "WHERE plan = :plan AND task = :task ORDER BY attempt, seq",
            {"plan": plan, "task": task},
        )
    )


def with_response(row: Mapping[str, Any], sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Head the current attempt's sections with the orchestrator's response.

    ``ledger_spec.RESPONSE_SECTION`` is rendered by ``read`` from ``tasks.response`` and is not a
    stored section, so it is built here rather than read from ``sections``. Its ``seq`` is zero,
    which no stored row uses, so a reader can tell it from a section a runner appended.

    Args:
        row: The task row, carrying ``response`` and the current ``attempts``.
        sections: The stored section rows, oldest attempt first.

    Returns:
        The section rows with the response inserted before the current attempt's own, or the rows
        unchanged when the task carries no response.
    """
    response = row["response"]
    if response is None or not str(response):
        return sections
    attempt = int(row["attempts"] or 0)
    entry: dict[str, Any] = {
        "plan": str(row["plan"]),
        "task": str(row["id"]),
        "name": ledger_spec.RESPONSE_SECTION,
        "attempt": attempt,
        "content": str(response),
        "seq": 0,
    }
    ahead = (position for position, section in enumerate(sections) if int(section["attempt"]) >= attempt)
    index = next(ahead, len(sections))
    return [*sections[:index], entry, *sections[index:]]


def report_complete(conn: sqlite3.Connection, plan: str, task: str, attempt: int) -> bool:
    """Report whether every ``ledger_spec.REPORT_SECTIONS`` name has a row for one attempt.

    Args:
        conn: An open ledger connection.
        plan: The plan id.
        task: The task id.
        attempt: The attempt the sections must be tagged with.

    Returns:
        True when no report section is missing.
    """
    present = {
        row["name"]
        for row in rows_of(
            conn.execute(
                "SELECT DISTINCT name FROM sections WHERE plan = :plan AND task = :task AND attempt = :attempt",
                {"plan": plan, "task": task, "attempt": attempt},
            )
        )
    }
    return set(ledger_spec.REPORT_SECTIONS) <= present


def latest_state_reason(conn: sqlite3.Connection, plan: str, task: str) -> str | None:
    """Return the ``reason`` of the newest ``task.state`` event for a task.

    The cascade records its reason only in the event payload, because ``ledger_spec.COLUMNS`` does
    not fold a ``task.state`` reason into ``tasks.reason``.

    Args:
        conn: An open ledger connection.
        plan: The plan id.
        task: The task id.

    Returns:
        The reason string, or None when the task has no ``task.state`` event or the payload
        carries no reason.
    """
    found = rows_of(
        conn.execute(
            "SELECT payload FROM events WHERE plan = :plan AND task = :task AND kind = :kind ORDER BY seq DESC LIMIT 1",
            {"plan": plan, "task": task, "kind": "task.state"},
        )
    )
    if not found:
        return None
    payload = found[0]["payload"]
    decoded = json.loads(payload) if isinstance(payload, str) else payload
    reason = decoded.get("reason") if isinstance(decoded, dict) else None
    return str(reason) if reason is not None else None


# ---------------------------------------------------------------------------
# The cascade and its reversal, used by every command that needs them
# ---------------------------------------------------------------------------


def cascade_code(task: str) -> str:
    """Return the ``cascade`` outcome reason for one failing task.

    Args:
        task: The task that became failed.

    Returns:
        The reason code with the task substituted for the specification's placeholder.
    """
    template = next(r.code for r in ledger_spec.REASONS if r.code.startswith("cascade:"))
    return template.replace("T{n}", task)


def reversal_code(task: str) -> str:
    """Return the ``cascade-reversed`` outcome reason for one reclaimed task.

    Args:
        task: The task that left failed.

    Returns:
        The reason code with the task substituted for the specification's placeholder.
    """
    template = next(r.code for r in ledger_spec.REASONS if r.code.startswith("cascade-reversed:"))
    return template.replace("T{n}", task)


def dependents_of(rows: Sequence[Mapping[str, Any]]) -> dict[str, list[str]]:
    """Build the reverse dependency edges of a plan.

    Args:
        rows: Every task row of one plan.

    Returns:
        A mapping from a task id to the ids of the tasks that name it in ``dependencies``.
    """
    reverse: dict[str, list[str]] = {}
    for row in rows:
        for dependency in json_list(row["dependencies"]):
            reverse.setdefault(dependency, []).append(str(row["id"]))
    return reverse


def transitive_dependents(rows: Sequence[Mapping[str, Any]], task: str) -> list[str]:
    """Walk every task reachable from one task through reverse dependency edges.

    The walk continues through dependents in any status, so a not-started task reachable only
    behind a finished one is still found.

    Args:
        rows: Every task row of one plan.
        task: The task to walk out from.

    Returns:
        The reachable task ids, sorted.
    """
    reverse = dependents_of(rows)
    seen: set[str] = set()
    frontier = list(reverse.get(task, []))
    while frontier:
        node = frontier.pop()
        if node in seen:
            continue
        seen.add(node)
        frontier.extend(reverse.get(node, []))
    return sorted(seen)


def cascade(conn: sqlite3.Connection, plan: str, task: str, moment: datetime) -> list[str]:
    """Skip every not-started transitive dependent of a task that has become failed.

    Args:
        conn: An open ledger connection, inside the caller's transaction.
        plan: The plan id.
        task: The task that entered failed.
        moment: The instant the caller sampled for this transition.

    Returns:
        The ids moved to skipped, sorted.
    """
    rows = plan_tasks(conn, plan)
    by_id = {str(row["id"]): row for row in rows}
    code = cascade_code(task)
    moved: list[str] = []
    for dependent in transitive_dependents(rows, task):
        row = by_id.get(dependent)
        if row is None or row["status"] != NOT_STARTED:
            continue
        conn.execute(
            "UPDATE tasks SET status = :status WHERE plan = :plan AND id = :task",
            {"status": SKIPPED, "plan": plan, "task": dependent},
        )
        append(
            conn,
            kind="task.state",
            plan=plan,
            task=dependent,
            payload={
                "status": SKIPPED,
                "reason": code,
                "accepted": int(row["accepted"] or 0),
                "attempt_open": int(row["attempt_open"] or 0),
            },
            at=moment,
        )
        moved.append(dependent)
    return moved


def reverse_cascade(conn: sqlite3.Connection, plan: str, task: str, moment: datetime) -> list[str]:
    """Return every dependent still skipped by one task's cascade to not-started.

    Args:
        conn: An open ledger connection, inside the caller's transaction.
        plan: The plan id.
        task: The task that left failed.
        moment: The instant the caller sampled for this transition.

    Returns:
        The ids moved back to not-started, sorted.
    """
    code = cascade_code(task)
    restored: list[str] = []
    for row in plan_tasks(conn, plan):
        dependent = str(row["id"])
        if row["status"] != SKIPPED or latest_state_reason(conn, plan, dependent) != code:
            continue
        conn.execute(
            "UPDATE tasks SET status = :status WHERE plan = :plan AND id = :task",
            {"status": NOT_STARTED, "plan": plan, "task": dependent},
        )
        append(
            conn,
            kind="task.state",
            plan=plan,
            task=dependent,
            payload={
                "status": NOT_STARTED,
                "reason": reversal_code(task),
                "accepted": int(row["accepted"] or 0),
                "attempt_open": int(row["attempt_open"] or 0),
            },
            at=moment,
        )
        restored.append(dependent)
    return sorted(restored)


def cascade_skipped(conn: sqlite3.Connection, plan: str, row: Mapping[str, Any], task: str) -> bool:
    """Report whether one row is skipped by another task's cascade.

    Args:
        conn: An open ledger connection.
        plan: The plan id.
        row: The candidate dependent's row.
        task: The task whose cascade is in question.

    Returns:
        True when the row is skipped and its newest ``task.state`` reason is that cascade's code.
    """
    if row["status"] != SKIPPED:
        return False
    return latest_state_reason(conn, plan, str(row["id"])) == cascade_code(task)


def dependents_started(conn: sqlite3.Connection, plan: str, task: str) -> bool:
    """Report whether any dependent of a task has spent an attempt.

    Args:
        conn: An open ledger connection.
        plan: The plan id.
        task: The task being reclaimed.

    Returns:
        True when a task naming this one in ``dependencies`` has ``attempts`` above zero and is
        not skipped by this task's cascade.
    """
    for row in plan_tasks(conn, plan):
        if task not in json_list(row["dependencies"]):
            continue
        if int(row["attempts"] or 0) <= 0:
            continue
        if not cascade_skipped(conn, plan, row, task):
            return True
    return False


# ---------------------------------------------------------------------------
# The lease
# ---------------------------------------------------------------------------


def renew_lease(conn: sqlite3.Connection, row: Mapping[str, Any], moment: datetime, *, via: str) -> None:
    """Apply the renew effects to one task and append ``lease.renewed``.

    Args:
        conn: An open ledger connection, inside the caller's transaction.
        row: The task row being renewed.
        moment: The instant the renewal happens at.
        via: The command that renewed, recorded in the event payload.
    """
    ttl = int(row["ttl_seconds"] or DEFAULT_TTL_SECONDS)
    stamp = timestamp(moment)
    conn.execute(
        "UPDATE tasks SET expires = :expires, last_activity = :now, "
        "first_renewed = COALESCE(first_renewed, :now) WHERE plan = :plan AND id = :task",
        {"expires": timestamp(moment + timedelta(seconds=ttl)), "now": stamp, "plan": row["plan"], "task": row["id"]},
    )
    append(
        conn,
        kind="lease.renewed",
        plan=str(row["plan"]),
        task=str(row["id"]),
        payload={"attempt": int(row["attempts"] or 0), "via": via},
        at=moment,
    )


def require_current_attempt(row: Mapping[str, Any], attempt: int) -> None:
    """Refuse with ``stale-attempt`` when an attempt number is not the row's current one.

    Args:
        row: The task row.
        attempt: The attempt the caller supplied.
    """
    if int(row["attempts"] or 0) != attempt:
        refuse("stale-attempt")


def require_open_attempt(row: Mapping[str, Any]) -> None:
    """Refuse with ``attempt-closed`` when the row's current attempt is closed.

    Args:
        row: The task row.
    """
    if int(row["attempt_open"] or 0) != 1:
        refuse("attempt-closed")


def task_for_path(conn: sqlite3.Connection, path: str, plan: str | None = None) -> dict[str, Any]:
    """Find the leased task whose worktree contains a path.

    Args:
        conn: An open ledger connection.
        path: A file or directory inside a dispatched worktree.
        plan: Restrict the search to one plan when given.

    Returns:
        The matching task row; the deepest worktree wins when several contain the path.
    """
    target = Path(path).expanduser().resolve()
    query = "SELECT * FROM tasks WHERE attempt_open = 1 AND worktree IS NOT NULL"
    parameters: dict[str, Any] = {}
    if plan is not None:
        query += " AND plan = :plan"
        parameters["plan"] = plan
    candidates = rows_of(conn.execute(query, parameters))
    matches = [
        row
        for row in candidates
        if target == Path(str(row["worktree"])).expanduser().resolve()
        or target.is_relative_to(Path(str(row["worktree"])).expanduser().resolve())
    ]
    if not matches:
        refuse("unmatched-path")
    return max(matches, key=lambda row: len(str(row["worktree"])))


# ---------------------------------------------------------------------------
# dispatch
# ---------------------------------------------------------------------------

DISPATCH_UPDATE = """
UPDATE tasks
   SET status = :in_progress,
       attempts = attempts + 1,
       attempt_open = 1,
       ttl_seconds = :ttl,
       worktree = :worktree,
       expires = :expires,
       first_renewed = NULL,
       started = :now,
       last_activity = :now,
       result = NULL,
       note = NULL,
       settled = 0,
       return_text = NULL,
       completed = NULL
 WHERE tasks.plan = :plan
   AND tasks.id = :task
   AND tasks.attempt_open = 0
   AND NOT EXISTS (SELECT 1 FROM plans p WHERE p.plan_id = tasks.plan AND p.archived IS NOT NULL)
   AND (
"""
"""Everything ``dispatch`` checks other than readiness, as the head of one conditional UPDATE."""

DISPATCH_SQL = f"{DISPATCH_UPDATE} {derive.READY_PREDICATE} ) RETURNING attempts"
"""The whole ``dispatch`` transition as one conditional UPDATE.

Every check the transition names rides in the WHERE clause, so two dispatchers of one task — or of
two tasks sharing a conflict group — cannot both pass. The conflict-group clause reads a different
row than the statement writes, which is why a SELECT followed by an UPDATE would admit both. The
readiness half is ``derive.READY_PREDICATE`` verbatim, so ``dispatch`` and ``tasks.ready`` are one
implementation rather than two that must be kept in step.
"""


def attribute_dispatch_refusal(conn: sqlite3.Connection, plan: str, task: str) -> NoReturn:
    """Name the first ``dispatch`` check that the conditional UPDATE failed.

    Args:
        conn: An open ledger connection, inside the caller's transaction.
        plan: The plan id.
        task: The task id.

    Raises:
        Refusal: Always, with ``archived``, ``leased`` or ``not-ready`` in that order.
    """
    row = fetch_task(conn, plan, task)
    if plan_archived(conn, plan):
        refuse("archived")
    if int(row["attempt_open"] or 0) == 1:
        refuse("leased")
    refuse("not-ready")


def dispatch(
    conn: sqlite3.Connection, plan: str, task: str, *, ttl_seconds: int | None = None, worktree: str | None = None
) -> TransitionResult:
    """Open an attempt on a ready task.

    Args:
        conn: An open ledger connection.
        plan: The plan id.
        task: The task id.
        ttl_seconds: The lease length; ``lease.ttl_seconds`` from the specification when absent.
        worktree: The worktree the runner works in, or None.

    Returns:
        A result whose ``attempt`` is the new attempt number the caller prints.
    """
    ttl = DEFAULT_TTL_SECONDS if ttl_seconds is None else ttl_seconds
    with store.transaction(conn):
        moment = now()
        found = rows_of(
            conn.execute(
                DISPATCH_SQL,
                {
                    **derive.ready_parameters(),
                    "ttl": ttl,
                    "worktree": worktree,
                    "expires": timestamp(moment + timedelta(seconds=ttl)),
                    "now": timestamp(moment),
                    "plan": plan,
                    "task": task,
                },
            )
        )
        if not found:
            attribute_dispatch_refusal(conn, plan, task)
        attempt = int(found[0]["attempts"])
        append(
            conn,
            kind="task.dispatched",
            plan=plan,
            task=task,
            payload={"attempt": attempt, "ttl_seconds": ttl, "worktree": worktree},
            at=moment,
        )
    return TransitionResult(
        command="dispatch", plan=plan, task=task, status=IN_PROGRESS, attempt=attempt, events=["task.dispatched"]
    )


# ---------------------------------------------------------------------------
# read
# ---------------------------------------------------------------------------


def read(conn: sqlite3.Connection, plan: str, task: str, *, attempt: int | None = None) -> TransitionResult:
    """Read one task with its sections, renewing the lease when an attempt is named.

    Without ``attempt`` this reads, renews nothing and appends nothing. With ``attempt`` on an
    in-progress task it renews the lease.

    Args:
        conn: An open ledger connection.
        plan: The plan id.
        task: The task id.
        attempt: The attempt the runner holds, or None.

    Returns:
        A result carrying the task row and every section row, headed by
        ``ledger_spec.RESPONSE_SECTION`` when the task carries an orchestrator response.
    """
    if attempt is None:
        row = fetch_task(conn, plan, task)
        return TransitionResult(
            command="read", plan=plan, task=task, row=row, sections=with_response(row, sections_of(conn, plan, task))
        )
    events: list[str] = []
    with store.transaction(conn):
        moment = now()
        row = fetch_task(conn, plan, task)
        require_current_attempt(row, attempt)
        if row["status"] == IN_PROGRESS:
            require_open_attempt(row)
            renew_lease(conn, row, moment, via="read")
            events.append("lease.renewed")
        row = fetch_task(conn, plan, task)
        found_sections = with_response(row, sections_of(conn, plan, task))
    return TransitionResult(
        command="read", plan=plan, task=task, row=row, sections=found_sections, events=events, attempt=attempt
    )


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


def update_statement(table: str, assignments: str, where: str) -> str:
    """Assemble an update from an already-validated assignment clause.

    Args:
        table: The table to update.
        assignments: The comma-separated ``column = :parameter`` pairs.
        where: The predicate, written by this module and never by a caller.

    Returns:
        The statement.
    """
    words = ["UPDATE", table, "SET", assignments, "WHERE", where]
    return " ".join(words)


def field_assignments(values: Mapping[str, Any]) -> tuple[str, dict[str, Any]]:
    """Build a SET clause from a mapping :func:`settable` has already permitted.

    Args:
        values: The permitted field-to-value mapping; every key is a column name from
            ``ledger_spec.COLUMNS``, so no caller value reaches the statement text.

    Returns:
        The comma-separated assignments and the parameters they bind, keyed ``set_<column>``.
    """
    parameters = {
        f"set_{name}": json.dumps(value) if isinstance(value, (list, dict)) else value for name, value in values.items()
    }
    return ", ".join(f"{name} = :set_{name}" for name in values), parameters


def next_section_seq(conn: sqlite3.Connection, plan: str, task: str) -> int:
    """Return the next insertion order number for a task's sections.

    Args:
        conn: An open ledger connection.
        plan: The plan id.
        task: The task id.

    Returns:
        One more than the highest ``seq`` the task holds, starting at one.
    """
    found = rows_of(
        conn.execute(
            "SELECT COALESCE(MAX(seq), 0) AS top FROM sections WHERE plan = :plan AND task = :task",
            {"plan": plan, "task": task},
        )
    )
    return int(found[0]["top"]) + 1


def append_section(
    conn: sqlite3.Connection, plan: str, task: str, *, name: str, content: str, attempt: int, moment: datetime
) -> None:
    """Append one section row and its ``task.section`` event.

    Args:
        conn: An open ledger connection, inside the caller's transaction.
        plan: The plan id.
        task: The task id.
        name: The section name.
        content: The section body.
        attempt: The attempt the section is tagged with.
        moment: The instant the caller sampled for this transition.
    """
    conn.execute(
        "INSERT INTO sections (plan, task, name, attempt, content, seq) "
        "VALUES (:plan, :task, :name, :attempt, :content, :seq)",
        {
            "plan": plan,
            "task": task,
            "name": name,
            "attempt": attempt,
            "content": content,
            "seq": next_section_seq(conn, plan, task),
        },
    )
    append(
        conn,
        kind="task.section",
        plan=plan,
        task=task,
        payload={"name": name, "attempt": attempt, "content": content},
        at=moment,
    )


def settable(table: str, columns: Sequence[str], values: Mapping[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Split ``--set`` values into the ones an event may write and the ones it may not.

    Args:
        table: The table being updated.
        columns: The columns the event's ``set_by`` names, from :func:`columns_set_by`.
        values: The caller's field-to-value mapping.

    Returns:
        The values the event sets, and the sorted names of the columns it does not.

    Raises:
        ValueError: When a name is not a stored column of that table in ``ledger_spec.COLUMNS``.
    """
    unknown = sorted(set(values) - set(stored_columns(table)))
    if unknown:
        msg = f"{', '.join(unknown)} are not columns of {table} in ledger_spec.COLUMNS"
        raise ValueError(msg)
    permitted = set(columns)
    return ({name: value for name, value in values.items() if name in permitted}, sorted(set(values) - permitted))


def write_fields(
    conn: sqlite3.Connection, table: str, where: str, parameters: Mapping[str, Any], values: Mapping[str, Any]
) -> None:
    """Apply an already-permitted field mapping to one row.

    Args:
        conn: An open ledger connection, inside the caller's transaction.
        table: The table to update.
        where: The predicate identifying the row, written by this module.
        parameters: The predicate's bound parameters.
        values: The permitted field-to-value mapping; nothing is written when it is empty.
    """
    if not values:
        return
    assignments, bound = field_assignments(values)
    conn.execute(update_statement(table, assignments, where), {**bound, **parameters})


def update_plan_fields(
    conn: sqlite3.Connection, plan: str, values: Mapping[str, Any], moment: datetime
) -> tuple[dict[str, Any], list[str]]:
    """Apply the ``--set`` values ``plan.fields`` sets to a plan row and append the event.

    Args:
        conn: An open ledger connection, inside the caller's transaction.
        plan: The plan id.
        values: The field-to-value mapping.
        moment: The instant the caller sampled for this transition.

    Returns:
        What was written, and the names ``plan.fields`` does not set.
    """
    applied, unsettable = settable("plans", PLAN_FIELD_COLUMNS, values)
    write_fields(conn, "plans", "plan_id = :plan", {"plan": plan}, applied)
    append(conn, kind="plan.fields", plan=plan, task=None, payload={"changed": applied}, at=moment)
    return applied, unsettable


def update_task_fields(
    conn: sqlite3.Connection, plan: str, task: str, values: Mapping[str, Any], moment: datetime
) -> tuple[dict[str, Any], list[str]]:
    """Apply the ``--set`` values ``task.fields`` sets to a task row and append the event.

    A name outside :data:`TASK_FIELD_COLUMNS` is a column no event this transition appends sets, so
    it is not written and comes back for the caller to report.

    Args:
        conn: An open ledger connection, inside the caller's transaction.
        plan: The plan id.
        task: The task id.
        values: The field-to-value mapping.
        moment: The instant the caller sampled for this transition.

    Returns:
        What was written, and the names ``task.fields`` does not set.
    """
    applied, unsettable = settable("tasks", TASK_FIELD_COLUMNS, values)
    write_fields(conn, "tasks", "plan = :plan AND id = :task", {"plan": plan, "task": task}, applied)
    append(conn, kind="task.fields", plan=plan, task=task, payload={"changed": applied}, at=moment)
    return applied, unsettable


def update(
    conn: sqlite3.Connection,
    plan: str,
    task: str | None = None,
    *,
    attempt: int | None = None,
    section: str | None = None,
    section_content: str | None = None,
    values: Mapping[str, Any] | None = None,
) -> TransitionResult:
    """Set fields on a plan or a task and append a section, renewing the lease when asked.

    ``--set`` reaches only the columns whose ``ledger_spec.COLUMNS`` ``set_by`` names the ``fields``
    event this transition appends. A name that is a stored column of the table but not one of those
    is left unwritten and named in the result's ``unsettable`` — ``status`` is the case that matters,
    because moving a task is ``dispatch``, ``finish``, ``state``, ``reclaim`` or ``accept``, each of
    which runs the checks and the cascade that ``update`` does not.

    Args:
        conn: An open ledger connection.
        plan: The plan id.
        task: The task id; when absent the values apply to the plan.
        attempt: The attempt the runner holds, or None.
        section: The section name to append, or None.
        section_content: The section body; required with ``section``.
        values: Field-to-value pairs from ``--set``.

    Returns:
        A result naming the events appended, the fields changed, and any ``--set`` name the
        ``fields`` event does not set.

    Raises:
        ValueError: When a section name is given without content, or a ``--set`` name is not a
            stored column of the table at all.
    """
    if section is not None and section_content is None:
        msg = "a section name needs --section-content"
        raise ValueError(msg)
    requested = dict(values or {})
    changed: dict[str, Any] = {}
    unsettable: list[str] = []
    events: list[str] = []
    with store.transaction(conn):
        moment = now()
        if task is None:
            if requested:
                changed, unsettable = update_plan_fields(conn, plan, requested, moment)
                events.append("plan.fields")
            return TransitionResult(command="update", plan=plan, events=events, changed=changed, unsettable=unsettable)
        row = fetch_task(conn, plan, task)
        if attempt is not None:
            require_current_attempt(row, attempt)
            if row["status"] == IN_PROGRESS:
                require_open_attempt(row)
        if section in ledger_spec.REPORT_SECTIONS and attempt is None:
            refuse("attempt-required")
        if section is not None:
            append_section(
                conn,
                plan,
                task,
                name=section,
                content=str(section_content),
                attempt=int(row["attempts"] or 0),
                moment=moment,
            )
            events.append("task.section")
        if requested:
            changed, unsettable = update_task_fields(conn, plan, task, requested, moment)
            events.append("task.fields")
        if attempt is not None and row["status"] == IN_PROGRESS:
            renew_lease(conn, row, moment, via="update")
            events.append("lease.renewed")
    return TransitionResult(
        command="update", plan=plan, task=task, events=events, changed=changed, unsettable=unsettable, attempt=attempt
    )


# ---------------------------------------------------------------------------
# renew
# ---------------------------------------------------------------------------


def renew(
    conn: sqlite3.Connection,
    plan: str | None = None,
    task: str | None = None,
    *,
    attempt: int | None = None,
    path: str | None = None,
) -> TransitionResult:
    """Push out the lease of the attempt named by an attempt number or by a worktree path.

    Args:
        conn: An open ledger connection.
        plan: The plan id, when addressing by attempt or narrowing a path search.
        task: The task id, when addressing by attempt.
        attempt: The attempt the runner holds.
        path: A file or directory inside a dispatched worktree.

    Returns:
        A result whose ``renew_by`` is the new deadline.

    Raises:
        ValueError: When neither an attempt nor a path addresses the lease.
    """
    if attempt is None and path is None:
        msg = "renew needs --attempt or --path"
        raise ValueError(msg)
    with store.transaction(conn):
        moment = now()
        if path is not None:
            row = task_for_path(conn, path, plan)
        else:
            if plan is None or task is None or attempt is None:
                msg = "renew by attempt needs --address and --attempt"
                raise ValueError(msg)
            row = fetch_task(conn, plan, task)
            require_current_attempt(row, attempt)
            if row["status"] == IN_PROGRESS:
                require_open_attempt(row)
        if row["status"] != IN_PROGRESS:
            return TransitionResult(command="renew", plan=str(row["plan"]), task=str(row["id"]))
        renew_lease(conn, row, moment, via="renew")
        deadline = derive.renew_by(conn, str(row["plan"]), str(row["id"]))
    return TransitionResult(
        command="renew",
        plan=str(row["plan"]),
        task=str(row["id"]),
        attempt=int(row["attempts"] or 0),
        renew_by=deadline,
        events=["lease.renewed"],
    )


# ---------------------------------------------------------------------------
# finish
# ---------------------------------------------------------------------------


def finish(
    conn: sqlite3.Connection, plan: str, task: str, *, attempt: int, result: str, note: str | None = None
) -> TransitionResult:
    """Close an attempt with its outcome; the runner's last command.

    Args:
        conn: An open ledger connection.
        plan: The plan id.
        task: The task id.
        attempt: The attempt the runner holds.
        result: One of ``ledger_spec``'s ``finish --result`` values.
        note: Free text stored on the row.

    Returns:
        A result naming the resulting status and every task the cascade skipped.

    Raises:
        ValueError: When the result is not one the specification lists.
    """
    if result not in FINISH_RESULTS:
        msg = f"--result must be one of {', '.join(FINISH_RESULTS)}"
        raise ValueError(msg)
    cascaded: list[str] = []
    with store.transaction(conn):
        moment = now()
        row = fetch_task(conn, plan, task)
        require_current_attempt(row, attempt)
        if row["status"] != IN_PROGRESS:
            return TransitionResult(command="finish", plan=plan, task=task, attempt=attempt)
        require_open_attempt(row)
        if result == COMPLETE and not report_complete(conn, plan, task, attempt):
            refuse("report-missing")
        new_status = RESULT_STATUS[result]
        conn.execute(
            "UPDATE tasks SET status = :status, attempt_open = 0, result = :result, note = :note, "
            "completed = :completed WHERE plan = :plan AND id = :task",
            {
                "status": new_status,
                "result": result,
                "note": note,
                "completed": timestamp(moment) if result == COMPLETE else row["completed"],
                "plan": plan,
                "task": task,
            },
        )
        append(
            conn,
            kind="task.finished",
            plan=plan,
            task=task,
            payload={"attempt": attempt, "result": result, "note": note},
            at=moment,
        )
        if new_status == FAILED:
            cascaded = cascade(conn, plan, task, moment)
    return TransitionResult(
        command="finish",
        plan=plan,
        task=task,
        attempt=attempt,
        status=new_status,
        cascaded=cascaded,
        events=["task.finished", *(["task.state"] if cascaded else [])],
    )


# ---------------------------------------------------------------------------
# settle
# ---------------------------------------------------------------------------


def settle(
    conn: sqlite3.Connection,
    plan: str | None = None,
    task: str | None = None,
    *,
    attempt: int | None = None,
    path: str | None = None,
    return_text: str | None = None,
) -> TransitionResult:
    """Record what the harness call returned for one attempt.

    Args:
        conn: An open ledger connection.
        plan: The plan id, when addressing by attempt or narrowing a path search.
        task: The task id, when addressing by attempt.
        attempt: The attempt the harness ran.
        path: A file or directory inside the dispatched worktree.
        return_text: What the harness call returned.

    Returns:
        A result, or a ``already-settled`` no-op.

    Raises:
        ValueError: When neither an attempt nor a path addresses the attempt.
    """
    if attempt is None and path is None:
        msg = "settle needs --attempt or --path"
        raise ValueError(msg)
    with store.transaction(conn):
        moment = now()
        if path is not None:
            row = task_for_path(conn, path, plan)
        else:
            if plan is None or task is None or attempt is None:
                msg = "settle by attempt needs --address and --attempt"
                raise ValueError(msg)
            row = fetch_task(conn, plan, task)
            require_current_attempt(row, attempt)
        plan, task = str(row["plan"]), str(row["id"])
        if row["status"] in {NOT_STARTED, DEFERRED, SKIPPED}:
            return TransitionResult(command="settle", plan=plan, task=task)
        if int(row["settled"] or 0) == 1:
            return declined("settle", "already-settled", plan, task)
        closes = row["status"] == IN_PROGRESS
        conn.execute(
            "UPDATE tasks SET settled = 1, return_text = :return_text, "
            "attempt_open = CASE WHEN :closes THEN 0 ELSE attempt_open END "
            "WHERE plan = :plan AND id = :task",
            {"return_text": return_text, "closes": 1 if closes else 0, "plan": plan, "task": task},
        )
        settled_attempt = int(row["attempts"] or 0)
        append(
            conn,
            kind="task.settled",
            plan=plan,
            task=task,
            payload={
                "attempt": settled_attempt,
                "return_text": return_text,
                "via": "path" if path is not None else "attempt",
            },
            at=moment,
        )
    return TransitionResult(command="settle", plan=plan, task=task, attempt=settled_attempt, events=["task.settled"])


# ---------------------------------------------------------------------------
# accept
# ---------------------------------------------------------------------------


def accept(
    conn: sqlite3.Connection, plan: str, task: str, *, note: str | None = None, force: bool = False
) -> TransitionResult:
    """Accept a complete task, completing a returned one first.

    Args:
        conn: An open ledger connection.
        plan: The plan id.
        task: The task id.
        note: Free text stored on the event.
        force: Waive the report check on a returned task.

    Returns:
        A result, or an ``already-accepted`` no-op.
    """
    with store.transaction(conn):
        moment = now()
        row = fetch_task(conn, plan, task)
        if int(row["accepted"] or 0) == 1:
            return declined("accept", "already-accepted", plan, task)
        status = row["status"]
        if status == COMPLETE:
            if int(row["attempt_open"] or 0) == 1:
                refuse("not-complete")
            conn.execute(
                "UPDATE tasks SET accepted = 1 WHERE plan = :plan AND id = :task", {"plan": plan, "task": task}
            )
            append(conn, kind="task.accepted", plan=plan, task=task, payload={"note": note}, at=moment)
            return TransitionResult(command="accept", plan=plan, task=task, events=["task.accepted"])
        if status != IN_PROGRESS:
            refuse("not-complete")
        if not derive.returned(conn, plan, task):
            refuse("not-complete")
        if not force and not report_complete(conn, plan, task, int(row["attempts"] or 0)):
            refuse("report-missing")
        conn.execute(
            "UPDATE tasks SET status = :status, completed = :completed, accepted = 1 WHERE plan = :plan AND id = :task",
            {"status": COMPLETE, "completed": timestamp(moment), "plan": plan, "task": task},
        )
        append(
            conn,
            kind="task.state",
            plan=plan,
            task=task,
            payload={
                "status": COMPLETE,
                "reason": RETURNED_COMPLETE,
                "accepted": 1,
                "attempt_open": int(row["attempt_open"] or 0),
            },
            at=moment,
        )
        append(conn, kind="task.accepted", plan=plan, task=task, payload={"note": note}, at=moment)
    return TransitionResult(
        command="accept", plan=plan, task=task, status=COMPLETE, events=["task.state", "task.accepted"]
    )


# ---------------------------------------------------------------------------
# reclaim
# ---------------------------------------------------------------------------

RECLAIM_SQL = """
UPDATE tasks
   SET status = :status,
       attempts_allowed = :attempts_allowed,
       attempt_open = 0,
       result = NULL,
       note = NULL,
       settled = 0,
       return_text = NULL,
       completed = NULL,
       accepted = 0,
       response = :response
 WHERE plan = :plan AND id = :task
"""


def reclaim_checks(conn: sqlite3.Connection, plan: str, task: str, row: Mapping[str, Any], *, force: bool) -> None:
    """Evaluate the ``task-accepted``, ``leased`` and ``dependents-started`` checks in order.

    Args:
        conn: An open ledger connection.
        plan: The plan id.
        task: The task id.
        row: The task row.
        force: Whether ``--force`` waives the checks.
    """
    if not force and int(row["accepted"] or 0) == 1:
        refuse("task-accepted")
    leased = int(row["attempt_open"] or 0) == 1
    if leased and not force and not derive.returned(conn, plan, task) and not derive.stale(conn, plan, task):
        refuse("leased")
    if not force and dependents_started(conn, plan, task):
        refuse("dependents-started")


def reclaim(
    conn: sqlite3.Connection,
    plan: str,
    task: str,
    *,
    reason: str,
    response: str | None = None,
    force: bool = False,
    more_attempts: bool = False,
    max_attempts: int | None = None,
) -> TransitionResult:
    """Send a task back to not-started for another attempt.

    Args:
        conn: An open ledger connection.
        plan: The plan id.
        task: The task id.
        reason: Why the task is coming back.
        response: Text the next runner reads first.
        force: Waive the acceptance, lease and dependents checks.
        more_attempts: Extend ``attempts_allowed`` by ``loop.max_attempts``.
        max_attempts: The ``loop.max_attempts`` value; the specification default when absent.

    Returns:
        A result naming every dependent whose cascade skip was reversed, or an ``already-open``
        no-op.
    """
    budget = DEFAULT_MAX_ATTEMPTS if max_attempts is None else max_attempts
    restored: list[str] = []
    with store.transaction(conn):
        moment = now()
        row = fetch_task(conn, plan, task)
        from_status = str(row["status"])
        if from_status == NOT_STARTED:
            return declined("reclaim", "already-open", plan, task)
        reclaim_checks(conn, plan, task, row, force=force)
        allowed = int(row["attempts_allowed"] or 0)
        if not (more_attempts or force) and int(row["attempts"] or 0) >= allowed:
            refuse("attempts-exhausted")
        allowed += budget if more_attempts else 0
        allowed += 1 if row["result"] == NEEDS_INPUT else 0
        conn.execute(
            RECLAIM_SQL,
            {"status": NOT_STARTED, "attempts_allowed": allowed, "response": response, "plan": plan, "task": task},
        )
        append(
            conn,
            kind="task.reclaimed",
            plan=plan,
            task=task,
            payload={"from_status": from_status, "reason": reason, "response": response, "attempts_allowed": allowed},
            at=moment,
        )
        if from_status == FAILED:
            restored = reverse_cascade(conn, plan, task, moment)
    return TransitionResult(
        command="reclaim",
        plan=plan,
        task=task,
        status=NOT_STARTED,
        reversed_tasks=restored,
        changed={"attempts_allowed": allowed},
        events=["task.reclaimed", *(["task.state"] if restored else [])],
    )


# ---------------------------------------------------------------------------
# state
# ---------------------------------------------------------------------------


def state(
    conn: sqlite3.Connection, plan: str, task: str, *, new_status: str, reason: str, force: bool = False
) -> TransitionResult:
    """Move a task to a new status without a runner.

    Entering failed runs the cascade. Leaving failed does not reverse it: the dependents stay
    skipped because the work was abandoned rather than redone, and only ``reclaim`` reverses it.

    Args:
        conn: An open ledger connection.
        plan: The plan id.
        task: The task id.
        new_status: One of ``ledger_spec``'s ``state --new-status`` values.
        reason: Why the orchestrator decided this.
        force: Waive the acceptance, lease and report checks and clear acceptance.

    Returns:
        A result naming the resulting status and every task the cascade skipped.
    """
    cascaded: list[str] = []
    with store.transaction(conn):
        moment = now()
        if new_status not in STATE_TARGETS:
            refuse("status-invalid")
        row = fetch_task(conn, plan, task)
        if not force and int(row["accepted"] or 0) == 1:
            refuse("task-accepted")
        if not force and int(row["attempt_open"] or 0) == 1:
            refuse("leased")
        if new_status == COMPLETE and not force and not report_complete(conn, plan, task, int(row["attempts"] or 0)):
            refuse("report-missing")
        conn.execute(
            "UPDATE tasks SET status = :status, attempt_open = 0, accepted = :accepted, completed = :completed "
            "WHERE plan = :plan AND id = :task",
            {
                "status": new_status,
                "accepted": 0 if force else int(row["accepted"] or 0),
                "completed": timestamp(moment) if new_status == COMPLETE else row["completed"],
                "plan": plan,
                "task": task,
            },
        )
        append(
            conn,
            kind="task.state",
            plan=plan,
            task=task,
            payload={
                "status": new_status,
                "reason": reason,
                "accepted": 0 if force else int(row["accepted"] or 0),
                "attempt_open": 0,
            },
            at=moment,
        )
        if new_status == FAILED:
            cascaded = cascade(conn, plan, task, moment)
    return TransitionResult(
        command="state", plan=plan, task=task, status=new_status, cascaded=cascaded, events=["task.state"]
    )


# ---------------------------------------------------------------------------
# Plan-scoped rows
# ---------------------------------------------------------------------------


def task_row(
    definition: Mapping[str, Any], *, plan: str, conflict_group: str | None, max_attempts: int
) -> dict[str, Any]:
    """Normalise a task definition into a full ``tasks`` row.

    Args:
        definition: The caller's task fields, validated through the canonical ``Task`` model.
        plan: The plan the row belongs to.
        conflict_group: The mutual-exclusion group, or None.
        max_attempts: The ``loop.max_attempts`` value ``attempts_allowed`` starts at.

    Returns:
        Every column of ``tasks``, with list-valued model fields JSON encoded.
    """
    fields = dict(definition)
    fields.setdefault("status", NOT_STARTED)
    fields.setdefault("created", now())
    model = Task.model_validate(fields).model_dump(mode="json", by_alias=False)
    row: dict[str, Any] = {
        name: json.dumps(model[name]) if isinstance(model.get(name), (list, dict)) else model.get(name)
        for name in ledger_spec.TASK_MODEL_FIELDS
    }
    row.update(
        plan=plan,
        conflict_group=conflict_group,
        attempts=0,
        attempts_allowed=max_attempts,
        accepted=0,
        attempt_open=0,
        ttl_seconds=None,
        worktree=None,
        expires=None,
        first_renewed=None,
        result=None,
        note=None,
        settled=0,
        return_text=None,
        response=None,
    )
    return row


TASK_INSERT_SQL = insert_statement("tasks", TASK_COLUMNS)
"""The ``tasks`` insert, built once from ``ledger_spec``'s column list rather than a literal."""

PLAN_COLUMNS: tuple[str, ...] = (
    *ledger_spec.PLAN_MODEL_FIELDS,
    "milestone",
    "integration_branch",
    "base_sha",
    "quality_gates",
    "archived",
)

PLAN_INSERT_SQL = insert_statement("plans", PLAN_COLUMNS)
"""The ``plans`` insert, built once from ``ledger_spec``'s column list rather than a literal."""


def insert_task(conn: sqlite3.Connection, row: Mapping[str, Any], *, event: str, moment: datetime) -> None:
    """Insert one task row and append the event that sets its columns.

    ``attempts_allowed`` rides in the payload beside the model fields: it is the one column of a
    fresh row that is not a constant, because ``loop.max_attempts`` is configuration and a fold of
    the log cannot know what it was when the task was added.

    Args:
        conn: An open ledger connection, inside the caller's transaction.
        row: A full ``tasks`` row as :func:`task_row` builds it.
        event: The event kind to append, ``task.added``.
        moment: The instant the caller sampled for this transition.
    """
    conn.execute(TASK_INSERT_SQL, dict(row))
    payload = {name: row.get(name) for name in (*ledger_spec.TASK_MODEL_FIELDS, "conflict_group")}
    payload["attempts_allowed"] = row["attempts_allowed"]
    append(conn, kind=event, plan=str(row["plan"]), task=str(row["id"]), payload=payload, at=moment)


def create(
    conn: sqlite3.Connection,
    *,
    slug: str,
    goal: str,
    owner_reference: str | None = None,
    base_sha: str | None = None,
    quality_gates: Sequence[str] | None = None,
    tasks: Sequence[Mapping[str, Any]] | None = None,
    plan_id: str | None = None,
    max_attempts: int | None = None,
) -> TransitionResult:
    """Create a plan, with its tasks when any are given.

    Args:
        conn: An open ledger connection.
        slug: The plan's human-readable identifier.
        goal: The one-sentence goal statement.
        owner_reference: The work item the plan serves.
        base_sha: The commit a judge diffs a report against.
        quality_gates: The shell commands run before a milestone item merges.
        tasks: Task definitions; the plan starts drafting when none are given.
        plan_id: The plan id to use; one is generated when absent.
        max_attempts: The ``loop.max_attempts`` value ``attempts_allowed`` starts at.

    Returns:
        A result whose ``plan`` is the plan id.
    """
    definitions = list(tasks or [])
    budget = DEFAULT_MAX_ATTEMPTS if max_attempts is None else max_attempts
    identifier = plan_id or f"P{uuid.uuid4().hex[:8]}"
    with store.transaction(conn):
        moment = now()
        if rows_of(conn.execute("SELECT plan_id FROM plans WHERE plan_id = :plan", {"plan": identifier})):
            refuse("exists")
        model = Plan(
            plan_id=identifier,
            feature=slug,
            goal=goal,
            issue=owner_reference,
            state=PlanState.DRAFTING if not definitions else PlanState.READY,
        ).model_dump(mode="json", by_alias=False)
        row: dict[str, Any] = {
            name: json.dumps(model[name]) if isinstance(model.get(name), (list, dict)) else model.get(name)
            for name in ledger_spec.PLAN_MODEL_FIELDS
        }
        row.update(
            milestone=None,
            integration_branch=None,
            base_sha=base_sha,
            quality_gates=json.dumps(list(quality_gates or [])),
            archived=None,
        )
        conn.execute(PLAN_INSERT_SQL, row)
        append(
            conn,
            kind="plan.created",
            plan=identifier,
            task=None,
            payload={name: row.get(name) for name in PLAN_COLUMNS if name != "archived"},
            at=moment,
        )
        for definition in definitions:
            insert_task(
                conn,
                task_row(
                    definition, plan=identifier, conflict_group=definition.get("conflict_group"), max_attempts=budget
                ),
                event="task.added",
                moment=moment,
            )
    return TransitionResult(
        command="create",
        plan=identifier,
        events=["plan.created", *(["task.added"] if definitions else [])],
        changed={"tasks": len(definitions)},
    )


def append_task(
    conn: sqlite3.Connection,
    plan: str,
    *,
    task_id: str,
    task_title: str,
    conflict_group: str | None = None,
    definition: Mapping[str, Any] | None = None,
    max_attempts: int | None = None,
) -> TransitionResult:
    """Add one task to a plan.

    Args:
        conn: An open ledger connection.
        plan: The plan id.
        task_id: The task's id within the plan.
        task_title: The task's title.
        conflict_group: The mutual-exclusion group, or None.
        definition: Further task fields, merged under the id and title.
        max_attempts: The ``loop.max_attempts`` value ``attempts_allowed`` starts at.

    Returns:
        A result naming the added task.
    """
    budget = DEFAULT_MAX_ATTEMPTS if max_attempts is None else max_attempts
    fields = {**dict(definition or {}), "id": task_id, "title": task_title}
    with store.transaction(conn):
        moment = now()
        require_unarchived(conn, plan)
        insert_task(
            conn,
            task_row(fields, plan=plan, conflict_group=conflict_group, max_attempts=budget),
            event="task.added",
            moment=moment,
        )
    return TransitionResult(command="append-task", plan=plan, task=task_id, events=["task.added"])


def finalize(conn: sqlite3.Connection, plan: str) -> TransitionResult:
    """Move a plan out of drafting.

    Args:
        conn: An open ledger connection.
        plan: The plan id.

    Returns:
        A result naming the field it changed.
    """
    ready = PlanState.READY.value
    with store.transaction(conn):
        moment = now()
        require_unarchived(conn, plan)
        conn.execute("UPDATE plans SET state = :state WHERE plan_id = :plan", {"state": ready, "plan": plan})
        append(conn, kind="plan.fields", plan=plan, task=None, payload={"changed": {"state": ready}}, at=moment)
    return TransitionResult(command="finalize", plan=plan, events=["plan.fields"], changed={"state": ready})


def archive(conn: sqlite3.Connection, plan: str, *, reason: str) -> TransitionResult:
    """Archive a plan and close every open attempt on it.

    Args:
        conn: An open ledger connection.
        plan: The plan id.
        reason: Why the plan is being archived.

    Returns:
        A result naming the event appended.
    """
    with store.transaction(conn):
        moment = now()
        require_unarchived(conn, plan)
        conn.execute(
            "UPDATE plans SET archived = :archived WHERE plan_id = :plan", {"archived": timestamp(moment), "plan": plan}
        )
        conn.execute("UPDATE tasks SET attempt_open = 0 WHERE plan = :plan", {"plan": plan})
        append(conn, kind="plan.archived", plan=plan, task=None, payload={"reason": reason}, at=moment)
    return TransitionResult(command="archive", plan=plan, events=["plan.archived"], changed={"archived": True})
