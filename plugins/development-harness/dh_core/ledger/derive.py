"""The derived columns of ``ledger_spec.COLUMNS``, each computed from its ``rule``.

A derived column is never stored. Every function here reads the stored columns and the current
instant and returns the value the specification's rule states, so there is exactly one place the
rule is implemented and one place it can be wrong.

Readiness is the exception worth naming: it is needed both as a question about one row and as the
condition of ``dispatch``'s single conditional UPDATE, which must evaluate it inside the statement
that writes. :data:`READY_PREDICATE` is that one implementation as a SQL fragment;
:mod:`dh_core.ledger.transitions` composes it into ``DISPATCH_SQL`` and :func:`ready` runs it as a
SELECT, so the dispatcher and the reader cannot disagree.

This module imports :mod:`dh_core.ledger.store` for the row reads and the time conventions, and
imports nothing else from the package: :mod:`dh_core.ledger.transitions` imports this one.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from dh_core import ledger_spec
from dh_core.ledger import store

if TYPE_CHECKING:  # pragma: no cover - typing only
    import sqlite3
    from collections.abc import Mapping

NOT_STARTED = ledger_spec.Status.NOT_STARTED.value
IN_PROGRESS = ledger_spec.Status.IN_PROGRESS.value
COMPLETE = ledger_spec.Status.COMPLETE.value
BLOCKED = ledger_spec.Status.BLOCKED.value
FAILED = ledger_spec.Status.FAILED.value
DEFERRED = ledger_spec.Status.DEFERRED.value
SKIPPED = ledger_spec.Status.SKIPPED.value

SUCCESSFUL_DEPENDENCY: tuple[str, ...] = tuple(sorted(s.value for s in ledger_spec.SUCCESSFUL_DEPENDENCY))
"""Statuses that satisfy a dependency without acceptance, in a stable order for binding to SQL."""


def rule_for(table: str, name: str) -> str:
    """Return the specification's rule sentence for one derived column.

    Args:
        table: The table the column belongs to.
        name: The column name.

    Returns:
        The rule as the specification words it.

    Raises:
        KeyError: When the specification declares no such derived column.
    """
    for column in ledger_spec.COLUMNS:
        if column.table == table and column.name == name and column.provenance is ledger_spec.Provenance.DERIVED:
            return column.rule
    msg = f"{table}.{name} is not a derived column in ledger_spec.COLUMNS"
    raise KeyError(msg)


# ---------------------------------------------------------------------------
# tasks.ready
# ---------------------------------------------------------------------------

READY_PREDICATE = """
       tasks.status = :not_started
   AND NOT EXISTS (
         SELECT 1 FROM json_each(COALESCE(tasks.dependencies, '[]')) d
          WHERE NOT EXISTS (
                SELECT 1 FROM tasks dep
                 WHERE dep.plan = tasks.plan
                   AND dep.id = d.value
                   AND (dep.accepted = 1 OR dep.status IN (SELECT value FROM json_each(:successful)))))
   AND NOT EXISTS (
         SELECT 1 FROM tasks o
          WHERE o.plan = tasks.plan
            AND o.id <> tasks.id
            AND o.conflict_group IS NOT NULL
            AND o.conflict_group = tasks.conflict_group
            AND (o.status = :in_progress OR (o.status = :complete AND o.accepted = 0)))
"""
"""``tasks.ready`` as a SQL predicate over the ``tasks`` row in scope.

The three clauses are the three the rule names: the status is not-started; every id in
``dependencies`` names a task that is accepted or in ``SUCCESSFUL_DEPENDENCY``, which a dangling id
therefore fails; and no other task sharing a non-null ``conflict_group`` is in-progress or
complete-unaccepted. A dependency read through ``json_each`` sees the same row version the
statement writes, which is why ``dispatch`` can carry this in its WHERE rather than checking first.

