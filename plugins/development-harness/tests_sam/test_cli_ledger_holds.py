"""``sam_plan.ledger_holds`` must answer through the shared ``dh_core.ledger.holds``, not a second implementation.

``dh_core.ledger.store.holds`` exists so a routing check asks with one ``SELECT 1`` rather than
``ledger.list_plans``'s full scan, which computes every plan's derived progress -- work a routing
check never uses (see its own docstring). Before this fix, the CLI's ``ledger_holds`` reimplemented
the same answer with that full scan instead of calling the shared function.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from dh_core import ledger
from sam_schema import sam_plan

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def _create_plan() -> str:
    """Create one ledger plan with a single task and return its id.

    Returns:
        The canonical plan id.
    """
    conn = ledger.open_ledger()
    try:
        return str(ledger.create(conn, slug="holds-delegates", goal="goal", tasks=[{"id": "T1", "title": "one"}]).plan)
    finally:
        conn.close()


def test_ledger_holds_delegates_to_the_shared_dh_core_check(mocker: MockerFixture) -> None:
    """``sam_plan.ledger_holds`` must call ``dh_core.ledger.holds``, not scan ``list_plans`` itself."""
    plan_id = _create_plan()
    holds_spy = mocker.spy(ledger, "holds")
    list_plans_spy = mocker.spy(ledger, "list_plans")

    assert sam_plan.ledger_holds(plan_id) is True

    holds_spy.assert_called_once_with(plan_id)
    list_plans_spy.assert_not_called()


def test_ledger_holds_answers_false_for_a_plan_the_ledger_does_not_hold(mocker: MockerFixture) -> None:
    """A plan id the ledger never saw answers False through the same shared check."""
    _create_plan()
    holds_spy = mocker.spy(ledger, "holds")

    assert sam_plan.ledger_holds("Pmissing") is False

    holds_spy.assert_called_once_with("Pmissing")
