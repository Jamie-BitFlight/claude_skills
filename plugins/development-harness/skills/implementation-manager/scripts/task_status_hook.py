#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pydantic>=2.12.3",
#   "ruamel.yaml>=0.18.0",
# ]
# ///
"""Task Status Hook - Update task status and timestamps automatically.

This hook script handles multiple hook events:
- SubagentStop: Parse prompt for task info, set status to COMPLETE, add Completed timestamp
- PostToolUse (Write|Edit|Bash): Update LastActivity timestamp using context file

All task state WRITES route through the SAM MCP server via fastmcp CLI subprocess,
making the hook backend-agnostic (ADR-001: hooks must not write directly to YAML).

Context File Mechanism:
- The /start-task command writes task context to ~/.dh/projects/{slug}/context/active-task-{session_id}.json
- PostToolUse hooks read from this file to know which task is active
- SubagentStop extracts the sub-agent's session_id from agent_transcript_path, then looks up
  active-task-{session_id}.json directly (targeted lookup, not glob-all)

Usage:
    Called automatically via hooks configuration.
    Receives JSON via stdin with hook context.

Exit Codes:
    0: Success
    2: Error (stderr message shown to Claude)
"""

from __future__ import annotations

import contextlib
import enum
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_DH_PLUGIN_DIR = Path(__file__).resolve().parents[3]
if str(_DH_PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(_DH_PLUGIN_DIR))

_SAM_RUN_SERVER_PATH = _DH_PLUGIN_DIR / "scripts" / "run_sam_server.py"

import dh_paths as _dh_paths

_HOOK_REPO_ROOT = Path(__file__).resolve().parents[5]
_HOOK_SAM_PACKAGES_DIR = str(_HOOK_REPO_ROOT / "packages")
if _HOOK_SAM_PACKAGES_DIR not in sys.path:
    sys.path.insert(0, _HOOK_SAM_PACKAGES_DIR)

# Import directly from submodules for concrete types (avoids lazy __getattr__ object).
from sam_schema.core.addressing import AddressingError, resolve_plan_address
from sam_schema.core.models import Task as SamTask, TaskStatus as SamTaskStatus

# Alphanumeric task ID pattern: "1", "1.1", "T1", "P0-T01", etc.
_TASK_ID_RE = r"[A-Za-z0-9]+(?:[-.][\dA-Za-z]+)*"


class HookProfile(enum.StrEnum):
    """Runtime profile controlling which hook handlers are active.

    Profiles are selected via the CLAUDE_SKILLS_HOOK_PROFILE environment variable.
    Default when unset or empty: STANDARD.
    """

    MINIMAL = "minimal"
    STANDARD = "standard"
    STRICT = "strict"


HOOK_ID_POST_TOOL_USE = "task-status:post-tool-use"
HOOK_ID_SUBAGENT_STOP = "task-status:subagent-stop"

_EVENT_TO_HOOK_ID: dict[str, str] = {"PostToolUse": HOOK_ID_POST_TOOL_USE, "SubagentStop": HOOK_ID_SUBAGENT_STOP}


def resolve_profile() -> HookProfile:
    """Read CLAUDE_SKILLS_HOOK_PROFILE and return the corresponding HookProfile.

    Returns HookProfile.STANDARD when the variable is unset or empty.
    Prints a warning to stderr and returns STANDARD for any unrecognised value.

    Returns:
        The active HookProfile.
    """
    raw = os.environ.get("CLAUDE_SKILLS_HOOK_PROFILE", "").strip()
    if not raw:
        return HookProfile.STANDARD
    try:
        return HookProfile(raw)
    except ValueError:
        print(f'[hook] Unknown profile "{raw}", using "standard"', file=sys.stderr)
        return HookProfile.STANDARD


def parse_disabled_hooks() -> set[str]:
    """Read CLAUDE_SKILLS_DISABLED_HOOKS and return the set of disabled hook IDs.

    Splits on commas, strips whitespace per segment, excludes empty segments.
    Unknown IDs are silently included — callers check presence against known IDs.

    Returns:
        Set of disabled hook ID strings. Empty when unset or empty.
    """
    raw = os.environ.get("CLAUDE_SKILLS_DISABLED_HOOKS", "")
    if not raw.strip():
        return set()
    return {segment.strip() for segment in raw.split(",") if segment.strip()}


