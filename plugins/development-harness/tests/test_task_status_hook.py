"""Tests for task_status_hook.py — SAM CLI write helpers and hook handlers.

Covers:
- _call_sam_task_state: routes state writes through the SAM CLI subprocess
- _call_sam_task_update: routes field writes through the SAM CLI subprocess
- Both helpers fall back gracefully (return False) on subprocess failure
- read_task_context / _call_sam_active_task_get / _read_context_file: read the plan
  address directly from the "plan" field (no path-parsing indirection)
- handle_subagent_stop: calls SAM CLI helpers instead of direct YAML writes
- handle_activity_update: calls SAM CLI helpers instead of direct YAML writes
"""

from __future__ import annotations

import importlib.util
import inspect
import json
import os
import sys
from pathlib import Path
from subprocess import CompletedProcess, SubprocessError, TimeoutExpired
from typing import TYPE_CHECKING, Any
from unittest.mock import ANY, MagicMock, patch

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
_call_sam_task_state = _hook_mod._call_sam_task_state
_call_sam_task_update = _hook_mod._call_sam_task_update
extract_task_info_from_prompt = _hook_mod.extract_task_info_from_prompt
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
# extract_task_info_from_prompt — plan address form
# ---------------------------------------------------------------------------


def test_extract_task_info_from_prompt_plan_address_skill_invocation(tmp_path: Path) -> None:
    """Skill(skill='start-task', args='Pdec8934d --task T01') resolves plan address to real path."""
    # Arrange
    resolved = tmp_path / "Pdec8934d-my-feature.yaml"
    resolved.touch()
    prompt = """Fix a confirmed code bug.

Skill(skill="start-task", args="Pdec8934d --task T01")

Working directory: /home/user/claude_skills"""

    # Act
    with patch.object(_hook_mod, "resolve_plan_address", return_value=resolved) as mock_resolve:
        task_file, task_id = extract_task_info_from_prompt(prompt)

    # Assert
    assert task_id == "T01"
    assert task_file == resolved
    mock_resolve.assert_called_once_with("Pdec8934d", ANY)


def test_extract_task_info_from_prompt_plan_address_different_task(tmp_path: Path) -> None:
    """Skill(skill='start-task', args='Pdec8934d --task T22') resolves plan address."""
    # Arrange
    resolved = tmp_path / "Pdec8934d-my-feature.yaml"
    resolved.touch()
    prompt = "Skill(skill='start-task', args='Pdec8934d --task T22')"

    # Act
    with patch.object(_hook_mod, "resolve_plan_address", return_value=resolved) as mock_resolve:
        task_file, task_id = extract_task_info_from_prompt(prompt)

    # Assert
    assert task_id == "T22"
    assert task_file == resolved
    mock_resolve.assert_called_once_with("Pdec8934d", ANY)


def test_extract_task_info_from_prompt_slash_command_plan_address(tmp_path: Path) -> None:
    """/start-task Pdec8934d --task T01 (literal slash-command form with plan address)."""
    # Arrange
    resolved = tmp_path / "Pdec8934d-my-feature.yaml"
    resolved.touch()
    prompt = "Run /start-task Pdec8934d --task T01 in the working directory."

    # Act
    with patch.object(_hook_mod, "resolve_plan_address", return_value=resolved) as mock_resolve:
        task_file, task_id = extract_task_info_from_prompt(prompt)

    # Assert
    assert task_id == "T01"
    assert task_file == resolved
    mock_resolve.assert_called_once_with("Pdec8934d", ANY)


def test_extract_task_info_from_prompt_plan_address_longer_hex(tmp_path: Path) -> None:
    """Plan address with longer hex ID is resolved to real path."""
    # Arrange
    resolved = tmp_path / "Pf4281187abcd-slug.yaml"
    resolved.touch()
    prompt = 'Skill(skill="start-task", args="Pf4281187abcd --task T05")'

    # Act
    with patch.object(_hook_mod, "resolve_plan_address", return_value=resolved) as mock_resolve:
        task_file, task_id = extract_task_info_from_prompt(prompt)

    # Assert
    assert task_id == "T05"
    assert task_file == resolved
    mock_resolve.assert_called_once_with("Pf4281187abcd", ANY)


def test_extract_task_info_from_prompt_plan_address_not_found() -> None:
    """When plan address cannot be resolved, (None, None) is returned."""
    from sam_schema.core.addressing import AddressingError

    prompt = 'Skill(skill="start-task", args="Pdead0000 --task T01")'

    with patch.object(_hook_mod, "resolve_plan_address", side_effect=AddressingError("Pdead0000", Path("/plan"))):
        task_file, task_id = extract_task_info_from_prompt(prompt)

    assert task_file is None
    assert task_id is None


# ---------------------------------------------------------------------------
# extract_task_info_from_prompt — bare address form (implement-feature dispatch)
# ---------------------------------------------------------------------------
# implement-feature/SKILL.md dispatches dh:task-worker with the task reference as its
# ENTIRE prompt, in the bare form "{plan_ref}/{task_id}" — no /start-task prefix, no
# Skill() wrapper.


def test_extract_task_info_from_prompt_bare_address_form(tmp_path: Path) -> None:
    """Bare "{plan_ref}/{task_id}" prompt (implement-feature's dispatch form) resolves."""
    # Arrange
    resolved = tmp_path / "Pdec8934d-my-feature.yaml"
    resolved.touch()
    prompt = "Pdec8934d/T01"

    # Act
    with patch.object(_hook_mod, "resolve_plan_address", return_value=resolved) as mock_resolve:
        task_file, task_id = extract_task_info_from_prompt(prompt)

    # Assert
    assert task_id == "T01"
    assert task_file == resolved
    mock_resolve.assert_called_once_with("Pdec8934d", ANY)


def test_extract_task_info_from_prompt_bare_address_form_strips_whitespace(tmp_path: Path) -> None:
    """Leading/trailing whitespace around the bare address form is tolerated."""
    # Arrange
    resolved = tmp_path / "Pdec8934d-my-feature.yaml"
    resolved.touch()
    prompt = "  Pdec8934d/T01\n"

    # Act
    with patch.object(_hook_mod, "resolve_plan_address", return_value=resolved):
        task_file, task_id = extract_task_info_from_prompt(prompt)

    # Assert
    assert task_id == "T01"
    assert task_file == resolved


def test_extract_task_info_from_prompt_bare_address_form_embedded_not_matched() -> None:
    """A plan/task address embedded in a longer prompt is NOT treated as the bare form."""
    # Arrange
    prompt = "Please review Pdec8934d/T01 as part of code review."

    # Act
    task_file, task_id = extract_task_info_from_prompt(prompt)

    # Assert
    assert task_file is None
    assert task_id is None


# ---------------------------------------------------------------------------
# extract_task_info_from_prompt — file path form (regression tests)
# ---------------------------------------------------------------------------


def test_extract_task_info_from_prompt_file_path_md_skill_invocation() -> None:
    """File path (.md) in Skill() args still parses correctly (regression)."""
    # Arrange
    prompt = 'Skill(skill="start-task", args="plan/Pf4281187-feature.md --task T1")'

    # Act
    task_file, task_id = extract_task_info_from_prompt(prompt)

    # Assert
    assert task_id == "T1"
    assert task_file is not None
    assert str(task_file) == "plan/Pf4281187-feature.md"


def test_extract_task_info_from_prompt_file_path_yaml_skill_invocation() -> None:
    """File path (.yaml) in Skill() args still parses correctly (regression)."""
    # Arrange
    prompt = 'Skill(skill="start-task", args="plan/Pf4281187-feature.yaml --task T2")'

    # Act
    task_file, task_id = extract_task_info_from_prompt(prompt)

    # Assert
    assert task_id == "T2"
    assert task_file is not None
    assert str(task_file) == "plan/Pf4281187-feature.yaml"


def test_extract_task_info_from_prompt_slash_command_file_path() -> None:
    """/start-task with .md file path parses correctly (regression)."""
    # Arrange
    prompt = "/start-task plan/Pf4281187-feature.md --task T3"

    # Act
    task_file, task_id = extract_task_info_from_prompt(prompt)

    # Assert
    assert task_id == "T3"
    assert task_file is not None
    assert str(task_file) == "plan/Pf4281187-feature.md"


