"""Tests for kage-bunshin spawn.py — bidirectional session manager."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add the scripts directory to sys.path so spawn can be imported directly.
_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from typing import TYPE_CHECKING

import spawn as _spawn

if TYPE_CHECKING:
    import argparse

# ---------------------------------------------------------------------------
# _slugify
# ---------------------------------------------------------------------------


def test_slugify_with_plain_text_returns_lowercase_hyphenated():
    result = _spawn._slugify("Hello World")
    assert result == "hello-world"


def test_slugify_with_special_chars_replaces_with_hyphens():
    result = _spawn._slugify("Load /dh:work-backlog-item #42!")
    assert result == "load-dh-work-backlog-item-42"


def test_slugify_with_long_text_truncates_to_max_length():
    # _slugify truncates to _NAME_MAX_CHARS (30) and strips trailing hyphens.
    long_text = "a" * 100
    result = _spawn._slugify(long_text)
    assert len(result) <= _spawn._NAME_MAX_CHARS


def test_slugify_with_trailing_hyphens_strips_them():
    # Input that would produce trailing hyphens after truncation.
    text = "hello" + "-" * 25
    result = _spawn._slugify(text)
    assert not result.endswith("-")


def test_slugify_with_empty_string_returns_empty():
    result = _spawn._slugify("")
    assert result == ""


# ---------------------------------------------------------------------------
# _repo_slug
# ---------------------------------------------------------------------------


def test_repo_slug_replaces_slashes_with_hyphens():
    result = _spawn._repo_slug(Path("/home/user/repos/claude_skills"))
    assert result == "-home-user-repos-claude_skills"


def test_repo_slug_leading_hyphen_is_intentional():
    result = _spawn._repo_slug(Path("/foo/bar"))
    assert result.startswith("-")


# ---------------------------------------------------------------------------
# _repo_dir_name
# ---------------------------------------------------------------------------


def test_repo_dir_name_returns_last_path_component():
    result = _spawn._repo_dir_name(Path("/home/user/repos/claude_skills"))
    assert result == "claude_skills"


def test_repo_dir_name_single_component():
    result = _spawn._repo_dir_name(Path("/myrepo"))
    assert result == "myrepo"


# ---------------------------------------------------------------------------
# _claude_tmux_session_name
# ---------------------------------------------------------------------------


def test_claude_tmux_session_name_uses_worktree_pattern():
    result = _spawn._claude_tmux_session_name("claude_skills", "test-1")
    assert result == "claude_skills_worktree-test-1"


def test_claude_tmux_session_name_with_different_repo():
    result = _spawn._claude_tmux_session_name("myproject", "sess")
    assert result == "myproject_worktree-sess"


# ---------------------------------------------------------------------------
# _dh_state_home
# ---------------------------------------------------------------------------


def test_dh_state_home_returns_default_when_env_unset():
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("DH_STATE_HOME", None)
        result = _spawn._dh_state_home()
    assert result == Path.home() / ".dh"


def test_dh_state_home_respects_env_override(tmp_path):
    with patch.dict(os.environ, {"DH_STATE_HOME": str(tmp_path)}):
        result = _spawn._dh_state_home()
    assert result == tmp_path


# ---------------------------------------------------------------------------
# Registry helpers
# ---------------------------------------------------------------------------


def test_load_registry_returns_empty_dict_when_file_absent(tmp_path):
    result = _spawn._load_registry(tmp_path, "default")
    assert result == {}


def test_save_and_load_registry_round_trips(tmp_path):
    registry = {"mysession": {"name": "mysession", "model": "sonnet"}}
    _spawn._save_registry(tmp_path, "default", registry)
    loaded = _spawn._load_registry(tmp_path, "default")
    assert loaded == registry


def test_save_registry_writes_atomically(tmp_path):
    registry = {"a": {"name": "a"}}
    _spawn._save_registry(tmp_path, "default", registry)
    rp = _spawn._registry_path(tmp_path, "default")
    assert rp.exists()
    # No .tmp file should remain.
    assert not rp.with_suffix(".tmp").exists()


def test_registry_path_uses_session_id_in_filename(tmp_path):
    path = _spawn._registry_path(tmp_path, "abc123")
    assert path.name == "registry-abc123.json"


def test_registry_path_default_session_id(tmp_path):
    path = _spawn._registry_path(tmp_path, "default")
    assert path.name == "registry-default.json"


def test_get_session_raises_system_exit_when_missing(tmp_path):
    with pytest.raises(SystemExit) as exc_info:
        _spawn._get_session(tmp_path, "default", "nonexistent")
    assert exc_info.value.code == 1


def test_get_session_returns_entry_when_present(tmp_path):
    registry = {"mysess": {"name": "mysess", "model": "haiku"}}
    _spawn._save_registry(tmp_path, "default", registry)
    result = _spawn._get_session(tmp_path, "default", "mysess")
    assert result["model"] == "haiku"


def test_session_id_scoping_isolates_registries(tmp_path):
    """Two session IDs write to separate files and do not clobber each other."""
    reg_a = {"sess-a": {"name": "sess-a", "model": "sonnet"}}
    reg_b = {"sess-b": {"name": "sess-b", "model": "haiku"}}

    _spawn._save_registry(tmp_path, "orchestrator-1", reg_a)
    _spawn._save_registry(tmp_path, "orchestrator-2", reg_b)

    loaded_a = _spawn._load_registry(tmp_path, "orchestrator-1")
    loaded_b = _spawn._load_registry(tmp_path, "orchestrator-2")

    assert "sess-a" in loaded_a
    assert "sess-b" not in loaded_a
    assert "sess-b" in loaded_b
    assert "sess-a" not in loaded_b


# ---------------------------------------------------------------------------
# tmux helpers
# ---------------------------------------------------------------------------


def test_tmux_alive_returns_false_when_session_absent():
    # Use an implausible session name that won't exist.
    result = _spawn._tmux_alive("kage-bunshin-test-nonexistent-xyzzy-99999")
    assert result is False


def test_tmux_run_in_session_calls_send_keys_with_enter():
    fake_result = MagicMock()
    fake_result.returncode = 0
    fake_result.stderr = ""

    with patch("subprocess.run", return_value=fake_result) as mock_run:
        _spawn._tmux_run_in_session("myproject_worktree-sess", "echo hello")

    mock_run.assert_called_once()
    cmd = mock_run.call_args[0][0]
    assert cmd[0] == "tmux"
    assert cmd[1] == "send-keys"
    assert "-t" in cmd
    assert "myproject_worktree-sess" in cmd
    assert "echo hello" in cmd
    assert "Enter" in cmd


def test_tmux_run_in_session_exits_1_on_failure():
    fake_result = MagicMock()
    fake_result.returncode = 1
    fake_result.stderr = "no session"

    with patch("subprocess.run", return_value=fake_result), pytest.raises(SystemExit) as exc_info:
        _spawn._tmux_run_in_session("nosuchsession", "echo hi")
    assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# _format_age
# ---------------------------------------------------------------------------


def test_format_age_seconds():
    assert _spawn._format_age(45) == "45s"


def test_format_age_minutes():
    assert _spawn._format_age(120) == "2m"


def test_format_age_hours():
    assert _spawn._format_age(7200) == "2h"


def test_format_age_days():
    assert _spawn._format_age(172800) == "2d"


# ---------------------------------------------------------------------------
# Argument parser — subcommands
# ---------------------------------------------------------------------------


def test_build_parser_spawn_subcommand_parses_prompt():
    parser = _spawn._build_parser()
    args = parser.parse_args(["spawn", "my prompt"])
    assert args.prompt == ["my prompt"]
    assert args.model == "sonnet"
    assert args.max_budget is None
    assert args.name is None


def test_build_parser_spawn_with_all_flags():
    parser = _spawn._build_parser()
    args = parser.parse_args(["spawn", "--name", "sess", "--model", "opus", "--max-budget", "3.0", "prompt"])
    assert args.name == "sess"
    assert args.model == "opus"
    assert args.max_budget == pytest.approx(3.0)


def test_build_parser_send_requires_name():
    parser = _spawn._build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["send", "message"])


def test_build_parser_send_with_name_and_message():
    parser = _spawn._build_parser()
    args = parser.parse_args(["send", "--name", "mysess", "hello"])
    assert args.name == "mysess"
    assert args.message == ["hello"]


def test_build_parser_read_defaults():
    parser = _spawn._build_parser()
    args = parser.parse_args(["read", "--name", "s"])
    assert args.wait == pytest.approx(0.0)
    assert args.follow is False


def test_build_parser_read_follow_flag():
    parser = _spawn._build_parser()
    args = parser.parse_args(["read", "--name", "s", "--follow"])
    assert args.follow is True


def test_build_parser_read_wait_option():
    parser = _spawn._build_parser()
    args = parser.parse_args(["read", "--name", "s", "--wait", "10"])
    assert args.wait == pytest.approx(10.0)


def test_build_parser_kill_requires_name():
    parser = _spawn._build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["kill"])


def test_build_parser_list_has_no_required_args():
    parser = _spawn._build_parser()
    args = parser.parse_args(["list"])
    assert args.command == "list"


def test_build_parser_status_requires_name():
    parser = _spawn._build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["status"])


# ---------------------------------------------------------------------------
# _build_spawn_shell_cmd
# ---------------------------------------------------------------------------


def test_build_spawn_shell_cmd_returns_interactive_argv_without_p_flag():
    argv = _spawn._build_spawn_shell_cmd("mysess", "sonnet", None, "sess-001", "tmux-mysess")
    assert argv[0] == "claude"
    assert "-p" not in argv
    assert "--output-format" not in argv
    assert "--input-format" not in argv
    assert "--worktree" in argv
    assert "mysess" in argv
    assert "--tmux" in argv
    assert "--model" in argv
    assert "sonnet" in argv


def test_build_spawn_shell_cmd_includes_max_budget_when_set():
    argv = _spawn._build_spawn_shell_cmd("sess", "haiku", 5.0, "sess-002", "tmux-sess")
    assert "--max-budget-usd" in argv
    assert "5.0" in argv


def test_build_spawn_shell_cmd_omits_max_budget_when_none():
    argv = _spawn._build_spawn_shell_cmd("sess", "haiku", None, "sess-003", "tmux-sess")
    assert "--max-budget-usd" not in argv


# ---------------------------------------------------------------------------
# cmd_spawn — integration with subprocess mocked
# ---------------------------------------------------------------------------


def _make_spawn_args(
    name: str = "testsess",
    prompt: str = "hello world",
    model: str = "sonnet",
    max_budget: float | None = None,
    session_id: str = "default",
) -> MagicMock:
    """Build a mock Namespace for cmd_spawn."""
    ns = MagicMock()
    ns.name = name
    ns.prompt = [prompt]
    ns.model = model
    ns.max_budget = max_budget
    ns.session_id = session_id
    return ns


def test_cmd_spawn_exits_1_when_claude_not_in_path(tmp_path):
    args = _make_spawn_args()
    with (
        patch("shutil.which", return_value=None),
        patch.object(_spawn, "_session_state_dir", return_value=tmp_path),
        patch.object(_spawn, "_git_repo_root", return_value=Path("/repo/claude_skills")),
        pytest.raises(SystemExit) as exc_info,
    ):
        _spawn.cmd_spawn(args)
    assert exc_info.value.code == 1


def test_cmd_spawn_exits_1_when_tmux_not_in_path(tmp_path):
    args = _make_spawn_args()

    def fake_which(name: str) -> str | None:
        return "/usr/bin/claude" if name == "claude" else None

    with (
        patch("shutil.which", side_effect=fake_which),
        patch.object(_spawn, "_session_state_dir", return_value=tmp_path),
        patch.object(_spawn, "_git_repo_root", return_value=Path("/repo/claude_skills")),
        pytest.raises(SystemExit) as exc_info,
    ):
        _spawn.cmd_spawn(args)
    assert exc_info.value.code == 1


def test_cmd_spawn_creates_registry_entry(tmp_path, capsys):
    args = _make_spawn_args()

    fake_run_result = MagicMock()
    fake_run_result.returncode = 0
    fake_run_result.stderr = ""

    with (
        patch("shutil.which", return_value="/usr/bin/claude"),
        patch.object(_spawn, "_git_repo_root", return_value=Path("/repo/claude_skills")),
        patch.object(_spawn, "_session_state_dir", return_value=tmp_path),
        patch("subprocess.run", return_value=fake_run_result),
        # claude tmux session appears immediately
        patch.object(_spawn, "_tmux_alive", return_value=True),
        patch("time.sleep"),
        patch.object(_spawn, "_tmux_run_in_session"),
    ):
        _spawn.cmd_spawn(args)

    # Registry entry written.
    registry = _spawn._load_registry(tmp_path, "default")
    assert "testsess" in registry
    entry = registry["testsess"]
    assert entry["model"] == "sonnet"
    assert entry["worktree"] is True
    assert "tmux_session" in entry
    assert entry["tmux_session"] == "claude_skills_worktree-testsess"
    assert "output_path" not in entry

    # JSON record printed to stdout.
    captured = capsys.readouterr()
    record = json.loads(captured.out)
    assert record["name"] == "testsess"
    assert record["model"] == "sonnet"
    assert record["tmux_session"] == "claude_skills_worktree-testsess"
    assert "output_path" not in record


def test_cmd_spawn_exits_1_when_tmux_launcher_fails(tmp_path):
    args = _make_spawn_args()

    fake_run_result = MagicMock()
    fake_run_result.returncode = 1
    fake_run_result.stderr = "duplicate session"

    with (
        patch("shutil.which", return_value="/usr/bin/claude"),
        patch.object(_spawn, "_git_repo_root", return_value=Path("/repo/claude_skills")),
        patch.object(_spawn, "_session_state_dir", return_value=tmp_path),
        patch("subprocess.run", return_value=fake_run_result),
        pytest.raises(SystemExit) as exc_info,
    ):
        _spawn.cmd_spawn(args)
    assert exc_info.value.code == 1


def test_cmd_spawn_includes_worktree_flag_in_argv(tmp_path, capsys):
    """Verify --worktree {name} appears in the argv passed to tmux new-session."""
    args = _make_spawn_args(name="myworktree")

    fake_run_result = MagicMock()
    fake_run_result.returncode = 0
    fake_run_result.stderr = ""

    captured_argv: list[list[str]] = []

    def fake_run(cmd: list[str] | str, **kwargs: object) -> object:
        if isinstance(cmd, list) and "new-session" in cmd:
            captured_argv.append(list(cmd))
        return fake_run_result

    with (
        patch("shutil.which", return_value="/usr/bin/claude"),
        patch.object(_spawn, "_git_repo_root", return_value=Path("/repo/claude_skills")),
        patch.object(_spawn, "_session_state_dir", return_value=tmp_path),
        patch("subprocess.run", side_effect=fake_run),
        patch.object(_spawn, "_tmux_alive", return_value=True),
        patch("time.sleep"),
        patch.object(_spawn, "_tmux_run_in_session"),
    ):
        _spawn.cmd_spawn(args)

    assert captured_argv, "tmux new-session was not called"
    argv = captured_argv[0]
    # claude argv is embedded directly in the tmux new-session command
    assert "--worktree" in argv
    assert "myworktree" in argv
    assert "--tmux" in argv
    # No -p in interactive mode
    assert "-p" not in argv
    # No --output-format in interactive mode
    assert "--output-format" not in argv
    # No file redirects
    assert not any(">>" in arg for arg in argv)


def test_cmd_spawn_waits_for_claude_tmux_session(tmp_path, capsys):
    """Verify spawn polls until the claude-created tmux session appears."""
    args = _make_spawn_args()

    fake_run_result = MagicMock()
    fake_run_result.returncode = 0
    fake_run_result.stderr = ""

    alive_calls: list[int] = [0]

    def fake_alive(tmux_session: str) -> bool:
        alive_calls[0] += 1
        # Return False for first 2 calls, then True (session appears).
        return alive_calls[0] >= 3

    with (
        patch("shutil.which", return_value="/usr/bin/claude"),
        patch.object(_spawn, "_git_repo_root", return_value=Path("/repo/claude_skills")),
        patch.object(_spawn, "_session_state_dir", return_value=tmp_path),
        patch("subprocess.run", return_value=fake_run_result),
        patch.object(_spawn, "_tmux_alive", side_effect=fake_alive),
        patch("time.sleep"),
        patch.object(_spawn, "_tmux_run_in_session"),
    ):
        _spawn.cmd_spawn(args)

    assert alive_calls[0] >= 3


def test_cmd_spawn_sends_initial_prompt_via_send_keys(tmp_path, capsys):
    """Verify spawn sends the initial prompt to the claude pane via tmux send-keys."""
    args = _make_spawn_args(prompt="explain recursion")

    fake_run_result = MagicMock()
    fake_run_result.returncode = 0
    fake_run_result.stderr = ""

    sent: list[tuple[str, str]] = []

    def fake_run_in_session(tmux_session: str, cmd: str) -> None:
        sent.append((tmux_session, cmd))

    with (
        patch("shutil.which", return_value="/usr/bin/claude"),
        patch.object(_spawn, "_git_repo_root", return_value=Path("/repo/claude_skills")),
        patch.object(_spawn, "_session_state_dir", return_value=tmp_path),
        patch("subprocess.run", return_value=fake_run_result),
        patch.object(_spawn, "_tmux_alive", return_value=True),
        patch("time.sleep"),
        patch.object(_spawn, "_tmux_run_in_session", side_effect=fake_run_in_session),
    ):
        _spawn.cmd_spawn(args)

    assert len(sent) == 1, "expected exactly one send-keys call for the initial prompt"
    tmux_session, prompt = sent[0]
    assert tmux_session == "claude_skills_worktree-testsess"
    assert "explain recursion" in prompt


def test_cmd_spawn_exits_1_when_claude_session_never_appears(tmp_path):
    """Verify spawn fails if claude's tmux session never appears within timeout."""
    args = _make_spawn_args()

    fake_run_result = MagicMock()
    fake_run_result.returncode = 0
    fake_run_result.stderr = ""

    with (
        patch("shutil.which", return_value="/usr/bin/claude"),
        patch.object(_spawn, "_git_repo_root", return_value=Path("/repo/claude_skills")),
        patch.object(_spawn, "_session_state_dir", return_value=tmp_path),
        patch("subprocess.run", return_value=fake_run_result),
        patch.object(_spawn, "_tmux_alive", return_value=False),
        patch("time.sleep"),
        # Make the deadline expire immediately.
        patch("time.monotonic", side_effect=[0.0, 0.0, _spawn._SPAWN_WAIT_SECONDS + 1]),
        pytest.raises(SystemExit) as exc_info,
    ):
        _spawn.cmd_spawn(args)
    assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# cmd_send
