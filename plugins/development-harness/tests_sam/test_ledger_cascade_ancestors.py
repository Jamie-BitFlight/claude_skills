"""A dependent two failures block, in both directions of the cascade.

``ledger_spec``'s ``CASCADE`` and ``REVERSAL`` effects are written per failing task: one task
enters failed, and every transitive dependent it blocks takes a ``task.state`` row naming it.
Nothing in ``COLUMNS`` folds that reason into ``tasks``, so how many failures hold one dependent
skipped exists only in the event log. Every other ledger test gives a task one dependency, which is
the shape in which the question never arises -- ``dependencies`` in ``tests_sam`` names a single id
in each case a ledger test builds -- so these cover the shape where it does.

The pair of properties under test:

the cascade records one row per blocking failure
    A second ancestor's failure reaches a dependent the first already holds skipped. It changes no
    status, but it must record that it also blocks the dependent, or the reversal has nothing to
    read.

the reversal releases one hold at a time
    Reclaiming one ancestor returns a dependent to not-started only when no other failure still
    holds it, and the two ancestors may be reclaimed in either order for the same end state.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from dh_core import ledger_spec as spec
from dh_core.ledger import derive, store, transitions

if TYPE_CHECKING:  # pragma: no cover - typing only
    import sqlite3
    from pathlib import Path

NOT_STARTED = spec.Status.NOT_STARTED.value
SKIPPED = spec.Status.SKIPPED.value
FAILED = spec.Status.FAILED.value


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    """Open a ledger in a temporary directory."""
    return store.open_ledger(tmp_path / store.DATABASE_NAME)


def two_parents(conn: sqlite3.Connection) -> str:
    """Create a plan whose third task depends on the two independent tasks before it.

    Args:
        conn: An open ledger connection.

    Returns:
        The plan id.
    """
    plan = "P1"
    transitions.create(
        conn,
        plan_id=plan,
        slug="two-parent",
        goal="one dependent, two ancestors",
        tasks=[
            {"id": "T1", "title": "first ancestor"},
            {"id": "T2", "title": "second ancestor"},
            {"id": "T3", "title": "shared dependent", "dependencies": ["T1", "T2"]},
        ],
    )
    transitions.finalize(conn, plan)
    return plan


def status_of(conn: sqlite3.Connection, plan: str, task: str) -> str:
    """Return one task's stored status."""
    return str(store.fetch_task(conn, plan, task)["status"])


def state_reasons(conn: sqlite3.Connection, plan: str, task: str) -> list[str]:
    """Return every ``task.state`` reason recorded against one task, oldest first."""
    return [
        str(json.loads(row["payload"])["reason"])
        for row in store.rows_of(
            conn.execute(
                "SELECT payload FROM events WHERE plan = :plan AND task = :task AND kind = 'task.state' ORDER BY seq",
                {"plan": plan, "task": task},
            )
        )
    ]


def fail(conn: sqlite3.Connection, plan: str, task: str) -> transitions.TransitionResult:
    """Move one task to failed without a runner, so its cascade runs."""
    return transitions.state(conn, plan, task, new_status=FAILED, reason=f"{task}-abandoned")


def reclaim(conn: sqlite3.Connection, plan: str, task: str) -> transitions.TransitionResult:
    """Return one failed task to not-started, so its reversal runs."""
    return transitions.reclaim(conn, plan, task, reason=f"{task}-retried")


def test_second_failure_records_itself_against_an_already_skipped_dependent(conn: sqlite3.Connection) -> None:
    """Both ancestors' failures name T3, so the log says two failures hold it rather than one."""
    plan = two_parents(conn)

    first = fail(conn, plan, "T1")
    assert first.cascaded == ["T3"]
    assert status_of(conn, plan, "T3") == SKIPPED

    second = fail(conn, plan, "T2")
    assert second.cascaded == ["T3"], "the second failure recorded nothing against the dependent it also blocks"
    assert status_of(conn, plan, "T3") == SKIPPED
    assert state_reasons(conn, plan, "T3") == [transitions.cascade_code("T1"), transitions.cascade_code("T2")]
    assert transitions.holding_cascades(conn, plan, "T3") == ["T1", "T2"]


def test_reclaiming_one_ancestor_leaves_the_dependent_held_by_the_other(conn: sqlite3.Connection) -> None:
    """T3 stays skipped while T2 is still failed, and its row records that T1 no longer blocks it."""
    plan = two_parents(conn)
    fail(conn, plan, "T1")
    fail(conn, plan, "T2")

    released = reclaim(conn, plan, "T1")
    assert released.reversed_tasks == ["T3"]
    assert status_of(conn, plan, "T3") == SKIPPED, "the dependent came back while a failed ancestor still blocked it"
    assert state_reasons(conn, plan, "T3")[-1] == transitions.reversal_code("T1")
    assert transitions.holding_cascades(conn, plan, "T3") == ["T2"]
    assert not derive.ready(conn, plan, "T3")


