#!/usr/bin/env python3
"""Task Status Hook - Update task status and timestamps automatically.

This hook script handles multiple hook events:
- SubagentStop: Parse prompt for task info, set status to COMPLETE, add Completed timestamp
- PostToolUse (Write|Edit|Bash): Update LastActivity timestamp using context file

All task file I/O routes through sam_schema (ADR-001 exception: Python API, not CLI
subprocess, because hooks fire on every tool call and latency matters).

Context File Mechanism:
- The /start-task command writes task context to .claude/context/active-task-{session_id}.json
- PostToolUse hooks read from this file to know which task is active
- SubagentStop parses the prompt directly (doesn't need context file)

Usage:
    Called automatically via hooks configuration.
    Receives JSON via stdin with hook context.

Exit Codes:
    0: Success
    2: Error (stderr message shown to Claude)
"""

from __future__ import annotations

import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# sam_schema is the canonical task/plan schema package.
# Installed as a workspace dependency in the project venv.
# Fallback: add packages/ to sys.path for direct-script execution outside the venv.
_HOOK_REPO_ROOT = Path(__file__).resolve().parents[5]
_HOOK_SAM_PACKAGES_DIR = str(_HOOK_REPO_ROOT / "packages")
if _HOOK_SAM_PACKAGES_DIR not in sys.path:
    sys.path.insert(0, _HOOK_SAM_PACKAGES_DIR)

# Import directly from submodules for concrete types (avoids lazy __getattr__ object).
import contextlib

from sam_schema.core.models import TaskStatus as SamTaskStatus
from sam_schema.core.query import (
    get_task as sam_get_task,
    update_plan_fields as sam_update_plan_fields,
    update_status as sam_update_status,
)

# Conditionally add backlog_core to sys.path for GitHub sync.
# The hook script lives at:
#   plugins/python3-development/skills/implementation-manager/scripts/task_status_hook.py
# parents[5] resolves to the repo root (e.g. /home/user/claude_skills).
_BACKLOG_CORE_HOOK = Path(__file__).resolve().parents[5] / ".claude" / "skills" / "backlog" / "backlog_core"
if _BACKLOG_CORE_HOOK.exists():
    sys.path.insert(0, str(_BACKLOG_CORE_HOOK.parent))

# Alphanumeric task ID pattern: "1", "1.1", "T1", "P0-T01", etc.
_TASK_ID_RE = r"[A-Za-z0-9]+(?:[-.][\dA-Za-z]+)*"


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


def extract_task_info_from_args(args: str) -> tuple[Path | None, str | None]:
    """Extract task file path and task ID from command args.

    Args:
        args: Command arguments string.

    Returns:
        Tuple of (task_file_path, task_id) or (None, None) if not extractable.
    """
    if not args:
        return None, None

    # Parse the args string
    # Format: "<task-file-path> --task <task-id>"
    # or: "<task-file-path> <task-id>"

    parts = args.split()
    if not parts:
        return None, None

    task_file_path: Path | None = None
    task_id: str | None = None

    # First part should be the task file path (.md or .yaml)
    if parts[0].endswith((".md", ".yaml")):
        task_file_path = Path(parts[0])

    # Look for --task flag or task ID pattern
    for i, part in enumerate(parts):
        if part == "--task" and i + 1 < len(parts):
            task_id = parts[i + 1]
            break
        # Match alphanumeric task ID pattern (e.g., "1.1", "T1", "P0-T01")
        if re.match(rf"^{_TASK_ID_RE}$", part) and i > 0:
            task_id = part
            break

    return task_file_path, task_id


def extract_task_info_from_prompt(prompt: str) -> tuple[Path | None, str | None]:
    """Extract task file path and task ID from sub-agent prompt.

    Args:
        prompt: The sub-agent's prompt string.

    Returns:
        Tuple of (task_file_path, task_id) or (None, None) if not extractable.
    """
    if not prompt:
        return None, None

    # Look for /start-task invocation pattern in the prompt
    # Pattern 1: /start-task <path> --task <id>  (literal slash-command)
    # Matches both .md and .yaml task file extensions.
    match = re.search(rf"/start-task\s+([^\s]+\.(?:md|yaml))(?:\s+--task\s+({_TASK_ID_RE}))?", prompt)
    if match:
        task_file = Path(match.group(1))
        task_id = match.group(2)
        return task_file, task_id

    # Pattern 2: Skill(skill="start-task", args="<path> --task <id>")
    # The orchestrator invokes start-task via the Skill tool, not as a literal command.
    # Matches both .md and .yaml task file extensions.
    skill_match = re.search(
        rf'Skill\(\s*skill\s*=\s*["\']start-task["\']\s*,\s*args\s*=\s*["\']'
        rf"([^\s\"']+\.(?:md|yaml))(?:\s+--task\s+({_TASK_ID_RE}))?"
        rf'["\']',
        prompt,
    )
    if skill_match:
        task_file = Path(skill_match.group(1))
        task_id = skill_match.group(2)
        return task_file, task_id

    return None, None


