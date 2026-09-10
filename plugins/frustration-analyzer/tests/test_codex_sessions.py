from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

import pytest
from _server import (
    ToolError,
    extract_user_messages,
    generate_social_post,
    get_context_window,
    get_scenario,
    list_sessions,
    read_session,
    scan_transcripts,
)


def write_jsonl(path: Path, records: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(f"{json.dumps(record)}\n" for record in records), encoding="utf-8")


def write_timed_jsonl(path: Path, records: list[dict[str, object]], modified: str) -> None:
    write_jsonl(path, records)
    timestamp = datetime.fromisoformat(modified).timestamp()
    os.utime(path, (timestamp, timestamp))


def minimal_codex_records(session_id: str) -> list[dict[str, object]]:
    return [
        {"type": "session_meta", "payload": {"id": session_id, "cwd": f"/tmp/{session_id}"}},
        {"type": "event_msg", "payload": {"type": "user_message", "message": f"Request from {session_id}"}},
    ]


def minimal_claude_records(session_id: str) -> list[dict[str, object]]:
    return [
        {
            "type": "user",
            "message": {"content": f"Request from {session_id}"},
            "sessionId": session_id,
            "toolUseResult": None,
        }
    ]


def legacy_codex_records() -> list[dict[str, object]]:
    return [
        {"type": "session_meta", "payload": {"id": "legacy-session", "cwd": "/tmp/legacy-project"}},
        {
            "type": "event_msg",
            "timestamp": "2026-01-01T00:00:01Z",
            "payload": {"type": "agent_message", "message": "I used React."},
        },
        {
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": "I used React."}],
            },
        },
        {
            "type": "event_msg",
            "timestamp": "2026-01-01T00:00:02Z",
            "payload": {"type": "user_message", "message": "I said Vue, not React!"},
        },
        {
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": "# AGENTS.md instructions"}],
            },
        },
    ]


def current_codex_records() -> list[dict[str, object]]:
    return [
        {"type": "session_meta", "payload": {"id": "current-session", "cwd": "/tmp/current-project"}},
        {
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": "# AGENTS.md instructions"}],
            },
        },
        {
            "type": "event_msg",
            "timestamp": "2026-01-02T00:00:01Z",
            "payload": {
                "type": "item_completed",
                "item": {
                    "type": "AgentMessage",
                    "phase": "commentary",
                    "content": [{"type": "Text", "text": "I used React."}],
                },
            },
        },
        {
            "type": "event_msg",
            "timestamp": "2026-01-02T00:00:02Z",
            "payload": {
                "type": "item_completed",
                "item": {
                    "type": "UserMessage",
                    "content": [
                        {"type": "text", "text": "I said Vue, not React!"},
                        {"type": "input_text", "text": "injected input block"},
                        {"type": "Text", "text": "Read the prompt."},
                        {"type": "image", "text": "image alt distractor"},
                    ],
                },
            },
        },
        {
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": "I said Vue, not React!"}],
            },
        },
        {
            "type": "event_msg",
            "timestamp": "2026-01-02T00:00:03Z",
            "payload": {
                "type": "item_completed",
                "item": {"type": "AgentMessage", "phase": "final", "content": [{"type": "Text", "text": "Fixed."}]},
            },
        },
        {
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "developer",
                "content": [{"type": "input_text", "text": "developer distractor"}],
            },
        },
        {
            "type": "response_item",
            "payload": {"type": "reasoning", "summary": [{"type": "summary_text", "text": "reasoning distractor"}]},
        },
        {"type": "response_item", "payload": {"type": "function_call_output", "output": "tool distractor"}},
        {"type": "turn_context", "payload": {"cwd": "/tmp/current-project", "text": "turn context distractor"}},
        {"type": "event_msg", "payload": {"type": "token_count", "message": "token distractor"}},
        {"type": "event_msg", "payload": {"type": "world_state", "message": "world state distractor"}},
    ]


async def test_extract_user_messages_reads_legacy_codex_presentation_events(tmp_path: Path) -> None:
    session = tmp_path / "rollout-legacy.jsonl"
    write_jsonl(session, legacy_codex_records())
    output = tmp_path / "batch.jsonl"

    result = await extract_user_messages(str(session), str(output))

    messages = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert result["message_count"] == 1
    assert messages[0]["line_index"] == 3
    assert messages[0]["text"] == "I said Vue, not React!"