# ---------------------------------------------------------------------------


def test_cmd_send_exits_1_when_session_not_found(tmp_path):
    ns = MagicMock()
    ns.name = "nosuchsession"
    ns.message = ["hi"]
    ns.session_id = "default"
    with patch.object(_spawn, "_session_state_dir", return_value=tmp_path), pytest.raises(SystemExit) as exc_info:
        _spawn.cmd_send(ns)
    assert exc_info.value.code == 1


def test_cmd_send_exits_1_when_tmux_dead(tmp_path):
    registry = {"sess": {"name": "sess", "model": "sonnet", "tmux_session": "claude_skills_worktree-sess"}}
    _spawn._save_registry(tmp_path, "default", registry)

    ns = MagicMock()
    ns.name = "sess"
    ns.message = ["hello"]
    ns.session_id = "default"

    with (
        patch.object(_spawn, "_session_state_dir", return_value=tmp_path),
        patch.object(_spawn, "_tmux_alive", return_value=False),
        pytest.raises(SystemExit) as exc_info,
    ):
        _spawn.cmd_send(ns)
    assert exc_info.value.code == 1


def test_cmd_send_sends_message_via_tmux(tmp_path, capsys):
    """Verify send calls _tmux_run_in_session with the message directly."""
    registry = {"sess": {"name": "sess", "model": "sonnet", "tmux_session": "claude_skills_worktree-sess"}}
    _spawn._save_registry(tmp_path, "default", registry)

    ns = MagicMock()
    ns.name = "sess"
    ns.message = ["do the thing"]
    ns.session_id = "default"

    sent_cmds: list[tuple[str, str]] = []

    def fake_run_in_session(tmux_session: str, cmd: str) -> None:
        sent_cmds.append((tmux_session, cmd))

    with (
        patch.object(_spawn, "_session_state_dir", return_value=tmp_path),
        patch.object(_spawn, "_tmux_alive", return_value=True),
        patch.object(_spawn, "_tmux_run_in_session", side_effect=fake_run_in_session),
    ):
        _spawn.cmd_send(ns)

    assert len(sent_cmds) == 1
    tmux_session, cmd = sent_cmds[0]
    assert tmux_session == "claude_skills_worktree-sess"
    assert "do the thing" in cmd

    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert result["status"] == "sent"
    assert result["name"] == "sess"