def test_reclaiming_both_ancestors_returns_the_dependent(conn: sqlite3.Connection) -> None:
    """The last hold released is the one that moves T3 back to not-started."""
    plan = two_parents(conn)
    fail(conn, plan, "T1")
    fail(conn, plan, "T2")
    reclaim(conn, plan, "T1")

    last = reclaim(conn, plan, "T2")
    assert last.reversed_tasks == ["T3"]
    assert status_of(conn, plan, "T3") == NOT_STARTED
    assert state_reasons(conn, plan, "T3")[-1] == transitions.reversal_code("T2")
    assert transitions.holding_cascades(conn, plan, "T3") == []
    assert [status_of(conn, plan, task) for task in ("T1", "T2", "T3")] == [NOT_STARTED] * 3


@pytest.mark.parametrize("order", [("T1", "T2"), ("T2", "T1")])
def test_the_reclaim_order_does_not_change_the_end_state(conn: sqlite3.Connection, order: tuple[str, str]) -> None:
    """Two ancestors reclaimed in either order leave the same plan."""
    plan = two_parents(conn)
    fail(conn, plan, "T1")
    fail(conn, plan, "T2")

    first, second = order
    assert status_of(conn, plan, "T3") == SKIPPED
    reclaim(conn, plan, first)
    assert status_of(conn, plan, "T3") == SKIPPED, f"reclaiming {first} freed a dependent {second} still blocks"
    reclaim(conn, plan, second)
    assert status_of(conn, plan, "T3") == NOT_STARTED
    assert transitions.holding_cascades(conn, plan, "T3") == []


def test_one_ancestor_still_reverses_on_its_own(conn: sqlite3.Connection) -> None:
    """The single-ancestor path is unchanged: one failure holds, one reclaim releases."""
    plan = two_parents(conn)

    fail(conn, plan, "T1")
    assert transitions.holding_cascades(conn, plan, "T3") == ["T1"]
    assert reclaim(conn, plan, "T1").reversed_tasks == ["T3"]
    assert status_of(conn, plan, "T3") == NOT_STARTED


def test_a_failure_does_not_claim_a_dependent_a_person_skipped(conn: sqlite3.Connection) -> None:
    """A skip with a reason of its own is not a cascade's, so no reclaim may undo it."""
    plan = two_parents(conn)
    transitions.state(conn, plan, "T3", new_status=SKIPPED, reason="out-of-scope")

    assert fail(conn, plan, "T1").cascaded == []
    assert transitions.holding_cascades(conn, plan, "T3") == []
    assert reclaim(conn, plan, "T1").reversed_tasks == []
    assert status_of(conn, plan, "T3") == SKIPPED


def test_a_dependent_the_second_failure_finds_open_is_skipped_by_it(conn: sqlite3.Connection) -> None:
    """A hold released and then re-taken by another failure holds on its own."""
    plan = two_parents(conn)
    fail(conn, plan, "T1")
    reclaim(conn, plan, "T1")
    assert status_of(conn, plan, "T3") == NOT_STARTED

    assert fail(conn, plan, "T2").cascaded == ["T3"]
    assert transitions.holding_cascades(conn, plan, "T3") == ["T2"]
    assert status_of(conn, plan, "T3") == SKIPPED


def test_the_two_parent_log_folds_back_to_the_same_tables(conn: sqlite3.Connection) -> None:
    """A hold recorded without a status change replays into the row the ledger already holds.

    ``ledger_spec.COLUMNS`` claims every materialised table is a fold over ``events``. The rows
    this shape appends -- one that repeats a skipped status, one that reverses a hold and leaves it
    -- carry the status the task keeps rather than one it moves to, so the claim is only true if
    the fold reads the payload rather than inferring from the command.
    """
    plan = two_parents(conn)
    fail(conn, plan, "T1")
    fail(conn, plan, "T2")
    reclaim(conn, plan, "T1")

    before = {task: status_of(conn, plan, task) for task in ("T1", "T2", "T3")}
    assert before == {"T1": NOT_STARTED, "T2": FAILED, "T3": SKIPPED}
    store.rebuild(conn)
    assert {task: status_of(conn, plan, task) for task in ("T1", "T2", "T3")} == before
