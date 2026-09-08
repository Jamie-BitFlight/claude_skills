"""Tests for task_status_hook.py — the SubagentStop settle and the PostToolUse activity update.

Covers:
- extract_launch_from_prompt: the address AND the attempt come from the sub-agent's own prompt
- _call_sam_plan_settle: routes the settle through the SAM CLI subprocess
- handle_subagent_stop: settles the attempt and writes no status
- _call_sam_task_status: reads a status from either the ledger's or the content store's shape
- _call_sam_task_update: routes field writes through the SAM CLI subprocess
- read_task_context: reads the plan address directly from the "plan" field
- handle_activity_update: calls SAM CLI helpers instead of direct YAML writes
"""

from __future__ import annotations

import importlib.util
import inspect
import json
import os
import sys
from pathlib import Path
from subprocess import CompletedProcess, TimeoutExpired
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

# Ensure hook script is importable from repo root.
_plugin_dir = Path(__file__).parent.parent
if str(_plugin_dir) not in sys.path:
    sys.path.insert(0, str(_plugin_dir))

# sam_schema must be on sys.path
_repo_root = _plugin_dir.parent.parent
_sam_packages = str(_repo_root / "packages")
if _sam_packages not in sys.path:
    sys.path.insert(0, _sam_packages)

_hook_path = _plugin_dir / "skills" / "implementation-manager" / "scripts" / "task_status_hook.py"
_spec = importlib.util.spec_from_file_location("task_status_hook", _hook_path)
assert _spec is not None
assert _spec.loader is not None
_hook_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_hook_mod)  # type: ignore[union-attr]

# Re-export symbols for clarity
Launch = _hook_mod.Launch
_NO_FINAL_MESSAGE = _hook_mod._NO_FINAL_MESSAGE
_call_sam_plan_settle = _hook_mod._call_sam_plan_settle
_call_sam_task_status = _hook_mod._call_sam_task_status
_call_sam_task_update = _hook_mod._call_sam_task_update
extract_launch_from_prompt = _hook_mod.extract_launch_from_prompt
handle_subagent_stop = _hook_mod.handle_subagent_stop
handle_activity_update = _hook_mod.handle_activity_update
HookProfile = _hook_mod.HookProfile
_SAM_CLI_PATH = _hook_mod._SAM_CLI_PATH


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _cli_success_response(data: dict[str, Any]) -> CompletedProcess[str]:
    """Build a successful SAM CLI subprocess response — plain JSON stdout, no envelope."""
    return CompletedProcess(args=[], returncode=0, stdout=json.dumps(data), stderr="")


def _mcp_error_response(returncode: int = 1) -> CompletedProcess[str]:
    """Build a failed SAM CLI subprocess response."""
    return CompletedProcess(args=[], returncode=returncode, stdout="", stderr="error")


def _popen_from_completed(cp: CompletedProcess[str], pid: int = 4242) -> MagicMock:
    """Build a fake Popen instance whose communicate()/.returncode mirror a CompletedProcess.

    The implementation moves off subprocess.run onto subprocess.Popen + communicate() so it
    can redirect a timeout's kill to the whole process group. This adapts tests that already
    express expected results as CompletedProcess to that new contract.
    """
    proc = MagicMock()
    proc.communicate.return_value = (cp.stdout, cp.stderr)
    proc.returncode = cp.returncode
    proc.poll.return_value = cp.returncode
    proc.pid = pid
    proc.__enter__.return_value = proc
    proc.__exit__.return_value = False
    return proc


def _popen_timeout(timeout: float = 8, pid: int = 4242) -> MagicMock:
    """Build a fake Popen instance whose communicate() times out once, then reaps cleanly.

    A list side_effect (rather than a bare exception) tolerates an implementation that calls
    communicate() a second time after killing the process group to reap pipes/avoid warnings.
    """
    proc = MagicMock()
    proc.communicate.side_effect = [TimeoutExpired(cmd="uv", timeout=timeout), ("", "")]
    proc.pid = pid
    proc.__enter__.return_value = proc
    proc.__exit__.return_value = False
    return proc


def _argv_after(cmd: list[str], token: str) -> list[str]:
    """Return the tail of *cmd* starting at the first occurrence of *token*.

    Isolates the subcommand-and-options shape from the uv/script invocation
    prefix, which callers should not need to hardcode.
    """
    return cmd[cmd.index(token) :]


# ---------------------------------------------------------------------------
# _call_sam_task_update — success path
# ---------------------------------------------------------------------------


def test_call_sam_task_update_routes_through_mcp_subprocess() -> None:
    """_call_sam_task_update calls the SAM CLI with the mapped --last-activity option."""
    # Arrange
    plan_addr = "Pf4281187"
    task_id = "T2"
    fields = {"last-activity": "2026-05-14T18:00:00+00:00"}
    response = _cli_success_response({"updated": True, "address": f"{plan_addr}/{task_id}"})

    with (
        patch("shutil.which", return_value="/usr/bin/uv"),
        patch.object(Path, "exists", return_value=True),
        patch("subprocess.Popen", return_value=_popen_from_completed(response)) as mock_popen,
    ):
        # Act
        result = _call_sam_task_update(plan_addr, task_id, fields)

    # Assert
    assert result is True
    cmd = mock_popen.call_args[0][0]
    assert _argv_after(cmd, "plan") == [
        "plan",
        "update",
        "--plan-address",
        f"{plan_addr}/{task_id}",
        "--last-activity",
        fields["last-activity"],
    ]