# ---------------------------------------------------------------------------
# cmd_kill
# ---------------------------------------------------------------------------


def test_cmd_kill_removes_registry_entry(tmp_path):
    registry = {"sess": {"name": "sess", "tmux_session": "claude_skills_worktree-sess"}}
    _spawn._save_registry(tmp_path, "default", registry)

    ns = MagicMock()
    ns.name = "sess"
    ns.session_id = "default"

    with patch.object(_spawn, "_session_state_dir", return_value=tmp_path), patch.object(_spawn, "_tmux_kill"):
        _spawn.cmd_kill(ns)

    assert "sess" not in _spawn._load_registry(tmp_path, "default")


def test_cmd_kill_kills_claude_tmux_session(tmp_path):
    registry = {"sess": {"name": "sess", "tmux_session": "claude_skills_worktree-sess"}}
    _spawn._save_registry(tmp_path, "default", registry)

    ns = MagicMock()
    ns.name = "sess"
    ns.session_id = "default"

    killed: list[str] = []

    with (
        patch.object(_spawn, "_session_state_dir", return_value=tmp_path),
        patch.object(_spawn, "_tmux_kill", side_effect=killed.append),
    ):
        _spawn.cmd_kill(ns)

    assert "claude_skills_worktree-sess" in killed


def test_cmd_kill_exits_1_when_session_not_found(tmp_path):
    ns = MagicMock()
    ns.name = "ghost"
    ns.session_id = "default"
    with patch.object(_spawn, "_session_state_dir", return_value=tmp_path), pytest.raises(SystemExit) as exc_info:
        _spawn.cmd_kill(ns)
    assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# cmd_list
