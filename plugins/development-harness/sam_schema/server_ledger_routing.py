"""The one place a plan-addressed MCP action decides which store answers it.

``sam_plan`` and ``sam_task`` read and write the work ledger once ``plan import`` has put a plan on
it, and the content store otherwise -- the same routing rule the CLI's ``store_for`` implements
(``sam_schema/sam_plan.py``). Before this module existed, the mechanical sequence behind that rule
-- canonicalise the plan id, ask whether the ledger holds it, open a connection, translate a ledger
error into ``ToolError``, close the connection -- was spelled out at each of the seven call sites
that needed it. :func:`route` is that sequence, once.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from dh_core import ledger
from dh_core.ledger import LedgerConnection
from fastmcp.exceptions import ToolError

from sam_schema.core.addressing import canonical_plan_id

__all__ = ["on_ledger", "route"]

_T = TypeVar("_T")


def on_ledger(fn: Callable[[LedgerConnection], _T]) -> _T:
    """Open the ledger and run *fn* against it, translating ledger errors into ``ToolError``.

    Mirrors the CLI's ``sam_plan._ledger()`` context manager without importing ``contextlib``,
    which the frontend files' import allowlist (``tests/test_frontend_logic_free.py``) does not
    carry. The open call sits inside the same guarded block as *fn* -- a ``Refusal`` raised while
    opening (e.g. ``network-filesystem``) is exactly as translatable as one *fn* raises, so both go
    through one ``except``.

    Args:
        fn: A callable that performs one or more ledger reads or writes on the open connection.

    Returns:
        Whatever *fn* returns.

    Raises:
        ToolError: When the ledger refuses to open or refuses the operation
            (:class:`dh_core.ledger.Refusal`), or the operation names a plan, task, or field the
            ledger does not recognise (``LookupError``/``ValueError``).
    """
    try:
        conn = ledger.open_ledger()
        try:
            return fn(conn)
        finally:
            conn.close()
    except ledger.Refusal as exc:
        raise ToolError(exc.reason) from exc
    except (LookupError, ValueError) as exc:
        raise ToolError(str(exc)) from exc


def _ledger_holds(canonical: str) -> bool:
    """Answer whether the ledger holds *canonical*, translating a ``Refusal`` into ``ToolError``.

    ``ledger.holds`` opens its own connection and lets a ``Refusal`` (e.g. ``network-filesystem``)
    propagate rather than translate it -- translation is a frontend concern. :func:`route` goes
    through here instead of calling ``ledger.holds`` directly, so that refusal reaches the caller as
    ``ToolError`` the same way :func:`on_ledger` translates one raised inside its guarded block.

    Args:
        canonical: The canonical plan id.

    Returns:
        Whether the ledger holds a plan row with that id.

    Raises:
        ToolError: When the ledger refuses to open.
    """
    try:
        return ledger.holds(canonical)
    except ledger.Refusal as exc:
        raise ToolError(exc.reason) from exc


def route(plan: str, *, on_ledger_call: Callable[[str, LedgerConnection], _T], on_content: Callable[[], _T]) -> _T:
    """Canonicalise *plan* and run whichever of *on_ledger_call* or *on_content* the store answers.

    Every plan-addressed ``sam_plan``/``sam_task`` action reaches this: canonicalise the plan id,
    ask :func:`_ledger_holds`, and if it holds the plan, open one connection via :func:`on_ledger`
    and run *on_ledger_call* against it; otherwise run *on_content*, which resolves its own content
    backend.

    Args:
        plan: The plan address as the caller passed it (not yet canonicalised).
        on_ledger_call: Run once the ledger is confirmed to hold the plan; receives the canonical
            plan id and the open connection.
        on_content: Run when the ledger does not hold the plan.

    Returns:
        Whatever the chosen callable returns.

    Raises:
        ToolError: When the ledger refuses to open, or *on_ledger_call* raises a ledger error (see
            :func:`on_ledger`).
    """
    canonical = canonical_plan_id(plan)
    if _ledger_holds(canonical):
        return on_ledger(lambda conn: on_ledger_call(canonical, conn))
    return on_content()
