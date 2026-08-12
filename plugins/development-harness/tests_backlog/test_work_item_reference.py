from __future__ import annotations

import inspect
from unittest.mock import MagicMock

from backlog_core.backends.beads_backend import BeadsBackend
from backlog_core.backends.memory_backend import InMemoryBackend
from backlog_core.backends.sqlite_backend import SQLiteBackend
from backlog_core.models import BacklogItem


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
