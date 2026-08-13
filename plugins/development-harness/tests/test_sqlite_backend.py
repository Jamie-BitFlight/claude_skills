from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from backlog_core.backends.sqlite_backend import SQLiteBackend
from backlog_core.models import BacklogItem, ContentKind, ContentRef, ContentWrite


def test_shared_connection_blocks_cross_operation_while_transaction_is_open(monkeypatch: pytest.MonkeyPatch) -> None:
    backend = SQLiteBackend(":memory:")
    transaction_started = threading.Event()
    release_transaction = threading.Event()
    work_item_started = threading.Event()
    work_item_completed = threading.Event()

    original_content_key = backend._content_key

    def pause_content_transaction(reference: ContentRef) -> tuple[str, str, str, str]:
        transaction_started.set()
        release_transaction.wait(timeout=1)
        return original_content_key(reference)

    def put_work_item() -> None:
        work_item_started.set()
        backend.put_work_item(BacklogItem(title="concurrent work item"))
        work_item_completed.set()

    monkeypatch.setattr(backend, "_content_key", pause_content_transaction)
    with ThreadPoolExecutor(max_workers=2) as executor:
        content_write = executor.submit(
            backend.put_content, ContentWrite(reference=ContentRef(kind=ContentKind.PLAN, name="P1"), content="content")
        )
        try:
            assert transaction_started.wait(timeout=1)
            work_item_write = executor.submit(put_work_item)
            assert work_item_started.wait(timeout=1)
            assert not work_item_completed.wait(timeout=0.1)
        finally:
            release_transaction.set()

        content_write.result()
        work_item_write.result()

    assert [item.title for item in backend.list_work_items()] == ["concurrent work item"]