# ---------------------------------------------------------------------------


def test_cmd_list_prints_no_sessions_when_registry_empty(tmp_path, capsys):
    ns = MagicMock()
    ns.session_id = "default"
    with patch.object(_spawn, "_session_state_dir", return_value=tmp_path):
        _spawn.cmd_list(ns)
    captured = capsys.readouterr()
    assert "No sessions" in captured.out


def test_cmd_list_shows_alive_and_dead_sessions(tmp_path, capsys):
    registry = {
        "alive-sess": {
            "name": "alive-sess",
            "model": "sonnet",
            "spawned_at": "2026-01-01T00:00:00+00:00",
            "worktree": True,
            "tmux_session": "claude_skills_worktree-alive-sess",
        },
        "dead-sess": {
            "name": "dead-sess",
            "model": "haiku",
            "spawned_at": "2026-01-01T00:00:00+00:00",
            "worktree": True,
            "tmux_session": "claude_skills_worktree-dead-sess",
        },
    }
    _spawn._save_registry(tmp_path, "default", registry)

    def fake_alive(tmux_session: str) -> bool:
        return "alive-sess" in tmux_session

    ns = MagicMock()
    ns.session_id = "default"
    with (
        patch.object(_spawn, "_session_state_dir", return_value=tmp_path),
        patch.object(_spawn, "_tmux_alive", side_effect=fake_alive),
    ):
        _spawn.cmd_list(ns)

    captured = capsys.readouterr()
    assert "alive-sess" in captured.out
    assert "dead-sess" in captured.out
    assert "alive" in captured.out
    assert "dead" in captured.out


