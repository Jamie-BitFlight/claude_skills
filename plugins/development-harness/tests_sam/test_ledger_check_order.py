"""Ordering tests for the checks ``ledger_spec.TRANSITIONS`` lists against each transition.

``ledger_spec.Check`` says a transition's checks are "evaluated in order; the first failing check's
reason is printed", and most transitions carry more than one. The conformance suite arranges one
state per transition and so only ever makes a single check fail: reversing two checks inside
``dh_core.ledger`` leaves it green. This module arranges states in which two checks of one
transition fail together and asserts the reason that arrives is the one the specification puts
first.

Nothing here names the winning reason. A case declares the command, the status it arranged, and the
unordered pair of checks it made fail; :func:`spec_order` reads ``ledger_spec.TRANSITIONS`` for that
entry and derives which of the two the implementation owes. Reordering the specification therefore
reorders the expectation, and an implementation left on the old order turns red.

:func:`test_every_constructible_ordering_has_a_case` closes the file over the specification: it
enumerates every ordered pair of checks of every transition, subtracts :data:`UNCONSTRUCTIBLE`, and
asserts the remainder is exactly what the cases cover. A transition gaining a second check, or a new
multi-check transition, fails that test rather than passing unnoticed.

Pairs are keyed by command rather than by ``(command, from_status)``: a command repeats one check
list across the statuses it refuses from, and
:func:`test_the_spec_orders_every_pair_the_same_way_in_every_status` proves no command orders a pair
one way in one status and the other way in another, which is what makes that collapse sound.

Several arrangements need a task that is accepted and something else at once — leased, unreported,
or in a status other than complete — and no sequence of task-scoped commands reaches those:
``accept`` needs a closed attempt on a complete or returned task, ``dispatch`` needs a not-started
one, and only ``reclaim`` reaches not-started, clearing acceptance on the way. ``import`` is the way
in, because it writes ``attempts``, ``accepted`` and the status from the source; those arrangements
import the task in the state they need and, where they need a lease, dispatch it afterwards.

The pairs no ledger state can make fail together, and why each was ruled out rather than missed:

* ``dispatch`` ``archived`` with ``leased`` — ``archive`` sets ``attempt_open`` to 0 on every task
  of the plan in the transaction that sets ``plans.archived``; ``dispatch`` is the only writer of
  ``attempt_open`` 1 and its statement refuses on an archived plan. No state holds both.
* ``update`` ``stale-attempt`` with ``attempt-required``, and ``attempt-closed`` with
  ``attempt-required`` — ``attempt-required``'s condition is that ``--attempt`` is absent, and the
  other two are evaluated only when it is present.
* ``renew`` ``stale-attempt`` with ``unmatched-path``, and ``attempt-closed`` with
  ``unmatched-path`` — ``renew`` addresses the lease by ``--path`` or by ``--attempt``, and each
  check's ``unless`` waives it in the other's branch, so at most one branch is ever evaluated.
* ``settle`` ``stale-attempt`` with ``unmatched-path`` — the same branch exclusivity.
* ``settle`` ``unmatched-path`` with ``already-settled`` — ``unmatched-path`` means the path search
  matched no row, so ``already-settled`` has no task to be true of; and the search considers only
  tasks with ``attempt_open`` 1, which a settled task never has.
* ``state`` ``status-invalid`` with ``report-missing`` — ``report-missing`` is reached only when
  ``--new-status`` is ``complete``, which is a status ``status-invalid`` accepts.
One pair is unreachable from one status but not from another, and so is not excused. ``accept``
from ``complete`` cannot hold ``already-accepted`` with ``not-complete``: ``not-complete`` needs an
open attempt there, and a task with an open attempt is one ``accept`` never accepted. The same pair
is reachable from ``blocked`` — an imported accepted task in a status ``accept`` refuses — and
pairs are keyed by command, so the case built from ``blocked`` covers it.
"""

from __future__ import annotations

import itertools
import sqlite3
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from dh_core import ledger, ledger_spec as spec
from pydantic import BaseModel, ConfigDict

# ---------------------------------------------------------------------------
# Values read from the specification
# ---------------------------------------------------------------------------

NOT_STARTED = spec.Status.NOT_STARTED.value
IN_PROGRESS = spec.Status.IN_PROGRESS.value
COMPLETE = spec.Status.COMPLETE.value
BLOCKED = spec.Status.BLOCKED.value
DEFERRED = spec.Status.DEFERRED.value

