"""A ``Refusal`` raised while opening the ledger must reach an MCP caller as ``ToolError``.

``dh_core.ledger.store.open_ledger`` raises ``Refusal("network-filesystem")`` when the ledger's
mount cannot share WAL's index (``check_local_filesystem``) -- a real, documented refusal, not a
hypothetical. Before the fix this test guards, ``sam_schema.server._on_ledger`` opened the
connection outside its own guarded block, and every routing check called ``dh_core.ledger.holds``
directly, so a ``Refusal`` raised while opening escaped both untranslated instead of surfacing as
the ``ToolError`` every other ledger refusal surfaces as. Both now live in
``sam_schema.server_ledger_routing``.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from dh_core import ledger
from dh_core.ledger import store
from fastmcp.exceptions import ToolError
from sam_schema import server_ledger_routing


def _raise_network_filesystem(_path: Path) -> None:
    """Stand in for ``check_local_filesystem`` on every call, refusing unconditionally.

    Raises:
        store.Refusal: Always, with ``network-filesystem``.
    """
    raise store.Refusal("network-filesystem")


def _create_plan() -> str:
    """Create one ledger plan with a single task and return its id.

    Returns:
        The canonical plan id.
    """
    conn = ledger.open_ledger()
    try:
        return str(ledger.create(conn, slug="open-refusal", goal="goal", tasks=[{"id": "T1", "title": "one"}]).plan)
    finally:
        conn.close()


def test_ledger_holds_translates_a_refusal_raised_while_opening(monkeypatch: pytest.MonkeyPatch) -> None:
    """``route``'s routing check must translate a ``Refusal`` the ledger raises while opening into ``ToolError``."""
    plan_id = _create_plan()
    monkeypatch.setattr(store, "check_local_filesystem", _raise_network_filesystem)

    with pytest.raises(ToolError, match="network-filesystem"):
        server_ledger_routing.route(plan_id, on_ledger_call=lambda _canonical, _conn: None, on_content=lambda: None)


def test_on_ledger_translates_a_refusal_raised_while_opening(monkeypatch: pytest.MonkeyPatch) -> None:
    """``on_ledger`` must translate a ``Refusal`` ``open_ledger`` itself raises, not just one *fn* raises."""
    monkeypatch.setattr(store, "check_local_filesystem", _raise_network_filesystem)

    with pytest.raises(ToolError, match="network-filesystem"):
        server_ledger_routing.on_ledger(lambda conn: None)
