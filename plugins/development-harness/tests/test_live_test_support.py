"""Hand-authored responses test the live scenario's observation machinery."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.live_test_support import Journal, LiveCalls, collect_items, issue_number, require_success


def page(offset: int, title: str, has_more: bool) -> dict[str, object]:
    return {
        "items": [{"title": title}],
        "count": 1,
        "pagination": {"offset": offset, "limit": 1, "total": 2, "has_more": has_more},
    }


@pytest.mark.parametrize("titles", [("unrelated", "expected"), ("expected", "unrelated")])
async def test_membership_is_independent_of_page_order(titles) -> None:
    calls = []

    async def call(operation, parameters):
        calls.append((operation, parameters))
        offset = parameters["offset"]
        return page(offset, titles[offset], offset == 0)

    items = await collect_items(call, {"limit": 1, "include_closed": True})
    assert {item["title"] for item in items} == {"unrelated", "expected"}
    assert calls == [
        ("backlog_list", {"limit": 1, "include_closed": True, "offset": 0}),
        ("backlog_list", {"limit": 1, "include_closed": True, "offset": 1}),
    ]


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"error": "contents permission denied"}, "contents permission denied"),
        ({"items": None, "count": None, "warnings": ["cache not confirmed"]}, "cache not confirmed"),
        ({"items": [], "count": 0}, "invalid pagination"),
        ({"items": [], "count": 2, "pagination": {}}, "count disagrees"),
        ({"items": [{}], "count": 1, "pagination": {"offset": 0, "limit": 0, "has_more": True}}, "cannot advance"),
        ({"items": [], "count": 0, "pagination": {"offset": 0, "limit": 1, "has_more": True}}, "cannot advance"),
    ],
)
async def test_invalid_or_withheld_results_fail_with_the_actual_reason(payload, message) -> None:
    async def call(operation, parameters):
        return payload

    with pytest.raises(AssertionError, match=message):
        await collect_items(call, {"limit": 1})


async def test_a_repeated_page_cannot_be_mistaken_for_progress() -> None:
    async def call(operation, parameters):
        return page(0, "same", True)

    with pytest.raises(AssertionError, match="invalid pagination at offset 1"):
        await collect_items(call, {"limit": 1})


@pytest.mark.parametrize("payload", [{"errors": ["write rejected"]}, {"error": "write rejected"}])
def test_payload_errors_are_not_hidden_by_later_field_assertions(payload) -> None:
    with pytest.raises(AssertionError, match="backlog_groom.*write rejected"):
        require_success("backlog_groom", payload)


def test_failure_is_written_before_control_returns_to_client_teardown(tmp_path) -> None:
    path = tmp_path / "events.jsonl"
    journal = Journal(path)
    with pytest.raises(AssertionError, match="remote content missing"):
        with journal.phase("fresh-cache readback"):
            raise AssertionError("remote content missing")
    events = [json.loads(line) for line in path.read_text().splitlines()]
    assert [event["event"] for event in events] == ["started", "failed"]
    assert events[-1]["phase"] == "fresh-cache readback"
    assert "remote content missing" in events[-1]["error"]


@pytest.mark.parametrize("reference", ["", "#", "#0", "42", None])
def test_creation_must_confirm_a_positive_native_issue(reference) -> None:
    with pytest.raises(AssertionError, match="backlog_add"):
        issue_number({"item_ref": reference})


def test_creation_reference_is_not_a_local_only_success() -> None:
    assert issue_number({"item_ref": "#42"}) == 42


@pytest.mark.parametrize("wire", ['{"error":"permission denied"}', '{"truncated":'])
async def test_wire_response_survives_decode_or_operation_failure(tmp_path, wire) -> None:
    client = MagicMock()
    client.call_tool = AsyncMock(return_value=SimpleNamespace(content=[SimpleNamespace(text=wire)]))
    path = tmp_path / "wire.jsonl"
    calls = LiveCalls(client, Journal(path))
    with pytest.raises((AssertionError, json.JSONDecodeError)):
        await calls.call("backlog_view", {"selector": "#7"})
    events = [json.loads(line) for line in path.read_text().splitlines()]
    assert next(event["text"] for event in events if event["event"] == "response") == wire
    assert events[-1]["event"] == "failed"
