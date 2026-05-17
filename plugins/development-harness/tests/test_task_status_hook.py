"""Tests for task_status_hook.py — MCP write helpers and refactored handlers.

Covers:
- _call_sam_task_state: routes state writes through MCP subprocess
- _call_sam_task_update: routes field writes through MCP subprocess
- Both helpers fall back gracefully (return False) on subprocess failure
- _extract_plan_addr_from_path: plan address extraction from filenames
- handle_subagent_stop: calls MCP helpers instead of direct YAML writes
- handle_activity_update: calls MCP helpers instead of direct YAML writes
"""

from __future__ import annotations

import importlib.util
import json
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
_extract_plan_addr_from_path = _hook_mod._extract_plan_addr_from_path
extract_task_info_from_prompt = _hook_mod.extract_task_info_from_prompt
handle_subagent_stop = _hook_mod.handle_subagent_stop
handle_activity_update = _hook_mod.handle_activity_update
HookProfile = _hook_mod.HookProfile
_SAM_RUN_SERVER_PATH = _hook_mod._SAM_RUN_SERVER_PATH


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mcp_success_response(data: dict[str, Any]) -> CompletedProcess[str]:
    """Build a successful fastmcp CLI response wrapping inner JSON."""
    outer = {"content": [{"text": json.dumps(data)}]}
    return CompletedProcess(args=[], returncode=0, stdout=json.dumps(outer), stderr="")


def _mcp_error_response(returncode: int = 1) -> CompletedProcess[str]:
    """Build a failed fastmcp CLI response."""
    return CompletedProcess(args=[], returncode=returncode, stdout="", stderr="error")


# ---------------------------------------------------------------------------
# _extract_plan_addr_from_path
# ---------------------------------------------------------------------------


def test_extract_plan_addr_from_path_returns_hex_address() -> None:
    """A filename containing a hex plan token returns that token."""
    # Arrange
    path = Path("/home/user/.dh/projects/foo/plan/Pf4281187-my-feature.yaml")

    # Act
    result = _extract_plan_addr_from_path(path)

    # Assert
    assert result == "Pf4281187"


def test_extract_plan_addr_from_path_returns_none_when_no_token() -> None:
    """A filename without a plan address token returns None."""
    # Arrange
    path = Path("/tmp/some-plan-file.yaml")

    # Act
    result = _extract_plan_addr_from_path(path)

    # Assert
    assert result is None


def test_extract_plan_addr_from_path_short_address() -> None:
    """Short hex plan IDs are also matched."""
    # Arrange
    path = Path("P1a2b3c4-slug.yaml")

    # Act
    result = _extract_plan_addr_from_path(path)

    # Assert
    assert result == "P1a2b3c4"


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
    """_call_sam_task_state calls fastmcp CLI with correct input JSON."""
    # Arrange
    plan_addr = "Pf4281187"
    task_id = "T1"
    status = "complete"
    response = _mcp_success_response({"id": task_id, "status": status})

    with (
        patch("shutil.which", return_value="/usr/bin/uv"),
        patch.object(Path, "exists", return_value=True),
        patch("subprocess.run", return_value=response) as mock_run,
    ):
        # Act
        result = _call_sam_task_state(plan_addr, task_id, status)

    # Assert
    assert result is True
    mock_run.assert_called_once()
    call_kwargs = mock_run.call_args
    cmd = call_kwargs[0][0]
    assert "--target" in cmd
    assert "sam_task" in cmd
    assert "--input-json" in cmd
    # Verify input JSON contains expected fields
    input_json_idx = cmd.index("--input-json") + 1
    input_data = json.loads(cmd[input_json_idx])
    assert input_data["plan"] == plan_addr
    assert input_data["task"] == task_id
    assert input_data["config"]["action"] == "state"
    assert input_data["config"]["status"] == status


def test_call_sam_task_state_sets_env_suppression_flags(tmp_path: Path) -> None:
    """_call_sam_task_state passes FASTMCP env vars to suppress banner and logs."""
    # Arrange
    response = _mcp_success_response({"id": "T1", "status": "complete"})

    with (
        patch("shutil.which", return_value="/usr/bin/uv"),
        patch.object(Path, "exists", return_value=True),
        patch("subprocess.run", return_value=response) as mock_run,
    ):
        # Act
        _call_sam_task_state("Pabc123", "T1", "complete")

    # Assert
    env_passed = mock_run.call_args[1]["env"]
    assert env_passed["FASTMCP_SHOW_SERVER_BANNER"] == "false"
    assert env_passed["FASTMCP_LOG_ENABLED"] == "false"


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
        patch("subprocess.run", return_value=_mcp_error_response()),
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
        patch("subprocess.run", side_effect=TimeoutExpired(cmd="uv", timeout=15)),
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
        patch("subprocess.run", side_effect=SubprocessError("broken pipe")),
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
        patch("subprocess.run", return_value=bad_response),
    ):
        # Act
        result = _call_sam_task_state("Pabc123", "T1", "complete")

    # Assert
    assert result is False