def should_skip_hook(event_name: str, profile: HookProfile, disabled_hooks: set[str]) -> bool:
    """Return True if the hook for this event should be skipped.

    Disabled hooks take precedence over profile rules.

    Args:
        event_name: Value of hook_event_name from the hook input (e.g. "PostToolUse").
        profile: The active HookProfile.
        disabled_hooks: Set of hook IDs to skip unconditionally.

    Returns:
        True if the hook should exit 0 without running its handler.
    """
    hook_id = _EVENT_TO_HOOK_ID.get(event_name)

    # Disabled hooks take precedence — check first.
    if hook_id and hook_id in disabled_hooks:
        return True

    # Profile rules: minimal skips PostToolUse only.
    return bool(profile == HookProfile.MINIMAL and event_name == "PostToolUse")


def run_strict_pre_completion_checks(task: SamTask, task_id: str) -> list[str]:
    """Run pre-completion validation checks for strict mode.

    Called when CLAUDE_SKILLS_HOOK_PROFILE=strict and a SubagentStop event fires.
    Warnings are observational — they do not prevent task completion.

    Args:
        task: The already-loaded SamTask object (avoids a second MCP round-trip).
        task_id: Task ID being completed (used in warning messages).

    Returns:
        List of warning strings. Empty list means all checks passed.
    """
    warnings: list[str] = []

    # Check 1: task must have been claimed (status should be IN_PROGRESS, not NOT_STARTED).
    if task.status == SamTaskStatus.NOT_STARTED:
        warnings.append(
            f"[hook] strict: task {task_id} status is not-started — task may not have been claimed before completion"
        )

    # Check 2: acceptance criteria must be non-empty.
    acceptance_criteria = getattr(task, "acceptance_criteria", "") or ""
    if not acceptance_criteria.strip():
        warnings.append(f"[hook] strict: task {task_id} has no acceptance criteria defined")

    return warnings


def parse_hook_input() -> dict[str, Any]:
    """Parse JSON input from stdin.

    Returns:
        Dictionary with hook input data.

    Raises:
        ValueError: If stdin is empty or invalid JSON.
    """
    stdin_data = sys.stdin.read()
    if not stdin_data.strip():
        raise ValueError("No input received on stdin")

    result: dict[str, Any] = json.loads(stdin_data)
    return result


def _plan_arg_to_path(plan_arg: str) -> Path | None:
    """Convert a plan argument string (file path or plan address) to an absolute Path.

    File path form (.md/.yaml) is returned as ``Path`` directly.
    Plan address form (e.g. ``Pdec8934d``) is resolved via ``resolve_plan_address()``.

    Returns:
        Resolved ``Path``, or ``None`` when resolution fails (plan not found in DH
        state directory or plan directory does not exist).
    """
    if plan_arg.endswith((".md", ".yaml")):
        return Path(plan_arg)
    try:
        return resolve_plan_address(plan_arg, _dh_paths.plan_dir())
    except (AddressingError, FileNotFoundError):
        print(
            f"[hook] extract_task_info: plan address {plan_arg!r} not found in {_dh_paths.plan_dir()} — skipping",
            file=sys.stderr,
        )
        return None


def extract_task_info_from_prompt(prompt: str) -> tuple[Path | None, str | None]:
    """Extract task file path and task ID from sub-agent prompt.

    Accepts two arg forms for the plan argument:
    - File path form: ``<path>.md`` or ``<path>.yaml`` — returned as ``Path`` directly.
    - Plan address form: ``P[0-9a-f]+`` (e.g. ``Pdec8934d``) — resolved to the actual
      filesystem path via ``resolve_plan_address()``.

    Args:
        prompt: The sub-agent's prompt string.

    Returns:
        Tuple of (task_file_path, task_id) or (None, None) if not extractable.
        Returns (None, None) when a plan address is found but cannot be resolved
        (plan not found in the DH state directory).
    """
    if not prompt:
        return None, None

    # Plan argument pattern: file path (.md/.yaml) OR plan address (P<hex>).
    # Named group ``plan`` captures whichever form is present.
    # re.IGNORECASE: plan address prefix P is case-insensitive (e.g. PDEADBEef).
    PLAN_ARG_RE = r"(?P<plan>(?:[^\s\"']+\.(?:md|yaml))|(?:P[0-9a-f]+))"

    # Pattern 1: /start-task <plan-arg> --task <id>  (literal slash-command)
    # Matches both file-path form and plan-address form.
    match = re.search(rf"/start-task\s+{PLAN_ARG_RE}(?:\s+--task\s+(?P<task_id>{_TASK_ID_RE}))?", prompt, re.IGNORECASE)
    if match:
        task_file = _plan_arg_to_path(match.group("plan"))
        if task_file is None:
            return None, None
        return task_file, match.group("task_id")

    # Pattern 2: Skill(skill="start-task", args="<plan-arg> --task <id>")
    # The orchestrator invokes start-task via the Skill tool, not as a literal command.
    # Matches both file-path form and plan-address form.
    skill_match = re.search(
        rf'Skill\(\s*skill\s*=\s*["\']start-task["\']\s*,\s*args\s*=\s*["\']'
        rf"{PLAN_ARG_RE}(?:\s+--task\s+(?P<task_id>{_TASK_ID_RE}))?"
        rf'["\']',
        prompt,
        re.IGNORECASE,
    )
    if skill_match:
        task_file = _plan_arg_to_path(skill_match.group("plan"))
        if task_file is None:
            return None, None
        return task_file, skill_match.group("task_id")

    return None, None


