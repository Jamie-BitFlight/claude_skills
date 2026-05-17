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


def test_extract_task_info_from_prompt_plan_address_skill_invocation() -> None:
    """Skill(skill='start-task', args='Pdec8934d --task T01') → (Path('Pdec8934d'), 'T01')."""
    # Arrange
    prompt = """Fix a confirmed code bug.

Skill(skill="start-task", args="Pdec8934d --task T01")

Working directory: /home/user/claude_skills"""

    # Act
    task_file, task_id = extract_task_info_from_prompt(prompt)

    # Assert
    assert task_id == "T01"
    assert task_file is not None
    assert task_file == Path("Pdec8934d")


def test_extract_task_info_from_prompt_plan_address_different_task() -> None:
    """Skill(skill='start-task', args='Pdec8934d --task T22') → (Path('Pdec8934d'), 'T22')."""
    # Arrange
    prompt = "Skill(skill='start-task', args='Pdec8934d --task T22')"

    # Act
    task_file, task_id = extract_task_info_from_prompt(prompt)

    # Assert
    assert task_id == "T22"
    assert task_file is not None
    assert task_file == Path("Pdec8934d")


def test_extract_task_info_from_prompt_slash_command_plan_address() -> None:
    """/start-task Pdec8934d --task T01 (literal slash-command form with plan address)."""
    # Arrange
    prompt = "Run /start-task Pdec8934d --task T01 in the working directory."

    # Act
    task_file, task_id = extract_task_info_from_prompt(prompt)

    # Assert
    assert task_id == "T01"
    assert task_file is not None
    assert task_file == Path("Pdec8934d")