def get_context_file_path(cwd: Path, session_id: str) -> Path:
    """Get the path to the active task context file.

    Args:
        cwd: Current working directory.
        session_id: Session ID from hook input.

    Returns:
        Path to the context file.
    """
    context_dir = cwd / ".claude" / "context"
    return context_dir / f"active-task-{session_id}.json"


def read_task_context(cwd: Path, session_id: str) -> tuple[Path | None, str | None]:
    """Read task info from context file.

    Args:
        cwd: Current working directory.
        session_id: Session ID from hook input.

    Returns:
        Tuple of (task_file_path, task_id) or (None, None) if not found.
    """
    context_file = get_context_file_path(cwd, session_id)
    if not context_file.exists():
        return None, None

    try:
        context_data: dict[str, str] = json.loads(context_file.read_text(encoding="utf-8"))
        task_file = context_data.get("task_file_path")
        task_id = context_data.get("task_id")
        if task_file and task_id:
            return Path(task_file), task_id
    except (json.JSONDecodeError, KeyError):
        pass

    return None, None


def write_task_context(cwd: Path, session_id: str, task_file_path: Path, task_id: str) -> None:
    """Write task info to context file.

    Args:
        cwd: Current working directory.
        session_id: Session ID from hook input.
        task_file_path: Path to the task file.
        task_id: Task ID being worked on.
    """
    context_file = get_context_file_path(cwd, session_id)
    context_file.parent.mkdir(parents=True, exist_ok=True)

    context_data = {"task_file_path": str(task_file_path), "task_id": task_id}
    context_file.write_text(json.dumps(context_data), encoding="utf-8")


def delete_task_context(cwd: Path, session_id: str) -> None:
    """Delete the task context file.

    Args:
        cwd: Current working directory.
        session_id: Session ID from hook input.
    """
    context_file = get_context_file_path(cwd, session_id)
    if context_file.exists():
        context_file.unlink()


def get_iso_timestamp() -> str:
    """Get current UTC timestamp in ISO format.

    Returns:
        ISO formatted timestamp string.
    """
    return datetime.now(UTC).isoformat(timespec="seconds")


def _fallback_to_context_file(hook_input: dict[str, Any]) -> tuple[Path | None, str | None]:
    """Read task info from the active-task context file as a fallback.

    When prompt parsing fails (e.g. Skill() syntax not matched), the context
    file written by /start-task step 4 provides the task_file_path and task_id.

    Returns:
        Tuple of (task_file_path, task_id) or (None, None) if context file not found.
    """
    cwd = Path(hook_input.get("cwd", "."))
    session_id = hook_input.get("session_id", "")
    if session_id:
        return read_task_context(cwd, session_id)
    return None, None


def get_parent_issue_number(hook_input: dict[str, Any]) -> int | None:
    """Read parent_issue_number from the active-task context file.

    Returns the integer issue number, or None if the field is absent or the
    context file does not exist. Never raises — all failures return None.

    Args:
        hook_input: Parsed hook input from stdin.

    Returns:
        Parent issue number as int, or None if not found.
    """
    cwd = Path(hook_input.get("cwd", "."))
    session_id = hook_input.get("session_id", "")
    if not session_id:
        return None
    context_file = get_context_file_path(cwd, session_id)
    if not context_file.exists():
        return None
    try:
        data: dict[str, Any] = json.loads(context_file.read_text(encoding="utf-8"))
        if "parent_issue_number" in data:
            return int(data["parent_issue_number"])
    except (json.JSONDecodeError, KeyError, ValueError, TypeError):
        pass
    return None


def sync_completion_to_github(task_file_path: Path, task_id: str, parent_issue_number: int | None) -> None:
    """Sync task completion status to GitHub sub-issue.

    Reads github_issue field from the task model via sam_schema. If absent,
    logs a warning to stderr and returns without making any GitHub API call.
    Wraps all GitHub operations in try/except — failure logs a warning to stderr
    and returns without raising. This function is always called after the local
    write succeeds; GitHub failure does not affect hook exit code.

    Args:
        task_file_path: Path to the plan file or directory.
        task_id: Task ID being completed.
        parent_issue_number: Optional parent story issue number from context file.
    """
    try:
        # Read github_issue from the task model via sam_schema.
        github_issue: int | None = None
        with contextlib.suppress(KeyError, FileNotFoundError, ValueError, OSError):
            github_issue = sam_get_task(task_file_path, task_id).github_issue

        if github_issue is None:
            print(f"[hook] No github_issue field in {task_file_path} — skipping GitHub sync", file=sys.stderr)
            return

        if not _BACKLOG_CORE_HOOK.exists():
            print("[hook] backlog_core not found — skipping GitHub sync", file=sys.stderr)
            return

        # Conditional import — only after path guard
        import backlog_core.github as _bc_github  # noqa: PLC0415

        try:
            repo = _bc_github.get_github()
        except Exception as e:  # noqa: BLE001
            print(f"[hook] GitHub unavailable — skipping GitHub sync: {e}", file=sys.stderr)
            return

        try:
            _bc_github.update_task_status(repo, github_issue, "complete")
        except Exception as e:  # noqa: BLE001
            print(f"[hook] GitHub sync update_task_status failed: {e}", file=sys.stderr)
            return

        print(f"[hook] Synced task {task_id} completion to GitHub issue #{github_issue}", file=sys.stderr)
    except Exception as e:  # noqa: BLE001
        print(f"[hook] GitHub sync failed: {e}", file=sys.stderr)