def test_extract_task_info_from_prompt_returns_none_when_no_match() -> None:
    """A prompt with no start-task invocation returns (None, None)."""
    # Arrange
    prompt = "This is a generic task description with no skill invocation."

    # Act
    task_file, task_id = extract_task_info_from_prompt(prompt)

    # Assert
    assert task_file is None
    assert task_id is None


def test_extract_task_info_from_prompt_empty_returns_none() -> None:
    """An empty prompt returns (None, None)."""
    # Act
    task_file, task_id = extract_task_info_from_prompt("")

    # Assert
    assert task_file is None
    assert task_id is None


# ---------------------------------------------------------------------------
# _call_sam_task_state — success path
# ---------------------------------------------------------------------------


def test_call_sam_task_state_routes_through_mcp_subprocess(tmp_path: Path) -> None:
    """_call_sam_task_state calls the SAM CLI with the correct argv shape."""
    # Arrange
    plan_addr = "Pf4281187"
    task_id = "T1"
    status = "complete"
    response = _cli_success_response({"id": task_id, "status": status})

    with (
        patch("shutil.which", return_value="/usr/bin/uv"),
        patch.object(Path, "exists", return_value=True),
        patch("subprocess.Popen", return_value=_popen_from_completed(response)) as mock_popen,
    ):
        # Act
        result = _call_sam_task_state(plan_addr, task_id, status)

    # Assert
    assert result is True
    mock_popen.assert_called_once()
    cmd = mock_popen.call_args[0][0]
    assert _argv_after(cmd, "plan") == ["plan", "state", "--address", f"{plan_addr}/{task_id}", "--new-status", status]


# ---------------------------------------------------------------------------
# _call_sam_task_state — failure paths
# ---------------------------------------------------------------------------


def test_call_sam_task_state_returns_false_when_uv_missing() -> None:
    """_call_sam_task_state returns False gracefully when uv is not on PATH."""
    # Arrange
    with patch("shutil.which", return_value=None):
        # Act
        result = _call_sam_task_state("Pabc123", "T1", "complete")

    # Assert
    assert result is False


def test_call_sam_task_state_returns_false_when_server_script_missing() -> None:
    """_call_sam_task_state returns False when the SAM server script does not exist."""
    # Arrange
    with patch("shutil.which", return_value="/usr/bin/uv"), patch.object(Path, "exists", return_value=False):
        # Act
        result = _call_sam_task_state("Pabc123", "T1", "complete")

    # Assert
    assert result is False


def test_call_sam_task_state_returns_false_on_nonzero_returncode() -> None:
    """_call_sam_task_state returns False when subprocess exits with error code."""
    # Arrange
    with (
        patch("shutil.which", return_value="/usr/bin/uv"),
        patch.object(Path, "exists", return_value=True),
        patch("subprocess.Popen", return_value=_popen_from_completed(_mcp_error_response())),
    ):
        # Act
        result = _call_sam_task_state("Pabc123", "T1", "complete")

    # Assert
    assert result is False


def test_call_sam_task_state_returns_false_on_timeout() -> None:
    """_call_sam_task_state returns False when subprocess times out."""
    # Arrange
    with (
        patch("shutil.which", return_value="/usr/bin/uv"),
        patch.object(Path, "exists", return_value=True),
        patch("subprocess.Popen", return_value=_popen_timeout()),
        patch("os.getpgid", return_value=4242),
        patch("os.killpg"),
    ):
        # Act
        result = _call_sam_task_state("Pabc123", "T1", "complete")

    # Assert
    assert result is False


def test_call_sam_task_state_returns_false_on_subprocess_error() -> None:
    """_call_sam_task_state returns False on a general subprocess error."""
    # Arrange
    with (
        patch("shutil.which", return_value="/usr/bin/uv"),
        patch.object(Path, "exists", return_value=True),
        patch("subprocess.Popen", side_effect=SubprocessError("broken pipe")),
    ):
        # Act
        result = _call_sam_task_state("Pabc123", "T1", "complete")

    # Assert
    assert result is False


def test_call_sam_task_state_returns_false_on_malformed_json_response() -> None:
    """_call_sam_task_state returns False when subprocess stdout is not valid JSON."""
    # Arrange
    bad_response = CompletedProcess(args=[], returncode=0, stdout="not json", stderr="")
    with (
        patch("shutil.which", return_value="/usr/bin/uv"),
        patch.object(Path, "exists", return_value=True),
        patch("subprocess.Popen", return_value=_popen_from_completed(bad_response)),
    ):
        # Act
        result = _call_sam_task_state("Pabc123", "T1", "complete")

    # Assert
    assert result is False


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