def get_context_file_path(cwd: Path, session_id: str) -> Path:
    """Get the path to the active task context file.

    Uses dh_paths.context_dir() which resolves to
    ``~/.dh/projects/{slug}/context/`` (or DH_STATE_HOME override).
    The ``cwd`` argument is accepted for call-site compatibility but is not
    used — dh_paths detects the project root from git.

    Args:
        cwd: Current working directory (unused; kept for compatibility).
        session_id: Session ID from hook input.

    Returns:
        Path to the context file under the DH state context directory.
    """
    return _dh_paths.context_dir() / f"active-task-{session_id}.json"


def read_task_context(cwd: Path, session_id: str) -> tuple[str | None, str | None]:
    """Read task info from context file.

    Args:
        cwd: Current working directory.
        session_id: Session ID from hook input.

    Returns:
        Tuple of (plan_id_or_path, task_id) or (None, None) if not found.
        The first element is the raw string value from the JSON context file
        (plan address or filesystem path).
    """
    context_file = get_context_file_path(cwd, session_id)
    if not context_file.exists():
        return None, None

    try:
        context_data: dict[str, str] = json.loads(context_file.read_text(encoding="utf-8"))
        task_file = context_data.get("task_file_path")
        task_id = context_data.get("task_id")
        if task_file and task_id:
            return task_file, task_id
    except json.JSONDecodeError:
        pass

    return None, None


def _call_sam_active_task_get(session_id: str, timeout: int = 10) -> tuple[str | None, str | None, str | int | None]:
    """Retrieve active task context via fastmcp CLI call to sam_active_task(action='get').

    Primary retrieval path for SubagentStop. Returns parsed fields from the
    ``ActiveTaskContext`` on success, or ``(None, None, None)`` if the call fails
    or no active task is stored for the session.

    Args:
        session_id: Sub-agent session identifier. Empty string is normalised to
            ``"_default"`` sentinel.
        timeout: Subprocess timeout in seconds.

    Returns:
        Tuple of ``(plan_id, task_id, parent_issue_number)`` where ``plan_id``
        is the raw string value from the MCP response (plan address or path).
        All ``None`` when the call fails or active task is not set.
    """
    uv = shutil.which("uv")
    if uv is None or not _SAM_RUN_SERVER_PATH.exists():
        return None, None, None

    resolved = session_id or "_default"
    input_data = json.dumps({"config": {"action": "get"}, "session_id": resolved})
    env = os.environ.copy()
    env["FASTMCP_SHOW_SERVER_BANNER"] = "false"
    env["FASTMCP_LOG_ENABLED"] = "false"

    try:
        result = subprocess.run(
            [
                uv,
                "run",
                "fastmcp",
                "call",
                "--command",
                f"uv run --script {_SAM_RUN_SERVER_PATH}",
                "--target",
                "sam_active_task",
                "--input-json",
                input_data,
                "--json",
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            check=False,
        )
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError):
        return None, None, None

    if result.returncode != 0:
        return None, None, None

    try:
        outer = json.loads(result.stdout)
        text = outer["content"][0]["text"]
        data: dict[str, Any] = json.loads(text)
        active = data.get("active_task")
        if not active:
            return None, None, None
        task_file_raw = active.get("task_file_path")
        task_id = active.get("task_id")
        if task_file_raw and task_id:
            parent_issue: str | int | None = active.get("parent_issue_number")
            return task_file_raw, task_id, parent_issue
    except (json.JSONDecodeError, KeyError, IndexError):
        pass

    return None, None, None