MAX_ATTEMPTS: int = next(entry.default for entry in spec.CONFIG if entry.key == "loop.max_attempts")
"""``loop.max_attempts``: how many attempts a task starts with before ``attempts-exhausted``."""

CHECKS: dict[tuple[str, str], tuple[str, ...]] = {
    (entry.command, entry.from_status): tuple(check.reason for check in entry.checks) for entry in spec.TRANSITIONS
}
"""Each transition's check order, keyed by the entry it belongs to."""

TTL = 60
"""The lease length every arrangement dispatches with."""

LEDGER_FILE = "check-order.db"
"""The database file each arrangement opens inside its own temporary directory."""

INVALID_STATUS = "not-a-status"
"""A ``state --new-status`` value no status matches, so ``status-invalid`` fails."""

ONE_TASK: list[dict[str, Any]] = [{"id": "T1", "title": "first"}]
"""A plan of one task."""

TASK_AND_DEPENDENT: list[dict[str, Any]] = [
    {"id": "T1", "title": "first"},
    {"id": "T2", "title": "second", "dependencies": ["T1"]},
]
"""A plan of one task and a dependent, so ``dependents-started`` has somewhere to come from."""

IMPORTED_PLAN = "Pimported"
"""The plan id the imported arrangements use."""


# ---------------------------------------------------------------------------
# What the specification says about a pair of checks
# ---------------------------------------------------------------------------


def pairs_of(reasons: tuple[str, ...]) -> list[tuple[str, str]]:
    """Return every ordered pair of one transition's checks, earlier first.

    Args:
        reasons: One transition's check reasons in specification order.

    Returns:
        Each ``(earlier, later)`` combination, in specification order.
    """
    return list(itertools.combinations(reasons, 2))


def spec_pairs() -> dict[str, set[tuple[str, str]]]:
    """Return every ordered pair of checks the specification states, by command.

    Returns:
        Command name to the set of ``(earlier, later)`` reason pairs its transitions order.
    """
    found: dict[str, set[tuple[str, str]]] = defaultdict(set)
    for entry in spec.TRANSITIONS:
        found[entry.command].update(pairs_of(tuple(check.reason for check in entry.checks)))
    return dict(found)


def unordered(command: str, checks: tuple[str, str]) -> tuple[str, str, str]:
    """Return one pair's identity, independent of which check the specification puts first.

    Args:
        command: The command whose transition orders the pair.
        checks: The two reason codes, in either order.

    Returns:
        The command with the two reasons sorted, so a case and the specification agree on the key.
    """
    first, second = sorted(checks)
    return command, first, second


SPEC_PAIRS: frozenset[tuple[str, str, str]] = frozenset(
    unordered(command, pair) for command, pairs in spec_pairs().items() for pair in pairs
)
"""Every pair of checks the specification orders, keyed by command and independent of direction."""

UNCONSTRUCTIBLE: dict[tuple[str, str, str], str] = {
    unordered("dispatch", ("archived", "leased")): (
        "archive closes every attempt of the plan in the transaction that sets plans.archived, and "
        "dispatch is the only writer of attempt_open 1 and refuses on an archived plan"
    ),
    unordered("update", ("stale-attempt", "attempt-required")): (
        "attempt-required fires only when --attempt is absent; stale-attempt only when it is present"
    ),
    unordered("update", ("attempt-closed", "attempt-required")): (
        "attempt-required fires only when --attempt is absent; attempt-closed only when it is present"
    ),
    unordered("renew", ("stale-attempt", "unmatched-path")): (
        "renew takes the --path branch or the --attempt branch, and each check's unless waives it in the other"
    ),
    unordered("renew", ("attempt-closed", "unmatched-path")): (
        "renew takes the --path branch or the --attempt branch, and each check's unless waives it in the other"
    ),
    unordered("settle", ("stale-attempt", "unmatched-path")): (
        "settle takes the --path branch or the --attempt branch, and each check's unless waives it in the other"
    ),
    unordered("settle", ("unmatched-path", "already-settled")): (
        "unmatched-path means the path search matched no row, so already-settled has no task to be true of; "
        "the search only considers tasks with attempt_open 1, which a settled task never has"
    ),
    unordered("state", ("status-invalid", "report-missing")): (
        "report-missing is reached only when --new-status is complete, which status-invalid accepts"
    ),
}
"""The pairs of checks no ledger state makes fail together, each with why it was ruled out."""