def test_cmd_list_all_registries_when_no_session_id(tmp_path, capsys):
    """When session_id is None, list aggregates all registry files."""
    reg_a = {
        "sess-a": {
            "name": "sess-a",
            "model": "sonnet",
            "spawned_at": "2026-01-01T00:00:00+00:00",
            "worktree": True,
            "tmux_session": "proj_worktree-sess-a",
        }
    }
    reg_b = {
        "sess-b": {
            "name": "sess-b",
            "model": "haiku",
            "spawned_at": "2026-01-01T00:00:00+00:00",
            "worktree": True,
            "tmux_session": "proj_worktree-sess-b",
        }
    }
    _spawn._save_registry(tmp_path, "orchestrator-1", reg_a)
    _spawn._save_registry(tmp_path, "orchestrator-2", reg_b)

    ns = MagicMock()
    ns.session_id = None
    with (
        patch.object(_spawn, "_session_state_dir", return_value=tmp_path),
        patch.object(_spawn, "_tmux_alive", return_value=False),
    ):
        _spawn.cmd_list(ns)

    captured = capsys.readouterr()
    assert "sess-a" in captured.out
    assert "sess-b" in captured.out
    assert "orchestrator-1" in captured.out
    assert "orchestrator-2" in captured.out
    # SESSION_ID column header should appear when listing all
    assert "SESSION_ID" in captured.out


def test_cmd_list_all_registries_no_sessions_at_all(tmp_path, capsys):
    """When session_id is None and no registries exist, prints no-sessions message."""
    ns = MagicMock()
    ns.session_id = None
    with patch.object(_spawn, "_session_state_dir", return_value=tmp_path):
        _spawn.cmd_list(ns)
    captured = capsys.readouterr()
    assert "No sessions" in captured.out


# ---------------------------------------------------------------------------
# cmd_status
# ---------------------------------------------------------------------------


def test_cmd_status_shows_alive_true(tmp_path, capsys):
    registry = {
        "sess": {
            "name": "sess",
            "model": "sonnet",
            "spawned_at": "2026-01-01T00:00:00+00:00",
            "worktree": True,
            "tmux_session": "claude_skills_worktree-sess",
        }
    }
    _spawn._save_registry(tmp_path, "default", registry)

    ns = MagicMock()
    ns.name = "sess"
    ns.session_id = "default"

    with (
        patch.object(_spawn, "_session_state_dir", return_value=tmp_path),
        patch.object(_spawn, "_tmux_alive", return_value=True),
    ):
        _spawn.cmd_status(ns)

    captured = capsys.readouterr()
    status = json.loads(captured.out)
    assert status["alive"] is True
    assert status["model"] == "sonnet"