Bind :func:`ready_parameters` alongside whatever the surrounding statement binds.
"""


def ready_parameters() -> dict[str, Any]:
    """Return the bindings :data:`READY_PREDICATE` needs.

    Returns:
        The statuses the predicate compares against, with the dependency-satisfying set as JSON.
    """
    return {
        "not_started": NOT_STARTED,
        "in_progress": IN_PROGRESS,
        "complete": COMPLETE,
        "successful": json.dumps(list(SUCCESSFUL_DEPENDENCY)),
    }


def ready(conn: sqlite3.Connection, plan: str, task: str) -> bool:
    """Report whether one task satisfies ``tasks.ready``.

    Args:
        conn: An open ledger connection.
        plan: The plan id.
        task: The task id.

    Returns:
        True when the task is dispatchable.

    Raises:
        LookupError: When the plan holds no such task.
    """
    store.fetch_task(conn, plan, task)
    words = ["SELECT 1 FROM tasks WHERE tasks.plan = :plan AND tasks.id = :task AND (", READY_PREDICATE, ")"]
    found = store.rows_of(conn.execute(" ".join(words), {**ready_parameters(), "plan": plan, "task": task}))
    return bool(found)


def ready_tasks(conn: sqlite3.Connection, plan: str) -> list[dict[str, Any]]:
    """Read every task of one plan whose ``ready`` is true.

    Args:
        conn: An open ledger connection.
        plan: The plan id.

    Returns:
        The rows as dictionaries, ordered by id.

    """
    words = ["SELECT * FROM tasks WHERE tasks.plan = :plan AND (", READY_PREDICATE, ") ORDER BY tasks.id"]
    return store.rows_of(conn.execute(" ".join(words), {**ready_parameters(), "plan": plan}))


# ---------------------------------------------------------------------------
# tasks.expired, tasks.stale, tasks.returned, tasks.renew_by
# ---------------------------------------------------------------------------


def attempt_open(row: Mapping[str, Any]) -> bool:
    """Report whether a task row holds an open attempt.

    Args:
        row: The task row.

    Returns:
        True when ``attempt_open`` is 1.
    """
    return int(row["attempt_open"] or 0) == 1


def expired_row(row: Mapping[str, Any], instant: datetime | None = None) -> bool:
    """Compute ``tasks.expired`` from a task row.

    Args:
        row: The task row.
        instant: The instant to compare against; the current one when absent.

    Returns:
        True when the attempt is open and the instant is past ``expires``.
    """
    deadline = store.moment(row["expires"])
    if not attempt_open(row) or deadline is None:
        return False
    return (instant or store.now()) > deadline


def stale_row(row: Mapping[str, Any], instant: datetime | None = None) -> bool:
    """Compute ``tasks.stale`` from a task row.

    Args:
        row: The task row.
        instant: The instant to compare against; the current one when absent.

    Returns:
        True when the attempt is open and the instant is past ``expires`` plus ``ttl_seconds``.
    """
    deadline = store.moment(row["expires"])
    if not attempt_open(row) or deadline is None:
        return False
    ttl = int(row["ttl_seconds"] or 0)
    return (instant or store.now()) > deadline + timedelta(seconds=ttl)


def returned_row(row: Mapping[str, Any]) -> bool:
    """Compute ``tasks.returned`` from a task row.

    Args:
        row: The task row.

    Returns:
        True when the status is in-progress and ``settled`` is 1.
    """
    return row["status"] == IN_PROGRESS and int(row["settled"] or 0) == 1


def renew_by_row(row: Mapping[str, Any]) -> datetime | None:
    """Compute ``tasks.renew_by`` from a task row.

    Args:
        row: The task row.

    Returns:
        ``expires`` when the attempt is open, None otherwise.
    """
    return store.moment(row["expires"]) if attempt_open(row) else None


def expired(conn: sqlite3.Connection, plan: str, task: str, instant: datetime | None = None) -> bool:
    """Read ``tasks.expired`` for one task.

    Args:
        conn: An open ledger connection.
        plan: The plan id.
        task: The task id.
        instant: The instant to compare against; the current one when absent.

    Returns:
        True when the lease deadline has passed with the attempt still open.
    """
    return expired_row(store.fetch_task(conn, plan, task), instant)


def stale(conn: sqlite3.Connection, plan: str, task: str, instant: datetime | None = None) -> bool:
    """Read ``tasks.stale`` for one task.

    Args:
        conn: An open ledger connection.
        plan: The plan id.
        task: The task id.
        instant: The instant to compare against; the current one when absent.

    Returns:
        True when a whole further lease length has passed since the deadline.
    """
    return stale_row(store.fetch_task(conn, plan, task), instant)


def returned(conn: sqlite3.Connection, plan: str, task: str) -> bool:
    """Read ``tasks.returned`` for one task.

    Args:
        conn: An open ledger connection.
        plan: The plan id.
        task: The task id.

    Returns:
        True when the runner's harness call has returned while the task is still in-progress.
    """
    return returned_row(store.fetch_task(conn, plan, task))


def renew_by(conn: sqlite3.Connection, plan: str, task: str) -> datetime | None:
    """Read ``tasks.renew_by`` for one task.

    Args:
        conn: An open ledger connection.
        plan: The plan id.
        task: The task id.

    Returns:
        The instant the lease must be renewed by, or None when no attempt is open.
    """
    return renew_by_row(store.fetch_task(conn, plan, task))


def task_derived(conn: sqlite3.Connection, row: Mapping[str, Any], instant: datetime | None = None) -> dict[str, Any]:
    """Compute every derived column of one task row.

    Args:
        conn: An open ledger connection, used for readiness.
        row: The task row.
        instant: The instant the lease columns compare against; the current one when absent.

    Returns:
        The derived columns keyed by name, ready to merge into the row for display.
    """
    return {
        "ready": ready(conn, str(row["plan"]), str(row["id"])),
        "expired": expired_row(row, instant),
        "stale": stale_row(row, instant),
        "returned": returned_row(row),
        "renew_by": renew_by_row(row),
    }


# ---------------------------------------------------------------------------
# plans.progress
# ---------------------------------------------------------------------------


class Progress(StrEnum):
    """The values of ``plans.progress``, each named by the column's rule."""

    ARCHIVED = "archived"
    FAILED = "failed"
    DONE = "done"
    OPEN = "open"


