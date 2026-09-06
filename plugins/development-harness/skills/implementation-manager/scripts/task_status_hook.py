#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "gitpython>=3.1.0",
#   "pydantic>=2.12.3",
#   "ruamel.yaml>=0.18.0",
# ]
#
# [tool.ty.environment]
# extra-paths = ["../../..", "../../../scripts"]
# ///
"""Task Status Hook - Update task status and timestamps automatically.

This hook script handles multiple hook events:
- SubagentStop: Parse prompt for task info; set status to COMPLETE with a Completed timestamp
  if the worker's final message reports a complete STATUS, otherwise set status to BLOCKED.
- PostToolUse (Write|Edit|Bash): Update LastActivity timestamp using context file

All task state WRITES route through the SAM CLI (scripts/run_sam_cli.py) as a single
subprocess, making the hook backend-agnostic (hooks must not write directly to YAML).

Context File Mechanism:
- The /start-task command writes task context to ~/.dh/projects/{slug}/context/active-task-{session_id}.json
- PostToolUse hooks read from this file to know which task is active
- SubagentStop extracts a session_id from agent_transcript_path, then looks up
  active-task-{session_id}.json directly

KNOWN DEFECT in that correlation: a sub-agent's transcript carries its PARENT session's id, not
its own, so every sub-agent of one plan resolves to the same record. A wave running N tasks in
parallel writes N registrations to one path and only the last survives, and a stopping agent can
therefore be attributed to another agent's task. The per-sub-agent identifier the harness does
supply is not read here. Task state written by this hook during parallel dispatch is unreliable
until the record is keyed by something unique to the task.

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
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_DH_PLUGIN_DIR = Path(__file__).resolve().parents[3]
if str(_DH_PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(_DH_PLUGIN_DIR))

_SAM_CLI_PATH = _DH_PLUGIN_DIR / "scripts" / "run_sam_cli.py"

_DH_PLUGIN_SCRIPTS_DIR = str(_DH_PLUGIN_DIR / "scripts")
if _DH_PLUGIN_SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _DH_PLUGIN_SCRIPTS_DIR)

import dh_paths as _dh_paths
from dh_config import DHConfig

_HOOK_REPO_ROOT = Path(__file__).resolve().parents[5]
_HOOK_SAM_PACKAGES_DIR = str(_HOOK_REPO_ROOT / "packages")
if _HOOK_SAM_PACKAGES_DIR not in sys.path:
    sys.path.insert(0, _HOOK_SAM_PACKAGES_DIR)

# Import directly from submodules for concrete types (avoids lazy __getattr__ object).
from sam_schema.core.addressing import AddressingError, resolve_plan_address
from sam_schema.core.models import Task as SamTask, TaskStatus as SamTaskStatus

from run_bounded import terminate_process_tree

# Alphanumeric task ID pattern: "1", "1.1", "T1", "P0-T01", etc.
_TASK_ID_RE = r"[A-Za-z0-9]+(?:[-.][\dA-Za-z]+)*"

# Plan argument pattern: file path (.md/.yaml) OR plan address (P<hex>).
# Named group ``plan`` captures whichever form is present.
# re.IGNORECASE: plan address prefix P is case-insensitive (e.g. PDEADBEef).
_PLAN_ARG_RE = r"(?P<plan>(?:[^\s\"']+\.(?:md|yaml))|(?:P[0-9a-f]+))"

# A worker's self-reported status, per subagent-contract. Every line is scanned rather
# than only the first, because agents/task-worker.md prescribes the completion report
# inside a ```text fence, so a worker following its own template emits a fence marker as
# line one. Leading markdown — fence, bold, bullet, blockquote — is tolerated, and the
# token may carry underscores (GAPS_FOUND).
#
# The token must END the line. That rejects two lookalikes that are not verdicts: the
# literal template placeholder `STATUS: COMPLETE|PARTIAL|FAILED` that task-worker.md
# prints, and prose such as `STATUS: DONE was reported by the sibling task`. Without the
# anchor the pattern captures a token out of both.
_STATUS_LINE_RE = re.compile(r"^[\s>*_`-]*STATUS:\s*\**\s*([A-Za-z][A-Za-z_]*)\s*\**\s*$", re.IGNORECASE)

# Tokens meaning the worker finished. ponytail: accepts all three spellings in use across
# the plugin; narrow to one token once the status vocabulary is unified.
_COMPLETE_STATUS_TOKENS = frozenset({"DONE", "COMPLETE", "COMPLETED"})

# Tokens that positively report NOT finishing. Only these block a task. A token outside
# both sets is a vocabulary this hook does not know — several shipped specialists report
# VERIFIED, CONNECTED, READY — and an unknown word is not evidence of failure, so it
# leaves task state alone rather than blocking correct work.
_INCOMPLETE_STATUS_TOKENS = frozenset({"PARTIAL", "FAILED", "BLOCKED", "INCOMPLETE"})


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
        task: The already-loaded SamTask object (avoids a second SAM CLI subprocess call).
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


def _resolve_matched_task(match: re.Match[str]) -> tuple[Path | None, str | None]:
    """Resolve a plan/task regex match's groups to (task_file, task_id).

    Shared by every pattern in ``extract_task_info_from_prompt`` — each pattern differs
    only in how it locates the plan-arg/task-id groups in the prompt, not in what happens
    once they're found.

    Returns:
        ``(task_file, task_id)``, or ``(None, None)`` when the plan arg cannot be resolved
        to a filesystem path (plan not found in the DH state directory).
    """
    task_file = _plan_arg_to_path(match.group("plan"))
    if task_file is None:
        return None, None
    return task_file, match.group("task_id")


def extract_task_info_from_prompt(prompt: str) -> tuple[Path | None, str | None]:
    """Extract task file path and task ID from sub-agent prompt.

    Accepts two arg forms for the plan argument:
    - File path form: ``<path>.md`` or ``<path>.yaml`` — returned as ``Path`` directly.
    - Plan address form: ``P[0-9a-f]+`` (e.g. ``Pdec8934d``) — resolved to the actual
      filesystem path via ``resolve_plan_address()``.

    Args:
        prompt: The sub-agent's prompt string.

    Returns:
        Tuple of (resolved_path, task_id) or (None, None) if not extractable.
        Returns (None, None) when a plan address is found but cannot be resolved
        (plan not found in the DH state directory).
    """
    if not prompt:
        return None, None

    # Pattern 1: /start-task <plan-arg> --task <id>  (literal slash-command)
    # Matches both file-path form and plan-address form.
    match = re.search(
        rf"/start-task\s+{_PLAN_ARG_RE}(?:\s+--task\s+(?P<task_id>{_TASK_ID_RE}))?", prompt, re.IGNORECASE
    )
    if match:
        return _resolve_matched_task(match)

    # Pattern 2: Skill(skill="start-task", args="<plan-arg> --task <id>")
    # The orchestrator invokes start-task via the Skill tool, not as a literal command.
    # Matches both file-path form and plan-address form.
    skill_match = re.search(
        rf'Skill\(\s*skill\s*=\s*["\']start-task["\']\s*,\s*args\s*=\s*["\']'
        rf"{_PLAN_ARG_RE}(?:\s+--task\s+(?P<task_id>{_TASK_ID_RE}))?"
        rf'["\']',
        prompt,
        re.IGNORECASE,
    )
    if skill_match:
        return _resolve_matched_task(skill_match)

    # Pattern 3: bare "<plan-arg>/<task-id>" address, with no /start-task prefix and no
    # Skill() wrapper. implement-feature/SKILL.md dispatches dh:task-worker with the task
    # reference as the sub-agent's ENTIRE prompt in this form, so it is matched as a full-string
    # match (not a substring search like Patterns 1 and 2) to avoid false-positiving on an
    # address mentioned in passing within a longer, unrelated prompt.
    bare_match = re.fullmatch(rf"{_PLAN_ARG_RE}/(?P<task_id>{_TASK_ID_RE})", prompt.strip(), re.IGNORECASE)
    if bare_match:
        return _resolve_matched_task(bare_match)

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
        Tuple of (plan_address, task_id) or (None, None) if not found.
    """
    context_file = get_context_file_path(cwd, session_id)
    if not context_file.exists():
        return None, None

    try:
        context_data: dict[str, str] = json.loads(context_file.read_text(encoding="utf-8"))
        plan_addr = context_data.get("plan")
        task_id = context_data.get("task_id")
        if plan_addr and task_id:
            return plan_addr, task_id
        if context_data.get("task_file_path") and task_id:
            print(
                f"[hook] read_task_context: {context_file}: legacy context record has "
                "task_file_path but no plan address (predates the plan/task fields) — not "
                "falling back to path-parsing; activity tracking for this session will not "
                "resume until a fresh /start-task runs",
                file=sys.stderr,
            )
    except json.JSONDecodeError as exc:
        print(f"[hook] read_task_context: malformed JSON in {context_file}: {exc}", file=sys.stderr)

    return None, None