def test_cmd_status_shows_session_fields(tmp_path, capsys):
    """Verify status output includes expected registry fields."""
    registry = {
        "sess": {
            "name": "sess",
            "model": "haiku",
            "spawned_at": "2026-01-01T00:00:00+00:00",
            "worktree": True,
            "tmux_session": "claude_skills_worktree-sess",
        }
    }
    _spawn._save_registry(tmp_path, "default", registry)

    ns = MagicMock()
    ns.name = "sess"
    ns.session_id = "default"

    with (
        patch.object(_spawn, "_session_state_dir", return_value=tmp_path),
        patch.object(_spawn, "_tmux_alive", return_value=False),
    ):
        _spawn.cmd_status(ns)

    captured = capsys.readouterr()
    status = json.loads(captured.out)
    assert status["alive"] is False
    assert status["model"] == "haiku"
    assert status["tmux_session"] == "claude_skills_worktree-sess"
    assert status["worktree"] is True


# ---------------------------------------------------------------------------
# cmd_read
# ---------------------------------------------------------------------------


def test_cmd_read_prints_pane_content(tmp_path, capsys):
    registry = {"sess": {"name": "sess", "tmux_session": "claude_skills_worktree-sess"}}
    _spawn._save_registry(tmp_path, "default", registry)

    ns = MagicMock()
    ns.name = "sess"
    ns.wait = 0.0
    ns.follow = False
    ns.session_id = "default"

    fake_result = MagicMock()
    fake_result.returncode = 0
    fake_result.stdout = "Claude says: The answer is 42.\n"
    fake_result.stderr = ""

    with (
        patch.object(_spawn, "_session_state_dir", return_value=tmp_path),
        patch.object(_spawn, "_tmux_alive", return_value=True),
        patch("subprocess.run", return_value=fake_result),
    ):
        _spawn.cmd_read(ns)

    captured = capsys.readouterr()
    assert "The answer is 42." in captured.out


def test_cmd_read_calls_capture_pane_with_correct_session(tmp_path):
    """Verify cmd_read invokes tmux capture-pane targeting the registered session."""
    registry = {"sess": {"name": "sess", "tmux_session": "claude_skills_worktree-sess"}}
    _spawn._save_registry(tmp_path, "default", registry)

    ns = MagicMock()
    ns.name = "sess"
    ns.wait = 0.0
    ns.follow = False
    ns.session_id = "default"

    fake_result = MagicMock()
    fake_result.returncode = 0
    fake_result.stdout = "output"
    fake_result.stderr = ""

    captured_cmds: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        captured_cmds.append(list(cmd))
        return fake_result

    with (
        patch.object(_spawn, "_session_state_dir", return_value=tmp_path),
        patch.object(_spawn, "_tmux_alive", return_value=True),
        patch("subprocess.run", side_effect=fake_run),
    ):
        _spawn.cmd_read(ns)

    assert captured_cmds, "subprocess.run was not called"
    cmd = captured_cmds[0]
    assert "tmux" in cmd
    assert "capture-pane" in cmd
    assert "claude_skills_worktree-sess" in cmd


def test_cmd_read_exits_1_when_session_not_alive(tmp_path):
    registry = {"sess": {"name": "sess", "tmux_session": "claude_skills_worktree-sess"}}
    _spawn._save_registry(tmp_path, "default", registry)

    ns = MagicMock()
    ns.name = "sess"
    ns.wait = 0.0
    ns.follow = False
    ns.session_id = "default"

    with (
        patch.object(_spawn, "_session_state_dir", return_value=tmp_path),
        patch.object(_spawn, "_tmux_alive", return_value=False),
        pytest.raises(SystemExit) as exc_info,
    ):
        _spawn.cmd_read(ns)

    assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# _wait_for_session_exit
# ---------------------------------------------------------------------------


def test_wait_for_session_exit_returns_true_when_session_exits_promptly():
    # Session is gone on the first poll.
    with (
        patch.object(_spawn, "_tmux_alive", return_value=False),
        patch("time.sleep"),
        patch("time.monotonic", side_effect=[0.0, 0.1]),
    ):
        result = _spawn._wait_for_session_exit("some-session", timeout=5.0)
    assert result is True


def test_wait_for_session_exit_returns_false_when_timeout_exceeded():
    # Session remains alive throughout; deadline expires.
    monotonic_values = [0.0] + [i * 0.5 for i in range(1, 70)]

    with (
        patch.object(_spawn, "_tmux_alive", return_value=True),
        patch("time.sleep"),
        patch("time.monotonic", side_effect=monotonic_values),
    ):
        result = _spawn._wait_for_session_exit("some-session", timeout=5.0)
    assert result is False


def test_wait_for_session_exit_returns_true_after_a_few_polls():
    # Session alive for first 2 polls then gone.
    alive_calls: list[int] = [0]

    def fake_alive(_session: str) -> bool:
        alive_calls[0] += 1
        return alive_calls[0] < 3

    with (
        patch.object(_spawn, "_tmux_alive", side_effect=fake_alive),
        patch("time.sleep"),
        patch("time.monotonic", side_effect=[0.0, 0.5, 1.0, 1.5, 2.0, 2.5]),
    ):
        result = _spawn._wait_for_session_exit("some-session", timeout=10.0)
    assert result is True