def test_call_sam_task_update_last_activity_maps_to_cli_option() -> None:
    """_call_sam_task_update maps a 'last-activity' field to the --last-activity CLI option."""
    # Arrange
    timestamp = "2026-08-29T12:00:00+00:00"
    response = _cli_success_response({"updated": True, "address": "Pabc123/T1"})

    with (
        patch("shutil.which", return_value="/usr/bin/uv"),
        patch.object(Path, "exists", return_value=True),
        patch("subprocess.Popen", return_value=_popen_from_completed(response)) as mock_popen,
    ):
        # Act
        result = _call_sam_task_update("Pabc123", "T1", {"last-activity": timestamp})

    # Assert
    assert result is True
    cmd = mock_popen.call_args[0][0]
    assert ["--last-activity", timestamp] == cmd[cmd.index("--last-activity") : cmd.index("--last-activity") + 2]


def test_call_sam_task_update_returns_false_for_unmapped_field() -> None:
    """_call_sam_task_update returns False without calling subprocess for an unmapped field.

    Only 'completed' and 'last-activity' map to CLI options. Any other key
    (e.g. an arbitrary task field) is not a supported patch target for this
    helper — it must fail closed rather than silently drop the field or crash.
    """
    # Arrange
    with patch("subprocess.Popen") as mock_popen:
        # Act
        result = _call_sam_task_update("Pabc123", "T1", {"title": "New title"})

    # Assert
    assert result is False
    mock_popen.assert_not_called()


# ---------------------------------------------------------------------------
# _call_sam_task_update — failure paths
# ---------------------------------------------------------------------------


def test_call_sam_task_update_returns_false_when_uv_missing() -> None:
    """_call_sam_task_update returns False gracefully when uv is not on PATH."""
    # Arrange
    with patch("shutil.which", return_value=None):
        # Act
        result = _call_sam_task_update("Pabc123", "T1", {"last-activity": "ts"})

    # Assert
    assert result is False


def test_call_sam_task_update_returns_false_on_nonzero_returncode() -> None:
    """_call_sam_task_update returns False when subprocess exits with error code."""
    # Arrange
    with (
        patch("shutil.which", return_value="/usr/bin/uv"),
        patch.object(Path, "exists", return_value=True),
        patch("subprocess.Popen", return_value=_popen_from_completed(_mcp_error_response())),
    ):
        # Act
        result = _call_sam_task_update("Pabc123", "T1", {"last-activity": "ts"})

    # Assert
    assert result is False


def test_call_sam_task_update_returns_false_on_timeout() -> None:
    """_call_sam_task_update returns False when subprocess times out."""
    # Arrange
    with (
        patch("shutil.which", return_value="/usr/bin/uv"),
        patch.object(Path, "exists", return_value=True),
        patch("subprocess.Popen", return_value=_popen_timeout()),
        patch("os.getpgid", return_value=4242),
        patch("os.killpg"),
    ):
        # Act
        result = _call_sam_task_update("Pabc123", "T1", {"last-activity": "ts"})

    # Assert
    assert result is False


def test_call_sam_task_update_returns_false_on_malformed_json() -> None:
    """_call_sam_task_update returns False when subprocess stdout is not valid JSON."""
    # Arrange
    bad_response = CompletedProcess(args=[], returncode=0, stdout="not-json", stderr="")
    with (
        patch("shutil.which", return_value="/usr/bin/uv"),
        patch.object(Path, "exists", return_value=True),
        patch("subprocess.Popen", return_value=_popen_from_completed(bad_response)),
    ):
        # Act
        result = _call_sam_task_update("Pabc123", "T1", {"x": "y"})

    # Assert
    assert result is False


# ---------------------------------------------------------------------------
# handle_activity_update — SAM CLI call path
# ---------------------------------------------------------------------------


