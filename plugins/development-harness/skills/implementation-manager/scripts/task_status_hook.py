#!/usr/bin/env python3
"""Task Status Hook - Update task status and timestamps automatically.

This hook script handles multiple hook events:
- SubagentStop: Parse prompt for task info, set status to COMPLETE, add Completed timestamp
- PostToolUse (Write|Edit|Bash): Update LastActivity timestamp using context file

All task file I/O routes through sam_schema (ADR-001 exception: Python API, not CLI
subprocess, because hooks fire on every tool call and latency matters).

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

import enum
import json
import os
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# dh_paths is at plugins/development-harness/dh_paths.py.
# Hook script lives at plugins/development-harness/skills/implementation-manager/scripts/
# parents[0]=scripts, [1]=implementation-manager, [2]=skills, [3]=development-harness
_DH_PLUGIN_DIR = Path(__file__).resolve().parents[3]
if str(_DH_PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(_DH_PLUGIN_DIR))

import dh_paths as _dh_paths

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


class HookProfile(enum.StrEnum):
    """Runtime profile controlling which hook handlers are active.

    Profiles are selected via the CLAUDE_SKILLS_HOOK_PROFILE environment variable.
    Default when unset or empty: STANDARD.
    """

    MINIMAL = "minimal"
    STANDARD = "standard"
    STRICT = "strict"


# Hook ID constants — used in CLAUDE_SKILLS_DISABLED_HOOKS.
HOOK_ID_POST_TOOL_USE = "task-status:post-tool-use"
HOOK_ID_SUBAGENT_STOP = "task-status:subagent-stop"

# Map hook_event_name values to hook IDs for disabled-hooks lookup.
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


def run_strict_pre_completion_checks(task_file_path: Path, task_id: str, hook_input: dict[str, Any]) -> list[str]:
    """Run pre-completion validation checks for strict mode.

    Called when CLAUDE_SKILLS_HOOK_PROFILE=strict and a SubagentStop event fires.
    Warnings are observational — they do not prevent task completion.

    Args:
        task_file_path: Path to the plan file.
        task_id: Task ID being completed.
        hook_input: Parsed hook input (reserved for future checks).

    Returns:
        List of warning strings. Empty list means all checks passed.
    """
    warnings: list[str] = []
    try:
        task = sam_get_task(task_file_path, task_id)
    except (KeyError, FileNotFoundError, ValueError, OSError) as e:
        warnings.append(f"[hook] strict: could not load task {task_id} for pre-completion checks: {e}")
        return warnings

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
        import backlog_core.gh_client as _bc_github  # noqa: PLC0415

        try:
            from backlog_core.models import BacklogError, GitHubUnavailableError  # noqa: PLC0415
            from github import GithubException  # noqa: PLC0415

            get_github_exc: tuple[type[BaseException], ...] = (GitHubUnavailableError, GithubException)
            update_exc: tuple[type[BaseException], ...] = (BacklogError, GithubException, RuntimeError)
        except ImportError:
            get_github_exc = (RuntimeError,)
            update_exc = (RuntimeError,)

        try:
            repo = _bc_github.get_github()
        except get_github_exc as e:
            print(f"[hook] GitHub unavailable — skipping GitHub sync: {e}", file=sys.stderr)
            return

        try:
            _bc_github.update_task_status(repo, github_issue, "complete")
        except update_exc as e:
            print(f"[hook] GitHub sync update_task_status failed: {e}", file=sys.stderr)
            return

        print(f"[hook] Synced task {task_id} completion to GitHub issue #{github_issue}", file=sys.stderr)
    except (ImportError, OSError, KeyError, ValueError) as e:
        print(f"[hook] GitHub sync failed: {e}", file=sys.stderr)


def _extract_session_id_from_transcript(transcript_path: Path) -> str | None:
    """Extract the sub-agent's session_id from the first parseable line of a JSONL transcript.

    The transcript file contains newline-delimited JSON objects. Each line may have
    a top-level ``session_id`` field that identifies the sub-agent's own session.
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
                session_id = record.get("session_id")
                if isinstance(session_id, str) and session_id:
                    return session_id
    except OSError as e:
        print(f"[hook] could not read transcript {transcript_path}: {e}", file=sys.stderr)

    return None