async def test_extract_user_messages_reads_current_codex_without_injected_or_duplicate_content(tmp_path: Path) -> None:
    session = tmp_path / "rollout-current.jsonl"
    write_jsonl(session, current_codex_records())
    output = tmp_path / "batch.jsonl"

    result = await extract_user_messages(str(session), str(output))

    messages = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert result["message_count"] == 1
    assert messages[0]["line_index"] == 3
    assert messages[0]["text"] == "I said Vue, not React! Read the prompt."


async def test_get_context_window_resolves_current_codex_source_line(tmp_path: Path) -> None:
    session = tmp_path / "rollout-current.jsonl"
    write_jsonl(session, current_codex_records())

    result = await get_context_window(str(session), line_index=3, before=2, after=1)

    assert result["target"] == {
        "role": "user",
        "line_index": 3,
        "text": "I said Vue, not React! Read the prompt.",
        "timestamp": "2026-01-02T00:00:02Z",
    }
    assert [(entry["role"], entry["text"]) for entry in result["before"]] == [("assistant", "I used React.")]
    assert [(entry["role"], entry["text"]) for entry in result["after"]] == [("assistant", "Fixed.")]


async def test_list_sessions_identifies_codex_provider_metadata_and_title(tmp_path: Path) -> None:
    session = tmp_path / "nested" / "rollout-current.jsonl"
    write_jsonl(session, current_codex_records())

    result = await list_sessions(str(tmp_path))

    assert result["count"] == 1
    assert result["sessions"][0]["provider"] == "codex"
    assert result["sessions"][0]["session_id"] == "current-session"
    assert result["sessions"][0]["project"] == "current-project"
    assert result["sessions"][0]["title"] == "I said Vue, not React! Read the prompt."


async def test_scan_and_scenario_read_codex_conversation_only(tmp_path: Path) -> None:
    session = tmp_path / "rollout-current.jsonl"
    write_jsonl(session, current_codex_records())

    scan = await scan_transcripts(str(tmp_path / "rollout-*.jsonl"))
    scenario = await get_scenario(str(session), line_index=3)

    assert scan["total"] == 1
    assert scan["files_scanned"] == 1
    assert scan["messages"][0]["text"] == "I said Vue, not React! Read the prompt."
    assert [(item["role"], item["text"]) for item in scan["messages"][0]["context"]] == [("assistant", "I used React.")]
    assert scenario["session_id"] == "current-session"
    assert scenario["text"] == "I said Vue, not React! Read the prompt."
    assert [(item["role"], item["text"]) for item in scenario["context"]] == [("assistant", "I used React.")]


async def test_generate_social_post_uses_codex_hashtag(tmp_path: Path) -> None:
    session = tmp_path / "rollout-current.jsonl"
    write_jsonl(session, current_codex_records())

    result = await generate_social_post(str(session), line_index=3)

    assert "#Codex" in result["hashtags"]
    assert "#Codex" in result["post"]