def _call_sam_active_task_get(session_id: str, timeout: float = 8) -> tuple[str | None, str | None, str | int | None]:
    """Retrieve active task context via the SAM CLI's ``active-task get`` subcommand.

    Primary retrieval path for SubagentStop. Returns parsed fields from the
    ``ActiveTaskContext`` on success, or ``(None, None, None)`` if the call fails
    or no active task is stored for the session.

    Args:
        session_id: Sub-agent session identifier. Empty string is normalised to
            ``"_default"`` sentinel.
        timeout: Subprocess timeout in seconds.

    Returns:
        Tuple of ``(plan_address, task_id, parent_issue_number)``.
        All ``None`` when the call fails or active task is not set.
    """
    resolved = session_id or "_default"
    stdout = _call_sam_cli(["active-task", "get", "--session-id", resolved], timeout=timeout)
    if stdout is None:
        return None, None, None

    try:
        data: dict[str, Any] = json.loads(stdout)
        active = data.get("active_task")
        if not active:
            return None, None, None
        plan_addr = active.get("plan")
        task_id = active.get("task_id")
        if plan_addr and task_id:
            parent_issue: str | int | None = active.get("parent_issue_number")
            return plan_addr, task_id, parent_issue
        if active.get("task_file_path") and task_id:
            print(
                f"[hook] _call_sam_active_task_get: session {resolved}: legacy active-task "
                "record has task_file_path but no plan address (predates the plan/task "
                "fields) — not falling back to path-parsing; activity tracking for this "
                "session will not resume until a fresh /start-task runs",
                file=sys.stderr,
            )
    except (json.JSONDecodeError, KeyError, IndexError):
        pass

    return None, None, None