# ---------------------------------------------------------------------------
# _call_sam_task_update — success path
# ---------------------------------------------------------------------------


def test_call_sam_task_update_routes_through_mcp_subprocess() -> None:
    """_call_sam_task_update calls fastmcp CLI with correct set_fields_json."""
    # Arrange
    plan_addr = "Pf4281187"
    task_id = "T2"
    fields = {"last-activity": "2026-05-14T18:00:00+00:00"}
    response = _mcp_success_response({"updated": True, "address": f"{plan_addr}/{task_id}"})

    with (
        patch("shutil.which", return_value="/usr/bin/uv"),
        patch.object(Path, "exists", return_value=True),
        patch("subprocess.run", return_value=response) as mock_run,
    ):
        # Act
        result = _call_sam_task_update(plan_addr, task_id, fields)

    # Assert
    assert result is True
    cmd = mock_run.call_args[0][0]
    input_json_idx = cmd.index("--input-json") + 1
    input_data = json.loads(cmd[input_json_idx])
    assert input_data["plan"] == plan_addr
    assert input_data["task"] == task_id
    assert input_data["config"]["action"] == "update"
    assert input_data["config"]["set_fields_json"] == fields


def test_call_sam_task_update_sets_env_suppression_flags() -> None:
    """_call_sam_task_update passes FASTMCP env vars to suppress banner and logs."""
    # Arrange
    response = _mcp_success_response({"updated": True, "address": "Pabc/T1"})

    with (
        patch("shutil.which", return_value="/usr/bin/uv"),
        patch.object(Path, "exists", return_value=True),
        patch("subprocess.run", return_value=response) as mock_run,
    ):
        # Act
        _call_sam_task_update("Pabc123", "T1", {"last-activity": "2026-05-14T00:00:00+00:00"})

    # Assert
    env_passed = mock_run.call_args[1]["env"]
    assert env_passed["FASTMCP_SHOW_SERVER_BANNER"] == "false"
    assert env_passed["FASTMCP_LOG_ENABLED"] == "false"


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
        patch("subprocess.run", return_value=_mcp_error_response()),
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
        patch("subprocess.run", side_effect=TimeoutExpired(cmd="uv", timeout=15)),
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
        patch("subprocess.run", return_value=bad_response),
    ):
        # Act
        result = _call_sam_task_update("Pabc123", "T1", {"x": "y"})

    # Assert
    assert result is False


# ---------------------------------------------------------------------------
# handle_activity_update — MCP call path
# ---------------------------------------------------------------------------