def _call_sam_active_task_clear(session_id: str, timeout: int = 10) -> bool:
    """Clear active task context via fastmcp CLI call to sam_active_task(action='clear').

    Best-effort cleanup after SubagentStop completes. Never raises.

    Args:
        session_id: Sub-agent session identifier. Empty string is normalised to
            ``"_default"`` sentinel.
        timeout: Subprocess timeout in seconds.

    Returns:
        ``True`` if the active task was successfully cleared, ``False`` otherwise.
    """
    uv = shutil.which("uv")
    if uv is None or not _SAM_RUN_SERVER_PATH.exists():
        return False

    resolved = session_id or "_default"
    input_data = json.dumps({"config": {"action": "clear"}, "session_id": resolved})
    env = os.environ.copy()
    env["FASTMCP_SHOW_SERVER_BANNER"] = "false"
    env["FASTMCP_LOG_ENABLED"] = "false"

    try:
        result = subprocess.run(
            [
                uv,
                "run",
                "fastmcp",
                "call",
                "--command",
                f"uv run --script {_SAM_RUN_SERVER_PATH}",
                "--target",
                "sam_active_task",
                "--input-json",
                input_data,
                "--json",
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            check=False,
        )
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError):
        return False
    else:
        return result.returncode == 0


def _extract_plan_addr_from_path(task_file_path: Path) -> str | None:
    """Extract plan address from a task file path.

    Searches for a hex plan ID token (e.g. ``Pf4281187``) in the filename.

    Args:
        task_file_path: Path to the plan file.

    Returns:
        Plan address string (e.g. ``"Pf4281187"``) or ``None`` if not found.
    """
    m = re.search(r"(P[0-9a-f]+)", Path(task_file_path).name, re.IGNORECASE)
    return m.group(1) if m else None


def _call_sam_task_state(plan_addr: str, task_id: str, status: SamTaskStatus, timeout: int = 15) -> bool:
    """Update task status via fastmcp CLI call to sam_task(action='state').

    Routes state writes through the SAM MCP server, keeping the hook
    backend-agnostic. The server handles downstream skip cascades when
    ``status="failed"``.

    Args:
        plan_addr: Plan address (e.g. ``"Pf4281187"``).
        task_id: Task ID within the plan (e.g. ``"T1"``).
        status: New task status string (e.g. ``"complete"``, ``"skipped"``).
        timeout: Subprocess timeout in seconds.

    Returns:
        ``True`` if the MCP call succeeded, ``False`` on any failure.
    """
    uv = shutil.which("uv")
    if uv is None or not _SAM_RUN_SERVER_PATH.exists():
        return False

    input_data = json.dumps({"plan": plan_addr, "task": task_id, "config": {"action": "state", "status": status}})
    env = os.environ.copy()
    env["FASTMCP_SHOW_SERVER_BANNER"] = "false"
    env["FASTMCP_LOG_ENABLED"] = "false"

    try:
        result = subprocess.run(
            [
                uv,
                "run",
                "fastmcp",
                "call",
                "--command",
                f"uv run --script {_SAM_RUN_SERVER_PATH}",
                "--target",
                "sam_task",
                "--input-json",
                input_data,
                "--json",
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            check=False,
        )
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError):
        return False

    if result.returncode != 0:
        print(f"[hook] sam_task state={status} failed for {plan_addr}/{task_id}", file=sys.stderr)
        return False

    try:
        outer = json.loads(result.stdout)
        json.loads(outer["content"][0]["text"])
    except (json.JSONDecodeError, KeyError, IndexError):
        print(f"[hook] sam_task state: unexpected response for {plan_addr}/{task_id}", file=sys.stderr)
        return False

    return True


def _call_sam_task_update(plan_addr: str, task_id: str, set_fields: dict[str, Any], timeout: int = 15) -> bool:
    """Update task fields via fastmcp CLI call to sam_task(action='update').

    Routes field writes through the SAM MCP server, keeping the hook
    backend-agnostic.

    Args:
        plan_addr: Plan address (e.g. ``"Pf4281187"``).
        task_id: Task ID within the plan (e.g. ``"T1"``).
        set_fields: Field name/value pairs to patch on the task.
        timeout: Subprocess timeout in seconds.

    Returns:
        ``True`` if the MCP call succeeded, ``False`` on any failure.
    """
    uv = shutil.which("uv")
    if uv is None or not _SAM_RUN_SERVER_PATH.exists():
        return False

    input_data = json.dumps({
        "plan": plan_addr,
        "task": task_id,
        "config": {"action": "update", "set_fields_json": set_fields},
    })
    env = os.environ.copy()
    env["FASTMCP_SHOW_SERVER_BANNER"] = "false"
    env["FASTMCP_LOG_ENABLED"] = "false"

    try:
        result = subprocess.run(
            [
                uv,
                "run",
                "fastmcp",
                "call",
                "--command",
                f"uv run --script {_SAM_RUN_SERVER_PATH}",
                "--target",
                "sam_task",
                "--input-json",
                input_data,
                "--json",
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            check=False,
        )
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError):
        return False

    if result.returncode != 0:
        print(f"[hook] sam_task update failed for {plan_addr}/{task_id}", file=sys.stderr)
        return False

    try:
        outer = json.loads(result.stdout)
        json.loads(outer["content"][0]["text"])
    except (json.JSONDecodeError, KeyError, IndexError):
        print(f"[hook] sam_task update: unexpected response for {plan_addr}/{task_id}", file=sys.stderr)
        return False

    return True


