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
"""Task status hook — the orchestrator's automatic ``settle`` when a launch ends.

Two hook events reach this script:

- **SubagentStop**: settle the attempt the stopping sub-agent was launched for, recording what
  came back. It writes no status.
- **PostToolUse** (``Write|Edit|Bash``): update the ``last-activity`` timestamp of the session's
  active task.

Every write routes through the SAM CLI (``scripts/run_sam_cli.py``) as a single subprocess, so
the hook stays backend-agnostic and never touches storage directly.

Why SubagentStop settles and does not decide
--------------------------------------------
The work ledger gives each of the three actors one command, and the reason each exists is that
no other actor can supply what it records:

- ``plan finish --result <complete|partial|failed|…>`` is the **runner's** own exit status. Only
  the runner knows whether the work was done.
- ``plan accept`` / ``plan reclaim`` is the **judge's** verdict, taken after reading the report
  against the acceptance criteria. Only a reader of the report can reach it.
- ``plan settle --attempt N --return-text …`` is the **orchestrator** recording that the launch
  ended at all, and what it returned. That is the one fact neither of the others can produce: a
  runner that died mid-flight writes nothing, and an unsettled attempt is indistinguishable from
  a worker still at work, so the loop waits on an agent that is gone.
- ``plan state --new-status X --reason Y`` is the runner-less status move — a decision nobody's
  attempt is responsible for, which is why the ledger demands a reason for it.

A ``SubagentStop`` hook registered in a plugin's ``hooks/hooks.json`` runs in the **orchestrator's
session** when a sub-agent it launched stops (``code.claude.com/docs/en/sub-agents.md`` §
"Project-level hooks for subagent events", as cached in
``plugins/plugin-creator/skills/claude-subagent-reference/references/hooks-for-subagents.md``,
accessed 2026-05-28: hooks configured this way "run in the main session when subagents start or
stop"). It is therefore the orchestrator's observation point, and ``settle`` is its command.

The orchestrator skills (``implement-feature``, ``dispatch``) settle explicitly as their own next
step. This hook is not a replacement for that; it is the safety net for the launch whose
orchestrator step never ran — a session that died, compacted, or skipped it. ``settle`` answers
the no-op code ``already-settled`` on exit 0 when the orchestrator got there first, so the two
never fight.

The hook writes no status because status already has a writer. ``runner-contract.md`` and
``start-task/SKILL.md`` both instruct a worker to "return ``STATUS: DONE`` once ``finish`` was
recorded, **whatever its ``--result``**". A hook mapping that returned token onto a status would
therefore write ``complete`` for a task whose runner reported ``failed`` — two encodings of one
fact, guaranteed by the contract to disagree. The worker's final message reaches the ledger here
as ``--return-text``, which is evidence for the judge, not a verdict.

Correlating the stopping agent to its attempt
---------------------------------------------
The address and the attempt both come from the sub-agent's own initial prompt, read from
``agent_transcript_path``. That transcript is per-sub-agent, so N workers dispatched in parallel
correlate to N distinct attempts.

The session-scoped active-task record is deliberately not used for this. It is keyed by
``${CLAUDE_CODE_SESSION_ID}``, which inside a sub-agent is the parent session's id, so every
sub-agent of one wave writes to one record and only the last survives; and it carries no attempt
number at all (``ActiveTaskContext`` in ``sam_schema/core/models.py`` declares none, and
``active-task set`` exposes no ``--attempt`` flag). It is still cleared here, because the record
is session state and the session stopped.

When the prompt names no attempt, no settle is possible and the hook says so on stderr rather
than absorbing it.

Usage:
    Called automatically via hooks configuration.
    Receives JSON via stdin with hook context.

Exit Codes:
    0: Success. The SubagentStop critical path must never be blocked by a failed write, so every
       failure is reported on stderr and the hook still exits 0.
    2: Malformed hook input (stderr message shown to Claude).
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

from pydantic import BaseModel

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
from sam_schema.core.models import TaskStatus as SamTaskStatus

from run_bounded import terminate_process_tree

# Alphanumeric task ID pattern: "1", "1.1", "T1", "P0-T01", etc.
_TASK_ID_RE = r"[A-Za-z0-9]+(?:[-.][\dA-Za-z]+)*"

# Plan argument pattern: file path (.md/.yaml) OR plan address (P<hex>).
# Named group ``plan`` captures whichever form is present.
# re.IGNORECASE: plan address prefix P is case-insensitive (e.g. PDEADBEef).
_PLAN_ARG_RE = r"(?P<plan>(?:[^\s\"']+\.(?:md|yaml))|(?:P[0-9a-f]+))"

# The ledger address form alone. Pattern 1 below searches for this inside a longer prompt, so it
# excludes the file-path form: a bare path followed by the word "attempt" is not a dispatch.
_PLAN_ADDRESS_RE = r"(?P<plan>P[0-9a-f]+)"

# The attempt clause the dispatch contract writes after the address, as an optional suffix.
# implement-feature/SKILL.md launches with "{plan_ref}/{task_id}, attempt {attempt}" and
# dispatch/SKILL.md with "You are working on P.../T..., attempt 1." — the comma and the
# surrounding prose both vary, so only "attempt <n>" itself is required.
_ATTEMPT_CLAUSE_RE = r"[\s,]*attempt\s+(?P<attempt>\d+)"

# The same clause as a flag, for the /start-task and Skill() forms.
_ATTEMPT_FLAG_RE = r"(?:\s+--attempt\s+(?P<attempt>\d+))?"

# Recorded as the return text when the launch produced no final message at all. settle is still
# run in that case: the work loop's step 4 settles "including when the response is empty or the
# agent crashed", because an unsettled attempt reads as a worker still at work.
_NO_FINAL_MESSAGE = "(no final message: the launch ended without one)"


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


class Launch(BaseModel):
    """The dispatch one stopping sub-agent was launched for, as read from its own prompt.

    The plan is carried as the address token the prompt wrote, not as a filesystem path: the
    ledger addresses a task as ``P/T`` and holds no plan file to resolve one against.
    """

    plan: str
    task_id: str
    attempt: int | None = None
    """The attempt ``dispatch`` opened, when the prompt named it. ``None`` means no ``settle``
    is possible — ``settle`` names the attempt it records against."""

    @property
    def address(self) -> str:
        """Return the ``P/T`` address the SAM CLI takes.

        Returns:
            The plan token and task id joined by a slash.
        """
        return f"{self.plan}/{self.task_id}"

    @property
    def is_ledger_address(self) -> bool:
        """Report whether the plan token is a ledger plan address rather than a legacy file path.

        Returns:
            True when the token has the ``P<hex>`` form every ledger command takes.
        """
        return re.fullmatch(r"P[0-9a-f]+", self.plan, re.IGNORECASE) is not None


def extract_launch_from_prompt(prompt: str) -> Launch | None:
    """Read the plan address, task id and attempt number out of a sub-agent's initial prompt.

    The prompt is the only per-sub-agent carrier of these three facts. The session-scoped
    active-task record is keyed by the parent session's id and holds no attempt number, so it
    cannot name the attempt a settle must record against — see the module docstring.

    Four prompt shapes are recognised, in this order:

    1. ``/start-task <plan> [--task <id>] [--attempt <n>]`` — the literal slash command.
    2. ``Skill(skill="start-task", args="<plan> [--task <id>] [--attempt <n>]")``.
    3. ``<plan-address>/<task-id>[,] attempt <n>`` anywhere in the prompt — the shape
       ``implement-feature/SKILL.md`` and ``dispatch/SKILL.md`` launch with. Searched rather
       than full-matched because ``dispatch`` wraps it in a sentence; the required ``attempt
       <n>`` suffix is what keeps the search from matching an address mentioned in passing.
    4. ``<plan>/<task-id>`` as the whole prompt, full-matched. This form names no attempt, so it
       identifies the task without enabling a settle.

    Args:
        prompt: The sub-agent's initial prompt string.

    Returns:
        The :class:`Launch` the prompt names, or ``None`` when it names none.
    """
    if not prompt:
        return None

    command_forms = (
        rf"/start-task\s+{_PLAN_ARG_RE}(?:\s+--task\s+(?P<task_id>{_TASK_ID_RE}))?{_ATTEMPT_FLAG_RE}",
        (
            rf'Skill\(\s*skill\s*=\s*["\']start-task["\']\s*,\s*args\s*=\s*["\']'
            rf"{_PLAN_ARG_RE}(?:\s+--task\s+(?P<task_id>{_TASK_ID_RE}))?{_ATTEMPT_FLAG_RE}"
            rf'["\']'
        ),
    )
    for pattern in command_forms:
        match = re.search(pattern, prompt, re.IGNORECASE)
        if match and match.group("task_id"):
            return _launch_of(match)

    dispatch_match = re.search(
        rf"{_PLAN_ADDRESS_RE}/(?P<task_id>{_TASK_ID_RE}){_ATTEMPT_CLAUSE_RE}", prompt, re.IGNORECASE
    )
    if dispatch_match:
        return _launch_of(dispatch_match)

    bare_match = re.fullmatch(rf"{_PLAN_ARG_RE}/(?P<task_id>{_TASK_ID_RE})", prompt.strip(), re.IGNORECASE)
    if bare_match:
        return _launch_of(bare_match)

    return None


def _launch_of(match: re.Match[str]) -> Launch:
    """Build a :class:`Launch` from a match carrying ``plan``, ``task_id`` and optional ``attempt``.

    Args:
        match: A match of one of :func:`extract_launch_from_prompt`'s patterns.

    Returns:
        The launch the match names.
    """
    groups = match.groupdict()
    raw_attempt = groups.get("attempt")
    return Launch(
        plan=match.group("plan"), task_id=match.group("task_id"), attempt=int(raw_attempt) if raw_attempt else None
    )


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


def _call_sam_active_task_clear(session_id: str, timeout: float = 8) -> bool:
    """Clear active task context via the SAM CLI's ``active-task clear`` subcommand.

    Best-effort cleanup after SubagentStop completes. Never raises.

    Args:
        session_id: Sub-agent session identifier. Required: ``dh_core.operations.require_session_id``
            rejects an empty one and the reserved ``"_default"`` sentinel, so an empty id is
            answered here rather than spent on a subprocess that can only fail.
        timeout: Subprocess timeout in seconds.

    Returns:
        ``True`` if the active task was successfully cleared, ``False`` otherwise.
    """
    resolved = session_id
    if not resolved:
        return False
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


def _call_sam_plan_settle(launch: Launch, return_text: str, timeout: float = 8) -> bool:
    """Record that one launch ended, and what it returned, via the SAM CLI's ``plan settle``.

    ``settle`` is the orchestrator's command: it marks the attempt settled and stores the harness
    return text, which is what makes a launch that ended distinguishable from a worker still at
    work. It writes no status — the runner's ``finish`` and the judge's ``accept``/``reclaim``
    own that, and a second writer of the same fact would drift from them.

    The call is safe to repeat. When the orchestrator already settled this attempt, ``settle``
    prints the no-op code ``already-settled`` on stdout and exits 0.

    Args:
        launch: The dispatch to settle. Its ``attempt`` must not be ``None``.
        return_text: What the launch returned — the sub-agent's final message, or
            :data:`_NO_FINAL_MESSAGE` when it produced none.
        timeout: Subprocess timeout in seconds.

    Returns:
        ``True`` when the ledger recorded the settle or reported it already settled,
        ``False`` on any failure.
    """
    stdout = _call_sam_cli(
        ["plan", "settle", "--address", launch.address, "--attempt", str(launch.attempt), "--return-text", return_text],
        timeout=timeout,
    )
    if stdout is None:
        print(
            f"[hook] SubagentStop: settle failed for {launch.address} attempt {launch.attempt} — "
            "the attempt stays open and the loop will read it as a worker still at work",
            file=sys.stderr,
        )
        return False

    reported = stdout.strip()
    try:
        json.loads(reported)
    except json.JSONDecodeError:
        # A no-op code (`already-settled`) is printed as a bare word on stdout with exit 0.
        print(f"[hook] SubagentStop: settle of {launch.address} attempt {launch.attempt}: {reported}", file=sys.stderr)
        return True

    print(f"[hook] SubagentStop: settled {launch.address} attempt {launch.attempt}", file=sys.stderr)
    return True


_UPDATE_FIELD_OPTIONS: dict[str, str] = {"last-activity": "--last-activity"}


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


def _call_sam_task_status(plan_id: str, task_id: str, timeout: float = 8) -> SamTaskStatus | None:
    """Read one task's current status via the SAM CLI's ``plan read`` subcommand.

    Two response shapes reach this function, because ``plan read`` serves two stores. The work
    ledger returns the task row under ``row`` and puts the task *id* — a bare string — under
    ``task``; the content store returns the task object under ``task``. Reading ``task`` alone
    therefore yields a string on a ledger plan, which is why this looks at ``row`` first.

    Only the status is extracted. Validating the whole row as a ``Task`` fails on a ledger
    response regardless of shape: the ledger stores list-valued columns as JSON text, and
    ``Task``'s own validators reject ``dependencies="[]"``.

    Args:
        plan_id: Plan address (e.g. ``"Pf4281187"``).
        task_id: Task ID within the plan (e.g. ``"T1"``).
        timeout: Subprocess timeout in seconds.

    Returns:
        The task's status, or ``None`` when the call failed or the response carried no
        recognisable status.
    """
    stdout = _call_sam_cli(["plan", "read", "--address", f"{plan_id}/{task_id}"], timeout=timeout)
    if stdout is None:
        return None

    try:
        data: dict[str, Any] = json.loads(stdout)
    except json.JSONDecodeError:
        return None

    for key in ("row", "task"):
        candidate = data.get(key)
        if isinstance(candidate, dict):
            raw_status = candidate.get("status")
            if isinstance(raw_status, str):
                try:
                    return SamTaskStatus(raw_status)
                except ValueError:
                    return None
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


def _resolve_return_text(hook_input: dict[str, Any], transcript_path: Path | None) -> str:
    """Return what the launch came back with, for ``settle --return-text``.

    Prefers ``last_assistant_message`` from the hook payload. Claude Code's hook documentation is
    explicit that hooks needing the final assistant text "should use last_assistant_message on
    Stop and SubagentStop instead of reading the transcript", and Codex supplies the same field.
    Reading it costs one dictionary lookup where scanning the transcript costs a full file read on
    every sub-agent stop.

    Falls back to the last assistant text block in the sub-agent's transcript, which covers
    harnesses that do not supply the field and older releases that predate it. When neither
    yields text, :data:`_NO_FINAL_MESSAGE` is returned rather than nothing: a launch that came
    back empty still ended, and recording that it ended is the whole point of settling.

    Args:
        hook_input: Parsed SubagentStop hook input.
        transcript_path: The sub-agent's own transcript, or ``None`` when the payload named none.

    Returns:
        The text to record against the attempt. Never empty.
    """
    payload_message = hook_input.get("last_assistant_message")
    if isinstance(payload_message, str) and payload_message.strip():
        return payload_message

    if transcript_path is not None:
        transcript_text = _last_assistant_text(transcript_path)
        if transcript_text:
            return transcript_text

    return _NO_FINAL_MESSAGE


def _last_assistant_text(transcript_path: Path) -> str | None:
    """Return the text of the last assistant message in a JSONL transcript.

    Args:
        transcript_path: Path to the sub-agent's JSONL transcript file.

    Returns:
        The final assistant text block, or ``None`` when the file is missing, unreadable, or
        carries no assistant text at all.
    """
    if not transcript_path.exists():
        print(f"[hook] transcript not found: {transcript_path}", file=sys.stderr)
        return None

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
        print(f"[hook] could not read transcript for return text {transcript_path}: {e}", file=sys.stderr)
        return None

    return final_text


def handle_subagent_stop(hook_input: dict[str, Any], profile: HookProfile = HookProfile.STANDARD) -> None:
    """Settle the attempt the stopping sub-agent was launched for; write no status.

    The one fact this hook holds that nobody else does is that the launch ended. It records that,
    with the text that came back, through ``plan settle``. What the work amounted to is the
    runner's ``finish`` to report and the judge's ``accept``/``reclaim`` to decide — see the
    module docstring for why a hook writing status alongside them would drift from them.

    Sequence:

    1. Read the sub-agent's own initial prompt from ``agent_transcript_path`` and take the plan
       address, task id and attempt number from it. The transcript is per-sub-agent, so parallel
       workers do not collide here.
    2. ``plan settle --address P/T --attempt N --return-text "<what came back>"``.
    3. Clear the session's active-task context.

    Every failure is printed to stderr and none is fatal: the SubagentStop critical path must not
    be blocked, so this returns normally however the settle went and :func:`main` exits 0. It never
    no-ops silently — a settle that could not be attempted says which fact was missing, and one
    that failed says the attempt stays open.

    Args:
        hook_input: Parsed hook input from stdin.
        profile: Active hook profile. Accepted for call-site compatibility; the profile gates
            whether this handler runs at all (see :func:`should_skip_hook`) and no longer varies
            what it does, because settling records evidence rather than deciding an outcome.
    """
    del profile

    transcript_path_raw = hook_input.get("agent_transcript_path", "")
    transcript_path = Path(transcript_path_raw) if transcript_path_raw else None
    if transcript_path is None:
        print(
            "[hook] SubagentStop: no agent_transcript_path in hook input — cannot correlate the "
            "stopping agent to an attempt, so nothing was settled",
            file=sys.stderr,
        )
        return

    sub_agent_session_id = _extract_session_id_from_transcript(transcript_path)
    context_file = _local_active_task_file(sub_agent_session_id) if sub_agent_session_id else None

    launch = _resolve_launch(transcript_path)
    if launch is not None:
        _call_sam_plan_settle(launch, _resolve_return_text(hook_input, transcript_path))
    _cleanup_active_task_context(sub_agent_session_id, context_file)


def _resolve_launch(transcript_path: Path) -> Launch | None:
    """Return the settle-able launch the sub-agent's prompt names, saying why when there is none.

    Args:
        transcript_path: The sub-agent's own JSONL transcript.

    Returns:
        A :class:`Launch` naming a ledger address and an attempt number, or ``None`` when the
        prompt names no dispatch, names one this hook cannot settle, or names no attempt.
    """
    prompt_text = _extract_prompt_from_transcript(transcript_path)
    if not prompt_text:
        print(
            f"[hook] SubagentStop: no initial prompt found in {transcript_path} — nothing was settled", file=sys.stderr
        )
        return None

    launch = extract_launch_from_prompt(prompt_text)
    if launch is None:
        # Not a dispatched task worker. Every sub-agent of every plugin reaches this hook, so this
        # is the ordinary case and not a fault.
        return None

    if not launch.is_ledger_address:
        print(
            f"[hook] SubagentStop: {launch.address} names a plan file rather than a ledger address; "
            "settle acts on ledger attempts only — nothing was settled",
            file=sys.stderr,
        )
        return None

    if launch.attempt is None:
        print(
            f"[hook] SubagentStop: {launch.address} was launched without an attempt number in its "
            "prompt; settle names the attempt it records against, so nothing was settled. Launch "
            "workers as the dispatch contract specifies: '{plan}/{task}, attempt {n}'",
            file=sys.stderr,
        )
        return None

    return launch


# Total wall-clock budget shared across every _call_sam_cli invocation made within
# one handle_activity_update() run, kept safely below the 10-second PostToolUse
# deadline in hooks/hooks.json. Each call below gets whatever budget remains rather
# than its own full default -- two independent 8-second defaults could sum past the
# outer deadline even though each call alone stays under it.
_POST_TOOL_USE_BUDGET_SECONDS = 8.0


def handle_activity_update(hook_input: dict[str, Any]) -> None:
    """Handle PostToolUse event — update the active task's ``last-activity`` timestamp.

    Reads the session's active task from the context record and updates the ``last-activity``
    field through the SAM CLI.

    Scope limit, deliberate and recorded here so it is not mistaken for a lease renewal: the
    ledger's liveness signal is the attempt's lease, pushed out by ``plan renew --address P/T
    --attempt N``, and ``--last-activity`` is a content-store field (``store_for`` in
    ``sam_schema/sam_plan.py`` classes it as a legacy flag, so an invocation naming it routes to
    the content store). This handler cannot renew a lease instead, because renewing needs the
    attempt number and the record it reads has none — ``ActiveTaskContext`` declares no attempt
    field and ``active-task set`` exposes no ``--attempt`` flag. Nor could adding one be enough:
    the record is keyed by ``session_id``, which inside a sub-agent is the parent session's, so
    one wave's workers share a record and this handler would renew a sibling's lease. Keying it
    per sub-agent needs an identifier the sub-agent can read for itself; looked for one in the
    cached Claude Code hooks documentation (``docs/work-ledger/measurements/harness-claude-code.md``
    § 6) and found ``agent_id`` only as a hook input field, never as an environment variable.

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

    current_status = _call_sam_task_status(plan_addr, task_id, timeout=max(0.1, deadline - time.monotonic()))
    if current_status is None:
        print(
            f"[hook] PostToolUse: could not read task {task_id} from plan {plan_addr} via the SAM CLI — skipping",
            file=sys.stderr,
        )
    elif current_status == SamTaskStatus.COMPLETE:
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