def test_handle_activity_update_calls_mcp_update(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """handle_activity_update calls _call_sam_task_update for last-activity field."""
    # Arrange — create a plan file with plan address in the name
    plan_file = tmp_path / "Pf4281187-feature.yaml"
    plan_file.write_text("tasks:\n- id: T1\n  status: in-progress\n  title: Test\n")

    # Set up context file
    monkeypatch.setenv("DH_STATE_HOME", str(tmp_path / "dh_state"))
    import dh_paths

    context_dir = dh_paths.context_dir()
    context_dir.mkdir(parents=True, exist_ok=True)
    session_id = "sess-abc"
    context_file = context_dir / f"active-task-{session_id}.json"
    context_file.write_text(json.dumps({"task_file_path": str(plan_file), "task_id": "T1"}))

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
    """handle_activity_update exits silently when filename has no plan address token."""
    # Arrange — plan file with no plan address in name
    plan_file = tmp_path / "my-plan-without-address.yaml"
    plan_file.write_text("tasks:\n- id: T1\n  status: in-progress\n  title: Test\n")

    monkeypatch.setenv("DH_STATE_HOME", str(tmp_path / "dh_state"))
    import dh_paths

    context_dir = dh_paths.context_dir()
    context_dir.mkdir(parents=True, exist_ok=True)
    session_id = "sess-xyz"
    context_file = context_dir / f"active-task-{session_id}.json"
    context_file.write_text(json.dumps({"task_file_path": str(plan_file), "task_id": "T1"}))

    hook_input = {"cwd": str(tmp_path), "session_id": session_id, "hook_event_name": "PostToolUse"}

    with (
        patch.object(_hook_mod, "_call_sam_task_update", return_value=True) as mock_update,
        pytest.raises(SystemExit) as exc_info,
    ):
        # Act
        handle_activity_update(hook_input)

    # Assert — exited cleanly without calling MCP update
    assert exc_info.value.code == 0
    mock_update.assert_not_called()


# ---------------------------------------------------------------------------
# handle_subagent_stop — MCP write path
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
    """handle_subagent_stop exits 0 (not 2) when MCP state call fails."""
    # Arrange — plan_id is a str plan address (post-refactor shape)
    plan_id = "Pf4281187"

    from sam_schema.core.models import Task, TaskStatus

    mock_task = MagicMock(spec=Task)
    mock_task.status = TaskStatus.IN_PROGRESS

    hook_input: dict[str, Any] = {"cwd": str(tmp_path), "hook_event_name": "SubagentStop", "agent_transcript_path": ""}

    with (
        patch.object(_hook_mod, "_resolve_active_task_context", return_value=(None, plan_id, "T1", None, None)),
        patch.object(_hook_mod, "_call_sam_task_read", return_value=mock_task, create=True),
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
# handle_subagent_stop — file-path form regression
# ---------------------------------------------------------------------------


def test_handle_subagent_stop_file_path_plan_addr_extracted_and_mcp_read_called(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    """When plan_id is a path string containing a P-token, plan addr is extracted and _call_sam_task_read is called.

    Regression test: ensures path-string plan identifiers (from context files storing
    full YAML paths) continue to work after the refactor. The hook extracts the plan
    address from the path filename and routes through _call_sam_task_read.
    """
    # Arrange — plan_id is a path string (as stored by older context files)
    plan_file = tmp_path / "Pf4281187-feature.yaml"
    plan_file.write_text("tasks:\n- id: T1\n  status: in-progress\n  title: Test\n")
    # _resolve_active_task_context returns the path as a str (no Path wrapping)
    plan_id_str = str(plan_file)

    from sam_schema.core.models import Task, TaskStatus

    mock_task = MagicMock(spec=Task)
    mock_task.status = TaskStatus.IN_PROGRESS

    hook_input: dict[str, Any] = {"cwd": str(tmp_path), "hook_event_name": "SubagentStop", "agent_transcript_path": ""}

    mocker.patch.object(_hook_mod, "_resolve_active_task_context", return_value=(None, plan_id_str, "T1", None, None))
    mock_read = mocker.patch.object(_hook_mod, "_call_sam_task_read", create=True, return_value=mock_task)
    mocker.patch.object(_hook_mod, "_call_sam_task_state", return_value=True)
    mocker.patch.object(_hook_mod, "_call_sam_task_update", return_value=True)
    mocker.patch.object(_hook_mod, "_cleanup_active_task_context")

    # Act
    handle_subagent_stop(hook_input)

    # Assert — _call_sam_task_read was called with extracted plan address
    mock_read.assert_called_once()
    read_args = mock_read.call_args[0]
    assert read_args[0] == "Pf4281187"  # plan addr extracted from path filename
    assert read_args[1] == "T1"  # task_id


# ===========================================================================
# REFACTOR TARGET TESTS — RED on current code, GREEN after plan_id refactor
#
# Target behavior:
#   - _resolve_active_task_context returns (session_id, plan_id: str, task_id, ...)
#     NOT (session_id, task_file_path: Path, task_id, ...)
#   - handle_subagent_stop calls _call_sam_task_read(plan_id, task_id) via MCP
#   - handle_subagent_stop NEVER calls sam_get_task (filesystem read)
#
# All new tests use pytest-mock (mocker: MockerFixture) exclusively.
# ===========================================================================


# ---------------------------------------------------------------------------
# _call_sam_task_read — new MCP read helper (does not exist yet on current code)
# ---------------------------------------------------------------------------


def test_call_sam_task_read_success_returns_task_object(mocker: MockerFixture) -> None:
    """_call_sam_task_read returns a SamTask on a successful MCP response.

    Verifies the new helper wraps sam_task(action='read') subprocess call and
    deserialises the Task from the MCP JSON response. RED: function does not exist.
    """
    from sam_schema.core.models import Task, TaskStatus

    # Arrange — craft a minimal task JSON response matching MCP envelope
    task_data = {
        "id": "T1",
        "title": "Write the tests",
        "status": "in-progress",
        "agent": "python-pytest-architect",
        "acceptance_criteria": "All tests pass",
        "dependencies": [],
    }
    inner = {"task": task_data}
    outer = {"content": [{"text": json.dumps(inner)}]}
    response = CompletedProcess(args=[], returncode=0, stdout=json.dumps(outer), stderr="")

    mocker.patch("shutil.which", return_value="/usr/bin/uv")
    mocker.patch.object(Path, "exists", return_value=True)
    mock_run = mocker.patch("subprocess.run", return_value=response)

    # Act — call the not-yet-existing helper
    call_sam_task_read = getattr(_hook_mod, "_call_sam_task_read", None)
    assert call_sam_task_read is not None, "_call_sam_task_read does not exist on module — refactor required (RED)"
    result = call_sam_task_read("Pf4281187", "T1")

    # Assert
    assert result is not None
    assert isinstance(result, Task)
    assert result.status == TaskStatus.IN_PROGRESS
    mock_run.assert_called_once()


def test_call_sam_task_read_sends_correct_mcp_input_json(mocker: MockerFixture) -> None:
    """_call_sam_task_read sends plan and task in MCP input JSON with action='read'.

    RED: _call_sam_task_read does not exist on current code.
    """
    task_data = {
        "id": "T3",
        "title": "Refactor hook",
        "status": "not-started",
        "agent": "",
        "acceptance_criteria": "",
        "dependencies": [],
    }
    inner = {"task": task_data}
    outer = {"content": [{"text": json.dumps(inner)}]}
    response = CompletedProcess(args=[], returncode=0, stdout=json.dumps(outer), stderr="")

    mocker.patch("shutil.which", return_value="/usr/bin/uv")
    mocker.patch.object(Path, "exists", return_value=True)
    mock_run = mocker.patch("subprocess.run", return_value=response)

    call_sam_task_read = getattr(_hook_mod, "_call_sam_task_read", None)
    assert call_sam_task_read is not None, "_call_sam_task_read does not exist — refactor required (RED)"

    # Act
    call_sam_task_read("Pdec8934d", "T3")

    # Assert — correct MCP input JSON structure
    mock_run.assert_called_once()
    cmd = mock_run.call_args[0][0]
    assert "--target" in cmd
    assert "sam_task" in cmd
    assert "--input-json" in cmd
    idx = cmd.index("--input-json") + 1
    input_data = json.loads(cmd[idx])
    assert input_data["plan"] == "Pdec8934d"
    assert input_data["task"] == "T3"
    assert input_data["config"]["action"] == "read"


def test_call_sam_task_read_returns_none_when_uv_missing(mocker: MockerFixture) -> None:
    """_call_sam_task_read returns None gracefully when uv is not on PATH.

    Mirrors the graceful-failure pattern of _call_sam_task_state.
    RED: function does not exist on current code.
    """
    mocker.patch("shutil.which", return_value=None)

    call_sam_task_read = getattr(_hook_mod, "_call_sam_task_read", None)
    assert call_sam_task_read is not None, "_call_sam_task_read does not exist (RED)"

    result = call_sam_task_read("Pf4281187", "T1")

    assert result is None


def test_call_sam_task_read_returns_none_on_subprocess_failure(mocker: MockerFixture) -> None:
    """_call_sam_task_read returns None when the subprocess exits non-zero.

    RED: function does not exist on current code.
    """
    mocker.patch("shutil.which", return_value="/usr/bin/uv")
    mocker.patch.object(Path, "exists", return_value=True)
    mocker.patch("subprocess.run", return_value=CompletedProcess(args=[], returncode=1, stdout="", stderr="err"))

    call_sam_task_read = getattr(_hook_mod, "_call_sam_task_read", None)
    assert call_sam_task_read is not None, "_call_sam_task_read does not exist (RED)"

    result = call_sam_task_read("Pf4281187", "T1")

    assert result is None


def test_call_sam_task_read_returns_none_on_timeout(mocker: MockerFixture) -> None:
    """_call_sam_task_read returns None when the subprocess times out.

    RED: function does not exist on current code.
    """
    from subprocess import TimeoutExpired

    mocker.patch("shutil.which", return_value="/usr/bin/uv")
    mocker.patch.object(Path, "exists", return_value=True)
    mocker.patch("subprocess.run", side_effect=TimeoutExpired(cmd="uv", timeout=15))

    call_sam_task_read = getattr(_hook_mod, "_call_sam_task_read", None)
    assert call_sam_task_read is not None, "_call_sam_task_read does not exist (RED)"

    result = call_sam_task_read("Pf4281187", "T1")

    assert result is None


# ---------------------------------------------------------------------------
# handle_subagent_stop — MCP read path assertions (RED on current code)
# The critical behavioral assertions of the refactor.
# ---------------------------------------------------------------------------


def test_handle_subagent_stop_calls_mcp_read_not_sam_get_task_on_happy_path(mocker: MockerFixture) -> None:
    """handle_subagent_stop uses _call_sam_task_read(plan_id_str, task_id) not sam_get_task.

    Happy path: task is IN_PROGRESS → hook marks it COMPLETE.
    Asserts:
      1. _call_sam_task_read IS called with a plain str plan_id, not a Path.
      2. sam_get_task is NEVER called.
      3. plan_id arg is type str (not Path).

    RED on current code:
      - _call_sam_task_read does not exist on the module.
      - Current code receives Path from _resolve_active_task_context and crashes at
        task_file_path.is_absolute() with AttributeError: 'str' has no attribute 'is_absolute'
        because the refactored shape (str plan_id) is incompatible with current code.
      - Even if that were fixed, sam_get_task would be called instead of _call_sam_task_read.

    GREEN after refactor:
      - _call_sam_task_read exists and is called with (plan_id_str, task_id).
      - sam_get_task is never invoked.
    """
    from sam_schema.core.models import Task, TaskStatus

    # Arrange — resolved context carries plan_id as a plain string (post-refactor shape)
    plan_id = "Pf4281187"
    task_id = "T1"
    session_id = "sess-refactor-001"

    mock_task = mocker.MagicMock(spec=Task)
    mock_task.status = TaskStatus.IN_PROGRESS

    hook_input: dict[str, Any] = {"cwd": "/workspace", "hook_event_name": "SubagentStop", "agent_transcript_path": ""}

    # _resolve_active_task_context returns str plan_id (refactored shape)
    mocker.patch.object(
        _hook_mod, "_resolve_active_task_context", return_value=(session_id, plan_id, task_id, None, None)
    )

    # _call_sam_task_read replaces _fetch_task_for_stop_hook in refactored code.
    # create=True is required because the function does not exist on current code.
    mock_read = mocker.patch.object(_hook_mod, "_call_sam_task_read", create=True, return_value=mock_task)

    # sam_get_task must NEVER be called after refactor
    mock_get = mocker.patch.object(_hook_mod, "sam_get_task", create=True)

    mocker.patch.object(_hook_mod, "_call_sam_task_state", return_value=True)
    mocker.patch.object(_hook_mod, "_call_sam_task_update", return_value=True)
    mocker.patch.object(_hook_mod, "_cleanup_active_task_context")

    # Act — RED: current code raises AttributeError at task_file_path.is_absolute()
    #           because str has no is_absolute. The refactor removes that line.
    # GREEN: runs to completion without raising.
    handle_subagent_stop(hook_input)

    # Assert 1: _call_sam_task_read was called (RED: never called on current code)
    mock_read.assert_called_once()
    read_args = mock_read.call_args[0]

    # Assert 2: first arg is a plain string (not Path)
    assert isinstance(read_args[0], str), f"_call_sam_task_read first arg must be str, got {type(read_args[0])}"
    assert read_args[0] == plan_id, f"Expected plan_id '{plan_id}', got '{read_args[0]}'"
    assert read_args[1] == task_id

    # Assert 3: sam_get_task was NOT called (RED: called on current code)
    mock_get.assert_not_called()


def test_handle_subagent_stop_cascades_via_mcp_when_task_already_failed(mocker: MockerFixture) -> None:
    """handle_subagent_stop cascades via MCP when task is already FAILED.

    Asserts:
      1. _call_sam_task_read IS called (to discover FAILED status).
      2. sam_get_task is NEVER called.
      3. _cascade_failed_task is called, which routes through _call_sam_task_state.

    RED on current code:
      - _call_sam_task_read does not exist.
      - Current code raises AttributeError at task_file_path.is_absolute() before
        ever reaching the FAILED branch.
      - Even if patched past that, sam_get_task would be called instead.
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

    # Act — RED: AttributeError on current code; GREEN: runs to completion
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

    RED on current code:
      - _call_sam_task_read does not exist.
      - Current code raises AttributeError at task_file_path.is_absolute() because
        the refactored tuple shape passes str where Path is expected.
      - Even if past that, sam_get_task would be called instead of _call_sam_task_read.
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

    # Act — RED: AttributeError crashes before sys.exit(0) on current code
    #           GREEN: exits cleanly via sys.exit(0) after status check
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
# _resolve_active_task_context — returns str plan_id not Path (RED on current code)
# ---------------------------------------------------------------------------


def test_resolve_active_task_context_returns_str_plan_id_from_mcp(mocker: MockerFixture, tmp_path: Path) -> None:
    """_resolve_active_task_context returns plan_id as str, not Path, when MCP primary resolves.

    After refactor, the second element of the tuple is a str plan_id (e.g. 'Pf4281187').
    Current code wraps the MCP response value in Path() inside _call_sam_active_task_get,
    so the returned type is Path on current code.

    RED on current code:
      - _call_sam_active_task_get wraps 'task_file_path' from MCP JSON in Path() (line 378).
      - _resolve_active_task_context propagates that Path as task_file_path.
      - isinstance(plan_id, Path) is True on current code → assertion fails.

    GREEN after refactor:
      - _call_sam_active_task_get returns str plan_id without wrapping in Path().
      - isinstance(plan_id, str) is True and isinstance(plan_id, Path) is False.
    """
    # Arrange — transcript with session_id so MCP primary path is taken
    transcript = tmp_path / "agent-session.jsonl"
    transcript.write_text(json.dumps({"sessionId": "sess-abc123", "type": "user"}) + "\n")

    hook_input: dict[str, Any] = {
        "cwd": str(tmp_path),
        "hook_event_name": "SubagentStop",
        "agent_transcript_path": str(transcript),
    }

    # Build a realistic MCP response for sam_active_task(action='get')
    active_task = {
        "active_task": {
            "task_file_path": "Pf4281187",  # plan_id string, not a filesystem path
            "task_id": "T1",
            "parent_issue_number": None,
        }
    }
    inner_json = json.dumps(active_task)
    outer = {"content": [{"text": inner_json}]}
    mcp_response = CompletedProcess(args=[], returncode=0, stdout=json.dumps(outer), stderr="")

    # Patch subprocess.run so _call_sam_active_task_get uses our response
    mocker.patch("shutil.which", return_value="/usr/bin/uv")
    mocker.patch.object(Path, "exists", return_value=True)
    mocker.patch("subprocess.run", return_value=mcp_response)

    # Act — let _resolve_active_task_context → _call_sam_active_task_get run naturally
    result = _hook_mod._resolve_active_task_context(hook_input)

    # Assert — result is not None
    assert result is not None, "_resolve_active_task_context returned None unexpectedly"
    _session_id, plan_id, task_id, _parent_issue, _context_file = result

    # RED on current code: Path("Pf4281187") is a Path, so isinstance(plan_id, Path) is True
    # GREEN after refactor: plan_id is a plain str
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
    without any message when the MCP read failed.
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
    assert f"could not read task {task_id} from plan {plan_id} via MCP" in captured.err
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
    # Arrange — context file pointing to a plan with a valid plan address token
    plan_file = tmp_path / "Pf4281187-feature.yaml"
    plan_file.write_text("tasks:\n- id: T1\n  status: in-progress\n  title: Test\n")

    monkeypatch.setenv("DH_STATE_HOME", str(tmp_path / "dh_state"))
    import dh_paths

    context_dir = dh_paths.context_dir()
    context_dir.mkdir(parents=True, exist_ok=True)
    session_id = "sess-no-task"
    context_file = context_dir / f"active-task-{session_id}.json"
    context_file.write_text(json.dumps({"task_file_path": str(plan_file), "task_id": "T1"}))

    hook_input: dict[str, Any] = {"cwd": str(tmp_path), "session_id": session_id, "hook_event_name": "PostToolUse"}

    mocker.patch.object(_hook_mod, "_call_sam_task_read", create=True, return_value=None)
    mock_update = mocker.patch.object(_hook_mod, "_call_sam_task_update", return_value=True)

    # Act
    handle_activity_update(hook_input)

    # Assert — diagnostic visible on stderr
    captured = capsys.readouterr()
    assert "could not read task T1 from plan Pf4281187 via MCP" in captured.err
    assert "skipping" in captured.err

    # Assert — update still proceeds (best-effort activity tracking continues)
    mock_update.assert_called_once()
