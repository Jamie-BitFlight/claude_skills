from __future__ import annotations

from pathlib import Path

from backlog_core.jsonl_utils import find_first_event, parse_jsonl_events


def test_parse_jsonl_events_skips_malformed_and_blank_lines(tmp_path: Path) -> None:
    # Given: a file with a malformed line and a blank line between two good ones
    jsonl_path = tmp_path / "transcript.jsonl"
    jsonl_path.write_text('{"type": "a", "n": 1}\nnot json\n\n{"type": "b", "n": 2}\n', encoding="utf-8")

    # When: parsing without a type filter
    events = parse_jsonl_events(jsonl_path)

    # Then: only the two well-formed events survive, in file order
    assert events == [{"type": "a", "n": 1}, {"type": "b", "n": 2}]


def test_parse_jsonl_events_filters_by_type(tmp_path: Path) -> None:
    jsonl_path = tmp_path / "transcript.jsonl"
    jsonl_path.write_text('{"type": "a"}\n{"type": "b"}\n{"type": "a"}\n', encoding="utf-8")

    events = parse_jsonl_events(jsonl_path, event_type="a")

    assert events == [{"type": "a"}, {"type": "a"}]


def test_parse_jsonl_events_returns_empty_for_missing_file(tmp_path: Path) -> None:
    assert parse_jsonl_events(tmp_path / "missing.jsonl") == []


def test_find_first_event_matches_type_and_subtype(tmp_path: Path) -> None:
    jsonl_path = tmp_path / "transcript.jsonl"
    jsonl_path.write_text('{"type": "a", "subtype": "x"}\n{"type": "a", "subtype": "y"}\n', encoding="utf-8")

    assert find_first_event(jsonl_path, "a", subtype="y") == {"type": "a", "subtype": "y"}
    assert find_first_event(jsonl_path, "a") == {"type": "a", "subtype": "x"}
    assert find_first_event(jsonl_path, "missing") is None


def test_find_first_event_returns_none_for_missing_file(tmp_path: Path) -> None:
    assert find_first_event(tmp_path / "missing.jsonl", "a") is None
