"""Backend-level regression tests for BacklogItem.reference self-healing (backlog item #2909).

``memory_backend.py`` and ``sqlite_backend.py`` previously each hand-rolled their own
``item.reference = item.reference or item.issue or uuid.uuid4().hex`` fallback inside
``put_work_item``. That logic now lives once, on ``BacklogItem`` itself (see
``models.py::_derive_stable_reference`` and the ``_sync_metadata`` validator) — every
``BacklogItem`` construction self-heals an unset ``reference`` deterministically before it
ever reaches a backend. These tests guard that the backends no longer need, and no longer
have, their own fallback: two items sharing a title resolve to the same key (impossible
under the old ``uuid4()`` fallback), and put/get round-trips through each backend preserve
the model-derived reference unchanged.
"""

from __future__ import annotations

import pytest
from backlog_core.backend_types import WorkItemBackend
from backlog_core.backends.memory_backend import InMemoryBackend
from backlog_core.backends.sqlite_backend import SQLiteBackend
from backlog_core.models import BacklogItem, ReferenceCollisionError


def _backends() -> list[WorkItemBackend]:
    """Return one fresh instance of each local backend under test.

    Returns:
        A new ``InMemoryBackend`` and a new in-memory ``SQLiteBackend``.
    """
    return [InMemoryBackend(), SQLiteBackend(":memory:")]


def test_memory_backend_put_work_item_reference_is_model_derived() -> None:
    """InMemoryBackend.put_work_item keys by the model-healed reference, not a fresh uuid."""
    backend = InMemoryBackend()
    item = BacklogItem(title="Untracked item")
    backend.put_work_item(item)
    assert backend.get_work_item(item.reference).title == "Untracked item"


def test_sqlite_backend_put_work_item_reference_is_model_derived() -> None:
    """SQLiteBackend.put_work_item keys by the model-healed reference, not a fresh uuid."""
    backend = SQLiteBackend(":memory:")
    item = BacklogItem(title="Untracked item")
    backend.put_work_item(item)
    assert backend.get_work_item(item.reference).title == "Untracked item"


def test_memory_and_sqlite_backends_derive_the_same_reference_for_the_same_title() -> None:
    """Both backends resolve an unset-reference item with the same title to the same key.

    Under the old per-backend ``uuid4()`` fallback this was never true — every call
    minted an unrelated random key. Parity here proves both backends now delegate to
    the single model-level derivation instead of hand-rolling their own.
    """
    memory_item = BacklogItem(title="Shared Title Item")
    sqlite_item = BacklogItem(title="Shared Title Item")
    assert memory_item.reference == sqlite_item.reference


def test_backend_put_work_item_reference_is_deterministic_across_reloads() -> None:
    """Reconstructing the same conceptual item twice resolves to the same backend key.

    This is the property the deterministic (SHA-256) fallback exists to guarantee: a
    stale on-disk or in-database record with no explicit reference must resolve to the
    same key every time it is reloaded, or reference-gated operations (groom, resolve)
    permanently orphan it. See backlog item #2900/#2902 for the incident this prevents.
    """
    for backend in _backends():
        first = BacklogItem(title="Reloaded item")
        backend.put_work_item(first)
        first_reference = first.reference

        second = BacklogItem(title="Reloaded item")
        backend.put_work_item(second)

        assert second.reference == first_reference
        assert len(backend.list_work_items()) == 1


def test_backend_put_work_item_rejects_distinct_items_that_share_a_title() -> None:
    """Two DIFFERENT never-issued items sharing a title must not silently collide.

    Regression test for the data-loss window the deterministic title-hash fallback
    introduced: unlike ``test_backend_put_work_item_reference_is_deterministic_across_reloads``
    above (same title, identical — i.e. reloaded — content, which must still collapse to one
    record), these two items share a title but carry different ``description`` values, so they
    are genuinely distinct backlog items. Before the ``ReferenceCollisionError`` check in
    ``InMemoryBackend``/``SQLiteBackend.put_work_item``, the second ``put_work_item`` call
    silently discarded the first record (``list_work_items()`` returned 1 item, and
    ``get_work_item(item_a.reference).description`` read back as ``"Item B"``).
    """
    for backend in _backends():
        item_a = BacklogItem(title="Duplicate Title", description="Item A")
        item_b = BacklogItem(title="Duplicate Title", description="Item B")
        assert item_a.reference == item_b.reference

        backend.put_work_item(item_a)
        with pytest.raises(ReferenceCollisionError, match="Duplicate Title"):
            backend.put_work_item(item_b)

        assert len(backend.list_work_items()) == 1
        assert backend.get_work_item(item_a.reference).description == "Item A"