PROGRESS_RULE = rule_for("plans", "progress")
"""The specification's sentence for ``plans.progress``, read at import."""


def check_progress_values() -> None:
    """Reject a :class:`Progress` value the specification's rule does not name.

    Raises:
        ValueError: When a value does not appear in the rule sentence.
    """
    missing = sorted(value for value in Progress if value not in PROGRESS_RULE)
    if missing:
        msg = f"plans.progress rule does not name {', '.join(missing)}"
        raise ValueError(msg)


check_progress_values()

BLOCKING_STATUSES: frozenset[str] = frozenset({NOT_STARTED, IN_PROGRESS, BLOCKED})
"""The statuses the ``failed`` clause counts as work still outstanding, besides complete-unaccepted."""

SETTLED_STATUSES: frozenset[str] = frozenset({DEFERRED, SKIPPED})
"""The statuses the ``done`` clause accepts without acceptance."""


def outstanding(row: Mapping[str, Any]) -> bool:
    """Report whether a task row is work the ``failed`` clause still counts.

    Args:
        row: The task row.

    Returns:
        True when the status is not-started, in-progress or blocked, or the task is complete and
        not yet accepted.
    """
    status = str(row["status"])
    if status in BLOCKING_STATUSES:
        return True
    return status == COMPLETE and int(row["accepted"] or 0) == 0


def satisfied(row: Mapping[str, Any]) -> bool:
    """Report whether a task row is one the ``done`` clause accepts.

    Args:
        row: The task row.

    Returns:
        True when the task is accepted, deferred or skipped.
    """
    return int(row["accepted"] or 0) == 1 or str(row["status"]) in SETTLED_STATUSES


def progress(conn: sqlite3.Connection, plan: str) -> str:
    """Read ``plans.progress`` for one plan.

    Args:
        conn: An open ledger connection.
        plan: The plan id.

    Returns:
        One of :class:`Progress`, following the column's rule clause by clause.

    Raises:
        LookupError: When no such plan exists.
    """
    if store.fetch_plan(conn, plan)["archived"] is not None:
        return Progress.ARCHIVED.value
    rows = store.plan_tasks(conn, plan)
    if not any(outstanding(row) for row in rows) and any(str(row["status"]) == FAILED for row in rows):
        return Progress.FAILED.value
    if rows and all(satisfied(row) for row in rows):
        return Progress.DONE.value
    return Progress.OPEN.value