def spec_order(command: str, from_status: str, checks: tuple[str, str]) -> tuple[str, str]:
    """Return a pair of checks in the order the specification evaluates them.

    Args:
        command: The command the case runs.
        from_status: The status the case arranged, or ``ledger_spec.ANY``.
        checks: The two reason codes the case made fail, in either order.

    Returns:
        The pair as ``(earlier, later)``, read from the entry's ``checks`` list.
    """
    order = CHECKS[command, from_status]
    first, second = checks
    assert first in order, f"{first} is not a check of {command}/{from_status}"
    assert second in order, f"{second} is not a check of {command}/{from_status}"
    return (first, second) if order.index(first) < order.index(second) else (second, first)


# ---------------------------------------------------------------------------
# The shape of one case
# ---------------------------------------------------------------------------


class Arranged(BaseModel):
    """One ledger in a state where two checks of a transition fail, and the run that hits them."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    conn: sqlite3.Connection
    plan: str
    run: Callable[[], Any]
    task: str = ""
    """The addressed task, when the transition is task-scoped."""


class OrderCase(BaseModel):
    """One transition entry, the two checks a scenario makes fail, and the scenario."""

    command: str
    from_status: str
    checks: tuple[str, str]
    """The two reason codes, in no particular order: the specification decides which wins."""
    build: Callable[[Path], Arranged]


CASES: list[OrderCase] = []


def register(command: str, from_status: str, checks: tuple[str, str]) -> Callable[..., Callable[[Path], Arranged]]:
    """Register one scenario against the transition entry and pair of checks it exercises.

    Args:
        command: The command the scenario runs.
        from_status: The status the scenario arranges, or ``ledger_spec.ANY``.
        checks: The two reason codes the scenario makes fail, in either order.

    Returns:
        A decorator that records the builder and returns it unchanged.
    """

    def decorate(builder: Callable[[Path], Arranged]) -> Callable[[Path], Arranged]:
        CASES.append(OrderCase(command=command, from_status=from_status, checks=checks, build=builder))
        return builder

    return decorate


# ---------------------------------------------------------------------------
# Building a ledger and reaching a state
# ---------------------------------------------------------------------------


def new_ledger(tmp_path: Path) -> sqlite3.Connection:
    """Open an empty ledger in a temporary directory.

    Args:
        tmp_path: The test's temporary directory.

    Returns:
        An open connection with the schema present.
    """
    return ledger.open_ledger(tmp_path / LEDGER_FILE)


def plan_with(conn: sqlite3.Connection, tasks: list[dict[str, Any]]) -> str:
    """Create a plan holding some tasks.

    Args:
        conn: An open ledger connection.
        tasks: The task definitions.

    Returns:
        The plan id.
    """
    return str(ledger.create(conn, slug="feature", goal="goal", tasks=tasks).plan)


def dispatch_task(conn: sqlite3.Connection, plan: str, task: str = "T1") -> int:
    """Dispatch one task and return the attempt it opened.

    Args:
        conn: An open ledger connection.
        plan: The plan id.
        task: The task id.

    Returns:
        The new attempt number.
    """
    return int(ledger.dispatch(conn, plan, task, ttl_seconds=TTL).attempt or 0)


def add_reports(conn: sqlite3.Connection, plan: str, task: str, attempt: int) -> None:
    """Append every report section for one attempt, so ``report-missing`` passes.

    Args:
        conn: An open ledger connection.
        plan: The plan id.
        task: The task id.
        attempt: The attempt the sections are tagged with.
    """
    for name in spec.REPORT_SECTIONS:
        ledger.update(conn, plan, task, attempt=attempt, section=name, section_content="body")


def returned_task(conn: sqlite3.Connection, plan: str, task: str = "T1") -> int:
    """Dispatch and settle a task, leaving it in-progress with its attempt closed.

    ``settle`` is the one command that closes an attempt without moving the task, which is the only
    way ``attempt-closed`` can fail while the entry under test is the in-progress one.

    Args:
        conn: An open ledger connection.
        plan: The plan id.
        task: The task id.

    Returns:
        The attempt that was opened and then closed.
    """
    attempt = dispatch_task(conn, plan, task)
    ledger.settle(conn, plan, task, attempt=attempt, return_text="the harness returned")
    return attempt


def complete_and_accept(conn: sqlite3.Connection, plan: str, task: str = "T1") -> int:
    """Take a task through a reported attempt to complete and accepted.

    Args:
        conn: An open ledger connection.
        plan: The plan id.
        task: The task id.

    Returns:
        The attempt that completed it.
    """
    attempt = dispatch_task(conn, plan, task)
    add_reports(conn, plan, task, attempt)
    ledger.finish(conn, plan, task, attempt=attempt, result=COMPLETE)
    ledger.accept(conn, plan, task)
    return attempt


def burn_attempts(conn: sqlite3.Connection, plan: str, count: int, task: str = "T1") -> None:
    """Spend attempts on a task, leaving it blocked with the last attempt closed.

    ``blocked`` is the outcome used rather than ``failed`` because finishing failed cascades over
    the not-started dependents, and ``dependents-started`` ignores a dependent this task skipped.

    Args:
        conn: An open ledger connection.
        plan: The plan id.
        count: How many attempts to spend.
        task: The task id.
    """
    for spent in range(1, count + 1):
        attempt = dispatch_task(conn, plan, task)
        ledger.finish(conn, plan, task, attempt=attempt, result=BLOCKED)
        if spent < count:
            ledger.reclaim(conn, plan, task, reason="another attempt")


def import_source(*, status: str, accepted: int, attempts: int = 0) -> ledger.PlanSource:
    """Build a one-task import source, which is where a state the commands cannot reach comes from.

    Args:
        status: The task's status in the source.
        accepted: Whether the source says the task was accepted.
        attempts: How many attempts the source says it has spent.

    Returns:
        The source, ready for ``import``.
    """
    return ledger.PlanSource(
        plan_id=IMPORTED_PLAN,
        fields={"feature": "imported", "goal": "carry a plan in"},
        tasks=[
            ledger.TaskSource(
                fields={"id": "T1", "title": "first", "status": status},
                attempts=attempts,
                attempts_allowed=MAX_ATTEMPTS,
                accepted=accepted,
            )
        ],
        source="content",
        revision="r1",
    )


def imported(conn: sqlite3.Connection, *, status: str, accepted: int, attempts: int = 0) -> str:
    """Import a one-task plan in a state the task commands cannot reach on their own.

    Args:
        conn: An open ledger connection.
        status: The task's status in the source.
        accepted: Whether the source says the task was accepted.
        attempts: How many attempts the source says it has spent.

    Returns:
        The imported plan's id.
    """
    ledger.import_plan(conn, import_source(status=status, accepted=accepted, attempts=attempts), projection_hash="hash")
    return IMPORTED_PLAN


def milestone_plan() -> ledger.PlanSource:
    """Build the plan one milestone item describes.

    Returns:
        The source, ready for ``from-milestone``.
    """
    return ledger.milestone_source(
        milestone_number=7,
        integration_branch="milestone-7",
        base_sha="0123456789abcdef",
        items=[ledger.MilestoneItem(issue=11, title="first", task_id="T1")],
    )


def task_status(conn: sqlite3.Connection, plan: str, task: str) -> str:
    """Read one task's status through the package's own reader.

    Args:
        conn: An open ledger connection.
        plan: The plan id.
        task: The task id.

    Returns:
        The status the row holds.
    """
    row = ledger.read(conn, plan, task).row
    assert row is not None, f"no row for {plan}/{task}"
    return str(row["status"])


def outcome_of(run: Callable[[], Any]) -> str:
    """Run a command and return the reason code it stopped on.

    A refusal raises; a no-op comes back on the result instead, and both kinds appear among the
    checks of a transition, so both are read the same way here.

    Args:
        run: The call that exercises the transition.

    Returns:
        The ``ledger_spec.REASONS`` code the command stopped on.
    """
    try:
        result = run()
    except ledger.Refusal as refusal:
        return refusal.reason
    noop = getattr(result, "noop", None)
    assert noop, f"the command neither refused nor declined: {result!r}"
    return str(noop)


# ---------------------------------------------------------------------------
# dispatch
# ---------------------------------------------------------------------------


@register("dispatch", NOT_STARTED, ("archived", "not-ready"))
def dispatch_archived_and_unready(tmp_path: Path) -> Arranged:
    """Archive a plan whose T2 is waiting on an unaccepted T1, then dispatch T2."""
    conn = new_ledger(tmp_path)
    plan = plan_with(conn, TASK_AND_DEPENDENT)
    ledger.archive(conn, plan, reason="superseded")
    return Arranged(conn=conn, plan=plan, task="T2", run=lambda: ledger.dispatch(conn, plan, "T2", ttl_seconds=TTL))


@register("dispatch", IN_PROGRESS, ("leased", "not-ready"))
def dispatch_leased_and_unready(tmp_path: Path) -> Arranged:
    """Dispatch a task that already holds an open attempt, which is also no longer ready."""
    conn = new_ledger(tmp_path)
    plan = plan_with(conn, ONE_TASK)
    dispatch_task(conn, plan)
    return Arranged(conn=conn, plan=plan, task="T1", run=lambda: ledger.dispatch(conn, plan, "T1", ttl_seconds=TTL))


# ---------------------------------------------------------------------------
# read, update, renew
# ---------------------------------------------------------------------------


@register("read", IN_PROGRESS, ("stale-attempt", "attempt-closed"))
def read_stale_and_closed(tmp_path: Path) -> Arranged:
    """Read a settled in-progress task with an attempt number that is not its current one."""
    conn = new_ledger(tmp_path)
    plan = plan_with(conn, ONE_TASK)
    attempt = returned_task(conn, plan)
    return Arranged(conn=conn, plan=plan, task="T1", run=lambda: ledger.read(conn, plan, "T1", attempt=attempt + 1))


@register("update", IN_PROGRESS, ("stale-attempt", "attempt-closed"))
def update_stale_and_closed(tmp_path: Path) -> Arranged:
    """Update a settled in-progress task with an attempt number that is not its current one."""
    conn = new_ledger(tmp_path)
    plan = plan_with(conn, ONE_TASK)
    attempt = returned_task(conn, plan)
    return Arranged(
        conn=conn,
        plan=plan,
        task="T1",
        run=lambda: ledger.update(conn, plan, "T1", attempt=attempt + 1, values={"title": "renamed"}),
    )


@register("renew", IN_PROGRESS, ("stale-attempt", "attempt-closed"))
def renew_stale_and_closed(tmp_path: Path) -> Arranged:
    """Renew a settled in-progress task with an attempt number that is not its current one."""
    conn = new_ledger(tmp_path)
    plan = plan_with(conn, ONE_TASK)
    attempt = returned_task(conn, plan)
    return Arranged(conn=conn, plan=plan, task="T1", run=lambda: ledger.renew(conn, plan, "T1", attempt=attempt + 1))


# ---------------------------------------------------------------------------
# finish
# ---------------------------------------------------------------------------


@register("finish", IN_PROGRESS, ("stale-attempt", "attempt-closed"))
def finish_stale_and_closed(tmp_path: Path) -> Arranged:
    """Finish a settled in-progress task with an attempt number that is not its current one."""
    conn = new_ledger(tmp_path)
    plan = plan_with(conn, ONE_TASK)
    attempt = returned_task(conn, plan)
    return Arranged(
        conn=conn,
        plan=plan,
        task="T1",
        run=lambda: ledger.finish(conn, plan, "T1", attempt=attempt + 1, result=COMPLETE),
    )


@register("finish", IN_PROGRESS, ("stale-attempt", "report-missing"))
def finish_stale_and_unreported(tmp_path: Path) -> Arranged:
    """Finish an unreported open attempt complete, with an attempt number that is not the current one."""
    conn = new_ledger(tmp_path)
    plan = plan_with(conn, ONE_TASK)
    attempt = dispatch_task(conn, plan)
    return Arranged(
        conn=conn,
        plan=plan,
        task="T1",
        run=lambda: ledger.finish(conn, plan, "T1", attempt=attempt + 1, result=COMPLETE),
    )


@register("finish", IN_PROGRESS, ("attempt-closed", "report-missing"))
def finish_closed_and_unreported(tmp_path: Path) -> Arranged:
    """Finish a settled, unreported in-progress task complete on its own attempt number."""
    conn = new_ledger(tmp_path)
    plan = plan_with(conn, ONE_TASK)
    attempt = returned_task(conn, plan)
    return Arranged(
        conn=conn, plan=plan, task="T1", run=lambda: ledger.finish(conn, plan, "T1", attempt=attempt, result=COMPLETE)
    )


# ---------------------------------------------------------------------------
# settle
# ---------------------------------------------------------------------------


@register("settle", IN_PROGRESS, ("stale-attempt", "already-settled"))
def settle_stale_and_settled(tmp_path: Path) -> Arranged:
    """Settle an already-settled in-progress task with an attempt number that is not its current one."""
    conn = new_ledger(tmp_path)
    plan = plan_with(conn, ONE_TASK)
    attempt = returned_task(conn, plan)
    return Arranged(
        conn=conn,
        plan=plan,
        task="T1",
        run=lambda: ledger.settle(conn, plan, "T1", attempt=attempt + 1, return_text="again"),
    )


@register("settle", COMPLETE, ("stale-attempt", "already-settled"))
def settle_stale_and_settled_when_complete(tmp_path: Path) -> Arranged:
    """Settle an already-settled complete task with an attempt number that is not its current one."""
    conn = new_ledger(tmp_path)
    plan = plan_with(conn, ONE_TASK)
    attempt = dispatch_task(conn, plan)
    add_reports(conn, plan, "T1", attempt)
    ledger.finish(conn, plan, "T1", attempt=attempt, result=COMPLETE)
    ledger.settle(conn, plan, "T1", attempt=attempt, return_text="the harness returned")
    return Arranged(
        conn=conn,
        plan=plan,
        task="T1",
        run=lambda: ledger.settle(conn, plan, "T1", attempt=attempt + 1, return_text="again"),
    )


# ---------------------------------------------------------------------------
# accept
# ---------------------------------------------------------------------------


@register("accept", BLOCKED, ("already-accepted", "not-complete"))
def accept_accepted_and_incomplete(tmp_path: Path) -> Arranged:
    """Accept an imported task the source calls accepted while its status is blocked."""
    conn = new_ledger(tmp_path)
    plan = imported(conn, status=BLOCKED, accepted=1)
    return Arranged(conn=conn, plan=plan, task="T1", run=lambda: ledger.accept(conn, plan, "T1"))


@register("accept", IN_PROGRESS, ("already-accepted", "report-missing"))
def accept_accepted_and_unreported(tmp_path: Path) -> Arranged:
    """Accept an already-accepted task that has been returned without writing its report."""
    conn = new_ledger(tmp_path)
    plan = imported(conn, status=NOT_STARTED, accepted=1)
    returned_task(conn, plan)
    return Arranged(conn=conn, plan=plan, task="T1", run=lambda: ledger.accept(conn, plan, "T1"))


@register("accept", IN_PROGRESS, ("not-complete", "report-missing"))
def accept_incomplete_and_unreported(tmp_path: Path) -> Arranged:
    """Accept a task whose runner has neither returned nor written a report."""
    conn = new_ledger(tmp_path)
    plan = plan_with(conn, ONE_TASK)
    dispatch_task(conn, plan)
    return Arranged(conn=conn, plan=plan, task="T1", run=lambda: ledger.accept(conn, plan, "T1"))


# ---------------------------------------------------------------------------
# reclaim
# ---------------------------------------------------------------------------


@register("reclaim", IN_PROGRESS, ("task-accepted", "leased"))
def reclaim_accepted_and_leased(tmp_path: Path) -> Arranged:
    """Reclaim an imported accepted task that has since been dispatched."""
    conn = new_ledger(tmp_path)
    plan = imported(conn, status=NOT_STARTED, accepted=1)
    dispatch_task(conn, plan)
    return Arranged(conn=conn, plan=plan, task="T1", run=lambda: ledger.reclaim(conn, plan, "T1", reason="redo"))


@register("reclaim", COMPLETE, ("task-accepted", "dependents-started"))
def reclaim_accepted_with_started_dependent(tmp_path: Path) -> Arranged:
    """Reclaim an accepted task whose dependent has already spent an attempt."""
    conn = new_ledger(tmp_path)
    plan = plan_with(conn, TASK_AND_DEPENDENT)
    complete_and_accept(conn, plan)
    dispatch_task(conn, plan, "T2")
    return Arranged(conn=conn, plan=plan, task="T1", run=lambda: ledger.reclaim(conn, plan, "T1", reason="redo"))


@register("reclaim", COMPLETE, ("task-accepted", "attempts-exhausted"))
def reclaim_accepted_and_exhausted(tmp_path: Path) -> Arranged:
    """Reclaim an accepted task that has already spent every attempt it was allowed."""
    conn = new_ledger(tmp_path)
    plan = plan_with(conn, ONE_TASK)
    burn_attempts(conn, plan, MAX_ATTEMPTS - 1)
    ledger.reclaim(conn, plan, "T1", reason="another attempt")
    complete_and_accept(conn, plan)
    return Arranged(conn=conn, plan=plan, task="T1", run=lambda: ledger.reclaim(conn, plan, "T1", reason="redo"))


@register("reclaim", IN_PROGRESS, ("leased", "dependents-started"))
def reclaim_leased_with_started_dependent(tmp_path: Path) -> Arranged:
    """Reclaim a leased task whose dependent has already spent an attempt."""
    conn = new_ledger(tmp_path)
    plan = plan_with(conn, TASK_AND_DEPENDENT)
    complete_and_accept(conn, plan)
    dispatch_task(conn, plan, "T2")
    ledger.reclaim(conn, plan, "T1", reason="redo", force=True)
    dispatch_task(conn, plan)
    return Arranged(conn=conn, plan=plan, task="T1", run=lambda: ledger.reclaim(conn, plan, "T1", reason="redo"))


@register("reclaim", IN_PROGRESS, ("leased", "attempts-exhausted"))
def reclaim_leased_and_exhausted(tmp_path: Path) -> Arranged:
    """Reclaim a leased task whose open attempt is the last one it was allowed."""
    conn = new_ledger(tmp_path)
    plan = plan_with(conn, ONE_TASK)
    burn_attempts(conn, plan, MAX_ATTEMPTS - 1)
    ledger.reclaim(conn, plan, "T1", reason="another attempt")
    dispatch_task(conn, plan)
    return Arranged(conn=conn, plan=plan, task="T1", run=lambda: ledger.reclaim(conn, plan, "T1", reason="redo"))


@register("reclaim", DEFERRED, ("dependents-started", "attempts-exhausted"))
def reclaim_exhausted_with_started_dependent(tmp_path: Path) -> Arranged:
    """Reclaim a deferred, exhausted task whose dependent has already spent an attempt."""
    conn = new_ledger(tmp_path)
    plan = plan_with(conn, TASK_AND_DEPENDENT)
    burn_attempts(conn, plan, MAX_ATTEMPTS)
    ledger.state(conn, plan, "T1", new_status=DEFERRED, reason="set aside")
    dispatch_task(conn, plan, "T2")
    return Arranged(conn=conn, plan=plan, task="T1", run=lambda: ledger.reclaim(conn, plan, "T1", reason="redo"))


# ---------------------------------------------------------------------------
# state
# ---------------------------------------------------------------------------


@register("state", COMPLETE, ("status-invalid", "task-accepted"))
def state_invalid_and_accepted(tmp_path: Path) -> Arranged:
    """Move an accepted task to a status no ``Status`` names."""
    conn = new_ledger(tmp_path)
    plan = plan_with(conn, ONE_TASK)
    complete_and_accept(conn, plan)
    return Arranged(
        conn=conn,
        plan=plan,
        task="T1",
        run=lambda: ledger.state(conn, plan, "T1", new_status=INVALID_STATUS, reason="set aside"),
    )


@register("state", IN_PROGRESS, ("status-invalid", "leased"))
def state_invalid_and_leased(tmp_path: Path) -> Arranged:
    """Move a leased task to a status no ``Status`` names."""
    conn = new_ledger(tmp_path)
    plan = plan_with(conn, ONE_TASK)
    dispatch_task(conn, plan)
    return Arranged(
        conn=conn,
        plan=plan,
        task="T1",
        run=lambda: ledger.state(conn, plan, "T1", new_status=INVALID_STATUS, reason="set aside"),
    )


@register("state", IN_PROGRESS, ("task-accepted", "leased"))
def state_accepted_and_leased(tmp_path: Path) -> Arranged:
    """Move an imported accepted task that has since been dispatched."""
    conn = new_ledger(tmp_path)
    plan = imported(conn, status=NOT_STARTED, accepted=1)
    dispatch_task(conn, plan)
    return Arranged(
        conn=conn,
        plan=plan,
        task="T1",
        run=lambda: ledger.state(conn, plan, "T1", new_status=BLOCKED, reason="set aside"),
    )


@register("state", COMPLETE, ("task-accepted", "report-missing"))
def state_accepted_and_unreported(tmp_path: Path) -> Arranged:
    """Re-mark an imported accepted task complete when its attempt carries no report."""
    conn = new_ledger(tmp_path)
    plan = imported(conn, status=COMPLETE, accepted=1, attempts=1)
    return Arranged(
        conn=conn,
        plan=plan,
        task="T1",
        run=lambda: ledger.state(conn, plan, "T1", new_status=COMPLETE, reason="re-mark"),
    )


@register("state", IN_PROGRESS, ("leased", "report-missing"))
def state_leased_and_unreported(tmp_path: Path) -> Arranged:
    """Mark a leased task complete when its attempt carries no report."""
    conn = new_ledger(tmp_path)
    plan = plan_with(conn, ONE_TASK)
    dispatch_task(conn, plan)
    return Arranged(
        conn=conn,
        plan=plan,
        task="T1",
        run=lambda: ledger.state(conn, plan, "T1", new_status=COMPLETE, reason="re-mark"),
    )


# ---------------------------------------------------------------------------
# import and from-milestone
# ---------------------------------------------------------------------------


@register("import", spec.ANY, ("exists", "leased"))
def import_existing_and_leased(tmp_path: Path) -> Arranged:
    """Import a plan the ledger already holds, one of whose tasks holds an open attempt."""
    conn = new_ledger(tmp_path)
    source = import_source(status=NOT_STARTED, accepted=0)
    ledger.import_plan(conn, source, projection_hash="hash")
    dispatch_task(conn, IMPORTED_PLAN)
    return Arranged(conn=conn, plan=IMPORTED_PLAN, run=lambda: ledger.import_plan(conn, source, projection_hash="hash"))


@register("from-milestone", spec.ANY, ("exists", "leased"))
def milestone_existing_and_leased(tmp_path: Path) -> Arranged:
    """Rebuild a milestone plan the ledger already holds, one of whose tasks holds an open attempt."""
    conn = new_ledger(tmp_path)
    source = milestone_plan()
    ledger.from_milestone(conn, source)
    dispatch_task(conn, source.plan_id)
    return Arranged(conn=conn, plan=source.plan_id, run=lambda: ledger.from_milestone(conn, source))


# ---------------------------------------------------------------------------
# The tests
# ---------------------------------------------------------------------------

CASE_IDS = [f"{case.command}/{case.from_status}:{'+'.join(case.checks)}" for case in CASES]


@pytest.mark.parametrize("case", CASES, ids=CASE_IDS)
def test_the_first_failing_check_is_the_one_the_spec_puts_first(case: OrderCase, tmp_path: Path) -> None:
    """A state failing two checks stops on whichever ``ledger_spec`` evaluates first.

    Args:
        case: The transition entry, the pair of checks, and the scenario that arranges them.
        tmp_path: The test's temporary directory.
    """
    arranged = case.build(tmp_path)
    if arranged.task:
        assert task_status(arranged.conn, arranged.plan, arranged.task) == case.from_status, (
            f"the scenario for {case.command}/{case.from_status} left the task in another status"
        )
    earlier, later = spec_order(case.command, case.from_status, case.checks)

    observed = outcome_of(arranged.run)

    assert observed == earlier, (
        f"{case.command} from {case.from_status} reported {observed}, but ledger_spec.TRANSITIONS "
        f"evaluates {earlier} before {later}"
    )


def test_every_constructible_ordering_has_a_case() -> None:
    """Every pair of checks the specification orders is either covered here or ruled out above."""
    constructible = SPEC_PAIRS - set(UNCONSTRUCTIBLE)
    covered = {unordered(case.command, case.checks) for case in CASES}

    assert covered == constructible, (
        f"uncovered orderings: {sorted(constructible - covered)}; "
        f"cases naming an ordering the specification does not state: {sorted(covered - constructible)}"
    )


def test_every_unconstructible_pair_is_one_the_spec_states() -> None:
    """Nothing is excused that the specification does not order, so a stale exclusion is caught."""
    assert set(UNCONSTRUCTIBLE) <= SPEC_PAIRS, (
        f"not orderings of any transition: {sorted(set(UNCONSTRUCTIBLE) - SPEC_PAIRS)}"
    )


def test_the_spec_orders_every_pair_the_same_way_in_every_status() -> None:
    """No command orders one pair of checks one way in one status and the other way in another.

    The cases are keyed by command rather than by transition entry, which is only sound while a
    command's entries agree on the order of every pair they share.
    """
    for command, pairs in spec_pairs().items():
        contradictions = sorted(pair for pair in pairs if (pair[1], pair[0]) in pairs)
        assert not contradictions, f"{command} orders these both ways across its statuses: {contradictions}"


def test_the_invalid_status_the_state_cases_use_names_no_status() -> None:
    """``INVALID_STATUS`` must be outside ``Status`` for ``status-invalid`` to fail."""
    assert INVALID_STATUS not in {status.value for status in spec.Status}