async def test_list_sessions_without_path_scans_claude_and_codex_roots(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "home"
    codex_home = tmp_path / "codex-home"
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("CODEX_HOME", str(codex_home))

    write_jsonl(
        home / ".claude" / "projects" / "claude-project" / "claude.jsonl",
        [
            {
                "type": "user",
                "message": {"content": "Claude request"},
                "timestamp": "2026-01-03T00:00:00Z",
                "sessionId": "claude-session",
                "uuid": "claude-message",
                "toolUseResult": None,
            }
        ],
    )
    write_jsonl(codex_home / "sessions" / "2026" / "01" / "03" / "rollout-active.jsonl", current_codex_records())
    write_jsonl(codex_home / "archived_sessions" / "rollout-archived.jsonl", legacy_codex_records())
    write_jsonl(codex_home / "sessions" / "2026" / "01" / "03" / "notes.jsonl", current_codex_records())

    result = await list_sessions()

    sessions = {Path(item["file"]).name: item for item in result["sessions"]}
    assert set(sessions) == {"claude.jsonl", "rollout-active.jsonl", "rollout-archived.jsonl"}
    assert sessions["claude.jsonl"]["provider"] == "claude"
    assert sessions["rollout-active.jsonl"]["provider"] == "codex"
    assert sessions["rollout-archived.jsonl"]["provider"] == "codex"
    assert result["count"] == result["matched_count"] == 3
    assert result["provider_counts"] == {"claude": 1, "codex": 2}
    assert result["truncated"] is False


async def test_list_sessions_time_window_is_lower_inclusive_upper_exclusive_and_offset_equivalent(
    tmp_path: Path,
) -> None:
    write_timed_jsonl(tmp_path / "rollout-before.jsonl", minimal_codex_records("before"), "2026-01-04T23:59:59+00:00")
    write_timed_jsonl(tmp_path / "rollout-lower.jsonl", minimal_codex_records("lower"), "2026-01-05T00:00:00+00:00")
    write_timed_jsonl(tmp_path / "rollout-inside.jsonl", minimal_codex_records("inside"), "2026-01-05T12:00:00+00:00")
    write_timed_jsonl(tmp_path / "rollout-upper.jsonl", minimal_codex_records("upper"), "2026-01-06T00:00:00+00:00")
    write_timed_jsonl(
        tmp_path / "unsupported.jsonl",
        [{"type": "response_item", "payload": {"text": "unsupported"}}],
        "2026-01-05T18:00:00+00:00",
    )

    utc_result = await list_sessions(
        str(tmp_path), modified_after="2026-01-05T00:00:00+00:00", modified_before="2026-01-06T00:00:00+00:00"
    )
    offset_result = await list_sessions(
        str(tmp_path), modified_after="2026-01-05T11:00:00+11:00", modified_before="2026-01-06T11:00:00+11:00"
    )

    assert [Path(item["file"]).name for item in utc_result["sessions"]] == [
        "rollout-inside.jsonl",
        "rollout-lower.jsonl",
    ]
    assert [item["file"] for item in offset_result["sessions"]] == [item["file"] for item in utc_result["sessions"]]
    assert utc_result["count"] == utc_result["matched_count"] == 2
    assert utc_result["provider_counts"] == {"claude": 0, "codex": 2}
    assert utc_result["truncated"] is False


async def test_list_sessions_filters_provider_before_newest_first_limit(tmp_path: Path) -> None:
    write_timed_jsonl(
        tmp_path / "claude-newest.jsonl", minimal_claude_records("claude-newest"), "2026-01-05T04:00:00+00:00"
    )
    write_timed_jsonl(
        tmp_path / "rollout-codex-newer.jsonl", minimal_codex_records("codex-newer"), "2026-01-05T03:00:00+00:00"
    )
    write_timed_jsonl(
        tmp_path / "rollout-codex-older.jsonl", minimal_codex_records("codex-older"), "2026-01-05T02:00:00+00:00"
    )

    result = await list_sessions(str(tmp_path), provider="codex", limit=1)

    assert [Path(item["file"]).name for item in result["sessions"]] == ["rollout-codex-newer.jsonl"]
    assert result["count"] == 1
    assert result["matched_count"] == 2
    assert result["provider_counts"] == {"claude": 0, "codex": 2}
    assert result["truncated"] is True


async def test_list_sessions_rejects_invalid_naive_and_reversed_time_bounds(tmp_path: Path) -> None:
    with pytest.raises(ToolError):
        await list_sessions(str(tmp_path), modified_after="not-a-timestamp")
    with pytest.raises(ToolError):
        await list_sessions(str(tmp_path), modified_after="2026-01-05T00:00:00")
    with pytest.raises(ToolError):
        await list_sessions(
            str(tmp_path), modified_after="2026-01-06T00:00:00+00:00", modified_before="2026-01-05T00:00:00+00:00"
        )


def test_read_session_distinguishes_malformed_and_unsupported_jsonl(tmp_path: Path) -> None:
    malformed = tmp_path / "malformed.jsonl"
    malformed.write_text('{"type":', encoding="utf-8")
    unsupported = tmp_path / "unsupported.jsonl"
    write_jsonl(unsupported, [{"type": "response_item", "payload": {"text": "not a session"}}])

    with pytest.raises(ToolError, match="Could not read session file"):
        read_session(str(malformed))
    with pytest.raises(ToolError, match="Unsupported session format"):
        read_session(str(unsupported))