def test_handle_activity_update_calls_mcp_update(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """handle_activity_update calls _call_sam_task_update for last-activity field."""
    # Arrange — context file carries the plan address directly
    monkeypatch.setenv("DH_STATE_HOME", str(tmp_path / "dh_state"))
    import dh_paths

    context_dir = dh_paths.context_dir()
    context_dir.mkdir(parents=True, exist_ok=True)
    session_id = "sess-abc"
    context_file = context_dir / f"active-task-{session_id}.json"
    context_file.write_text(json.dumps({"plan": "Pf4281187", "task_id": "T1"}))

    hook_input = {"cwd": str(tmp_path), "session_id": session_id, "hook_event_name": "PostToolUse"}

    from sam_schema.core.models import TaskStatus

    with (
        patch.object(_hook_mod, "_call_sam_task_status", return_value=TaskStatus.IN_PROGRESS),
        patch.object(_hook_mod, "_call_sam_task_update", return_value=True) as mock_update,
    ):
        # Act
        handle_activity_update(hook_input)

    # Assert
    mock_update.assert_called_once()
    call_args = mock_update.call_args
    assert call_args[0][0] == "Pf4281187"  # plan_addr
    assert call_args[0][1] == "T1"  # task_id
    assert "last-activity" in call_args[0][2]  # set_fields has last-activity key


def test_handle_activity_update_skips_when_no_plan_addr(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """handle_activity_update exits silently when the context file has no plan address."""
    # Arrange — context file missing the "plan" field
    monkeypatch.setenv("DH_STATE_HOME", str(tmp_path / "dh_state"))
    import dh_paths

    context_dir = dh_paths.context_dir()
    context_dir.mkdir(parents=True, exist_ok=True)
    session_id = "sess-xyz"
    context_file = context_dir / f"active-task-{session_id}.json"
    context_file.write_text(json.dumps({"task_id": "T1"}))

    hook_input = {"cwd": str(tmp_path), "session_id": session_id, "hook_event_name": "PostToolUse"}

    with (
        patch.object(_hook_mod, "_call_sam_task_update", return_value=True) as mock_update,
        pytest.raises(SystemExit) as exc_info,
    ):
        # Act
        handle_activity_update(hook_input)

    # Assert — exited cleanly without calling the SAM CLI update
    assert exc_info.value.code == 0
    mock_update.assert_not_called()


def _write_transcript(tmp_path: Path, records: list[dict[str, Any]]) -> Path:
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    return transcript


def _assistant_record(text: str) -> dict[str, Any]:
    return {"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}


# ---------------------------------------------------------------------------
# handle_activity_update — stderr diagnostic when _call_sam_task_status returns None
# ---------------------------------------------------------------------------


def test_handle_activity_update_emits_stderr_when_mcp_read_returns_none(
    mocker: MockerFixture, capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """handle_activity_update prints a diagnostic to stderr when _call_sam_task_status returns None.

    Verifies the silent failure case is now visible: before this fix the hook fell
    through to the activity update without any indication the read had failed.
    """
    # Arrange — context file carries the plan address directly
    monkeypatch.setenv("DH_STATE_HOME", str(tmp_path / "dh_state"))
    import dh_paths

    context_dir = dh_paths.context_dir()
    context_dir.mkdir(parents=True, exist_ok=True)
    session_id = "sess-no-task"
    context_file = context_dir / f"active-task-{session_id}.json"
    context_file.write_text(json.dumps({"plan": "Pf4281187", "task_id": "T1"}))

    hook_input: dict[str, Any] = {"cwd": str(tmp_path), "session_id": session_id, "hook_event_name": "PostToolUse"}

    mocker.patch.object(_hook_mod, "_call_sam_task_status", create=True, return_value=None)
    mock_update = mocker.patch.object(_hook_mod, "_call_sam_task_update", return_value=True)

    # Act
    handle_activity_update(hook_input)

    # Assert — diagnostic visible on stderr
    captured = capsys.readouterr()
    assert "could not read task T1 from plan Pf4281187 via the SAM CLI" in captured.err
    assert "skipping" in captured.err

    # Assert — update still proceeds (best-effort activity tracking continues)
    mock_update.assert_called_once()


def test_call_sam_active_task_clear_passes_sam_active_task_target(mocker: MockerFixture) -> None:
    """_call_sam_active_task_clear calls the SAM CLI's ``active-task clear`` subcommand.

    A bug where the wrapper routes to the wrong subcommand would leave stale
    active-task context, causing the next SubagentStop to read a ghost task.
    """
    # Arrange — clear response; wrapper only checks stdout is not None
    clear_data = {"cleared": True}
    response = CompletedProcess(args=[], returncode=0, stdout=json.dumps(clear_data), stderr="")

    mocker.patch("shutil.which", return_value="/usr/bin/uv")
    mocker.patch.object(Path, "exists", return_value=True)
    mock_popen = mocker.patch("subprocess.Popen", return_value=_popen_from_completed(response))

    # Act
    _hook_mod._call_sam_active_task_clear("test-session-id")

    # Assert
    mock_popen.assert_called_once()
    cmd: list[str] = mock_popen.call_args[0][0]
    assert _argv_after(cmd, "active-task") == ["active-task", "clear", "--session-id", "test-session-id"]


# ---------------------------------------------------------------------------
# _cleanup_active_task_context suppresses FileNotFoundError only
# ---------------------------------------------------------------------------


def test_cleanup_active_task_context_propagates_permission_error(mocker: MockerFixture, tmp_path: Path) -> None:
    """_cleanup_active_task_context lets PermissionError propagate from fallback unlink.

    The old code used suppress(OSError), which swallowed PermissionError (an OSError
    subclass). The new code uses suppress(FileNotFoundError). PermissionError is NOT
    a FileNotFoundError, so it must propagate — a filesystem access problem is a real
    failure that must be observable, not silently discarded.
    """
    # Arrange — session_id=None forces the fallback filesystem path (skips the SAM CLI clear)
    fallback_file = tmp_path / "active-task-sess.json"
    fallback_file.write_text("{}")
    mocker.patch.object(Path, "unlink", side_effect=PermissionError("read-only filesystem"))

    # Act & Assert — PermissionError must propagate; suppress(FileNotFoundError) does not catch it
    with pytest.raises(PermissionError):
        _hook_mod._cleanup_active_task_context(session_id=None, fallback_context_file=fallback_file)


def test_cleanup_active_task_context_suppresses_file_not_found(mocker: MockerFixture, tmp_path: Path) -> None:
    """_cleanup_active_task_context silently ignores FileNotFoundError during fallback unlink.

    FileNotFoundError means the context file was already removed by a concurrent
    process — this is expected during parallel agent teardown and should not fail.
    """
    # Arrange — session_id=None forces the fallback filesystem path
    fallback_file = tmp_path / "active-task-sess.json"
    # File does not need to exist; suppress(FileNotFoundError) should absorb the error
    mocker.patch.object(Path, "unlink", side_effect=FileNotFoundError("already gone"))

    # Act — must not raise; FileNotFoundError is a legitimate concurrent-removal scenario
    _hook_mod._cleanup_active_task_context(session_id=None, fallback_context_file=fallback_file)


# ---------------------------------------------------------------------------
# read_task_context — local backend shape (both plan and task_file_path present)
# ---------------------------------------------------------------------------


def test_read_task_context_reads_plan_field_for_local_backend_shape(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """read_task_context reads the "plan" field even when a genuine task_file_path is also present.

    The local-YAML ContextBackend populates BOTH task_file_path (a real filesystem
    path) and plan (the address) in the same context file. This proves reading
    "plan" is correct for local sessions too, not just for memory/GitHub/beads
    where task_file_path is None.
    """
    monkeypatch.setenv("DH_STATE_HOME", str(tmp_path / "dh_state"))
    import dh_paths

    context_dir = dh_paths.context_dir()
    context_dir.mkdir(parents=True, exist_ok=True)
    session_id = "sess-local-backend"
    context_file = context_dir / f"active-task-{session_id}.json"
    context_file.write_text(
        json.dumps({"task_file_path": str(tmp_path / "plan" / "Pf4281187.yaml"), "plan": "Pf4281187", "task_id": "T1"})
    )

    plan_addr, task_id = _hook_mod.read_task_context(tmp_path, session_id)

    assert plan_addr == "Pf4281187"
    assert task_id == "T1"


# ---------------------------------------------------------------------------
# read_task_context logs to stderr on malformed JSON
# ---------------------------------------------------------------------------


def test_read_task_context_returns_none_tuple_and_logs_on_malformed_json(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """read_task_context returns (None, None) and emits a [hook]-prefixed stderr message on bad JSON.

    The contract (None, None) is unchanged from the pre-refactor behavior. The new
    observable behavior is the stderr log: callers need to know the context file is
    malformed so the failure is not invisible in production. The message must contain
    the file path so operators can locate and delete the corrupt file.
    """
    # Arrange — create a real malformed JSON file at the context path
    monkeypatch.setenv("DH_STATE_HOME", str(tmp_path / "dh_state"))
    import dh_paths  # dh_paths is a runtime import needed after env setup

    context_dir = dh_paths.context_dir()
    context_dir.mkdir(parents=True, exist_ok=True)
    session_id = "sess-bad-json"
    context_file = context_dir / f"active-task-{session_id}.json"
    context_file.write_text("{not valid json", encoding="utf-8")

    cwd = tmp_path

    # Act
    result = _hook_mod.read_task_context(cwd, session_id)

    # Assert — contract: returns (None, None)
    assert result == (None, None)

    # Assert — stderr contains [hook] prefix and the file path
    captured = capsys.readouterr()
    assert "[hook]" in captured.err
    assert str(context_file) in captured.err


def test_read_task_context_fails_loudly_on_legacy_record_missing_plan_field(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A pre-migration context record (task_file_path + task_id, no plan) returns (None, None)
    and logs a stderr diagnostic — it must not silently do nothing, and must not fall back to
    parsing the address out of task_file_path (that fallback was deliberately rejected; see #3151).
    """
    monkeypatch.setenv("DH_STATE_HOME", str(tmp_path / "dh_state"))
    import dh_paths

    context_dir = dh_paths.context_dir()
    context_dir.mkdir(parents=True, exist_ok=True)
    session_id = "sess-legacy-pre-migration"
    context_file = context_dir / f"active-task-{session_id}.json"
    context_file.write_text(json.dumps({"task_file_path": str(tmp_path / "plan" / "Pf4281187.yaml"), "task_id": "T1"}))

    result = _hook_mod.read_task_context(tmp_path, session_id)

    assert result == (None, None)

    captured = capsys.readouterr()
    assert "[hook]" in captured.err
    assert "legacy context record" in captured.err
    assert str(context_file) in captured.err


# ---------------------------------------------------------------------------
# Regression guard — no fastmcp invocation left in the hook source
# ---------------------------------------------------------------------------


def test_hook_source_contains_no_fastmcp_invocation() -> None:
    """task_status_hook.py's own source never mentions 'fastmcp'.

    All task-state writes/reads now route through direct SAM CLI subprocess
    calls (see _SAM_CLI_PATH). A reintroduced fastmcp invocation would bring
    back the orphaned-process defect (keep_alive=True) and the ~10s PostToolUse
    budget overrun this migration fixed.
    """
    source = _hook_path.read_text(encoding="utf-8")
    assert "fastmcp" not in source.lower()


# ---------------------------------------------------------------------------
# Timeout ordering and process-group cleanup
#
# Two compounding defects this section guards against:
#   1. Every _call_sam_cli-family timeout default (15s, or 10s for the
#      active-task helpers) is not safely below the outer 10s PostToolUse hook
#      deadline Claude Code itself enforces — the external SIGKILL can beat
#      subprocess's own internal timeout handling.
#   2. subprocess.run(timeout=...) only kills the immediate child (uv); a
#      descendant process uv forks (the real sam_schema/cli.py interpreter)
#      can be left running — the orphaned-process failure mode this whole
#      area of the codebase exists to prevent.
# ---------------------------------------------------------------------------


def test_timeout_defaults_are_below_outer_hook_deadline() -> None:
    """Every _call_sam_cli-family function's own timeout default must be < 10s.

    The outer PostToolUse hook deadline is a hard 10s SIGKILL of the whole
    hook process, enforced externally by Claude Code. An internal subprocess
    timeout default at or above that value can never fire before the outer
    kill does, so subprocess's own timeout/cleanup path never gets a chance
    to run — this is the exact defect already fixed once for the old
    fastmcp-call path, recurring here for the plain-CLI replacement.
    """
    funcs = [
        _hook_mod._call_sam_cli,
        _hook_mod._call_sam_plan_settle,
        _hook_mod._call_sam_task_update,
        _hook_mod._call_sam_task_status,
        _hook_mod._call_sam_active_task_clear,
    ]
    for func in funcs:
        default = inspect.signature(func).parameters["timeout"].default
        assert default < 10, f"{func.__name__} timeout default is {default!r}, must be < 10"


def test_call_sam_cli_delegates_timeout_cleanup_to_terminate_process_tree(mocker: MockerFixture) -> None:
    """On timeout, _call_sam_cli delegates process-tree cleanup to run_bounded.terminate_process_tree.

    Supersedes the hand-rolled os.killpg(os.getpgid(pid), SIGKILL) approach, which only
    works on POSIX (os.killpg does not exist on Windows) and always jumps straight to
    SIGKILL with no graceful-termination attempt. The repo already solves this — see
    scripts/run_bounded.py's terminate_process_tree, already used the same way by
    scripts/validate_codex_plugin_isolated.py.

    os.getpgid/os.killpg are stubbed here too because terminate_process_tree itself calls
    them for real — without the stub this test would SIGKILL a real process group on the
    test machine.
    """
    proc = _popen_timeout(pid=4242)

    mocker.patch("shutil.which", return_value="/usr/bin/uv")
    mocker.patch.object(Path, "exists", return_value=True)
    mocker.patch("subprocess.Popen", return_value=proc)
    mocker.patch("os.getpgid", return_value=4242)
    mocker.patch("os.killpg")
    mock_terminate = mocker.patch.object(_hook_mod, "terminate_process_tree", create=True)

    result = _hook_mod._call_sam_cli(["plan", "read", "--address", "P1/T1"])

    assert result is None
    mock_terminate.assert_called_once_with(proc)


def test_call_sam_cli_uses_posix_session_flag(mocker: MockerFixture) -> None:
    """_call_sam_cli launches its subprocess with start_new_session matching the platform.

    POSIX process groups are the prerequisite for terminate_process_tree's group-wide
    SIGTERM/SIGKILL escalation; Windows has no such concept and terminate_process_tree
    instead walks the OS process tree by PID via taskkill (see
    run_bounded.terminate_windows_process_tree). The assertion is written against
    os.name == "posix" rather than a hardcoded True so it stays correct off of POSIX too.
    """
    proc = _popen_from_completed(CompletedProcess(args=[], returncode=0, stdout="{}", stderr=""), pid=1234)

    mocker.patch("shutil.which", return_value="/usr/bin/uv")
    mocker.patch.object(Path, "exists", return_value=True)
    mock_popen = mocker.patch("subprocess.Popen", return_value=proc)

    _hook_mod._call_sam_cli(["plan", "read", "--address", "P1/T1"])

    mock_popen.assert_called_once()
    assert mock_popen.call_args.kwargs.get("start_new_session") == (os.name == "posix")


# ---------------------------------------------------------------------------
# handle_activity_update shares a single wall-clock deadline across its two
# sequential _call_sam_cli-backed calls
#
# _call_sam_task_status then _call_sam_task_update are each individually kept
# below the outer 10s PostToolUse hook deadline, but nothing stops their SUM
# from exceeding it: worst case ~8s + ~8s = ~16s, well past the 10s
# external SIGKILL Claude Code enforces on the whole hook process. The fix
# computes a shared remaining-budget deadline once (time.monotonic()) and
# passes the REMAINING time to each call, skipping the update call outright
# once the budget is exhausted rather than dispatching it with a doomed
# near-zero/negative timeout.
# ---------------------------------------------------------------------------


def _write_activity_update_context(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, session_id: str) -> dict[str, Any]:
    """Set up a plan file + context file for handle_activity_update and return its hook_input.

    Shared fixture setup for the two shared-deadline tests below — mirrors the setup
    already used by test_handle_activity_update_calls_mcp_update.
    """
    plan_file = tmp_path / "Pf4281187-feature.yaml"
    plan_file.write_text("tasks:\n- id: T1\n  status: in-progress\n  title: Test\n")

    monkeypatch.setenv("DH_STATE_HOME", str(tmp_path / "dh_state"))
    import dh_paths

    context_dir = dh_paths.context_dir()
    context_dir.mkdir(parents=True, exist_ok=True)
    context_file = context_dir / f"active-task-{session_id}.json"
    context_file.write_text(json.dumps({"task_file_path": str(plan_file), "plan": "Pf4281187", "task_id": "T1"}))

    return {"cwd": str(tmp_path), "session_id": session_id, "hook_event_name": "PostToolUse"}


def test_handle_activity_update_shares_deadline_between_read_and_update(
    mocker: MockerFixture, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The timeout passed to _call_sam_task_update reflects the budget remaining after the read call.

    time.monotonic() is mocked to a 3-value sequence: [deadline computed, right before the
    read call, right before the update call] = [0.0, 0.0, 6.0] — simulating the read call
    alone consuming 6 of the shared budget's seconds. The update call must NOT receive its
    own fresh ~8s default; it must receive whatever budget remains (< 8s).

    RED on current code: handle_activity_update calls _call_sam_task_update(plan_addr,
    task_id, set_fields) with no timeout= kwarg at all (it relies on the function's own
    8s default), so mock_update.call_args.kwargs.get("timeout") is None here.
    """
    session_id = "sess-budget-shared"
    hook_input = _write_activity_update_context(tmp_path, monkeypatch, session_id)

    from sam_schema.core.models import TaskStatus

    mocker.patch("time.monotonic", side_effect=[0.0, 0.0, 6.0])
    mocker.patch.object(_hook_mod, "_call_sam_task_status", return_value=TaskStatus.IN_PROGRESS)
    mock_update = mocker.patch.object(_hook_mod, "_call_sam_task_update", return_value=True)

    handle_activity_update(hook_input)

    mock_update.assert_called_once()
    passed_timeout = mock_update.call_args.kwargs.get("timeout")
    assert passed_timeout is not None, (
        "expected _call_sam_task_update to receive an explicit timeout= reflecting the "
        "remaining shared budget, not fall back to its own default"
    )
    assert 0 < passed_timeout < 8, f"expected a reduced remaining-budget timeout, got {passed_timeout!r}"


def test_handle_activity_update_skips_update_when_budget_exhausted(
    mocker: MockerFixture, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """_call_sam_task_update is skipped entirely once the shared budget is exhausted by the read call.

    time.monotonic() simulates the read call alone consuming the entire shared budget
    (remaining <= 0 by the time the update call would be dispatched). Rather than
    dispatching _call_sam_task_update with a doomed near-zero/negative timeout, the fix
    must skip it outright (logging to stderr) and return.

    RED on current code: handle_activity_update unconditionally calls
    _call_sam_task_update whenever the task isn't already COMPLETE — there is no budget
    check at all, so mock_update.assert_not_called() fails (it WAS called).
    """
    session_id = "sess-budget-exhausted"
    hook_input = _write_activity_update_context(tmp_path, monkeypatch, session_id)

    from sam_schema.core.models import TaskStatus

    mocker.patch("time.monotonic", side_effect=[0.0, 0.0, 8.5])
    mocker.patch.object(_hook_mod, "_call_sam_task_status", return_value=TaskStatus.IN_PROGRESS)
    mock_update = mocker.patch.object(_hook_mod, "_call_sam_task_update", return_value=True)

    handle_activity_update(hook_input)

    mock_update.assert_not_called()


def test_terminate_process_tree_resolves_from_inside_the_plugin_package() -> None:
    """terminate_process_tree must resolve from inside the plugin package, not repo-root scripts/.

    A marketplace install ships only plugins/development-harness — a sibling
    repo-root scripts/ import would silently break there. Assert the imported
    function's own source file lives inside the plugin directory.
    """
    source_file = Path(_hook_mod.terminate_process_tree.__code__.co_filename).resolve()
    assert _plugin_dir.resolve() in source_file.parents


# ---------------------------------------------------------------------------
# SubagentStop coverage — the hook must fire for any agent that claimed a task
# ---------------------------------------------------------------------------


def test_subagent_stop_hook_is_not_restricted_to_task_worker() -> None:
    """SubagentStop must not filter by agent name.

    execution/SKILL.md dispatches a named specialist whenever one matches the task and
    only falls back to dh:task-worker otherwise. A name-based matcher therefore decides
    task-state tracking by which specialist got picked, and a specialist's task is never
    marked at all. The hook gates on whether an active SAM task resolves, so it is safe
    to run for every sub-agent.
    """
    hooks_config = json.loads((_plugin_dir / "hooks" / "hooks.json").read_text(encoding="utf-8"))

    subagent_stop = hooks_config["hooks"]["SubagentStop"]
    assert subagent_stop, "SubagentStop must have at least one hook entry"

    for entry in subagent_stop:
        matcher = entry.get("matcher")
        assert matcher is None, (
            f"SubagentStop must not filter by agent name (found matcher={matcher!r}). "
            "Coverage must depend on whether a SAM task was claimed, not on the agent's name."
        )
        commands = [h.get("command", "") for h in entry.get("hooks", [])]
        assert any("task_status_hook.py" in c for c in commands), "SubagentStop must invoke task_status_hook.py"


# ---------------------------------------------------------------------------
# extract_launch_from_prompt — the address AND the attempt come from the prompt
#
# The attempt number is reachable nowhere else per sub-agent. The active-task record
# is keyed by the parent session's id and carries no attempt field, so a hook that
# read it could neither tell two parallel workers apart nor name the attempt a settle
# records against.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("label", "prompt"),
    [
        ("implement-feature dispatch", "Pdec8934d/T01, attempt 3"),
        ("dispatch skill prose", "Your ROLE_TYPE is sub-agent. You are working on Pdec8934d/T01, attempt 3."),
        ("no comma", "Pdec8934d/T01 attempt 3"),
        ("slash command", "/start-task Pdec8934d --task T01 --attempt 3"),
        ("Skill() wrapper", 'Skill(skill="start-task", args="Pdec8934d --task T01 --attempt 3")'),
    ],
)
def test_every_shipped_launch_shape_yields_address_and_attempt(label: str, prompt: str) -> None:
    """Each prompt shape the orchestrator skills write must yield plan, task AND attempt.

    implement-feature/SKILL.md launches with "{plan_ref}/{task_id}, attempt {attempt}" and
    dispatch/SKILL.md wraps the same address in a sentence. A matcher that only full-matched a
    bare "{plan}/{task}" saw neither, so no settle was possible for either.
    """
    launch = extract_launch_from_prompt(prompt)

    assert launch is not None, label
    assert launch.plan == "Pdec8934d"
    assert launch.task_id == "T01"
    assert launch.attempt == 3
    assert launch.address == "Pdec8934d/T01"
    assert launch.is_ledger_address


def test_bare_address_yields_no_attempt() -> None:
    """A bare address names the task but no attempt, so it cannot be settled."""
    launch = extract_launch_from_prompt("Pdec8934d/T01")

    assert launch is not None
    assert launch.attempt is None


def test_an_address_mentioned_in_passing_is_not_a_launch() -> None:
    """An address inside unrelated prose, with no attempt clause, does not name a launch.

    The attempt clause is what makes the in-prose search safe: without it the pattern would
    settle whatever address a sub-agent happened to mention.
    """
    assert extract_launch_from_prompt("The blocker was tracked under Pdec8934d/T01 last week.") is None


def test_a_file_path_plan_is_recognised_but_not_a_ledger_address() -> None:
    """A legacy file-path plan arg parses, and is reported as not settle-able."""
    launch = extract_launch_from_prompt('Skill(skill="start-task", args="plans/tasks-1-foo.yaml --task T2")')

    assert launch is not None
    assert launch.plan == "plans/tasks-1-foo.yaml"
    assert not launch.is_ledger_address


def test_extract_launch_from_prompt_empty_returns_none() -> None:
    """An empty prompt names no launch."""
    assert extract_launch_from_prompt("") is None


# ---------------------------------------------------------------------------
# _call_sam_plan_settle — the orchestrator's command, and the only write this hook makes
# ---------------------------------------------------------------------------


def test_settle_passes_address_attempt_and_return_text() -> None:
    """_call_sam_plan_settle builds `plan settle --address P/T --attempt N --return-text …`."""
    launch = Launch(plan="Pf4281187", task_id="T1", attempt=2)
    response = _cli_success_response({"command": "settle", "plan": "Pf4281187", "task": "T1", "attempt": 2})

    with (
        patch.object(_hook_mod, "_get_uv_executable", return_value="/usr/bin/uv"),
        patch("subprocess.Popen", return_value=_popen_from_completed(response)) as mock_popen,
    ):
        assert _call_sam_plan_settle(launch, "STATUS: DONE") is True

    argv = _argv_after(mock_popen.call_args[0][0], "plan")
    assert argv == ["plan", "settle", "--address", "Pf4281187/T1", "--attempt", "2", "--return-text", "STATUS: DONE"]


def test_settle_treats_already_settled_as_success() -> None:
    """`already-settled` is a no-op code on stdout with exit 0, not a failure.

    It is what the orchestrator's own settle leaves behind when it got there first, so the hook
    and the orchestrator never fight over one attempt.
    """
    response = CompletedProcess(args=[], returncode=0, stdout="already-settled\n", stderr="")

    with (
        patch.object(_hook_mod, "_get_uv_executable", return_value="/usr/bin/uv"),
        patch("subprocess.Popen", return_value=_popen_from_completed(response)),
    ):
        assert _call_sam_plan_settle(Launch(plan="Pf4281187", task_id="T1", attempt=2), "text") is True


def test_settle_failure_is_reported_not_absorbed(capsys: pytest.CaptureFixture[str]) -> None:
    """A settle that cannot land says so on stderr, naming the consequence.

    Silence here is the failure mode this hook exists to prevent: an unsettled attempt reads as
    a worker still at work and the loop waits on an agent that is gone.
    """
    with (
        patch.object(_hook_mod, "_get_uv_executable", return_value="/usr/bin/uv"),
        patch("subprocess.Popen", return_value=_popen_from_completed(_mcp_error_response())),
    ):
        assert _call_sam_plan_settle(Launch(plan="Pf4281187", task_id="T1", attempt=2), "text") is False

    assert "settle failed for Pf4281187/T1 attempt 2" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# handle_subagent_stop — settles, and writes no status
# ---------------------------------------------------------------------------


def _launch_transcript(tmp_path: Path, prompt: str, session_id: str = "sess-1") -> Path:
    """Write a transcript in the JSONL shape the hook parses, carrying *prompt* as the first turn."""
    records: list[dict[str, Any]] = [
        {"type": "user", "sessionId": session_id, "message": {"content": [{"type": "text", "text": prompt}]}},
        {
            "type": "assistant",
            "sessionId": session_id,
            "message": {"content": [{"type": "text", "text": "STATUS: DONE"}]},
        },
    ]
    transcript = tmp_path / f"{session_id}.jsonl"
    transcript.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    return transcript


def test_subagent_stop_settles_the_attempt_the_prompt_names(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The stop settles P/T at the attempt its own prompt named, with the final message as evidence."""
    monkeypatch.setenv("DH_STATE_HOME", str(tmp_path / "dh_state"))
    transcript = _launch_transcript(tmp_path, "Pf4281187/T1, attempt 2")
    hook_input = {
        "hook_event_name": "SubagentStop",
        "agent_transcript_path": str(transcript),
        "last_assistant_message": "STATUS: DONE\nall criteria met",
    }

    with (
        patch.object(_hook_mod, "_call_sam_plan_settle", return_value=True) as mock_settle,
        patch.object(_hook_mod, "_cleanup_active_task_context") as mock_cleanup,
    ):
        handle_subagent_stop(hook_input)

    settled_launch, return_text = mock_settle.call_args[0]
    assert settled_launch.address == "Pf4281187/T1"
    assert settled_launch.attempt == 2
    assert return_text == "STATUS: DONE\nall criteria met"
    mock_cleanup.assert_called_once()


def test_subagent_stop_writes_no_status(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """No `plan state` and no `plan update` reaches the CLI on a stop — settle is the only write.

    Status has two writers already: the runner's `finish` records the outcome and the judge's
    `accept`/`reclaim` records the verdict. A third writer here would be a second encoding of the
    same fact, and the runner contract guarantees it would disagree — a worker returns
    "STATUS: DONE" once `finish` was recorded, whatever its `--result`.
    """
    monkeypatch.setenv("DH_STATE_HOME", str(tmp_path / "dh_state"))
    transcript = _launch_transcript(tmp_path, "Pf4281187/T1, attempt 2")
    hook_input = {
        "hook_event_name": "SubagentStop",
        "agent_transcript_path": str(transcript),
        "last_assistant_message": "STATUS: DONE\nfinish was recorded with --result failed",
    }

    with (
        patch.object(_hook_mod, "_get_uv_executable", return_value="/usr/bin/uv"),
        patch.object(_hook_mod, "_cleanup_active_task_context"),
        patch(
            "subprocess.Popen", return_value=_popen_from_completed(_cli_success_response({"command": "settle"}))
        ) as mock_popen,
    ):
        handle_subagent_stop(hook_input)

    subcommands = [_argv_after(call[0][0], "plan")[:2] for call in mock_popen.call_args_list]
    assert subcommands == [["plan", "settle"]], subcommands


def test_subagent_stop_settles_a_launch_that_returned_nothing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A launch that produced no final message is still settled, with a marker as return text.

    The work loop settles "including when the response is empty or the agent crashed" — that a
    launch ended is exactly the fact a crashed runner cannot report for itself.
    """
    monkeypatch.setenv("DH_STATE_HOME", str(tmp_path / "dh_state"))
    transcript = tmp_path / "sess-crash.jsonl"
    transcript.write_text(
        json.dumps({
            "type": "user",
            "sessionId": "sess-crash",
            "message": {"content": [{"type": "text", "text": "Pf4281187/T1, attempt 1"}]},
        })
        + "\n",
        encoding="utf-8",
    )
    hook_input = {"hook_event_name": "SubagentStop", "agent_transcript_path": str(transcript)}

    with (
        patch.object(_hook_mod, "_call_sam_plan_settle", return_value=True) as mock_settle,
        patch.object(_hook_mod, "_cleanup_active_task_context"),
    ):
        handle_subagent_stop(hook_input)

    assert mock_settle.call_args[0][1] == _NO_FINAL_MESSAGE


def test_subagent_stop_says_why_it_could_not_settle_without_an_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A launch whose prompt named no attempt is reported on stderr, never absorbed."""
    monkeypatch.setenv("DH_STATE_HOME", str(tmp_path / "dh_state"))
    transcript = _launch_transcript(tmp_path, "Pf4281187/T1")
    hook_input = {"hook_event_name": "SubagentStop", "agent_transcript_path": str(transcript)}

    with (
        patch.object(_hook_mod, "_call_sam_plan_settle") as mock_settle,
        patch.object(_hook_mod, "_cleanup_active_task_context"),
    ):
        handle_subagent_stop(hook_input)

    mock_settle.assert_not_called()
    assert "without an attempt number in its prompt" in capsys.readouterr().err


def test_subagent_stop_stays_quiet_for_an_unrelated_sub_agent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A sub-agent of another plugin reaches this hook too, and must cost it no subprocess.

    hooks.json registers SubagentStop with no matcher, so every stopping sub-agent in the session
    arrives here. Whether it is a dispatched worker is decided by whether its prompt names a
    launch, not by its agent name.
    """
    monkeypatch.setenv("DH_STATE_HOME", str(tmp_path / "dh_state"))
    transcript = _launch_transcript(tmp_path, "Please review the README for typos.")
    hook_input = {
        "hook_event_name": "SubagentStop",
        "agent_transcript_path": str(transcript),
        "last_assistant_message": "STATUS: VERIFIED",
    }

    with patch("subprocess.Popen") as mock_popen, patch.object(_hook_mod, "_cleanup_active_task_context"):
        handle_subagent_stop(hook_input)

    mock_popen.assert_not_called()


def test_subagent_stop_without_a_transcript_path_reports_it(capsys: pytest.CaptureFixture[str]) -> None:
    """With no agent_transcript_path there is no correlation at all, and the hook says so."""
    handle_subagent_stop({"hook_event_name": "SubagentStop"})

    assert "no agent_transcript_path" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# _call_sam_task_status — the ledger and the content store answer in different shapes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("label", "payload"),
    [
        # The ledger returns the row under "row" and the task *id* — a bare string — under "task".
        ("ledger", {"command": "read", "task": "T1", "row": {"id": "T1", "status": "in-progress"}}),
        ("content store", {"task": {"id": "T1", "status": "in-progress"}}),
    ],
)
def test_task_status_is_read_from_either_response_shape(label: str, payload: dict[str, Any]) -> None:
    """Both `plan read` response shapes yield the status.

    Reading `task` alone returned the string "T1" on a ledger plan, which validated as no task at
    all — so every ledger-backed read reported failure and the caller skipped its work.
    """
    with (
        patch.object(_hook_mod, "_get_uv_executable", return_value="/usr/bin/uv"),
        patch("subprocess.Popen", return_value=_popen_from_completed(_cli_success_response(payload))),
    ):
        status = _call_sam_task_status("Pf4281187", "T1")

    from sam_schema.core.models import TaskStatus

    assert status == TaskStatus.IN_PROGRESS, label


def test_task_status_returns_none_on_subprocess_failure() -> None:
    """A failed CLI call yields None rather than a guessed status."""
    with (
        patch.object(_hook_mod, "_get_uv_executable", return_value="/usr/bin/uv"),
        patch("subprocess.Popen", return_value=_popen_from_completed(_mcp_error_response())),
    ):
        assert _call_sam_task_status("Pf4281187", "T1") is None


# ---------------------------------------------------------------------------
# Regression guard — the hook makes no status write of its own
# ---------------------------------------------------------------------------


def test_hook_source_issues_no_plan_state_command() -> None:
    """task_status_hook.py's own source never builds a `plan state` invocation.

    `plan state` is the runner-less status move, and this hook always runs behind a runner the
    orchestrator dispatched. Reintroducing it would reinstate two writers of one fact — and on a
    ledger plan it would also fail outright, because `state` requires `--reason`.
    """
    source = _hook_path.read_text(encoding="utf-8")

    assert '"state"' not in source, "the hook must not issue `plan state`"
    assert '"--new-status"' not in source, "the hook must not set a task status"