def test_extract_task_info_from_prompt_plan_address_longer_hex() -> None:
    """Plan address with longer hex ID is matched correctly."""
    # Arrange
    prompt = 'Skill(skill="start-task", args="Pf4281187abcd --task T05")'

    # Act
    task_file, task_id = extract_task_info_from_prompt(prompt)

    # Assert
    assert task_id == "T05"
    assert task_file is not None
    assert task_file == Path("Pf4281187abcd")


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
        patch.object(_hook_mod, "sam_get_task", return_value=mock_task),
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

    from sam_schema.core.models import Task, TaskStatus

    mock_task = MagicMock(spec=Task)
    mock_task.status = TaskStatus.IN_PROGRESS

    with (
        patch.object(_hook_mod, "sam_get_task", return_value=mock_task),
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
    # Arrange
    plan_file = tmp_path / "Pf4281187-feature.yaml"
    plan_file.write_text("tasks:\n- id: T1\n  status: in-progress\n  title: Test\n")

    from sam_schema.core.models import Task, TaskStatus

    mock_task = MagicMock(spec=Task)
    mock_task.status = TaskStatus.IN_PROGRESS

    hook_input: dict[str, Any] = {"cwd": str(tmp_path), "hook_event_name": "SubagentStop", "agent_transcript_path": ""}

    with (
        patch.object(_hook_mod, "_resolve_active_task_context", return_value=(None, plan_file, "T1", None, None)),
        patch.object(_hook_mod, "sam_get_task", return_value=mock_task),
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
    # Arrange
    plan_file = tmp_path / "Pf4281187-feature.yaml"
    plan_file.write_text("tasks:\n- id: T1\n  status: in-progress\n  title: Test\n")

    from sam_schema.core.models import Task, TaskStatus

    mock_task = MagicMock(spec=Task)
    mock_task.status = TaskStatus.IN_PROGRESS

    hook_input: dict[str, Any] = {"cwd": str(tmp_path), "hook_event_name": "SubagentStop", "agent_transcript_path": ""}

    with (
        patch.object(_hook_mod, "_resolve_active_task_context", return_value=(None, plan_file, "T1", None, None)),
        patch.object(_hook_mod, "sam_get_task", return_value=mock_task),
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
# _is_plan_address — predicate for bare plan address strings
# ---------------------------------------------------------------------------


def test_is_plan_address_standard_short_hex_returns_true() -> None:
    """Pdec8934d is a valid plan address — 8 hex digits after P."""
    # Arrange / Act / Assert
    assert _hook_mod._is_plan_address("Pdec8934d") is True  # type: ignore[attr-defined]


def test_is_plan_address_seven_hex_digits_returns_true() -> None:
    """P1a2b3c4 (7 hex digits) is a valid plan address."""
    # Arrange / Act / Assert
    assert _hook_mod._is_plan_address("P1a2b3c4") is True  # type: ignore[attr-defined]


def test_is_plan_address_longer_hex_returns_true() -> None:
    """Pf4281187abcd (12 hex digits) is a valid plan address."""
    # Arrange / Act / Assert
    assert _hook_mod._is_plan_address("Pf4281187abcd") is True  # type: ignore[attr-defined]


def test_is_plan_address_file_path_form_returns_false() -> None:
    """plan/P60d669b9.yaml contains a plan address but is a file path — must return False."""
    # Arrange / Act / Assert
    assert _hook_mod._is_plan_address("plan/P60d669b9.yaml") is False  # type: ignore[attr-defined]


def test_is_plan_address_bare_P_no_hex_digits_returns_false() -> None:
    """'P' with no following hex digits is not a valid plan address."""
    # Arrange / Act / Assert
    assert _hook_mod._is_plan_address("P") is False  # type: ignore[attr-defined]


def test_is_plan_address_empty_string_returns_false() -> None:
    """Empty string is not a valid plan address."""
    # Arrange / Act / Assert
    assert _hook_mod._is_plan_address("") is False  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# handle_subagent_stop — plan-address path (currently broken: exits 0 at exists())
# ---------------------------------------------------------------------------


def test_handle_subagent_stop_plan_address_calls_sam_task_state_directly(tmp_path: Path, mocker: MockerFixture) -> None:
    """When task_file_path is a bare plan address, _call_sam_task_state is called directly.

    This test targets the CURRENTLY BROKEN path: handle_subagent_stop receives
    Path("Pdec8934d") from _resolve_active_task_context, then constructs
    full_path = cwd / Path("Pdec8934d"). That path does not exist on disk, so
    the current code exits 0 before calling _call_sam_task_state.

    After the fix, _is_plan_address("Pdec8934d") returns True and the code must
    skip the exists() check and call _call_sam_task_state("Pdec8934d", "T01", "complete").
    """
    # Arrange — transcript with Skill() invocation using plan address
    plan_address = "Pdec8934d"
    task_id = "T01"

    hook_input: dict[str, Any] = {"cwd": str(tmp_path), "hook_event_name": "SubagentStop", "agent_transcript_path": ""}

    # _resolve_active_task_context returns the plan address as a bare Path
    mocker.patch.object(
        _hook_mod, "_resolve_active_task_context", return_value=(None, Path(plan_address), task_id, None, None)
    )
    mock_state = mocker.patch.object(_hook_mod, "_call_sam_task_state", return_value=True)
    mock_update = mocker.patch.object(_hook_mod, "_call_sam_task_update", return_value=True)
    mocker.patch.object(_hook_mod, "_cleanup_active_task_context")
    # _fetch_task_for_stop_hook must NOT be called for plan-address path
    mock_fetch = mocker.patch.object(_hook_mod, "_fetch_task_for_stop_hook")

    # Act
    handle_subagent_stop(hook_input)

    # Assert — _call_sam_task_state called with plan address (not a file path)
    mock_state.assert_called_once_with(plan_address, task_id, "complete")
    # _call_sam_task_update called for timestamp
    mock_update.assert_called_once()
    update_args = mock_update.call_args[0]
    assert update_args[0] == plan_address
    assert update_args[1] == task_id
    assert "completed" in update_args[2]
    # _fetch_task_for_stop_hook must be skipped for plan-address path
    mock_fetch.assert_not_called()


def test_handle_subagent_stop_plan_address_state_fails_exits_zero(tmp_path: Path, mocker: MockerFixture) -> None:
    """When plan-address path _call_sam_task_state returns False, hook exits 0 (best-effort).

    After the fix, the hook should call cleanup and exit 0 — not exit 2 — when
    the MCP state write fails. This mirrors existing behaviour for the file-path path.
    """
    # Arrange
    plan_address = "Pdec8934d"
    task_id = "T01"

    hook_input: dict[str, Any] = {"cwd": str(tmp_path), "hook_event_name": "SubagentStop", "agent_transcript_path": ""}

    mocker.patch.object(
        _hook_mod, "_resolve_active_task_context", return_value=(None, Path(plan_address), task_id, None, None)
    )
    mocker.patch.object(_hook_mod, "_call_sam_task_state", return_value=False)
    mock_update = mocker.patch.object(_hook_mod, "_call_sam_task_update", return_value=True)
    mock_cleanup = mocker.patch.object(_hook_mod, "_cleanup_active_task_context")

    # Act
    with pytest.raises(SystemExit) as exc_info:
        handle_subagent_stop(hook_input)

    # Assert — exits 0 (not 2); update skipped on state failure; cleanup called
    assert exc_info.value.code == 0
    mock_update.assert_not_called()
    mock_cleanup.assert_called_once()


# ---------------------------------------------------------------------------
# handle_subagent_stop — file-path form regression
# ---------------------------------------------------------------------------


def test_handle_subagent_stop_file_path_calls_fetch_task_for_stop_hook(tmp_path: Path, mocker: MockerFixture) -> None:
    """When task_file_path is a .yaml file path, _fetch_task_for_stop_hook IS called.

    Regression test: ensures the file-path branch continues to work after the
    plan-address short-circuit is added. _fetch_task_for_stop_hook must be called
    (not skipped) for file-path forms.
    """
    # Arrange — plan file on disk
    plan_file = tmp_path / "Pf4281187-feature.yaml"
    plan_file.write_text("tasks:\n- id: T1\n  status: in-progress\n  title: Test\n")

    from sam_schema.core.models import Task, TaskStatus

    mock_task = MagicMock(spec=Task)
    mock_task.status = TaskStatus.IN_PROGRESS

    hook_input: dict[str, Any] = {"cwd": str(tmp_path), "hook_event_name": "SubagentStop", "agent_transcript_path": ""}

    mocker.patch.object(_hook_mod, "_resolve_active_task_context", return_value=(None, plan_file, "T1", None, None))
    # _fetch_task_for_stop_hook should be called and return mock_task
    mock_fetch = mocker.patch.object(_hook_mod, "_fetch_task_for_stop_hook", return_value=mock_task)
    mocker.patch.object(_hook_mod, "_call_sam_task_state", return_value=True)
    mocker.patch.object(_hook_mod, "_call_sam_task_update", return_value=True)
    mocker.patch.object(_hook_mod, "_cleanup_active_task_context")

    # Act
    handle_subagent_stop(hook_input)

    # Assert — _fetch_task_for_stop_hook was called with the resolved file path
    mock_fetch.assert_called_once()
    fetch_args = mock_fetch.call_args[0]
    assert fetch_args[0] == plan_file  # full_path
    assert fetch_args[1] == "T1"  # task_id


# ---------------------------------------------------------------------------
# handle_subagent_stop — STRICT profile skipped on plan-address path
# ---------------------------------------------------------------------------


def test_handle_subagent_stop_strict_not_called_for_plan_address_path(mocker: MockerFixture) -> None:
    """STRICT profile pre-completion checks are skipped when task_file_path is a bare plan address.

    The plan-address branch (lines 1003-1005) returns early via
    _complete_task_via_plan_address before reaching the STRICT profile check at
    line 1025-1027. This ensures filesystem-free paths never attempt to open a
    task file for validation.
    """
    # Arrange
    plan_address = "Pdec8934d"
    task_id = "T01"
    hook_input: dict[str, Any] = {"cwd": "/tmp", "hook_event_name": "SubagentStop", "agent_transcript_path": ""}

    mocker.patch.object(
        _hook_mod, "_resolve_active_task_context", return_value=(None, Path(plan_address), task_id, None, None)
    )
    mock_complete = mocker.patch.object(_hook_mod, "_complete_task_via_plan_address")
    mock_strict = mocker.patch.object(_hook_mod, "run_strict_pre_completion_checks")

    # Act
    handle_subagent_stop(hook_input, profile=HookProfile.STRICT)

    # Assert — plan-address branch taken; strict checks must not run
    mock_complete.assert_called_once_with(plan_address, task_id, None, None)
    mock_strict.assert_not_called()


# ---------------------------------------------------------------------------
# handle_activity_update — plan-address guard exits 0 without MCP write
# ---------------------------------------------------------------------------


def test_handle_activity_update_exits_silently_when_context_contains_plan_address(mocker: MockerFixture) -> None:
    """handle_activity_update exits 0 without calling _call_sam_task_update when context file
    holds a bare plan address as task_file_path.

    The defensive guard at lines 1076-1081 detects this form and exits cleanly.
    This prevents a path-existence check against a non-filesystem address and
    avoids triggering an MCP write with an invalid path.
    """
    # Arrange
    hook_input: dict[str, Any] = {"cwd": "/tmp", "session_id": "sess-test", "hook_event_name": "PostToolUse"}
    # read_task_context returns a bare plan address (the form stored in the context file)
    mocker.patch.object(_hook_mod, "read_task_context", return_value=(Path("Pdec8934d"), "T01"))
    mock_update = mocker.patch.object(_hook_mod, "_call_sam_task_update")

    # Act / Assert — exits 0 without calling MCP update
    with pytest.raises(SystemExit) as exc_info:
        handle_activity_update(hook_input)

    assert exc_info.value.code == 0
    mock_update.assert_not_called()


# ---------------------------------------------------------------------------
# _complete_task_via_plan_address — calls update after successful state write
# ---------------------------------------------------------------------------


def test_complete_task_via_plan_address_calls_update_after_state_write(mocker: MockerFixture) -> None:
    """_complete_task_via_plan_address calls _call_sam_task_update with completed timestamp
    only after _call_sam_task_state returns True.

    Verifies the MCP update carries the plan_addr, task_id, and a 'completed' key
    so that callers of the plan-address completion path get the same timestamp
    written as the file-path completion path.
    """
    # Arrange
    plan_addr = "Pdec8934d"
    task_id = "T01"

    mock_state = mocker.patch.object(_hook_mod, "_call_sam_task_state", return_value=True)
    mock_update = mocker.patch.object(_hook_mod, "_call_sam_task_update", return_value=True)
    mocker.patch.object(_hook_mod, "_cleanup_active_task_context")

    # Act
    _hook_mod._complete_task_via_plan_address(plan_addr, task_id, None, None)

    # Assert — state written first, then update with completed timestamp
    mock_state.assert_called_once_with(plan_addr, task_id, "complete")
    mock_update.assert_called_once()
    update_args = mock_update.call_args[0]
    assert update_args[0] == plan_addr
    assert update_args[1] == task_id
    assert "completed" in update_args[2]
