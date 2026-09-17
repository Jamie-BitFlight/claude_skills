"""Tests for the kage-bunshin team health snapshot."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import health
import monitor


def assistant_record(content: list[dict[str, object]]) -> str:
    """Serialize one assistant JSONL record."""
    return json.dumps({
        "type": "assistant",
        "timestamp": "2026-09-17T12:00:00Z",
        "message": {"role": "assistant", "content": content},
    })


def test_extract_actions_reads_complete_jsonl_and_returns_mixed_actions() -> None:
    complete_input = "old-" + "x" * 100
    complete_text = "Tests passed " + "y" * 100
    old_tool = assistant_record([{"type": "tool_use", "name": "Read", "input": {"file": complete_input}}])
    filler = [json.dumps({"type": "user", "content": "filler"}) for _ in range(300)]
    recent = assistant_record([
        {"type": "tool_use", "name": "Bash", "input": {"command": "pytest"}},
        {"type": "text", "text": complete_text},
    ])

    actions = health.extract_actions("\n".join([old_tool, *filler, recent]), None)

    assert len(actions) == 3
    assert complete_input in actions[0]
    assert "Bash(" in actions[1]
    assert complete_text in actions[2]


def test_extract_actions_ignores_non_action_and_malformed_record_variants() -> None:
    records = [
        "not json",
        json.dumps([]),
        json.dumps({"type": "user", "message": {"content": [{"type": "text", "text": "prompt"}]}}),
        json.dumps({"type": "assistant"}),
        json.dumps({"type": "assistant", "message": {"content": "plain text"}}),
        json.dumps({"type": "assistant", "message": {"content": [None, {"type": "thinking"}]}}),
        assistant_record([{"type": "text", "text": "kept action"}]),
    ]

    actions = health.extract_actions("\n".join(records), None)

    assert actions == ["  2026-09-17 12:00:00  [text] kept action"]


def test_agent_last_actions_searches_all_files_and_complete_contents(tmp_path: Path) -> None:
    target = tmp_path / "target.jsonl"
    target.write_text(
        "x" * 4000 + "worker@team\n" + assistant_record([{"type": "text", "text": "target action"}]) + "\n"
    )
    os.utime(target, (1, 1))
    for index in range(30):
        candidate = tmp_path / f"newer-{index}.jsonl"
        candidate.write_text(assistant_record([{"type": "text", "text": f"unrelated {index}"}]) + "\n")
        os.utime(candidate, (index + 2, index + 2))

    actions, session = health.agent_last_actions("worker", None, tmp_path, agent_id="worker@team")

    assert session == "target.jsonl"
    assert actions == ["  2026-09-17 12:00:00  [text] target action"]


def test_run_health_uses_latest_team_and_prints_member_snapshot(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    teams_dir = tmp_path / "teams"
    team_dir = teams_dir / "example"
    team_dir.mkdir(parents=True)
    (team_dir / "config.json").write_text(
        json.dumps({"members": [{"name": "worker", "agentType": "reviewer"}], "leadSessionId": "lead"})
    )

    with (
        patch.object(health, "_TEAMS_DIR", teams_dir),
        patch.object(health, "agent_last_actions", return_value=(["  action"], "worker.jsonl")),
    ):
        health.run_health(None, tmp_path, action_limit=5)

    output = capsys.readouterr().out
    assert "Team : example" in output
    assert "worker  [reviewer]" in output
    assert "session: worker.jsonl" in output
    assert "  action" in output
    assert "tmux: no pane assigned" in output


def test_main_prints_all_actions_by_default() -> None:
    with (
        patch.object(sys, "argv", ["monitor.py", "health", "example"]),
        patch.object(monitor, "run_health") as run_health,
    ):
        monitor.main()

    run_health.assert_called_once_with(team_name="example", jsonl_dir=None, action_limit=None)


def test_main_passes_caller_selected_action_limit() -> None:
    with (
        patch.object(sys, "argv", ["monitor.py", "health", "example", "--action-limit", "2"]),
        patch.object(monitor, "run_health") as run_health,
    ):
        monitor.main()

    run_health.assert_called_once_with(team_name="example", jsonl_dir=None, action_limit=2)