def _call_sam_task_read(plan_id: str, task_id: str, timeout: int = 15) -> SamTask | None:
    """Read a task via fastmcp CLI call to sam_task(action='read').

    Routes task reads through the SAM MCP server, keeping the hook backend-agnostic.
    Returns the parsed Task object on success, None on any failure.

    Args:
        plan_id: Plan address (e.g. ``"Pf4281187"``).
        task_id: Task ID within the plan (e.g. ``"T1"``).
        timeout: Subprocess timeout in seconds.

    Returns:
        The parsed ``SamTask`` on success, ``None`` on any failure.
    """
    uv = shutil.which("uv")
    if uv is None or not _SAM_RUN_SERVER_PATH.exists():
        return None

    input_data = json.dumps({"plan": plan_id, "task": task_id, "config": {"action": "read"}})
    env = os.environ.copy()
    env["FASTMCP_SHOW_SERVER_BANNER"] = "false"
    env["FASTMCP_LOG_ENABLED"] = "false"

    try:
        result = subprocess.run(
            [
                uv,
                "run",
                "fastmcp",
                "call",
                "--command",
                f"uv run --script {_SAM_RUN_SERVER_PATH}",
                "--target",
                "sam_task",
                "--input-json",
                input_data,
                "--json",
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            check=False,
        )
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError):
        return None

    if result.returncode != 0:
        return None

    try:
        outer = json.loads(result.stdout)
        text = outer["content"][0]["text"]
        data: dict[str, Any] = json.loads(text)
        task_data = data.get("task")
        if not task_data:
            return None
        return SamTask.model_validate(task_data)
    except (json.JSONDecodeError, KeyError, IndexError, ValueError):
        return None


def _cleanup_active_task_context(session_id: str | None, fallback_context_file: Path | None) -> None:
    """Clean up active task context after SubagentStop completes.

    Primary path: call sam_active_task(action='clear') via fastmcp CLI.
    Fallback: delete the filesystem context file if MCP clear fails or is unavailable.

    Args:
        session_id: Sub-agent session identifier for MCP clear. ``None`` skips
            the MCP path entirely.
        fallback_context_file: Filesystem context file to delete if MCP clear
            fails or session_id is ``None``.
    """
    mcp_cleared = False
    if session_id:
        mcp_cleared = _call_sam_active_task_clear(session_id)

    if not mcp_cleared and fallback_context_file is not None:
        with contextlib.suppress(OSError):
            fallback_context_file.unlink()


def get_iso_timestamp() -> str:
    """Get current UTC timestamp in ISO format.

    Returns:
        ISO formatted timestamp string.
    """
    return datetime.now(UTC).isoformat(timespec="seconds")


def _extract_text_from_user_record(record: dict[str, Any]) -> str | None:
    """Extract the first non-empty text block from a ``type: "user"`` JSONL record.

    Args:
        record: A parsed JSONL record from a sub-agent transcript.

    Returns:
        The first non-empty text string found in the record's content list,
        or None if the record is not a user message or has no text content.
    """
    if record.get("type") != "user":
        return None
    message = record.get("message", {})
    if not isinstance(message, dict):
        return None
    content = message.get("content", [])
    if not isinstance(content, list):
        return None
    for item in content:
        if isinstance(item, dict) and item.get("type") == "text":
            text = item.get("text", "")
            if text:
                return text
    return None


def _extract_prompt_from_transcript(transcript_path: Path) -> str | None:
    """Extract the sub-agent's initial prompt from a JSONL transcript.

    Scans the transcript for the first ``type: "user"`` record whose message
    content contains a text block. This corresponds to the initial prompt passed
    to the sub-agent by the orchestrator and may contain a
    ``Skill(skill="start-task", args="...")`` invocation or ``/start-task`` pattern.

    Reads at most 50 lines to avoid loading large transcripts.

    Args:
        transcript_path: Path to the sub-agent's JSONL transcript file.

    Returns:
        The text of the first user message if found, or None if the file is
        missing, unreadable, or no user text content appears in the first 50 lines.
    """
    if not transcript_path.exists():
        print(f"[hook] transcript not found: {transcript_path}", file=sys.stderr)
        return None

    try:
        with transcript_path.open(encoding="utf-8") as fh:
            for _ in range(50):
                line = fh.readline()
                if not line:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    record: dict[str, Any] = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(record, dict):
                    continue
                text = _extract_text_from_user_record(record)
                if text:
                    return text
    except OSError as e:
        print(f"[hook] could not read transcript for prompt extraction {transcript_path}: {e}", file=sys.stderr)

    return None