def _call_sam_active_task_clear(session_id: str, timeout: float = 8) -> bool:
    """Clear active task context via the SAM CLI's ``active-task clear`` subcommand.

    Best-effort cleanup after SubagentStop completes. Never raises.

    Args:
        session_id: Sub-agent session identifier. Empty string is normalised to
            ``"_default"`` sentinel.
        timeout: Subprocess timeout in seconds.

    Returns:
        ``True`` if the active task was successfully cleared, ``False`` otherwise.
    """
    resolved = session_id or "_default"
    stdout = _call_sam_cli(["active-task", "clear", "--session-id", resolved], timeout=timeout)
    return stdout is not None


def _get_uv_executable() -> str | None:
    """Return the path to the uv executable, or None if not found on PATH.

    Returns:
        Absolute path string to uv, or None when uv is absent.
    """
    return shutil.which("uv")


def _call_sam_cli(args: list[str], timeout: float = 8) -> str | None:
    """Execute the SAM CLI as a subprocess and return raw stdout.

    Handles uv resolution, subprocess execution, and common failure modes.
    Callers are responsible for JSON parsing and context-specific error
    logging.

    Launches the subprocess in its own session on POSIX so a timeout can
    terminate the whole process tree via :func:`run_bounded.terminate_process_tree`,
    not just the immediate ``uv`` child -- ``uv run --script`` may spawn its
    own child interpreter, and killing only the ``uv`` pid would leave that
    interpreter orphaned. The default timeout is kept comfortably below the
    10-second PostToolUse hook deadline in ``hooks/hooks.json`` -- a default
    at or above that deadline lets Claude Code's own external SIGKILL win the
    race before this method's internal timeout handling (and process-tree
    cleanup) ever runs, which is exactly the orphaned-process failure mode
    described in ``.claude/rules/hook-subprocess-invocation.md``.

    Args:
        args: Subcommand and options to pass to the SAM CLI (e.g.
            ``["plan", "read", "--address", "P1/T1"]``).
        timeout: Subprocess timeout in seconds. Must stay below the
            PostToolUse hook's own timeout for the reason above.

    Returns:
        Raw stdout string on success, None on any failure (uv missing,
        CLI script missing, subprocess error, timeout, non-zero exit).
    """
    uv = _get_uv_executable()
    if uv is None or not _SAM_CLI_PATH.exists():
        return None

    try:
        proc = subprocess.Popen(
            [uv, "run", "--script", str(_SAM_CLI_PATH), *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=os.name == "posix",
        )
    except (subprocess.SubprocessError, OSError):
        return None

    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        terminate_process_tree(proc)
        proc.communicate()
        return None

    if proc.returncode != 0:
        if stderr:
            print(f"[hook] sam CLI {args[0] if args else ''} failed: {stderr.strip()}", file=sys.stderr)
        return None

    return stdout


def _call_sam_task_state(plan_addr: str, task_id: str, status: SamTaskStatus, timeout: float = 8) -> bool:
    """Update task status via the SAM CLI's ``plan state`` subcommand.

    Routes state writes through the SAM CLI, keeping the hook
    backend-agnostic. The CLI handles downstream skip cascades when
    ``status="failed"``.

    Args:
        plan_addr: Plan address (e.g. ``"Pf4281187"``).
        task_id: Task ID within the plan (e.g. ``"T1"``).
        status: New task status string (e.g. ``"complete"``, ``"skipped"``).
        timeout: Subprocess timeout in seconds.

    Returns:
        ``True`` if the CLI call succeeded, ``False`` on any failure.
    """
    stdout = _call_sam_cli(
        ["plan", "state", "--address", f"{plan_addr}/{task_id}", "--new-status", str(status)], timeout=timeout
    )
    if stdout is None:
        print(f"[hook] sam_task state={status} failed for {plan_addr}/{task_id}", file=sys.stderr)
        return False

    try:
        json.loads(stdout)
    except json.JSONDecodeError:
        print(f"[hook] sam_task state: unexpected response for {plan_addr}/{task_id}", file=sys.stderr)
        return False

    return True


_UPDATE_FIELD_OPTIONS: dict[str, str] = {"completed": "--completed", "last-activity": "--last-activity"}


def _call_sam_task_update(plan_addr: str, task_id: str, set_fields: dict[str, Any], timeout: float = 8) -> bool:
    """Update task fields via the SAM CLI's ``plan update`` subcommand.

    Only fields with a mapped CLI option are supported (a typed allowlist,
    not a generic JSON passthrough). An unmapped field fails closed without
    invoking the CLI at all.

    Args:
        plan_addr: Plan address (e.g. ``"Pf4281187"``).
        task_id: Task ID within the plan (e.g. ``"T1"``).
        set_fields: Field name/value pairs to patch on the task. Keys must
            be one of ``_UPDATE_FIELD_OPTIONS``.
        timeout: Subprocess timeout in seconds.

    Returns:
        ``True`` if the CLI call succeeded, ``False`` on any failure or
        unmapped field.
    """
    options: list[str] = []
    for key, value in set_fields.items():
        option = _UPDATE_FIELD_OPTIONS.get(key)
        if option is None:
            print(f"[hook] sam_task update: unsupported field {key!r} for {plan_addr}/{task_id}", file=sys.stderr)
            return False
        options.extend([option, str(value)])

    stdout = _call_sam_cli(["plan", "update", "--plan-address", f"{plan_addr}/{task_id}", *options], timeout=timeout)
    if stdout is None:
        print(f"[hook] sam_task update failed for {plan_addr}/{task_id}", file=sys.stderr)
        return False

    try:
        json.loads(stdout)
    except json.JSONDecodeError:
        print(f"[hook] sam_task update: unexpected response for {plan_addr}/{task_id}", file=sys.stderr)
        return False

    return True


def _call_sam_task_read(plan_id: str, task_id: str, timeout: float = 8) -> SamTask | None:
    """Read a task via the SAM CLI's ``plan read`` subcommand.

    Routes task reads through the SAM CLI, keeping the hook backend-agnostic.
    Returns the parsed Task object on success, None on any failure.

    Args:
        plan_id: Plan address (e.g. ``"Pf4281187"``).
        task_id: Task ID within the plan (e.g. ``"T1"``).
        timeout: Subprocess timeout in seconds.

    Returns:
        The parsed ``SamTask`` on success, ``None`` on any failure.
    """
    stdout = _call_sam_cli(["plan", "read", "--address", f"{plan_id}/{task_id}"], timeout=timeout)
    if stdout is None:
        return None

    try:
        data: dict[str, Any] = json.loads(stdout)
        task_data = data.get("task")
        return SamTask.model_validate(task_data) if task_data else None
    except (json.JSONDecodeError, ValueError):
        return None


def _cleanup_active_task_context(session_id: str | None, fallback_context_file: Path | None) -> None:
    """Clean up active task context after SubagentStop completes.

    Primary path: call the SAM CLI's ``active-task clear`` subcommand.
    Fallback: delete the filesystem context file if the CLI clear fails or is unavailable.

    Args:
        session_id: Sub-agent session identifier for the CLI clear call. ``None``
            skips that path entirely.
        fallback_context_file: Filesystem context file to delete if the CLI
            clear fails or session_id is ``None``.
    """
    cli_cleared = False
    if session_id:
        cli_cleared = _call_sam_active_task_clear(session_id)

    if not cli_cleared and fallback_context_file is not None:
        with contextlib.suppress(FileNotFoundError):
            fallback_context_file.unlink()


def get_iso_timestamp() -> str:
    """Return the current UTC time as an ISO-8601 string, truncated to whole seconds.

    Returns:
        ISO-8601 timestamp string (UTC, no microseconds).
    """
    return datetime.now(UTC).isoformat(timespec="seconds")


def _first_text_block(content: object) -> str | None:
    """Return the first non-empty ``type: "text"`` block's text from a message content list.

    Args:
        content: The ``message.content`` value from a parsed JSONL transcript record.

    Returns:
        The first non-empty text string found, or None if ``content`` is not a
        list or contains no text block.
    """
    if not isinstance(content, list):
        return None
    for item in content:
        if isinstance(item, dict) and item.get("type") == "text":
            text = item.get("text", "")
            if text:
                return text
    return None


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
    return _first_text_block(message.get("content", []))


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


def _parse_status_line(final_text: str) -> str | None:
    """Return the upper-cased STATUS token from *final_text*, or None if it carries none.

    Takes the FIRST match, because ``skills/subagent-contract/SKILL.md`` places the verdict
    on the report's opening line and says consumers branch on it "in that position". A later
    ``STATUS:`` line is therefore not a verdict — the ``NOTES:`` field of the
    ``agents/task-worker.md`` template is free text and comes last, so preferring the final
    match would let a note override the worker's own report.

    Every line is scanned rather than only line one because that same template wraps the
    report in a fence, which occupies the first line.

    Args:
        final_text: The worker's final message.

    Returns:
        The token in upper case, or None when no line is a well-formed STATUS report line.
    """
    for line in final_text.strip().splitlines():
        match = _STATUS_LINE_RE.match(line)
        if match:
            return match.group(1).upper()
    return None


def _resolve_final_message(hook_input: dict[str, Any]) -> tuple[str | None, str | None]:
    """Resolve the sub-agent's final message and its STATUS token.

    Prefers ``last_assistant_message`` from the hook payload. Claude Code's hook
    documentation is explicit that hooks needing the final assistant text "should use
    last_assistant_message on Stop and SubagentStop instead of reading the transcript",
    and Codex supplies the same field. Reading it costs one dictionary lookup where
    scanning the transcript costs a full file read on every sub-agent stop.

    Falls back to the transcript when the field is absent, which covers harnesses that
    do not supply it and older releases that predate it.

    Args:
        hook_input: Parsed SubagentStop hook input.

    Returns:
        Tuple of ``(status_token, final_text)``. ``final_text`` is None only when the
        message could not be obtained at all, which callers treat as evidence of nothing.
    """
    payload_message = hook_input.get("last_assistant_message")
    if isinstance(payload_message, str) and payload_message.strip():
        return _parse_status_line(payload_message), payload_message

    return _extract_status_from_transcript(Path(hook_input.get("agent_transcript_path", "")))


def _extract_status_from_transcript(transcript_path: Path) -> tuple[str | None, str | None]:
    """Extract the sub-agent's self-reported status from its final assistant message.

    Scans the whole transcript for the LAST ``type: "assistant"`` record with
    text content, then checks whether the first line of that text matches a
    ``STATUS: <TOKEN>`` line per subagent-contract.

    Args:
        transcript_path: Path to the sub-agent's JSONL transcript file.

    Returns:
        Tuple of ``(status_token, final_text)``. ``status_token`` is the
        upper-cased token (e.g. ``"DONE"``, ``"PARTIAL"``) or ``None`` if the
        final message has no recognizable ``STATUS:`` line. ``final_text`` is
        the full text of that message, or ``None`` if the transcript is
        missing, unreadable, or has no assistant text content at all.
    """
    if not transcript_path.exists():
        print(f"[hook] transcript not found: {transcript_path}", file=sys.stderr)
        return None, None

    final_text: str | None = None
    try:
        with transcript_path.open(encoding="utf-8") as fh:
            for raw_line in fh:
                stripped_line = raw_line.strip()
                if not stripped_line:
                    continue
                try:
                    record: dict[str, Any] = json.loads(stripped_line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(record, dict) or record.get("type") != "assistant":
                    continue
                message = record.get("message", {})
                if not isinstance(message, dict):
                    continue
                text = _first_text_block(message.get("content", []))
                if text:
                    final_text = text
    except OSError as e:
        print(f"[hook] could not read transcript for status extraction {transcript_path}: {e}", file=sys.stderr)
        return None, None

    if not final_text or not final_text.strip():
        return None, None

    return _parse_status_line(final_text), final_text


def _read_context_file(context_file: Path) -> tuple[str | None, str | None, str | int | None]:
    """Read plan address, task_id, and parent_issue_number from a context file.

    Args:
        context_file: Path to an active-task-*.json file.

    Returns:
        Tuple of (plan_address, task_id, parent_issue_number). Any field absent
        or unreadable is returned as None.
    """
    try:
        data: dict[str, Any] = json.loads(context_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None, None, None

    plan_addr = data.get("plan")
    task_id = data.get("task_id")
    if not plan_addr or not task_id:
        if data.get("task_file_path") and task_id:
            print(
                f"[hook] {context_file}: legacy context record has task_file_path but no plan "
                "address (predates the plan/task fields) — not falling back to path-parsing; "
                "activity tracking for this session will not resume until a fresh /start-task runs",
                file=sys.stderr,
            )
        return None, None, None

    parent_issue: str | int | None = data.get("parent_issue_number")

    return plan_addr, task_id, parent_issue


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


def _local_active_task_file(session_id: str) -> Path | None:
    """Return the local-backend active-task record for *session_id*, or None.

    The default ``local`` context backend stores each record at
    ``context_dir()/active-task-{session_id}.json``, so this hook can stat the exact
    file the SAM CLI would read. That matters for cost: this hook runs on every
    sub-agent stop in every plugin, and the ``active-task get`` subprocess costs
    ~1.3s of the ~1.75s total whether or not a task exists.

    Returns None — meaning "ask the CLI instead" — when the configured backend is
    anything else, because those keep the record where this process cannot see it.

    The key is not unique. Every sub-agent of one parent session carries that parent's
    session id, so several agents share one record and only the last write survives. A
    hit here does not prove the record belongs to the agent that just stopped.

    Args:
        session_id: Sub-agent session identifier.

    Returns:
        Path to the record for a local backend, or None to fall back to the CLI.
    """
    if DHConfig().get_backend(subsystem="context") != "local":
        return None

    try:
        context_dir = _dh_paths.context_dir()
    except (FileNotFoundError, subprocess.CalledProcessError, RuntimeError):
        # No resolvable project root — fall back to the CLI, as _resolve_context_file_from_transcript does.
        return None

    return context_dir / f"active-task-{session_id}.json"


def _resolve_active_task_context(
    hook_input: dict[str, Any],
) -> tuple[str | None, str | None, str | None, str | int | None, Path | None] | None:
    """Resolve the active task context for the agent that just stopped.

    Three-step resolution chain:
    1. The SAM CLI's ``active-task get`` subcommand, using the sub-agent's
       session_id extracted from the transcript (primary path).
    2. Filesystem context file via ``_resolve_context_file_from_transcript``
       (fallback when the agent did not call ``active-task set``).
    3. Prompt extraction from the JSONL transcript via
       ``_extract_prompt_from_transcript`` + ``extract_task_info_from_prompt``
       (final fallback for agents dispatched without context registration).

    Args:
        hook_input: Parsed SubagentStop hook input from stdin.

    Returns:
        ``(sub_agent_session_id, plan_id, task_id, parent_issue_number, context_file)``
        where ``plan_id`` is the plan address string.
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

    # Step 1: the active-task record.
    if sub_agent_session_id:
        local_record = _local_active_task_file(sub_agent_session_id)
        if local_record is None:
            # Backend stores the record somewhere this process cannot stat — ask the CLI.
            plan_id, task_id, parent_issue_number = _call_sam_active_task_get(sub_agent_session_id)
        elif local_record.exists():
            context_file = local_record
            plan_id, task_id, parent_issue_number = _read_context_file(local_record)
        # Local backend with no record: no active task. Steps 2 and 3 still run, and
        # both read files, so the no-active-task path spawns no subprocess at all.

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
                # extract_task_info_from_prompt resolves plan-arg to a local filesystem
                # path (resolve_plan_address). Recover the address token from its filename,
                # falling back to the path string itself if no address token is present.
                address_match = re.search(r"(P[0-9a-f]+)", extracted_path.name, re.IGNORECASE)
                extracted_plan_id = address_match.group(1) if address_match else str(extracted_path)
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

    Routes the cascade through the SAM CLI's ``plan state`` subcommand
    (``--new-status failed``). The CLI handles DependencyGraph construction and
    downstream SKIPPED writes atomically. Absorbs all failures — SubagentStop
    critical path must not be blocked by subprocess or write errors.

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


def _block_task_on_report(
    plan_addr: str,
    task_id: str,
    status_token: str | None,
    final_text: str | None,
    sub_agent_session_id: str | None,
    context_file: Path | None,
) -> None:
    """Mark a task BLOCKED because its worker did not report completion.

    Echoes the worker's own first line to stderr so the reported token and reason
    survive into the hook log. Names the specific contract failure: a non-complete
    token, a final message with no ``STATUS:`` line, or no final message at all.
    Terminal — calls sys.exit(0).

    Args:
        plan_addr: Plan address (e.g. ``"Pf4281187"``).
        task_id: Task ID within the plan.
        status_token: The token parsed from the worker's STATUS line, or None if
            the final message carried no recognizable STATUS line.
        final_text: The worker's final message, or None if unavailable.
        sub_agent_session_id: Agent session ID for context cleanup.
        context_file: Context file path for cleanup.
    """
    if status_token is not None:
        cause = f"reported STATUS: {status_token}"
    elif final_text is not None:
        cause = "final message has no 'STATUS:' first line"
    else:
        cause = "produced no final message"
    first_line = final_text.strip().splitlines()[0][:200] if final_text else "(no final message found)"
    print(f"[hook] SubagentStop: {task_id} {cause} ({first_line!r}) — marking blocked instead", file=sys.stderr)
    if not _call_sam_task_state(plan_addr, task_id, SamTaskStatus.BLOCKED):
        print(f"[hook] SubagentStop: failed to mark {task_id} blocked via the SAM CLI", file=sys.stderr)
    _cleanup_active_task_context(sub_agent_session_id, context_file)
    sys.exit(0)


def _resolve_non_complete_report(
    plan_addr: str,
    task_id: str,
    status_token: str | None,
    final_text: str | None,
    already_complete: bool,
    sub_agent_session_id: str | None,
    context_file: Path | None,
) -> None:
    """Decide what a non-completion report does to task state. Terminal — calls sys.exit(0).

    Three outcomes, because the reasons a report is not a completion are not equivalent:

    - **Unreadable transcript, task already COMPLETE** — leave it. Writing COMPLETE and
      reverting one both need positive evidence, and a failed read is evidence of nothing.
      Un-completing finished work here would stall the whole wave.
    - **A token in neither vocabulary** — leave state alone. Shipped specialists report
      VERIFIED, CONNECTED, GAPS_FOUND, READY and DRAFTING; since the SubagentStop matcher
      no longer filters non-task-worker agents out, blocking on an unrecognised word would
      turn their correct work into BLOCKED.
    - **Everything else** — block. A known non-completion token, or a readable final message
      with no STATUS line at all, both positively evidence that the worker did not finish.

    Args:
        plan_addr: Plan address (e.g. ``"Pf4281187"``).
        task_id: Task ID within the plan.
        status_token: Token parsed from the worker's STATUS line, or None if there was none.
        final_text: The worker's final message, or None if the transcript was unreadable.
        already_complete: Whether the task already reads COMPLETE.
        sub_agent_session_id: Agent session ID for context cleanup.
        context_file: Context file path for cleanup.
    """
    if final_text is None and already_complete:
        print(
            f"[hook] SubagentStop: no final message readable for {task_id}; leaving existing COMPLETE unchanged",
            file=sys.stderr,
        )
        _cleanup_active_task_context(sub_agent_session_id, context_file)
        sys.exit(0)

    if status_token is not None and status_token not in _INCOMPLETE_STATUS_TOKENS:
        print(
            f"[hook] SubagentStop: {task_id} reported STATUS: {status_token}, which is neither a "
            "completion nor a failure token — task state unchanged",
            file=sys.stderr,
        )
        _cleanup_active_task_context(sub_agent_session_id, context_file)
        sys.exit(0)

    _block_task_on_report(plan_addr, task_id, status_token, final_text, sub_agent_session_id, context_file)


def handle_subagent_stop(hook_input: dict[str, Any], profile: HookProfile = HookProfile.STANDARD) -> None:
    """Handle SubagentStop event - mark task COMPLETE or BLOCKED based on the worker's report.

    Discovers the active task via the SAM CLI's ``active-task get`` subcommand
    (primary) or the ``active-task-{session_id}.json`` context file (fallback).
    This ensures only the task belonging to the finished agent is marked
    complete — not all in-progress tasks — which is critical for correct
    behaviour with parallel agents.

    Discovery steps:
    1. Extract sub-agent's session_id from ``agent_transcript_path``.
    2. Call the SAM CLI's ``active-task get`` subcommand (primary path).
    3. Fall back to ``active-task-{session_id}.json`` on disk if that call fails.
    4. After status update, call ``active-task clear`` or delete the file.

    Before writing COMPLETE, reads the worker's own final message via
    ``_extract_status_from_transcript`` and checks its ``STATUS:`` line against
    ``_COMPLETE_STATUS_TOKENS``. Anything else — a non-complete token, an
    unrecognized one, or a final message with no STATUS line — marks the task
    BLOCKED instead.

    Evidence is asymmetric, and the two failure kinds are not the same:

    - **The worker's report** decides the state. A readable final message that
      does not report completion blocks the task, including one that omits the
      ``STATUS:`` line entirely — that is a contract violation by the worker,
      and the most common one.
    - **A transcript the hook could not read** decides nothing. Writing COMPLETE
      and reverting a COMPLETE both require positive evidence, so a missing,
      unreadable, or empty transcript leaves an existing COMPLETE untouched
      rather than un-completing finished work and stalling the wave. With no
      existing COMPLETE it still blocks, because nothing has evidenced success.

    All status and field writes route through the SAM CLI as a single
    subprocess, making the hook backend-agnostic.

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

    plan_addr = plan_id

    current_task = _call_sam_task_read(plan_addr, task_id)
    if current_task is None:
        print(
            f"[hook] SubagentStop: could not read task {task_id} from plan {plan_addr} via the SAM CLI — skipping",
            file=sys.stderr,
        )
        _cleanup_active_task_context(sub_agent_session_id, context_file)
        sys.exit(0)

    if current_task.status == SamTaskStatus.FAILED:
        # Agent explicitly set task to FAILED before stopping. That is a deliberate
        # self-report of a terminal state, more specific than anything the transcript
        # says, so it wins. Cascade skip signals to all downstream dependents.
        # _cascade_failed_task is terminal (calls sys.exit(0)); return guards mocked callers.
        _cascade_failed_task(plan_addr, task_id, sub_agent_session_id, context_file)
        return

    # The worker's final message is the authority on whether it finished, NOT the task
    # state — start-task lets a worker mark itself complete before stopping, so a task
    # already reading COMPLETE proves nothing about what the worker actually reported.
    # This check therefore runs before any COMPLETE short-circuit.
    status_token, final_text = _resolve_final_message(hook_input)
    already_complete = current_task.status == SamTaskStatus.COMPLETE

    if status_token not in _COMPLETE_STATUS_TOKENS:
        # _resolve_non_complete_report is terminal (calls sys.exit(0)); return guards mocked callers.
        _resolve_non_complete_report(
            plan_addr, task_id, status_token, final_text, already_complete, sub_agent_session_id, context_file
        )
        return

    # Worker reported completion and already marked itself complete — nothing to write.
    if already_complete:
        _cleanup_active_task_context(sub_agent_session_id, context_file)
        sys.exit(0)

    if profile == HookProfile.STRICT:
        for warning in run_strict_pre_completion_checks(current_task, task_id):
            print(warning, file=sys.stderr)

    timestamp = get_iso_timestamp()
    state_ok = _call_sam_task_state(plan_addr, task_id, SamTaskStatus.COMPLETE)
    if not state_ok:
        print(f"[hook] SubagentStop: failed to mark {task_id} complete via the SAM CLI", file=sys.stderr)
        _cleanup_active_task_context(sub_agent_session_id, context_file)
        sys.exit(0)
    _call_sam_task_update(plan_addr, task_id, {"completed": timestamp})
    _cleanup_active_task_context(sub_agent_session_id, context_file)


# Total wall-clock budget shared across every _call_sam_cli invocation made within
# one handle_activity_update() run, kept safely below the 10-second PostToolUse
# deadline in hooks/hooks.json. Each call below gets whatever budget remains rather
# than its own full default -- two independent 8-second defaults could sum past the
# outer deadline even though each call alone stays under it.
_POST_TOOL_USE_BUDGET_SECONDS = 8.0


def handle_activity_update(hook_input: dict[str, Any]) -> None:
    """Handle PostToolUse event - update LastActivity timestamp.

    Reads task info from context file and updates the last-activity field
    via the SAM CLI (backend-agnostic write path).

    Args:
        hook_input: Parsed hook input from stdin.
    """
    cwd = Path(hook_input.get("cwd", "."))
    session_id = hook_input.get("session_id", "")

    if not session_id:
        sys.exit(0)

    plan_addr, task_id = read_task_context(cwd, session_id)

    if plan_addr is None or task_id is None:
        sys.exit(0)

    deadline = time.monotonic() + _POST_TOOL_USE_BUDGET_SECONDS

    current_task = _call_sam_task_read(plan_addr, task_id, timeout=max(0.1, deadline - time.monotonic()))
    if current_task is None:
        print(
            f"[hook] PostToolUse: could not read task {task_id} from plan {plan_addr} via the SAM CLI — skipping",
            file=sys.stderr,
        )
    elif current_task.status == SamTaskStatus.COMPLETE:
        return

    remaining = deadline - time.monotonic()
    if remaining <= 0:
        print(
            f"[hook] PostToolUse: skipping last-activity update for {task_id} — shared time budget exhausted",
            file=sys.stderr,
        )
        return

    timestamp = get_iso_timestamp()
    _call_sam_task_update(plan_addr, task_id, {"last-activity": timestamp}, timeout=remaining)


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