def test_call_sam_task_update_completed_maps_to_cli_option() -> None:
    """_call_sam_task_update maps a 'completed' field to the --completed CLI option."""
    # Arrange
    timestamp = "2026-08-29T12:00:00+00:00"
    response = _cli_success_response({"updated": True, "address": "Pabc123/T1"})

    with (
        patch("shutil.which", return_value="/usr/bin/uv"),
        patch.object(Path, "exists", return_value=True),
        patch("subprocess.Popen", return_value=_popen_from_completed(response)) as mock_popen,
    ):
        # Act
        result = _call_sam_task_update("Pabc123", "T1", {"completed": timestamp})

    # Assert
    assert result is True
    cmd = mock_popen.call_args[0][0]
    assert ["--completed", timestamp] == cmd[cmd.index("--completed") : cmd.index("--completed") + 2]


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

    from sam_schema.core.models import Task, TaskStatus

    mock_task = MagicMock(spec=Task)
    mock_task.status = TaskStatus.IN_PROGRESS

    with (
        patch.object(_hook_mod, "_call_sam_task_read", return_value=mock_task, create=True),
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


# ---------------------------------------------------------------------------
# handle_subagent_stop — SAM CLI write path
# ---------------------------------------------------------------------------


def test_handle_subagent_stop_calls_state_and_update(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """handle_subagent_stop calls sam_task state=complete then update with timestamp."""
    # Arrange — plan_id is a str plan address (post-refactor shape)
    plan_id = "Pf4281187"

    from sam_schema.core.models import Task, TaskStatus

    mock_task = MagicMock(spec=Task)
    mock_task.status = TaskStatus.IN_PROGRESS

    hook_input: dict[str, Any] = {"cwd": str(tmp_path), "hook_event_name": "SubagentStop", "agent_transcript_path": ""}

    with (
        patch.object(_hook_mod, "_resolve_active_task_context", return_value=(None, plan_id, "T1", None, None)),
        patch.object(_hook_mod, "_call_sam_task_read", return_value=mock_task, create=True),
        patch.object(_hook_mod, "_extract_status_from_transcript", return_value=("DONE", "STATUS: DONE\n")),
        patch.object(_hook_mod, "_call_sam_task_state", return_value=True) as mock_state,
        patch.object(_hook_mod, "_call_sam_task_update", return_value=True) as mock_update,
        patch.object(_hook_mod, "_cleanup_active_task_context"),
    ):
        # Act
        handle_subagent_stop(hook_input)

    # Assert
    mock_state.assert_called_once_with("Pf4281187", "T1", "complete")
    mock_update.assert_called_once()
    update_args = mock_update.call_args[0]
    assert update_args[0] == "Pf4281187"
    assert update_args[1] == "T1"
    assert "completed" in update_args[2]


def test_handle_subagent_stop_exits_cleanly_when_state_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """handle_subagent_stop exits 0 (not 2) when the SAM CLI state call fails."""
    # Arrange — plan_id is a str plan address (post-refactor shape)
    plan_id = "Pf4281187"

    from sam_schema.core.models import Task, TaskStatus

    mock_task = MagicMock(spec=Task)
    mock_task.status = TaskStatus.IN_PROGRESS

    hook_input: dict[str, Any] = {"cwd": str(tmp_path), "hook_event_name": "SubagentStop", "agent_transcript_path": ""}

    with (
        patch.object(_hook_mod, "_resolve_active_task_context", return_value=(None, plan_id, "T1", None, None)),
        patch.object(_hook_mod, "_call_sam_task_read", return_value=mock_task, create=True),
        patch.object(_hook_mod, "_extract_status_from_transcript", return_value=("DONE", "STATUS: DONE\n")),
        patch.object(_hook_mod, "_call_sam_task_state", return_value=False),
        patch.object(_hook_mod, "_call_sam_task_update") as mock_update,
        patch.object(_hook_mod, "_cleanup_active_task_context"),
        pytest.raises(SystemExit) as exc_info,
    ):
        # Act
        handle_subagent_stop(hook_input)

    # Assert — exit 0, not 2 (best-effort, not fatal)
    assert exc_info.value.code == 0
    # Update should not be called if state failed
    mock_update.assert_not_called()


# ---------------------------------------------------------------------------
# handle_subagent_stop — status-gated completion
#
# Only a recognized complete token reaches COMPLETE; everything else —
# including no signal at all — becomes BLOCKED.
# ---------------------------------------------------------------------------


def _in_progress_task() -> MagicMock:
    from sam_schema.core.models import Task, TaskStatus

    mock_task = MagicMock(spec=Task)
    mock_task.status = TaskStatus.IN_PROGRESS
    return mock_task


@pytest.mark.parametrize("status_text", ["STATUS: PARTIAL\n3 of 5 criteria done.", "STATUS: BLOCKED\nmissing creds."])
def test_handle_subagent_stop_marks_blocked_on_non_complete_status(status_text: str, tmp_path: Path) -> None:
    """A worker reporting PARTIAL or BLOCKED must not be marked COMPLETE."""
    plan_id = "Pf4281187"
    hook_input: dict[str, Any] = {"cwd": str(tmp_path), "hook_event_name": "SubagentStop", "agent_transcript_path": ""}
    token = status_text.split()[1].rstrip(".,;:")

    with (
        patch.object(_hook_mod, "_resolve_active_task_context", return_value=(None, plan_id, "T1", None, None)),
        patch.object(_hook_mod, "_call_sam_task_read", return_value=_in_progress_task(), create=True),
        patch.object(_hook_mod, "_extract_status_from_transcript", return_value=(token, status_text)),
        patch.object(_hook_mod, "_call_sam_task_state", return_value=True) as mock_state,
        patch.object(_hook_mod, "_call_sam_task_update") as mock_update,
        patch.object(_hook_mod, "_cleanup_active_task_context"),
        pytest.raises(SystemExit) as exc_info,
    ):
        handle_subagent_stop(hook_input)

    assert exc_info.value.code == 0
    mock_state.assert_called_once_with(plan_id, "T1", _hook_mod.SamTaskStatus.BLOCKED)
    mock_update.assert_not_called()


@pytest.mark.parametrize("status_token", ["PARTIAL", "BLOCKED"])
def test_handle_subagent_stop_reverts_self_marked_complete_on_non_complete_status(
    status_token: str, tmp_path: Path
) -> None:
    """A worker that marks itself COMPLETE then reports PARTIAL/BLOCKED is reverted to blocked.

    start-task marks the task complete via the SAM CLI before the worker stops, so the
    task already reads COMPLETE by the time this hook runs. The worker's report, not the
    state it wrote about itself, decides the outcome.
    """
    from sam_schema.core.models import Task, TaskStatus

    plan_id = "Pf4281187"
    self_marked = MagicMock(spec=Task)
    self_marked.status = TaskStatus.COMPLETE

    hook_input: dict[str, Any] = {"cwd": str(tmp_path), "hook_event_name": "SubagentStop", "agent_transcript_path": ""}

    with (
        patch.object(_hook_mod, "_resolve_active_task_context", return_value=(None, plan_id, "T1", None, None)),
        patch.object(_hook_mod, "_call_sam_task_read", return_value=self_marked, create=True),
        patch.object(
            _hook_mod,
            "_extract_status_from_transcript",
            return_value=(status_token, f"STATUS: {status_token}\n2 of 5 criteria met."),
        ),
        patch.object(_hook_mod, "_call_sam_task_state", return_value=True) as mock_state,
        patch.object(_hook_mod, "_call_sam_task_update") as mock_update,
        patch.object(_hook_mod, "_cleanup_active_task_context"),
        pytest.raises(SystemExit) as exc_info,
    ):
        handle_subagent_stop(hook_input)

    assert exc_info.value.code == 0
    mock_state.assert_called_once_with(plan_id, "T1", _hook_mod.SamTaskStatus.BLOCKED)
    mock_update.assert_not_called()


def test_handle_subagent_stop_leaves_self_marked_complete_alone_on_done(tmp_path: Path) -> None:
    """A worker that marks itself COMPLETE and reports DONE needs no further write."""
    from sam_schema.core.models import Task, TaskStatus

    plan_id = "Pf4281187"
    self_marked = MagicMock(spec=Task)
    self_marked.status = TaskStatus.COMPLETE

    hook_input: dict[str, Any] = {"cwd": str(tmp_path), "hook_event_name": "SubagentStop", "agent_transcript_path": ""}

    with (
        patch.object(_hook_mod, "_resolve_active_task_context", return_value=(None, plan_id, "T1", None, None)),
        patch.object(_hook_mod, "_call_sam_task_read", return_value=self_marked, create=True),
        patch.object(_hook_mod, "_extract_status_from_transcript", return_value=("DONE", "STATUS: DONE\n")),
        patch.object(_hook_mod, "_call_sam_task_state") as mock_state,
        patch.object(_hook_mod, "_call_sam_task_update") as mock_update,
        patch.object(_hook_mod, "_cleanup_active_task_context"),
        pytest.raises(SystemExit) as exc_info,
    ):
        handle_subagent_stop(hook_input)

    assert exc_info.value.code == 0
    mock_state.assert_not_called()
    mock_update.assert_not_called()


def test_handle_subagent_stop_failed_state_still_cascades_regardless_of_report(tmp_path: Path) -> None:
    """An explicit state=failed is terminal and wins over whatever the transcript says."""
    from sam_schema.core.models import Task, TaskStatus

    plan_id = "Pf4281187"
    failed_task = MagicMock(spec=Task)
    failed_task.status = TaskStatus.FAILED

    hook_input: dict[str, Any] = {"cwd": str(tmp_path), "hook_event_name": "SubagentStop", "agent_transcript_path": ""}

    with (
        patch.object(_hook_mod, "_resolve_active_task_context", return_value=(None, plan_id, "T1", None, None)),
        patch.object(_hook_mod, "_call_sam_task_read", return_value=failed_task, create=True),
        patch.object(_hook_mod, "_extract_status_from_transcript", return_value=("DONE", "STATUS: DONE\n")),
        patch.object(_hook_mod, "_cascade_failed_task") as mock_cascade,
        patch.object(_hook_mod, "_call_sam_task_state") as mock_state,
        patch.object(_hook_mod, "_cleanup_active_task_context"),
    ):
        handle_subagent_stop(hook_input)

    mock_cascade.assert_called_once()
    mock_state.assert_not_called()


def test_handle_subagent_stop_marks_blocked_when_no_status_line_found(tmp_path: Path) -> None:
    """A worker whose final message has no STATUS: line is treated as not-complete, not COMPLETE."""
    plan_id = "Pf4281187"
    hook_input: dict[str, Any] = {"cwd": str(tmp_path), "hook_event_name": "SubagentStop", "agent_transcript_path": ""}

    with (
        patch.object(_hook_mod, "_resolve_active_task_context", return_value=(None, plan_id, "T1", None, None)),
        patch.object(_hook_mod, "_call_sam_task_read", return_value=_in_progress_task(), create=True),
        patch.object(
            _hook_mod, "_extract_status_from_transcript", return_value=(None, "Here's a summary of what I did.")
        ),
        patch.object(_hook_mod, "_call_sam_task_state", return_value=True) as mock_state,
        patch.object(_hook_mod, "_call_sam_task_update") as mock_update,
        patch.object(_hook_mod, "_cleanup_active_task_context"),
        pytest.raises(SystemExit) as exc_info,
    ):
        handle_subagent_stop(hook_input)

    assert exc_info.value.code == 0
    mock_state.assert_called_once_with(plan_id, "T1", _hook_mod.SamTaskStatus.BLOCKED)
    mock_update.assert_not_called()


def test_handle_subagent_stop_marks_blocked_when_transcript_unreadable(tmp_path: Path) -> None:
    """A missing transcript against a non-COMPLETE task blocks — nothing evidenced success.

    The task is IN_PROGRESS here, so there is no existing COMPLETE to protect. The
    inverse case, where an unreadable transcript must leave an existing COMPLETE alone,
    is ``test_unreadable_transcript_leaves_self_marked_complete_alone``.
    """
    plan_id = "Pf4281187"
    hook_input: dict[str, Any] = {
        "cwd": str(tmp_path),
        "hook_event_name": "SubagentStop",
        "agent_transcript_path": str(tmp_path / "does-not-exist.jsonl"),
    }

    with (
        patch.object(_hook_mod, "_resolve_active_task_context", return_value=(None, plan_id, "T1", None, None)),
        patch.object(_hook_mod, "_call_sam_task_read", return_value=_in_progress_task(), create=True),
        patch.object(_hook_mod, "_call_sam_task_state", return_value=True) as mock_state,
        patch.object(_hook_mod, "_call_sam_task_update") as mock_update,
        patch.object(_hook_mod, "_cleanup_active_task_context"),
        pytest.raises(SystemExit) as exc_info,
    ):
        # No mock on _extract_status_from_transcript — exercise the real function
        # against a transcript path that does not exist.
        handle_subagent_stop(hook_input)

    assert exc_info.value.code == 0
    mock_state.assert_called_once_with(plan_id, "T1", _hook_mod.SamTaskStatus.BLOCKED)
    mock_update.assert_not_called()


@pytest.mark.parametrize("status_token", ["DONE", "COMPLETE", "COMPLETED"])
def test_handle_subagent_stop_accepts_every_current_complete_spelling(status_token: str, tmp_path: Path) -> None:
    """Every complete spelling in live use across the plugin still reaches COMPLETE."""
    plan_id = "Pf4281187"
    hook_input: dict[str, Any] = {"cwd": str(tmp_path), "hook_event_name": "SubagentStop", "agent_transcript_path": ""}

    with (
        patch.object(_hook_mod, "_resolve_active_task_context", return_value=(None, plan_id, "T1", None, None)),
        patch.object(_hook_mod, "_call_sam_task_read", return_value=_in_progress_task(), create=True),
        patch.object(
            _hook_mod, "_extract_status_from_transcript", return_value=(status_token, f"STATUS: {status_token}")
        ),
        patch.object(_hook_mod, "_call_sam_task_state", return_value=True) as mock_state,
        patch.object(_hook_mod, "_call_sam_task_update", return_value=True) as mock_update,
        patch.object(_hook_mod, "_cleanup_active_task_context"),
    ):
        handle_subagent_stop(hook_input)

    mock_state.assert_called_once_with(plan_id, "T1", "complete")
    mock_update.assert_called_once()


# ---------------------------------------------------------------------------
# _extract_status_from_transcript
# ---------------------------------------------------------------------------


def _write_transcript(tmp_path: Path, records: list[dict[str, Any]]) -> Path:
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    return transcript


def _assistant_record(text: str) -> dict[str, Any]:
    return {"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}


def test_extract_status_from_transcript_reads_last_assistant_message(tmp_path: Path) -> None:
    """Uses the LAST assistant text block, not the first, so mid-run status updates are ignored."""
    transcript = _write_transcript(
        tmp_path,
        [
            _assistant_record("STATUS: BLOCKED\nstill working, this is a progress note"),
            {"type": "user", "message": {"content": [{"type": "text", "text": "STATUS: DONE (echoed input, ignore)"}]}},
            _assistant_record("STATUS: DONE\nall acceptance criteria satisfied"),
        ],
    )

    status_token, final_text = _hook_mod._extract_status_from_transcript(transcript)

    assert status_token == "DONE"
    assert final_text is not None
    assert "all acceptance criteria satisfied" in final_text


def test_extract_status_from_transcript_missing_file_returns_none() -> None:
    status_token, final_text = _hook_mod._extract_status_from_transcript(Path("/nonexistent/transcript.jsonl"))
    assert status_token is None
    assert final_text is None


def test_extract_status_from_transcript_no_status_line_returns_none_token(tmp_path: Path) -> None:
    transcript = _write_transcript(tmp_path, [_assistant_record("Just a plain summary, no status line.")])

    status_token, final_text = _hook_mod._extract_status_from_transcript(transcript)

    assert status_token is None
    assert final_text == "Just a plain summary, no status line."


def test_extract_status_from_transcript_case_insensitive(tmp_path: Path) -> None:
    transcript = _write_transcript(tmp_path, [_assistant_record("status: done\nlowercase variant")])

    status_token, _ = _hook_mod._extract_status_from_transcript(transcript)

    assert status_token == "DONE"


# ===========================================================================
# _resolve_active_task_context / handle_subagent_stop — plan addressing
#
# plan_id is a plain str plan address end-to-end (e.g. "Pf4281187"), never a
# filesystem Path — task reads go through _call_sam_task_read via the SAM
# CLI, not a direct file read. sam_get_task (that removed file-read path) no
# longer exists on the module; tests below patch it with create=True purely
# to assert it is never touched.
# ===========================================================================


# ---------------------------------------------------------------------------
# _call_sam_task_read — SAM CLI task-read helper
# ---------------------------------------------------------------------------


def test_call_sam_task_read_success_returns_task_object(mocker: MockerFixture) -> None:
    """_call_sam_task_read returns a SamTask on a successful CLI response."""
    from sam_schema.core.models import Task, TaskStatus

    # Arrange — craft a minimal task JSON response matching the CLI's plain output
    task_data = {
        "id": "T1",
        "title": "Write the tests",
        "status": "in-progress",
        "agent": "python-pytest-architect",
        "acceptance_criteria": "All tests pass",
        "dependencies": [],
    }
    inner = {"task": task_data}
    response = CompletedProcess(args=[], returncode=0, stdout=json.dumps(inner), stderr="")

    mocker.patch("shutil.which", return_value="/usr/bin/uv")
    mocker.patch.object(Path, "exists", return_value=True)
    mock_popen = mocker.patch("subprocess.Popen", return_value=_popen_from_completed(response))

    # Act
    result = _hook_mod._call_sam_task_read("Pf4281187", "T1")

    # Assert
    assert result is not None
    assert isinstance(result, Task)
    assert result.status == TaskStatus.IN_PROGRESS
    mock_popen.assert_called_once()


def test_call_sam_task_read_sends_correct_mcp_input_json(mocker: MockerFixture) -> None:
    """_call_sam_task_read calls the SAM CLI with plan read --address <plan>/<task>."""
    task_data = {
        "id": "T3",
        "title": "Refactor hook",
        "status": "not-started",
        "agent": "",
        "acceptance_criteria": "",
        "dependencies": [],
    }
    inner = {"task": task_data}
    response = CompletedProcess(args=[], returncode=0, stdout=json.dumps(inner), stderr="")

    mocker.patch("shutil.which", return_value="/usr/bin/uv")
    mocker.patch.object(Path, "exists", return_value=True)
    mock_popen = mocker.patch("subprocess.Popen", return_value=_popen_from_completed(response))

    # Act
    _hook_mod._call_sam_task_read("Pdec8934d", "T3")

    # Assert — correct CLI argv shape
    mock_popen.assert_called_once()
    cmd = mock_popen.call_args[0][0]
    assert _argv_after(cmd, "plan") == ["plan", "read", "--address", "Pdec8934d/T3"]


def test_call_sam_task_read_returns_none_when_uv_missing(mocker: MockerFixture) -> None:
    """_call_sam_task_read returns None gracefully when uv is not on PATH.

    Mirrors the graceful-failure pattern of _call_sam_task_state.
    """
    mocker.patch("shutil.which", return_value=None)

    call_sam_task_read = getattr(_hook_mod, "_call_sam_task_read", None)
    assert call_sam_task_read is not None, "_call_sam_task_read does not exist (RED)"

    result = call_sam_task_read("Pf4281187", "T1")

    assert result is None


def test_call_sam_task_read_returns_none_on_subprocess_failure(mocker: MockerFixture) -> None:
    """_call_sam_task_read returns None when the subprocess exits non-zero."""
    mocker.patch("shutil.which", return_value="/usr/bin/uv")
    mocker.patch.object(Path, "exists", return_value=True)
    mocker.patch(
        "subprocess.Popen",
        return_value=_popen_from_completed(CompletedProcess(args=[], returncode=1, stdout="", stderr="err")),
    )

    call_sam_task_read = getattr(_hook_mod, "_call_sam_task_read", None)
    assert call_sam_task_read is not None, "_call_sam_task_read does not exist (RED)"

    result = call_sam_task_read("Pf4281187", "T1")

    assert result is None


def test_call_sam_task_read_returns_none_on_timeout(mocker: MockerFixture) -> None:
    """_call_sam_task_read returns None when the subprocess times out."""
    mocker.patch("shutil.which", return_value="/usr/bin/uv")
    mocker.patch.object(Path, "exists", return_value=True)
    mocker.patch("subprocess.Popen", return_value=_popen_timeout())
    mocker.patch("os.getpgid", return_value=4242)
    mocker.patch("os.killpg")

    call_sam_task_read = getattr(_hook_mod, "_call_sam_task_read", None)
    assert call_sam_task_read is not None, "_call_sam_task_read does not exist (RED)"

    result = call_sam_task_read("Pf4281187", "T1")

    assert result is None


# ---------------------------------------------------------------------------
# handle_subagent_stop — SAM CLI read-path assertions
# ---------------------------------------------------------------------------


def test_handle_subagent_stop_calls_mcp_read_not_sam_get_task_on_happy_path(mocker: MockerFixture) -> None:
    """handle_subagent_stop uses _call_sam_task_read(plan_id_str, task_id) not sam_get_task.

    Happy path: task is IN_PROGRESS → hook marks it COMPLETE.
    Asserts:
      1. _call_sam_task_read IS called with a plain str plan_id, not a Path.
      2. sam_get_task is NEVER called.
      3. plan_id arg is type str (not Path).
    """
    from sam_schema.core.models import Task, TaskStatus

    # Arrange — resolved context carries plan_id as a plain string
    plan_id = "Pf4281187"
    task_id = "T1"
    session_id = "sess-refactor-001"

    mock_task = mocker.MagicMock(spec=Task)
    mock_task.status = TaskStatus.IN_PROGRESS

    hook_input: dict[str, Any] = {"cwd": "/workspace", "hook_event_name": "SubagentStop", "agent_transcript_path": ""}

    mocker.patch.object(
        _hook_mod, "_resolve_active_task_context", return_value=(session_id, plan_id, task_id, None, None)
    )

    # _call_sam_task_read replaces the old filesystem-based _fetch_task_for_stop_hook read.
    mock_read = mocker.patch.object(_hook_mod, "_call_sam_task_read", create=True, return_value=mock_task)

    # sam_get_task (the old filesystem-read path) no longer exists — assert it's never touched.
    mock_get = mocker.patch.object(_hook_mod, "sam_get_task", create=True)

    mocker.patch.object(_hook_mod, "_extract_status_from_transcript", return_value=("DONE", "STATUS: DONE\n"))
    mocker.patch.object(_hook_mod, "_call_sam_task_state", return_value=True)
    mocker.patch.object(_hook_mod, "_call_sam_task_update", return_value=True)
    mocker.patch.object(_hook_mod, "_cleanup_active_task_context")

    # Act
    handle_subagent_stop(hook_input)

    # Assert 1: _call_sam_task_read was called
    mock_read.assert_called_once()
    read_args = mock_read.call_args[0]

    # Assert 2: first arg is a plain string (not Path)
    assert isinstance(read_args[0], str), f"_call_sam_task_read first arg must be str, got {type(read_args[0])}"
    assert read_args[0] == plan_id, f"Expected plan_id '{plan_id}', got '{read_args[0]}'"
    assert read_args[1] == task_id

    # Assert 3: sam_get_task was NOT called
    mock_get.assert_not_called()


def test_handle_subagent_stop_cascades_via_mcp_when_task_already_failed(mocker: MockerFixture) -> None:
    """handle_subagent_stop reads the task via the SAM CLI when it is already FAILED.

    Asserts:
      1. _call_sam_task_read IS called (to discover FAILED status).
      2. sam_get_task is NEVER called.
      3. _cascade_failed_task is called, which routes through _call_sam_task_state.
    """
    from sam_schema.core.models import Task, TaskStatus

    plan_id = "Pdec8934d"
    task_id = "T2"
    session_id = "sess-failed-task"

    mock_task = mocker.MagicMock(spec=Task)
    mock_task.status = TaskStatus.FAILED

    hook_input: dict[str, Any] = {"cwd": "/workspace", "hook_event_name": "SubagentStop", "agent_transcript_path": ""}

    mocker.patch.object(
        _hook_mod, "_resolve_active_task_context", return_value=(session_id, plan_id, task_id, None, None)
    )

    mock_read = mocker.patch.object(_hook_mod, "_call_sam_task_read", create=True, return_value=mock_task)
    mock_get = mocker.patch.object(_hook_mod, "sam_get_task", create=True)
    # _cascade_failed_task calls sys.exit(0) — patch it to prevent SystemExit
    mocker.patch.object(_hook_mod, "_cascade_failed_task")
    mocker.patch.object(_hook_mod, "_cleanup_active_task_context")

    # Act
    handle_subagent_stop(hook_input)

    # Assert: _call_sam_task_read was called with str plan_id
    mock_read.assert_called_once()
    read_args = mock_read.call_args[0]
    assert isinstance(read_args[0], str), f"_call_sam_task_read first arg must be str, got {type(read_args[0])}"
    assert read_args[0] == plan_id
    assert read_args[1] == task_id

    # Assert: sam_get_task was NOT called
    mock_get.assert_not_called()


def test_handle_subagent_stop_skips_state_write_when_task_already_complete(mocker: MockerFixture) -> None:
    """handle_subagent_stop exits 0 without writing state when task is already COMPLETE.

    Asserts:
      1. _call_sam_task_read IS called to check current status.
      2. sam_get_task is NEVER called.
      3. _call_sam_task_state is NOT called (no unnecessary state write).
    """
    from sam_schema.core.models import Task, TaskStatus

    plan_id = "P1a2b3c4"
    task_id = "T5"
    session_id = "sess-already-done"

    mock_task = mocker.MagicMock(spec=Task)
    mock_task.status = TaskStatus.COMPLETE

    hook_input: dict[str, Any] = {"cwd": "/workspace", "hook_event_name": "SubagentStop", "agent_transcript_path": ""}

    mocker.patch.object(
        _hook_mod, "_resolve_active_task_context", return_value=(session_id, plan_id, task_id, None, None)
    )

    mock_read = mocker.patch.object(_hook_mod, "_call_sam_task_read", create=True, return_value=mock_task)
    mock_get = mocker.patch.object(_hook_mod, "sam_get_task", create=True)
    mock_state = mocker.patch.object(_hook_mod, "_call_sam_task_state")
    mocker.patch.object(_hook_mod, "_cleanup_active_task_context")

    # Act
    with pytest.raises(SystemExit) as exc_info:
        handle_subagent_stop(hook_input)

    # Assert exit code
    assert exc_info.value.code == 0

    # Assert _call_sam_task_read was called with str plan_id
    mock_read.assert_called_once()
    read_args = mock_read.call_args[0]
    assert isinstance(read_args[0], str), f"_call_sam_task_read first arg must be str, got {type(read_args[0])}"
    assert read_args[0] == plan_id
    assert read_args[1] == task_id

    # Assert sam_get_task was never called
    mock_get.assert_not_called()

    # Assert no state write occurred (task already complete — no transition needed)
    mock_state.assert_not_called()


# ---------------------------------------------------------------------------
# _resolve_active_task_context — returns str plan_id, never a Path
# ---------------------------------------------------------------------------


def test_resolve_active_task_context_returns_str_plan_id_from_mcp(mocker: MockerFixture, tmp_path: Path) -> None:
    """_resolve_active_task_context returns plan_id as str, read from the "plan" field.

    _call_sam_active_task_get reads the ActiveTaskContext.plan field directly —
    no path parsing or extraction involved.
    """
    # Arrange — transcript with session_id so the SAM CLI primary path is taken
    transcript = tmp_path / "agent-session.jsonl"
    transcript.write_text(json.dumps({"sessionId": "sess-abc123", "type": "user"}) + "\n")

    hook_input: dict[str, Any] = {
        "cwd": str(tmp_path),
        "hook_event_name": "SubagentStop",
        "agent_transcript_path": str(transcript),
    }

    # Build a realistic CLI response for `active-task get`
    active_task = {"active_task": {"plan": "Pf4281187", "task_id": "T1", "parent_issue_number": None}}
    mcp_response = CompletedProcess(args=[], returncode=0, stdout=json.dumps(active_task), stderr="")

    # Patch subprocess.Popen so _call_sam_active_task_get uses our response
    mocker.patch("shutil.which", return_value="/usr/bin/uv")
    mocker.patch.object(Path, "exists", return_value=True)
    mocker.patch("subprocess.Popen", return_value=_popen_from_completed(mcp_response))
    # None means "this backend keeps the record where the hook cannot stat it", which
    # is what routes resolution through the CLI — the path this test covers.
    mocker.patch.object(_hook_mod, "_local_active_task_file", return_value=None)

    # Act — let _resolve_active_task_context → _call_sam_active_task_get run naturally
    result = _hook_mod._resolve_active_task_context(hook_input)

    # Assert — result is not None
    assert result is not None, "_resolve_active_task_context returned None unexpectedly"
    _session_id, plan_id, task_id, _parent_issue, _context_file = result

    # plan_id must be a plain str, never a filesystem Path (that abstraction was removed).
    assert isinstance(plan_id, str), f"plan_id must be str after refactor, got {type(plan_id)}: {plan_id!r}"
    assert not isinstance(plan_id, Path), "plan_id must NOT be a Path after refactor — filesystem abstraction removed"
    assert plan_id == "Pf4281187"
    assert task_id == "T1"


# ---------------------------------------------------------------------------
# handle_subagent_stop — stderr diagnostic when _call_sam_task_read returns None
# ---------------------------------------------------------------------------


def test_handle_subagent_stop_emits_stderr_when_mcp_read_returns_none(
    mocker: MockerFixture, capsys: pytest.CaptureFixture[str]
) -> None:
    """handle_subagent_stop prints a diagnostic to stderr when _call_sam_task_read returns None.

    Verifies the silent failure case is now visible: before this fix the hook exited 0
    without any message when the SAM CLI read failed.
    """
    # Arrange
    plan_id = "Pf4281187"
    task_id = "T1"

    hook_input: dict[str, Any] = {"cwd": "/workspace", "hook_event_name": "SubagentStop", "agent_transcript_path": ""}

    mocker.patch.object(_hook_mod, "_resolve_active_task_context", return_value=(None, plan_id, task_id, None, None))
    mocker.patch.object(_hook_mod, "_call_sam_task_read", create=True, return_value=None)
    mocker.patch.object(_hook_mod, "_cleanup_active_task_context")

    # Act — exits 0 after printing the diagnostic
    with pytest.raises(SystemExit) as exc_info:
        handle_subagent_stop(hook_input)

    # Assert — non-blocking exit
    assert exc_info.value.code == 0

    # Assert — diagnostic visible on stderr
    captured = capsys.readouterr()
    assert f"could not read task {task_id} from plan {plan_id} via the SAM CLI" in captured.err
    assert "skipping" in captured.err


# ---------------------------------------------------------------------------
# handle_activity_update — stderr diagnostic when _call_sam_task_read returns None
# ---------------------------------------------------------------------------


def test_handle_activity_update_emits_stderr_when_mcp_read_returns_none(
    mocker: MockerFixture, capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """handle_activity_update prints a diagnostic to stderr when _call_sam_task_read returns None.

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

    mocker.patch.object(_hook_mod, "_call_sam_task_read", create=True, return_value=None)
    mock_update = mocker.patch.object(_hook_mod, "_call_sam_task_update", return_value=True)

    # Act
    handle_activity_update(hook_input)

    # Assert — diagnostic visible on stderr
    captured = capsys.readouterr()
    assert "could not read task T1 from plan Pf4281187 via the SAM CLI" in captured.err
    assert "skipping" in captured.err

    # Assert — update still proceeds (best-effort activity tracking continues)
    mock_update.assert_called_once()


# ---------------------------------------------------------------------------
# _call_sam_active_task_get — CLI subcommand routing
# ---------------------------------------------------------------------------


def test_call_sam_active_task_get_passes_sam_active_task_target(mocker: MockerFixture) -> None:
    """_call_sam_active_task_get calls the SAM CLI's ``active-task get`` subcommand.

    A bug where the wrapper routes to the wrong subcommand would silently
    return (None, None, None) without any error, making it a correctness
    failure invisible at the call site.
    """
    # Arrange — valid active task response so the call succeeds
    active_task_data = {"active_task": {"plan": "Pf4281187", "task_id": "T1", "parent_issue_number": None}}
    response = CompletedProcess(args=[], returncode=0, stdout=json.dumps(active_task_data), stderr="")

    mocker.patch("shutil.which", return_value="/usr/bin/uv")
    mocker.patch.object(Path, "exists", return_value=True)
    mock_popen = mocker.patch("subprocess.Popen", return_value=_popen_from_completed(response))

    # Act
    _hook_mod._call_sam_active_task_get("test-session-id")

    # Assert
    mock_popen.assert_called_once()
    cmd: list[str] = mock_popen.call_args[0][0]
    assert _argv_after(cmd, "active-task") == ["active-task", "get", "--session-id", "test-session-id"]


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
        _hook_mod._call_sam_task_state,
        _hook_mod._call_sam_task_update,
        _hook_mod._call_sam_task_read,
        _hook_mod._call_sam_active_task_get,
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
# _call_sam_task_read then _call_sam_task_update are each individually kept
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

    from sam_schema.core.models import Task, TaskStatus

    mock_task = mocker.MagicMock(spec=Task)
    mock_task.status = TaskStatus.IN_PROGRESS

    mocker.patch("time.monotonic", side_effect=[0.0, 0.0, 6.0])
    mocker.patch.object(_hook_mod, "_call_sam_task_read", return_value=mock_task, create=True)
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

    from sam_schema.core.models import Task, TaskStatus

    mock_task = mocker.MagicMock(spec=Task)
    mock_task.status = TaskStatus.IN_PROGRESS

    mocker.patch("time.monotonic", side_effect=[0.0, 0.0, 8.5])
    mocker.patch.object(_hook_mod, "_call_sam_task_read", return_value=mock_task, create=True)
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


def _transcript_with_status(tmp_path: Path, status_line: str, session_id: str = "sess-specialist-1") -> Path:
    """Write a transcript in the real JSONL shape the hook parses.

    Mirrors an actual sub-agent transcript: a sessionId-bearing first record, a user
    prompt, tool traffic, then the final assistant message carrying the STATUS line.
    """
    records: list[dict[str, Any]] = [
        {"type": "user", "sessionId": session_id, "message": {"content": [{"type": "text", "text": "P1a2b3c4/T7"}]}},
        {
            "type": "assistant",
            "sessionId": session_id,
            "message": {"content": [{"type": "text", "text": "Working on it."}]},
        },
        {"type": "user", "sessionId": session_id, "message": {"content": [{"type": "tool_result", "text": "ok"}]}},
        {"type": "assistant", "sessionId": session_id, "message": {"content": [{"type": "text", "text": status_line}]}},
    ]
    transcript = tmp_path / f"{session_id}.jsonl"
    transcript.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    return transcript


def test_specialist_agent_stopping_with_done_marks_task_complete(tmp_path: Path) -> None:
    """A non-task-worker specialist that claims a task and reports DONE gets it marked complete.

    Drives a real transcript file rather than a mocked status, so the JSONL parsing path
    is exercised end to end.
    """
    from sam_schema.core.models import Task, TaskStatus

    plan_id = "P1a2b3c4"
    in_progress = MagicMock(spec=Task)
    in_progress.status = TaskStatus.IN_PROGRESS

    transcript = _transcript_with_status(tmp_path, "STATUS: DONE\nAll acceptance criteria met.")
    hook_input: dict[str, Any] = {
        "cwd": str(tmp_path),
        "hook_event_name": "SubagentStop",
        "agent_transcript_path": str(transcript),
    }

    with (
        patch.object(
            _hook_mod, "_resolve_active_task_context", return_value=("sess-specialist-1", plan_id, "T7", None, None)
        ),
        patch.object(_hook_mod, "_call_sam_task_read", return_value=in_progress, create=True),
        patch.object(_hook_mod, "_call_sam_task_state", return_value=True) as mock_state,
        patch.object(_hook_mod, "_call_sam_task_update", return_value=True) as mock_update,
        patch.object(_hook_mod, "_cleanup_active_task_context"),
    ):
        handle_subagent_stop(hook_input)

    mock_state.assert_called_once_with(plan_id, "T7", "complete")
    mock_update.assert_called_once()


def test_self_marked_complete_specialist_reporting_partial_is_reverted(tmp_path: Path) -> None:
    """The happy-path state the system actually produces: task already COMPLETE via start-task.

    start-task marks the task complete before the worker stops, so COMPLETE — not
    IN_PROGRESS — is the state this hook normally observes. A PARTIAL report against that
    state must still revert to blocked.
    """
    from sam_schema.core.models import Task, TaskStatus

    plan_id = "P1a2b3c4"
    self_marked = MagicMock(spec=Task)
    self_marked.status = TaskStatus.COMPLETE

    transcript = _transcript_with_status(tmp_path, "STATUS: PARTIAL\nBLOCKER: 2 of 5 criteria unmet.")
    hook_input: dict[str, Any] = {
        "cwd": str(tmp_path),
        "hook_event_name": "SubagentStop",
        "agent_transcript_path": str(transcript),
    }

    with (
        patch.object(
            _hook_mod, "_resolve_active_task_context", return_value=("sess-specialist-1", plan_id, "T7", None, None)
        ),
        patch.object(_hook_mod, "_call_sam_task_read", return_value=self_marked, create=True),
        patch.object(_hook_mod, "_call_sam_task_state", return_value=True) as mock_state,
        patch.object(_hook_mod, "_call_sam_task_update") as mock_update,
        patch.object(_hook_mod, "_cleanup_active_task_context"),
        pytest.raises(SystemExit) as exc_info,
    ):
        handle_subagent_stop(hook_input)

    assert exc_info.value.code == 0
    mock_state.assert_called_once_with(plan_id, "T7", _hook_mod.SamTaskStatus.BLOCKED)
    mock_update.assert_not_called()


def test_self_marked_complete_omitting_the_status_line_is_reverted(tmp_path: Path) -> None:
    """A readable final message with no STATUS: line blocks a self-marked COMPLETE.

    Omitting the STATUS line is a contract violation by the worker and the most common
    one. The hook read the transcript and saw what the worker said, so it has positive
    evidence the worker did not report completion — distinct from not being able to read
    the transcript at all, which is the next test.
    """
    from sam_schema.core.models import Task, TaskStatus

    plan_id = "P1a2b3c4"
    self_marked = MagicMock(spec=Task)
    self_marked.status = TaskStatus.COMPLETE

    transcript = _transcript_with_status(tmp_path, "Here's a summary of what I did.\nUpdated five files.")
    hook_input: dict[str, Any] = {
        "cwd": str(tmp_path),
        "hook_event_name": "SubagentStop",
        "agent_transcript_path": str(transcript),
    }

    with (
        patch.object(
            _hook_mod, "_resolve_active_task_context", return_value=("sess-specialist-1", plan_id, "T7", None, None)
        ),
        patch.object(_hook_mod, "_call_sam_task_read", return_value=self_marked, create=True),
        patch.object(_hook_mod, "_call_sam_task_state", return_value=True) as mock_state,
        patch.object(_hook_mod, "_call_sam_task_update") as mock_update,
        patch.object(_hook_mod, "_cleanup_active_task_context"),
        pytest.raises(SystemExit) as exc_info,
    ):
        handle_subagent_stop(hook_input)

    assert exc_info.value.code == 0
    mock_state.assert_called_once_with(plan_id, "T7", _hook_mod.SamTaskStatus.BLOCKED)
    mock_update.assert_not_called()


@pytest.mark.parametrize(
    ("label", "final_text"),
    [
        ("fenced per task-worker.md", "```text\nSTATUS: PARTIAL\nBLOCKER: 2 of 5 unmet.\n```"),
        ("lead sentence first", "Here is the completion report.\n\nSTATUS: PARTIAL\nBLOCKER: unmet."),
        ("bold markdown", "**STATUS: PARTIAL**\nBLOCKER: unmet."),
        ("heading first", "## Completion Report\n\nSTATUS: PARTIAL\nBLOCKER: unmet."),
    ],
)
def test_status_line_is_found_below_the_first_line(label: str, final_text: str, tmp_path: Path) -> None:
    """The STATUS line is matched anywhere in the final message, not only on line one.

    agents/task-worker.md prescribes the completion report inside a ```text fence, so a
    worker following its own documented template puts the fence marker on line one. Reading
    only the first line scored every such report as "no STATUS line" — which both blocked
    honest DONE reports and let a self-marked COMPLETE survive a fenced PARTIAL.
    """
    from sam_schema.core.models import Task, TaskStatus

    plan_id = "P1a2b3c4"
    self_marked = MagicMock(spec=Task)
    self_marked.status = TaskStatus.COMPLETE

    transcript = _transcript_with_status(tmp_path, final_text)
    hook_input: dict[str, Any] = {
        "cwd": str(tmp_path),
        "hook_event_name": "SubagentStop",
        "agent_transcript_path": str(transcript),
    }

    with (
        patch.object(
            _hook_mod, "_resolve_active_task_context", return_value=("sess-specialist-1", plan_id, "T7", None, None)
        ),
        patch.object(_hook_mod, "_call_sam_task_read", return_value=self_marked, create=True),
        patch.object(_hook_mod, "_call_sam_task_state", return_value=True) as mock_state,
        patch.object(_hook_mod, "_cleanup_active_task_context"),
        pytest.raises(SystemExit),
    ):
        handle_subagent_stop(hook_input)

    assert mock_state.call_args is not None, f"{label}: PARTIAL was not detected, task left COMPLETE"
    mock_state.assert_called_once_with(plan_id, "T7", _hook_mod.SamTaskStatus.BLOCKED)


@pytest.mark.parametrize("status_token", ["VERIFIED", "GAPS_FOUND", "CONNECTED", "READY", "DRAFTING"])
def test_unregistered_status_token_leaves_task_state_unchanged(status_token: str, tmp_path: Path) -> None:
    """A token outside both vocabularies is not evidence of failure and must not block.

    The SubagentStop matcher no longer filters to task-worker, so shipped specialists —
    feature-verifier, integration-checker, plan-validator — now reach this hook reporting
    their own vocabularies. Blocking on an unrecognised word would turn their correct work
    into BLOCKED.
    """
    from sam_schema.core.models import Task, TaskStatus

    in_progress = MagicMock(spec=Task)
    in_progress.status = TaskStatus.IN_PROGRESS

    transcript = _transcript_with_status(tmp_path, f"STATUS: {status_token}\nAll checks ran.")
    hook_input: dict[str, Any] = {
        "cwd": str(tmp_path),
        "hook_event_name": "SubagentStop",
        "agent_transcript_path": str(transcript),
    }

    with (
        patch.object(
            _hook_mod, "_resolve_active_task_context", return_value=("sess-specialist-1", "P1a2b3c4", "T7", None, None)
        ),
        patch.object(_hook_mod, "_call_sam_task_read", return_value=in_progress, create=True),
        patch.object(_hook_mod, "_call_sam_task_state", return_value=True) as mock_state,
        patch.object(_hook_mod, "_call_sam_task_update") as mock_update,
        patch.object(_hook_mod, "_cleanup_active_task_context"),
        pytest.raises(SystemExit) as exc_info,
    ):
        handle_subagent_stop(hook_input)

    assert exc_info.value.code == 0
    mock_state.assert_not_called()
    mock_update.assert_not_called()


def test_last_assistant_message_is_used_without_reading_the_transcript(tmp_path: Path) -> None:
    """The payload's final message wins over the transcript, and the file is never opened.

    Claude Code's hook docs direct hooks needing the final assistant text to use
    ``last_assistant_message`` "instead of reading the transcript", and Codex supplies the
    same field. Scanning a transcript to recover a string already on stdin costs a full
    file read on every sub-agent stop.
    """
    from sam_schema.core.models import Task, TaskStatus

    plan_id = "P1a2b3c4"
    self_marked = MagicMock(spec=Task)
    self_marked.status = TaskStatus.COMPLETE

    hook_input: dict[str, Any] = {
        "cwd": str(tmp_path),
        "hook_event_name": "SubagentStop",
        # Deliberately unreadable: if the hook falls back to it, the payload was ignored.
        "agent_transcript_path": str(tmp_path / "never-written.jsonl"),
        "last_assistant_message": "STATUS: PARTIAL\nBLOCKER: 2 of 5 criteria unmet.",
    }

    with (
        patch.object(
            _hook_mod, "_resolve_active_task_context", return_value=("sess-specialist-1", plan_id, "T7", None, None)
        ),
        patch.object(_hook_mod, "_call_sam_task_read", return_value=self_marked, create=True),
        patch.object(_hook_mod, "_call_sam_task_state", return_value=True) as mock_state,
        patch.object(_hook_mod, "_extract_status_from_transcript") as mock_transcript,
        patch.object(_hook_mod, "_cleanup_active_task_context"),
        pytest.raises(SystemExit),
    ):
        handle_subagent_stop(hook_input)

    mock_transcript.assert_not_called()
    mock_state.assert_called_once_with(plan_id, "T7", _hook_mod.SamTaskStatus.BLOCKED)


def test_the_template_placeholder_is_not_a_verdict() -> None:
    """``STATUS: COMPLETE|PARTIAL|FAILED`` is the printed format, not a report.

    agents/task-worker.md documents the report shape with that literal alternation. A
    worker that shows the format before filling it in emits it as a line-initial STATUS,
    and a token pattern that does not require the token to end the line captures COMPLETE
    out of it — reading a completion out of a placeholder.
    """
    report = (
        "## Completion Report\n\n"
        "Reporting in the documented format:\n\n"
        "STATUS: COMPLETE|PARTIAL|FAILED\n\n"
        "STATUS: PARTIAL\n"
        "BLOCKER: 2 of 5 criteria unmet.\n"
    )

    assert _hook_mod._parse_status_line(report) == "PARTIAL"


def test_a_later_status_line_does_not_override_the_verdict() -> None:
    """The first well-formed STATUS line is the verdict, per the subagent contract.

    skills/subagent-contract/SKILL.md: "Begin your response with STATUS: DONE or
    STATUS: BLOCKED as its own first line. Consumers branch on that line in that position."
    The task-worker template's last field is NOTES, which is free text for discoveries and
    out-of-scope work. Preferring a later match would let a note silently outrank the
    worker's own report.
    """
    report = (
        "STATUS: PARTIAL\n"
        "BLOCKER: 2 of 5 criteria unmet.\n"
        "NOTES: the integration checker finished its own task first.\n"
        "STATUS: DONE\n"
    )

    assert _hook_mod._parse_status_line(report) == "PARTIAL"


def test_prose_mentioning_a_status_is_not_a_verdict() -> None:
    """A STATUS token embedded in a sentence is not a report line."""
    assert _hook_mod._parse_status_line("STATUS: DONE was reported by the sibling task.") is None


def test_local_backend_with_no_active_task_spawns_no_subprocess(mocker: MockerFixture, tmp_path: Path) -> None:
    """The no-active-task path costs no subprocess under the default local backend.

    This hook fires on every sub-agent stop in every plugin, and most of those agents
    hold no SAM task. The ``active-task get`` subprocess was ~1.3s of the ~1.75s total
    on that path, so the record is stat-ed directly instead.
    """
    transcript = tmp_path / "agent-session.jsonl"
    transcript.write_text(json.dumps({"sessionId": "sess-no-task", "type": "user"}) + "\n")
    hook_input: dict[str, Any] = {
        "cwd": str(tmp_path),
        "hook_event_name": "SubagentStop",
        "agent_transcript_path": str(transcript),
    }

    # Local backend, and the record for this session was never written.
    mocker.patch.object(_hook_mod, "_local_active_task_file", return_value=tmp_path / "active-task-sess-no-task.json")
    popen = mocker.patch("subprocess.Popen")

    assert _hook_mod._resolve_active_task_context(hook_input) is None
    popen.assert_not_called()


def test_local_backend_reads_the_active_task_record_without_a_subprocess(mocker: MockerFixture, tmp_path: Path) -> None:
    """An existing local record resolves the task by file read, not by CLI call."""
    transcript = tmp_path / "agent-session.jsonl"
    transcript.write_text(json.dumps({"sessionId": "sess-has-task", "type": "user"}) + "\n")
    record = tmp_path / "active-task-sess-has-task.json"
    record.write_text(json.dumps({"plan": "Pf4281187", "task_id": "T1", "parent_issue_number": 42}))

    hook_input: dict[str, Any] = {
        "cwd": str(tmp_path),
        "hook_event_name": "SubagentStop",
        "agent_transcript_path": str(transcript),
    }
    mocker.patch.object(_hook_mod, "_local_active_task_file", return_value=record)
    popen = mocker.patch("subprocess.Popen")

    result = _hook_mod._resolve_active_task_context(hook_input)

    assert result is not None
    _session_id, plan_id, task_id, _parent_issue, context_file = result
    assert plan_id == "Pf4281187"
    assert task_id == "T1"
    assert context_file == record
    popen.assert_not_called()


def test_unreadable_transcript_leaves_self_marked_complete_alone(tmp_path: Path) -> None:
    """A transcript the hook cannot read never un-completes finished work.

    The hook has no evidence about the worker either way, and reverting a COMPLETE
    requires positive evidence just as writing one does. An infrastructure read failure
    must not stall the wave by blocking a task that finished.
    """
    from sam_schema.core.models import Task, TaskStatus

    plan_id = "P1a2b3c4"
    self_marked = MagicMock(spec=Task)
    self_marked.status = TaskStatus.COMPLETE

    hook_input: dict[str, Any] = {
        "cwd": str(tmp_path),
        "hook_event_name": "SubagentStop",
        "agent_transcript_path": str(tmp_path / "never-written.jsonl"),
    }

    with (
        patch.object(
            _hook_mod, "_resolve_active_task_context", return_value=("sess-specialist-1", plan_id, "T7", None, None)
        ),
        patch.object(_hook_mod, "_call_sam_task_read", return_value=self_marked, create=True),
        patch.object(_hook_mod, "_call_sam_task_state", return_value=True) as mock_state,
        patch.object(_hook_mod, "_call_sam_task_update") as mock_update,
        patch.object(_hook_mod, "_cleanup_active_task_context"),
        pytest.raises(SystemExit) as exc_info,
    ):
        # No mock on _extract_status_from_transcript — the real function must return
        # (None, None) for a path that was never written.
        handle_subagent_stop(hook_input)

    assert exc_info.value.code == 0
    mock_state.assert_not_called()
    mock_update.assert_not_called()
