"""Observable MCP calls and pagination for the live scenarios, not a backend double."""

from __future__ import annotations

import json
import time
import traceback
from collections.abc import Awaitable, Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp.client import Client

ToolCall = Callable[[str, dict[str, object]], Awaitable[dict[str, object]]]


def require_success(operation: str, payload: object) -> dict[str, object]:
    """Reject protocol/operation errors before a later assertion obscures their cause."""
    if not isinstance(payload, dict) or not all(isinstance(key, str) for key in payload):
        raise AssertionError(f"{operation}: expected a JSON object, received {payload!r}")
    result = {str(key): value for key, value in payload.items()}
    if result.get("error") or result.get("errors"):
        raise AssertionError(f"{operation}: unsuccessful response: {json.dumps(result, ensure_ascii=False)}")
    return result


class Journal:
    """Flush observations before client teardown or an outer process deadline."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path

    def record(self, event: str, **details: object) -> None:
        line = json.dumps({"at": datetime.now(UTC).isoformat(), "event": event, **details}, ensure_ascii=False)
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(line + "\n")
            stream.flush()
        print(line, flush=True)

    @contextmanager
    def phase(self, name: str) -> Iterator[None]:
        start = time.monotonic()
        self.record("started", phase=name)
        try:
            yield
        except BaseException as exc:
            # Diagnostics must be durable before unwinding the in-memory transport.
            self.record("failed", phase=name, elapsed=time.monotonic() - start, error=repr(exc))
            traceback.print_exc()
            raise
        else:
            self.record("passed", phase=name, elapsed=time.monotonic() - start)


class LiveCalls:
    """Use one real client per scenario and retain every complete response."""

    def __init__(self, client: Client, journal: Journal) -> None:
        self.client = client
        self.journal = journal

    async def call(self, operation: str, parameters: dict[str, object]) -> dict[str, object]:
        with self.journal.phase(operation):
            self.journal.record("request", operation=operation, parameters=parameters)
            response = await self.client.call_tool(operation, parameters)
            if not response.content:
                raise AssertionError(f"{operation}: MCP returned no content")
            text = getattr(response.content[0], "text", None)
            assert isinstance(text, str), f"{operation}: expected JSON text content, received {response.content!r}"
            self.journal.record("response", operation=operation, text=text)
            payload = json.loads(text)
            return require_success(operation, payload)


async def collect_items(call: ToolCall, parameters: dict[str, object]) -> list[dict[str, object]]:
    """Follow collection pagination without assuming membership on the first page."""
    offset = 0
    collected: list[dict[str, object]] = []
    while True:
        result = require_success("backlog_list", await call("backlog_list", {**parameters, "offset": offset}))
        items = result.get("items")
        assert isinstance(items, list), f"backlog_list withheld its collection: {json.dumps(result, ensure_ascii=False)}"
        page = [require_success("backlog_list item", item) for item in items]
        if result.get("count") != len(page):
            raise AssertionError(f"backlog_list count disagrees with its page: {result!r}")
        pagination = result.get("pagination")
        if not isinstance(pagination, dict) or pagination.get("offset") != offset:
            raise AssertionError(f"backlog_list returned invalid pagination at offset {offset}: {result!r}")
        has_more = pagination.get("has_more")
        assert isinstance(has_more, bool), f"backlog_list omitted an explicit continuation verdict: {result!r}"
        collected.extend(page)
        if not has_more:
            return collected
        limit = pagination.get("limit")
        if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0 or not page:
            raise AssertionError(f"backlog_list pagination cannot advance: {result!r}")
        offset += limit


def issue_number(result: dict[str, object]) -> int:
    """Extract a created issue reference while preserving the original error context."""
    reference = result.get("item_ref")
    if not isinstance(reference, str) or not reference.startswith("#") or not reference[1:].isdigit():
        raise AssertionError(f"backlog_add did not confirm a native issue: {result!r}")
    number = int(reference[1:])
    if number <= 0:
        raise AssertionError(f"backlog_add returned an invalid issue number: {result!r}")
    return number