# ---------------------------------------------------------------------------
# cmd_stop
# ---------------------------------------------------------------------------


def _make_stop_ns(name: str = "sess", session_id: str = "default") -> MagicMock:
    ns = MagicMock()
    ns.name = name
    ns.session_id = session_id
    return ns


def test_cmd_stop_graceful_exit_path_removes_registry_entry(tmp_path, capsys):
    """Ctrl-C causes session to exit within timeout — success without force."""
    registry = {"sess": {"name": "sess", "tmux_session": "claude_skills_worktree-sess"}}
    _spawn._save_registry(tmp_path, "default", registry)

    ns = _make_stop_ns()

    with (
        patch.object(_spawn, "_session_state_dir", return_value=tmp_path),
        # Session is alive initially (liveness check), then exits after Ctrl-C.
        patch.object(_spawn, "_tmux_alive", return_value=True),
        patch.object(_spawn, "_tmux_send_ctrlc"),
        patch.object(_spawn, "_wait_for_session_exit", return_value=True),
        patch.object(_spawn, "_tmux_kill"),
    ):
        _spawn.cmd_stop(ns)

    assert "sess" not in _spawn._load_registry(tmp_path, "default")
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert result["status"] == "stopped"
    assert result["name"] == "sess"
    assert result["forced"] is False


def test_cmd_stop_graceful_exit_path_does_not_force_kill(tmp_path):
    """Ctrl-C causes session to exit within timeout — tmux kill-session NOT called for main session."""
    registry = {"sess": {"name": "sess", "tmux_session": "claude_skills_worktree-sess"}}
    _spawn._save_registry(tmp_path, "default", registry)

    ns = _make_stop_ns()
    killed: list[str] = []

    with (
        patch.object(_spawn, "_session_state_dir", return_value=tmp_path),
        patch.object(_spawn, "_tmux_alive", return_value=True),
        patch.object(_spawn, "_tmux_send_ctrlc"),
        patch.object(_spawn, "_wait_for_session_exit", return_value=True),
        patch.object(_spawn, "_tmux_kill", side_effect=killed.append),
    ):
        _spawn.cmd_stop(ns)

    # Only the launcher session should be killed (not the claude session).
    assert "claude_skills_worktree-sess" not in killed
    assert "kb-launcher-sess" in killed


def test_cmd_stop_timeout_path_force_kills_and_sets_forced_true(tmp_path, capsys):
    """Session does not exit within timeout — force kill and forced=true in output."""
    registry = {"sess": {"name": "sess", "tmux_session": "claude_skills_worktree-sess"}}
    _spawn._save_registry(tmp_path, "default", registry)

    ns = _make_stop_ns()
    killed: list[str] = []

    with (
        patch.object(_spawn, "_session_state_dir", return_value=tmp_path),
        patch.object(_spawn, "_tmux_alive", return_value=True),
        patch.object(_spawn, "_tmux_send_ctrlc"),
        patch.object(_spawn, "_wait_for_session_exit", return_value=False),
        patch.object(_spawn, "_tmux_kill", side_effect=killed.append),
    ):
        _spawn.cmd_stop(ns)

    assert "claude_skills_worktree-sess" in killed
    assert "kb-launcher-sess" in killed
    assert "sess" not in _spawn._load_registry(tmp_path, "default")

    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert result["forced"] is True
    assert result["status"] == "stopped"


def test_cmd_stop_already_dead_session_cleans_up_registry_without_force(tmp_path, capsys):
    """Session tmux is already gone — registry cleaned, already_dead=true reported."""
    registry = {"sess": {"name": "sess", "tmux_session": "claude_skills_worktree-sess"}}
    _spawn._save_registry(tmp_path, "default", registry)

    ns = _make_stop_ns()

    with (
        patch.object(_spawn, "_session_state_dir", return_value=tmp_path),
        # Session is already dead.
        patch.object(_spawn, "_tmux_alive", return_value=False),
        patch.object(_spawn, "_tmux_send_ctrlc") as mock_ctrlc,
        patch.object(_spawn, "_tmux_kill"),
    ):
        _spawn.cmd_stop(ns)

    mock_ctrlc.assert_not_called()
    assert "sess" not in _spawn._load_registry(tmp_path, "default")
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert result["already_dead"] is True
    assert result["forced"] is False


def test_cmd_stop_sends_ctrlc_to_correct_session(tmp_path):
    """Verify Ctrl-C is sent to the tmux session from the registry, not the launcher."""
    registry = {"sess": {"name": "sess", "tmux_session": "claude_skills_worktree-sess"}}
    _spawn._save_registry(tmp_path, "default", registry)

    ns = _make_stop_ns()
    ctrlc_targets: list[str] = []

    with (
        patch.object(_spawn, "_session_state_dir", return_value=tmp_path),
        patch.object(_spawn, "_tmux_alive", return_value=True),
        patch.object(_spawn, "_tmux_send_ctrlc", side_effect=ctrlc_targets.append),
        patch.object(_spawn, "_wait_for_session_exit", return_value=True),
        patch.object(_spawn, "_tmux_kill"),
    ):
        _spawn.cmd_stop(ns)

    assert ctrlc_targets == ["claude_skills_worktree-sess"]