def _read_context_file(context_file: Path) -> tuple[Path | None, str | None, int | None]:
    """Read task_file_path, task_id, and parent_issue_number from a context file.

    Args:
        context_file: Path to an active-task-*.json file.

    Returns:
        Tuple of (task_file_path, task_id, parent_issue_number).
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

    parent_issue: int | None = None
    if "parent_issue_number" in data:
        with contextlib.suppress(TypeError, ValueError):
            parent_issue = int(data["parent_issue_number"])

    return Path(raw_path), task_id, parent_issue


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


def handle_subagent_stop(hook_input: dict[str, Any], profile: HookProfile = HookProfile.STANDARD) -> None:
    """Handle SubagentStop event - mark task COMPLETE with timestamp.

    Discovers the active task by extracting the sub-agent's session_id from
    ``agent_transcript_path`` in the hook input, then looking up the single
    context file ``active-task-{session_id}.json``. This ensures only the task
    belonging to the finished agent is marked complete — not all in-progress
    tasks — which is critical for correct behaviour with parallel agents.

    Discovery steps:
    1. Read ``agent_transcript_path`` from hook input.
    2. Extract the sub-agent's session_id from the first parseable JSONL line.
    3. Look up ``active-task-{session_id}.json`` directly (no glob).
    4. If not found: log warning and exit 0 (not a /start-task sub-agent).

    Delegates all file writes to sam_schema.core.query.update_status
    (handles both .yaml and .md formats).

    When profile is STRICT, runs pre-completion validation checks and prints
    any warnings to stderr before completing (warnings do not prevent completion).

    Args:
        hook_input: Parsed hook input from stdin.
        profile: Active hook profile. Defaults to STANDARD.
    """
    cwd = Path(hook_input.get("cwd", "."))

    context_file = _resolve_context_file_from_transcript(hook_input)
    if context_file is None:
        sys.exit(0)

    task_file_path, task_id, parent_issue_number = _read_context_file(context_file)

    if task_file_path is None or task_id is None:
        # Unreadable or malformed context file — clean up.
        print(f"[hook] SubagentStop: malformed context file {context_file} — cleaning up", file=sys.stderr)
        with contextlib.suppress(OSError):
            context_file.unlink()
        sys.exit(0)

    # Resolve task file path relative to cwd.
    full_path = cwd / task_file_path if not task_file_path.is_absolute() else task_file_path

    if not full_path.exists():
        # Task file gone — delete stale context file.
        print(f"[hook] SubagentStop: task file {full_path} not found — cleaning up context", file=sys.stderr)
        with contextlib.suppress(OSError):
            context_file.unlink()
        sys.exit(0)

    # Check current task status before marking complete.
    try:
        current_task = sam_get_task(full_path, task_id)
    except (KeyError, FileNotFoundError, ValueError, OSError):
        # Task not found in file — delete stale context file.
        with contextlib.suppress(OSError):
            context_file.unlink()
        sys.exit(0)

    if current_task.status == SamTaskStatus.COMPLETE:
        # Already complete — just clean up the stale context file.
        with contextlib.suppress(OSError):
            context_file.unlink()
        sys.exit(0)

    # Strict mode: run pre-completion checks and emit warnings. Never blocks completion.
    if profile == HookProfile.STRICT:
        for warning in run_strict_pre_completion_checks(full_path, task_id, hook_input):
            print(warning, file=sys.stderr)

    try:
        # Single code path for all formats: sam_schema handles .yaml and .md uniformly.
        sam_update_status(full_path, task_id, SamTaskStatus.COMPLETE, timestamp_field="completed")
    except (ValueError, KeyError, FileNotFoundError) as e:
        print(str(e), file=sys.stderr)
        sys.exit(2)

    # Delete the context file now that the task is marked complete.
    with contextlib.suppress(OSError):
        context_file.unlink()

    # Sync completion to GitHub — best-effort, never changes exit code.
    sync_completion_to_github(full_path, task_id, parent_issue_number)


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

    # Profile and disabled-hook controls. stdin is already consumed above.
    # Disabled hooks take precedence over profile (checked inside should_skip_hook).
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
        # Update LastActivity for Write/Edit/Bash operations
        tool_name = hook_input.get("tool_name", "")
        if tool_name in {"Write", "Edit", "Bash"}:
            handle_activity_update(hook_input)
    # Unknown event or non-matching tool, exit silently
    sys.exit(0)


if __name__ == "__main__":
    main()