def _extract_session_id_from_transcript(transcript_path: Path) -> str | None:
    """Extract the sub-agent's session_id from the first parseable line of a JSONL transcript.

    The transcript file contains newline-delimited JSON objects. Each line may have
    a top-level ``sessionId`` field (camelCase, as written by Claude Code) that
    identifies the sub-agent's own session.
    Reading only the first few lines avoids loading the entire (potentially large) file.

    Args:
        transcript_path: Path to the sub-agent's JSONL transcript file.

    Returns:
        The session_id string if found, or None if the file is missing,
        unreadable, or contains no parseable session_id in the first 10 lines.
    """
    if not transcript_path.exists():
        print(f"[hook] transcript not found: {transcript_path}", file=sys.stderr)
        return None

    try:
        with transcript_path.open(encoding="utf-8") as fh:
            # Read at most 10 lines — session_id appears in the first message.
            for _ in range(10):
                line = fh.readline()
                if not line:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    record: dict[str, Any] = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(record, dict):
                    continue
                session_id = record.get("sessionId") or record.get("session_id")
                if isinstance(session_id, str) and session_id:
                    return session_id
    except OSError as e:
        print(f"[hook] could not read transcript {transcript_path}: {e}", file=sys.stderr)

    return None


def _read_context_file(context_file: Path) -> tuple[str | None, str | None, str | int | None]:
    """Read task_file_path, task_id, and parent_issue_number from a context file.

    Args:
        context_file: Path to an active-task-*.json file.

    Returns:
        Tuple of (plan_id_or_path, task_id, parent_issue_number) where the first
        element is the raw string value from the JSON (plan address or filesystem path).
        Any field absent or unreadable is returned as None.
    """
    try:
        data: dict[str, Any] = json.loads(context_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None, None, None

    raw_path = data.get("task_file_path")
    task_id = data.get("task_id")
    if not raw_path or not task_id:
        return None, None, None

    parent_issue: str | int | None = data.get("parent_issue_number")

    return raw_path, task_id, parent_issue


def _resolve_context_file_from_transcript(hook_input: dict[str, Any]) -> Path | None:
    """Resolve the active-task context file for the agent that just stopped.

    Reads ``agent_transcript_path`` from hook input, extracts the sub-agent's
    session_id from the transcript, and returns the path to the matching
    ``active-task-{session_id}.json`` context file. Returns None (with a stderr
    warning) if any step fails or the context file does not exist.

    Args:
        hook_input: Parsed SubagentStop hook input from stdin.

    Returns:
        Path to the context file if found, or None.
    """
    transcript_path_raw = hook_input.get("agent_transcript_path", "")
    if not transcript_path_raw:
        print(
            "[hook] SubagentStop: no agent_transcript_path in hook input — cannot correlate agent to task",
            file=sys.stderr,
        )
        return None

    sub_agent_session_id = _extract_session_id_from_transcript(Path(transcript_path_raw))
    if not sub_agent_session_id:
        print(
            f"[hook] SubagentStop: could not extract session_id from transcript {transcript_path_raw} — skipping",
            file=sys.stderr,
        )
        return None

    try:
        context_dir = _dh_paths.context_dir()
    except (FileNotFoundError, subprocess.CalledProcessError, RuntimeError):
        return None

    context_file = context_dir / f"active-task-{sub_agent_session_id}.json"
    if not context_file.exists():
        print(
            f"[hook] SubagentStop: no context file for session {sub_agent_session_id} — not a /start-task agent",
            file=sys.stderr,
        )
        return None

    return context_file


def _resolve_active_task_context(
    hook_input: dict[str, Any],
) -> tuple[str | None, str | None, str | None, str | int | None, Path | None] | None:
    """Resolve the active task context for the agent that just stopped.

    Three-step resolution chain:
    1. sam_active_task(action='get') via fastmcp CLI using the sub-agent's
       session_id extracted from the transcript (primary path).
    2. Filesystem context file via ``_resolve_context_file_from_transcript``
       (fallback when agent did not call sam_active_task(set)).
    3. Prompt extraction from the JSONL transcript via
       ``_extract_prompt_from_transcript`` + ``extract_task_info_from_prompt``
       (final fallback for agents dispatched without context registration).

    Args:
        hook_input: Parsed SubagentStop hook input from stdin.

    Returns:
        ``(sub_agent_session_id, plan_id, task_id, parent_issue_number, context_file)``
        where ``plan_id`` is a str (plan address or raw path string from context).
        Returns ``None`` when no active task exists (caller should exit 0).
    """
    transcript_path_raw = hook_input.get("agent_transcript_path", "")
    sub_agent_session_id: str | None = None
    if transcript_path_raw:
        sub_agent_session_id = _extract_session_id_from_transcript(Path(transcript_path_raw))

    plan_id: str | None = None
    task_id: str | None = None
    parent_issue_number: str | int | None = None
    context_file: Path | None = None

    # Step 1: MCP lookup via sam_active_task(get)
    if sub_agent_session_id:
        plan_id, task_id, parent_issue_number = _call_sam_active_task_get(sub_agent_session_id)

    # Step 2: Filesystem context file written by /start-task
    if plan_id is None or task_id is None:
        context_file = _resolve_context_file_from_transcript(hook_input)
        if context_file is not None:
            plan_id, task_id, parent_issue_number = _read_context_file(context_file)

    # Step 3: Extract task reference from the agent's prompt in the JSONL transcript
    if (plan_id is None or task_id is None) and transcript_path_raw:
        prompt_text = _extract_prompt_from_transcript(Path(transcript_path_raw))
        if prompt_text:
            extracted_path, extracted_id = extract_task_info_from_prompt(prompt_text)
            if extracted_path is not None and extracted_id is not None:
                # Convert Path to plan_id string: extract plan address from filename
                # or use the path string directly as a fallback identifier.
                extracted_plan_id = _extract_plan_addr_from_path(extracted_path)
                if extracted_plan_id is None:
                    extracted_plan_id = str(extracted_path)
                print(
                    f"[hook] SubagentStop: resolved task from prompt — {extracted_plan_id} / {extracted_id}",
                    file=sys.stderr,
                )
                plan_id = extracted_plan_id
                task_id = extracted_id
                # parent_issue_number remains None — not available from prompt alone

    if plan_id is None or task_id is None:
        return None

    return sub_agent_session_id, plan_id, task_id, parent_issue_number, context_file


def _cascade_failed_task(
    plan_id: str, task_id: str, sub_agent_session_id: str | None, context_file: Path | None
) -> None:
    """Best-effort downstream skip cascade when a task is already in FAILED status.

    Routes the cascade through the SAM MCP server via sam_task(action='state',
    status='failed'). The server handles DependencyGraph construction and
    downstream SKIPPED writes atomically. Absorbs all failures — SubagentStop
    critical path must not be blocked by network or write errors.

    Args:
        plan_id: Plan address string (e.g. ``"Pf4281187"``).
        task_id: ID of the task that transitioned to FAILED.
        sub_agent_session_id: Agent session ID for context cleanup.
        context_file: Context file path for cleanup.
    """
    ok = _call_sam_task_state(plan_id, task_id, SamTaskStatus.FAILED)
    if not ok:
        print(f"[hook] SubagentStop: downstream skip cascade failed for {task_id}", file=sys.stderr)
    _cleanup_active_task_context(sub_agent_session_id, context_file)
    sys.exit(0)


def handle_subagent_stop(hook_input: dict[str, Any], profile: HookProfile = HookProfile.STANDARD) -> None:
    """Handle SubagentStop event - mark task COMPLETE with timestamp.

    Discovers the active task via sam_active_task MCP tool (primary) or the
    ``active-task-{session_id}.json`` context file (fallback). This ensures only
    the task belonging to the finished agent is marked complete — not all
    in-progress tasks — which is critical for correct behaviour with parallel agents.

    Discovery steps:
    1. Extract sub-agent's session_id from ``agent_transcript_path``.
    2. Call sam_active_task(action='get') via fastmcp CLI (primary path).
    3. Fall back to ``active-task-{session_id}.json`` on disk if MCP call fails.
    4. After status update, call sam_active_task(action='clear') or delete file.

    All status and field writes route through the SAM MCP server via fastmcp CLI,
    making the hook backend-agnostic.

    When profile is STRICT, runs pre-completion validation checks and prints
    any warnings to stderr before completing (warnings do not prevent completion).

    Args:
        hook_input: Parsed hook input from stdin.
        profile: Active hook profile. Defaults to STANDARD.
    """
    resolved = _resolve_active_task_context(hook_input)
    if resolved is None:
        sys.exit(0)

    sub_agent_session_id, plan_id, task_id, _parent_issue_number, context_file = resolved

    if plan_id is None or task_id is None:
        if context_file is not None:
            print(f"[hook] SubagentStop: malformed context file {context_file} — cleaning up", file=sys.stderr)
        _cleanup_active_task_context(sub_agent_session_id, context_file)
        sys.exit(0)

    # Extract plan address from plan_id: if it looks like a path, extract the P-token;
    # otherwise use plan_id directly (it already is a plan address string).
    plan_addr_candidate = _extract_plan_addr_from_path(Path(plan_id))
    plan_addr = plan_addr_candidate if plan_addr_candidate is not None else plan_id

    current_task = _call_sam_task_read(plan_addr, task_id)
    if current_task is None:
        print(
            f"[hook] SubagentStop: could not read task {task_id} from plan {plan_addr} via MCP — skipping",
            file=sys.stderr,
        )
        _cleanup_active_task_context(sub_agent_session_id, context_file)
        sys.exit(0)

    if current_task.status == SamTaskStatus.COMPLETE:
        _cleanup_active_task_context(sub_agent_session_id, context_file)
        sys.exit(0)

    if current_task.status == SamTaskStatus.FAILED:
        # Agent explicitly set task to FAILED before stopping.
        # Cascade skip signals to all downstream dependents via MCP.
        # _cascade_failed_task is terminal (calls sys.exit(0)); return guards mocked callers.
        _cascade_failed_task(plan_addr, task_id, sub_agent_session_id, context_file)
        return

    if profile == HookProfile.STRICT:
        for warning in run_strict_pre_completion_checks(current_task, task_id):
            print(warning, file=sys.stderr)

    timestamp = get_iso_timestamp()
    state_ok = _call_sam_task_state(plan_addr, task_id, SamTaskStatus.COMPLETE)
    if not state_ok:
        print(f"[hook] SubagentStop: failed to mark {task_id} complete via MCP", file=sys.stderr)
        _cleanup_active_task_context(sub_agent_session_id, context_file)
        sys.exit(0)
    _call_sam_task_update(plan_addr, task_id, {"completed": timestamp})
    _cleanup_active_task_context(sub_agent_session_id, context_file)


def handle_activity_update(hook_input: dict[str, Any]) -> None:
    """Handle PostToolUse event - update LastActivity timestamp.

    Reads task info from context file and updates the last-activity field
    via the SAM MCP server (backend-agnostic write path).

    Args:
        hook_input: Parsed hook input from stdin.
    """
    cwd = Path(hook_input.get("cwd", "."))
    session_id = hook_input.get("session_id", "")

    if not session_id:
        sys.exit(0)

    raw_plan_ref, task_id = read_task_context(cwd, session_id)

    if raw_plan_ref is None or task_id is None:
        sys.exit(0)

    # Extract plan address from the raw reference: if it looks like a path, extract
    # the P-token; otherwise use the string directly as a plan address.
    plan_addr = _extract_plan_addr_from_path(Path(raw_plan_ref))
    if plan_addr is None:
        sys.exit(0)

    current_task = _call_sam_task_read(plan_addr, task_id)
    if current_task is None:
        print(
            f"[hook] PostToolUse: could not read task {task_id} from plan {plan_addr} via MCP — skipping",
            file=sys.stderr,
        )
    elif current_task.status == SamTaskStatus.COMPLETE:
        return

    timestamp = get_iso_timestamp()

    # Best-effort write — no plan address token in filename means no MCP target.
    _call_sam_task_update(plan_addr, task_id, {"last-activity": timestamp})


def main() -> None:
    """Main entry point for the hook script."""
    try:
        hook_input = parse_hook_input()
    except (ValueError, json.JSONDecodeError) as e:
        print(f"Failed to parse hook input: {e}", file=sys.stderr)
        sys.exit(2)

    event_name = hook_input.get("hook_event_name", "")

    # Disabled hooks take precedence over profile — checked inside should_skip_hook.
    profile = resolve_profile()
    disabled_hooks = parse_disabled_hooks()
    if should_skip_hook(event_name, profile, disabled_hooks):
        hook_id = _EVENT_TO_HOOK_ID.get(event_name, event_name)
        if hook_id in disabled_hooks:
            print(f"[hook] Skipped: {hook_id} (disabled)", file=sys.stderr)
        else:
            print(f"[hook] Skipped: {hook_id} (profile={profile})", file=sys.stderr)
        sys.exit(0)

    if event_name == "SubagentStop":
        handle_subagent_stop(hook_input, profile=profile)
    elif event_name == "PostToolUse":
        tool_name = hook_input.get("tool_name", "")
        if tool_name in {"Write", "Edit", "Bash"}:
            handle_activity_update(hook_input)
    sys.exit(0)


if __name__ == "__main__":
    main()
