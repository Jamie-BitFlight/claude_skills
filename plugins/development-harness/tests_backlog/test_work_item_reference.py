from __future__ import annotations

import inspect
from unittest.mock import MagicMock

from backlog_core.backend_protocol import reset_config, set_config
from backlog_core.backend_types import BacklogConfig
from backlog_core.backends.beads_backend import BeadsBackend
from backlog_core.backends.memory_backend import InMemoryBackend
from backlog_core.backends.sqlite_backend import SQLiteBackend
from backlog_core.models import BacklogItem
from backlog_core.operations import _filter_closed_items, update_item


def test_reference_survives_model_round_trip() -> None:
    item = BacklogItem(title="Stable", reference="native-1")

    assert BacklogItem.model_validate_json(item.model_dump_json()).reference == "native-1"


def test_memory_assigns_stable_unlinked_reference() -> None:
    backend = InMemoryBackend()
    item = BacklogItem(title="Unlinked")

    backend.put_work_item(item)
    assigned = item.reference
    item.title = "Renamed"
    backend.put_work_item(item)

    assert assigned
    assert backend.get_work_item(assigned).title == "Renamed"
    assert len(backend.list_work_items()) == 1


def test_memory_revalidates_metadata_mutations_before_persisting() -> None:
    backend = InMemoryBackend()
    item = BacklogItem(title="Lifecycle", issue="#7")

    backend.put_work_item(item)
    reference = item.reference
    item.metadata.status = "closed"
    item.metadata.priority = "completed"
    backend.put_work_item(item)

    stored = backend.get_work_item(reference)
    assert stored.reference == reference
    assert stored.status == stored.metadata.status == "closed"
    assert stored.priority == stored.metadata.priority == "completed"
    assert _filter_closed_items([stored], include_closed=False) == []
    assert len(backend.list_work_items()) == 1


def test_sqlite_assigns_stable_unlinked_reference() -> None:
    backend = SQLiteBackend()
    item = BacklogItem(title="Unlinked")

    backend.put_work_item(item)
    assigned = item.reference
    item.title = "Renamed"
    backend.put_work_item(item)

    assert assigned
    assert backend.get_work_item(assigned).title == "Renamed"
    assert len(backend.list_work_items()) == 1


def test_beads_work_items_use_native_issue_commands_not_kv() -> None:
    runner = MagicMock()
    backend = BeadsBackend(runner=runner)
    item = BacklogItem(title="Native", issue="bd-native", reference="bd-native")

    backend.put_work_item(item)

    command = runner.run_text.call_args.args[0]
    assert command[:2] == ["update", "bd-native"]
    assert "--notes" in command
    work_item_source = "\n".join(
        inspect.getsource(method)
        for method in (BeadsBackend.list_work_items, BeadsBackend.get_work_item, BeadsBackend.put_work_item)
    )
    assert '"kv"' not in work_item_source
    assert "dh.work-item" not in work_item_source


def test_update_item_resolves_selector_by_printed_reference() -> None:
    """update_item finds its target when selected by the reference backlog add printed.

    Guards: the reference (e.g. "p1-repro-selector-crash") uses hyphens where the
    title uses spaces, so it is not a title substring. Before the fix, find_item
    fell through to title-substring matching and update_item raised
    ItemNotFoundError even though the item exists (#3449).
    """
    backend = SQLiteBackend()
    backend.put_work_item(BacklogItem(title="repro selector crash", reference="p1-repro-selector-crash"))
    set_config(BacklogConfig(backend=backend))

    try:
        result = update_item(selector="p1-repro-selector-crash", status="groomed")
    finally:
        reset_config()

    assert result["title"] == "repro selector crash"