def handle_subagent_stop(hook_input: dict[str, Any]) -> None:
    """Handle SubagentStop event - mark task COMPLETE with timestamp.

    Parses the sub-agent's prompt to find the /start-task invocation
    and extracts task file path and task ID. Delegates all file writes
    to sam_schema.core.query.update_status (handles both .yaml and .md formats).

    Args:
        hook_input: Parsed hook input from stdin.
    """
    # Get the sub-agent's prompt which contains /start-task invocation
    prompt = hook_input.get("prompt", "")
    if not prompt:
        # Try tool_input for backwards compatibility
        tool_input = hook_input.get("tool_input", {})
        prompt = tool_input.get("prompt", "")

    task_file_path, task_id = extract_task_info_from_prompt(prompt)

    # Fallback: read from context file written by /start-task step 4
    if task_file_path is None or task_id is None:
        task_file_path, task_id = _fallback_to_context_file(hook_input)

    if task_file_path is None or task_id is None:
        # Not a /start-task sub-agent, exit silently
        sys.exit(0)

    # Resolve path relative to cwd
    cwd = Path(hook_input.get("cwd", "."))
    full_path = cwd / task_file_path if not task_file_path.is_absolute() else task_file_path

    if not full_path.exists():
        print(f"Task file not found: {full_path}", file=sys.stderr)
        sys.exit(2)

    try:
        # Single code path for all formats: sam_schema handles .yaml and .md uniformly.
        sam_update_status(full_path, task_id, SamTaskStatus.COMPLETE, timestamp_field="completed")
    except (ValueError, KeyError, FileNotFoundError) as e:
        print(str(e), file=sys.stderr)
        sys.exit(2)

    # Clean up context file
    session_id = hook_input.get("session_id", "")
    if session_id:
        delete_task_context(cwd, session_id)

    # Step 5: sync_completion_to_github — best-effort, never changes exit code
    sync_completion_to_github(full_path, task_id, get_parent_issue_number(hook_input))


def handle_activity_update(hook_input: dict[str, Any]) -> None:
    """Handle PostToolUse event - update LastActivity timestamp.

    Reads task info from context file and updates the last-activity field.
    Delegates all file writes to sam_schema.core.query.update_plan_fields
    (handles both .yaml and .md formats via a single code path).

    Args:
        hook_input: Parsed hook input from stdin.
    """
    cwd = Path(hook_input.get("cwd", "."))
    session_id = hook_input.get("session_id", "")

    if not session_id:
        # No session ID, can't find context file
        sys.exit(0)

    task_file_path, task_id = read_task_context(cwd, session_id)

    if task_file_path is None or task_id is None:
        # No active task context, exit silently
        sys.exit(0)

    # Resolve path relative to cwd
    full_path = cwd / task_file_path if not task_file_path.is_absolute() else task_file_path

    if not full_path.exists():
        # Task file doesn't exist, exit silently
        sys.exit(0)

    # Guard: skip silently if task is already complete.
    # sam_get_task raises KeyError if task not found — treat as "not active", exit silently.
    try:
        current_task = sam_get_task(full_path, task_id)
        if current_task.status == SamTaskStatus.COMPLETE:
            return
    except (KeyError, FileNotFoundError, ValueError, OSError):
        sys.exit(0)

    timestamp = get_iso_timestamp()

    try:
        # Single code path for all formats: sam_schema handles .yaml and .md uniformly.
        sam_update_plan_fields(full_path, task_id, set_fields={"last-activity": timestamp})
    except (ValueError, KeyError, FileNotFoundError):
        # Task section not found or file unavailable, exit silently
        sys.exit(0)


def main() -> None:
    """Main entry point for the hook script."""
    try:
        hook_input = parse_hook_input()
    except (ValueError, json.JSONDecodeError) as e:
        print(f"Failed to parse hook input: {e}", file=sys.stderr)
        sys.exit(2)

    event_name = hook_input.get("hook_event_name", "")

    if event_name == "SubagentStop":
        handle_subagent_stop(hook_input)
    elif event_name == "PostToolUse":
        # Update LastActivity for Write/Edit/Bash operations
        tool_name = hook_input.get("tool_name", "")
        if tool_name in {"Write", "Edit", "Bash"}:
            handle_activity_update(hook_input)
    # Unknown event or non-matching tool, exit silently
    sys.exit(0)


if __name__ == "__main__":
    main()