def test_cmd_stop_exits_1_when_session_not_in_registry(tmp_path):
    ns = _make_stop_ns(name="ghost")
    with patch.object(_spawn, "_session_state_dir", return_value=tmp_path), pytest.raises(SystemExit) as exc_info:
        _spawn.cmd_stop(ns)
    assert exc_info.value.code == 1


def test_cmd_stop_kills_launcher_session_after_graceful_exit(tmp_path):
    """kb-launcher-{name} is killed after the session exits gracefully."""
    registry = {"myname": {"name": "myname", "tmux_session": "proj_worktree-myname"}}
    _spawn._save_registry(tmp_path, "default", registry)

    ns = _make_stop_ns(name="myname")
    killed: list[str] = []

    with (
        patch.object(_spawn, "_session_state_dir", return_value=tmp_path),
        patch.object(_spawn, "_tmux_alive", return_value=True),
        patch.object(_spawn, "_tmux_send_ctrlc"),
        patch.object(_spawn, "_wait_for_session_exit", return_value=True),
        patch.object(_spawn, "_tmux_kill", side_effect=killed.append),
    ):
        _spawn.cmd_stop(ns)

    assert "kb-launcher-myname" in killed


# ---------------------------------------------------------------------------
# Argument parser — stop subcommand
# ---------------------------------------------------------------------------


def test_build_parser_stop_requires_name():
    parser = _spawn._build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["stop"])


def test_build_parser_stop_with_name_sets_func():
    parser = _spawn._build_parser()
    args = parser.parse_args(["stop", "--name", "mysess"])
    assert args.name == "mysess"
    assert args.func is _spawn.cmd_stop


# ---------------------------------------------------------------------------
# --session-id argument and KB_SESSION_ID env var
# ---------------------------------------------------------------------------


def test_build_parser_session_id_defaults_to_none():
    """Parser leaves session_id as None; main() resolves the default."""
    parser = _spawn._build_parser()
    args = parser.parse_args(["list"])
    assert args.session_id is None


def test_build_parser_session_id_explicit_value():
    parser = _spawn._build_parser()
    args = parser.parse_args(["--session-id", "my-session", "list"])
    assert args.session_id == "my-session"


def test_main_resolves_session_id_to_default_for_non_list_subcommands(tmp_path):
    """When --session-id and KB_SESSION_ID are absent, main() sets 'default' for spawn etc."""
    dispatched: list[str] = []

    def fake_func(args: argparse.Namespace) -> None:
        dispatched.append(args.session_id)  # type: ignore[attr-defined]

    with patch.dict(os.environ, {}, clear=False), patch.object(_spawn, "_build_parser") as mock_bp:
        os.environ.pop("KB_SESSION_ID", None)
        fake_parser = MagicMock()
        fake_args = MagicMock()
        fake_args.session_id = None
        fake_args.command = "kill"
        fake_args.func = fake_func
        fake_parser.parse_args.return_value = fake_args
        mock_bp.return_value = fake_parser

        _spawn.main(["kill", "--name", "x"])

    assert dispatched == ["default"]


def test_main_resolves_session_id_from_env_var():
    """KB_SESSION_ID env var is used when --session-id is not supplied."""
    dispatched: list[str] = []

    def fake_func(args: argparse.Namespace) -> None:
        dispatched.append(args.session_id)  # type: ignore[attr-defined]

    with (
        patch.dict(os.environ, {"KB_SESSION_ID": "env-session"}, clear=False),
        patch.object(_spawn, "_build_parser") as mock_bp,
    ):
        fake_parser = MagicMock()
        fake_args = MagicMock()
        fake_args.session_id = None
        fake_args.command = "kill"
        fake_args.func = fake_func
        fake_parser.parse_args.return_value = fake_args
        mock_bp.return_value = fake_parser

        _spawn.main(["kill", "--name", "x"])

    assert dispatched == ["env-session"]


def test_main_explicit_session_id_overrides_env_var():
    """Explicit --session-id takes priority over KB_SESSION_ID."""
    dispatched: list[str] = []

    def fake_func(args: argparse.Namespace) -> None:
        dispatched.append(args.session_id)  # type: ignore[attr-defined]

    with (
        patch.dict(os.environ, {"KB_SESSION_ID": "env-session"}, clear=False),
        patch.object(_spawn, "_build_parser") as mock_bp,
    ):
        fake_parser = MagicMock()
        fake_args = MagicMock()
        fake_args.session_id = "explicit-session"
        fake_args.command = "kill"
        fake_args.func = fake_func
        fake_parser.parse_args.return_value = fake_args
        mock_bp.return_value = fake_parser

        _spawn.main(["--session-id", "explicit-session", "kill", "--name", "x"])

    # session_id was already set by the parser; main() should not override it.
    assert dispatched == ["explicit-session"]


def test_main_list_subcommand_leaves_session_id_none_when_not_supplied():
    """For 'list', main() leaves session_id as None so all registries are shown."""
    dispatched: list[str | None] = []

    def fake_func(args: argparse.Namespace) -> None:
        dispatched.append(args.session_id)  # type: ignore[attr-defined]

    with patch.dict(os.environ, {}, clear=False), patch.object(_spawn, "_build_parser") as mock_bp:
        os.environ.pop("KB_SESSION_ID", None)
        fake_parser = MagicMock()
        fake_args = MagicMock()
        fake_args.session_id = None
        fake_args.command = "list"
        fake_args.func = fake_func
        fake_parser.parse_args.return_value = fake_args
        mock_bp.return_value = fake_parser

        _spawn.main(["list"])

    assert dispatched == [None]
