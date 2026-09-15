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

One hook event reaches this script: **SubagentStop**. The hook settles the attempt the
stopping sub-agent was launched for, and records what came back. It writes no status.

The hook calls the SAM CLI (``scripts/run_sam_cli.py``) as one subprocess. It does not touch
storage directly.

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
The address and the attempt come from the sub-agent's own initial prompt, read from
``agent_transcript_path``. Each sub-agent has its own transcript, so N workers dispatched in
parallel correlate to N attempts. Settling is the whole of this hook (``ARCHITECTURE.md``).

When the prompt names no attempt, no settle is possible and the hook says so on stderr rather
than absorbing it.

No dispatcher-owned channel exists, so the prompt is read as a delimited field
----------------------------------------------------------------------------
The prompt is not a channel only the dispatcher writes — it is one field of a document whose
other fields the launched agent's own content fills. Looked for a channel that is: read the
SubagentStop input roster in ``docs/work-ledger/measurements/harness-claude-code.md`` §§ 2 and 6
(taken 2026-09-06 from the cached ``code.claude.com/docs/en/hooks`` page) and found only
``session_id``, ``prompt_id``, ``transcript_path``, ``cwd``, ``permission_mode``, ``effort``,
``hook_event_name``, ``stop_hook_active``, ``agent_id``, ``agent_type``, ``agent_transcript_path``
and ``last_assistant_message``. Every one is harness-assigned; none carries a value the
dispatcher chose, and § 6 records that no per-subagent environment variable was found either.
``SubagentStart`` cannot bridge the gap: its own input schema
(``plugin-creator/skills/claude-subagent-reference/references/hooks-for-subagents.md``, accessed
2026-05-28) carries ``agent_id`` and ``agent_type`` but neither the prompt nor a transcript path,
so it cannot bind a harness-assigned ``agent_id`` to a launch either. That is a statement about
those two documents, not a proof that no such channel can exist.

So this is containment, not a fix for the root cause. What it does: the launch reference must be
the *whole* of the prompt's first line. That is where the dispatch contract puts it and nothing
follows it — ``implement-feature/SKILL.md`` and ``qg-dispatch-step.md`` make the reference the
agent's entire prompt. ``dispatch/SKILL.md`` puts it in one sentence that ends at the attempt. Prose that mentions an
attempt in passing keeps going after it, so requiring the line to end there is what separates a
launch from a mention.

Residual exposure, unclosed: a sub-agent of any plugin whose prompt's *first line* both ends at
an attempt clause and reaches it through the words "working on" is still read as a launch — a
prompt quoting a dispatch sentence verbatim on its opening line is the realistic shape. Such a
settle is harmless against an attempt already settled (``settle`` answers ``already-settled``)
but wrong against a live one. Closing it needs a launch identity the sub-agent's content cannot
imitate, which needs a channel the harness does not currently offer.

Usage:
    Called automatically via hooks configuration.
    Receives JSON via stdin with hook context.

Exit Codes:
    0: Success. The SubagentStop critical path must never be blocked by a failed write, so every
       failure is reported on stderr and the hook still exits 0.
    2: Malformed hook input (stderr message shown to Claude).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
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

_HOOK_REPO_ROOT = Path(__file__).resolve().parents[5]
_HOOK_SAM_PACKAGES_DIR = str(_HOOK_REPO_ROOT / "packages")
if _HOOK_SAM_PACKAGES_DIR not in sys.path:
    sys.path.insert(0, _HOOK_SAM_PACKAGES_DIR)

from run_bounded import terminate_process_tree

# Alphanumeric task ID pattern: "1", "1.1", "T1", "P0-T01", etc.
_TASK_ID_RE = r"[A-Za-z0-9]+(?:[-.][\dA-Za-z]+)*"

# Plan argument pattern: file path (.md/.yaml) OR plan address (P<hex>).
# Named group ``plan`` captures whichever form is present.
# re.IGNORECASE: plan address prefix P is case-insensitive (e.g. PDEADBEef).
_PLAN_ARG_RE = r"(?P<plan>(?:[^\s\"']+\.(?:md|yaml))|(?:P[0-9a-f]+))"

# The ledger address form alone. The dispatch pattern below matches this against a whole line
# rather than a whole prompt, so it excludes the file-path form: a bare path followed by the word
# "attempt" is not a dispatch.
_PLAN_ADDRESS_RE = r"(?P<plan>P[0-9a-f]+)"

# The dispatch contract's sentence lead-in, as written by dispatch/SKILL.md: "Your ROLE_TYPE is
# sub-agent. You are working on {plan}/{task}, attempt {n}." Optional, because
# implement-feature/SKILL.md launches with the reference alone.
_LAUNCH_LEAD_IN_RE = r"(?:.*?\bworking on\s+)?"

# Trailing punctuation a launch line may carry: the dispatch sentence's full stop, the closing
# paren of a Skill() call. It admits no further words, which is what keeps the whole-line match
# from degenerating back into a search of free text.
_LAUNCH_TAIL_RE = r"[\s.)\"']*"

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


HOOK_ID_SUBAGENT_STOP = "task-status:subagent-stop"

_EVENT_TO_HOOK_ID: dict[str, str] = {"SubagentStop": HOOK_ID_SUBAGENT_STOP}


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


def should_skip_hook(event_name: str, disabled_hooks: set[str]) -> bool:
    """Return True if the hook for this event should be skipped.

    Args:
        event_name: Value of hook_event_name from the hook input (e.g. "SubagentStop").
        disabled_hooks: Set of hook IDs to skip unconditionally.

    Returns:
        True if the hook should exit 0 without running its handler.
    """
    hook_id = _EVENT_TO_HOOK_ID.get(event_name)
    return bool(hook_id and hook_id in disabled_hooks)


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

    The prompt is the only per-sub-agent carrier of these three facts.

    Every shape is matched against a *delimited position* rather than searched for in free text:
    the first three against the whole of the prompt's first line, the fourth against the whole
    prompt. See the module docstring for why the prompt is read this way and what that does not
    close. Four shapes are recognised, in this order:

    1. ``/start-task <plan> [--task <id>] [--attempt <n>]``, with or without the ``dh:`` plugin
       prefix. This is the slash command.
    2. ``Skill(skill="start-task", args="<plan> [--task <id>] [--attempt <n>]")``, with or without
       the ``dh:`` plugin prefix.
    3. ``[<lead-in> working on ]<plan-address>/<task-id>[,] attempt <n>`` — the shape
       ``implement-feature/SKILL.md`` and ``dispatch/SKILL.md`` launch with, the latter inside a
       sentence that ends at the attempt. The line must end there; prose that mentions an
       attempt in passing carries on past it.
    4. ``<plan>/<task-id>`` as the whole prompt. This form names no attempt, so it identifies the
       task without enabling a settle.

    Args:
        prompt: The sub-agent's initial prompt string.

    Returns:
        The :class:`Launch` the prompt names, or ``None`` when it names none.
    """
    if not prompt:
        return None

    line = _first_nonempty_line(prompt)
    if not line:
        return None

    command_forms = (
        rf"/(?:dh:)?start-task\s+{_PLAN_ARG_RE}(?:\s+--task\s+(?P<task_id>{_TASK_ID_RE}))?{_ATTEMPT_FLAG_RE}",
        (
            rf'Skill\(\s*skill\s*=\s*["\'](?:dh:)?start-task["\']\s*,\s*args\s*=\s*["\']'
            rf"{_PLAN_ARG_RE}(?:\s+--task\s+(?P<task_id>{_TASK_ID_RE}))?{_ATTEMPT_FLAG_RE}"
            rf'["\']'
        ),
    )
    for pattern in command_forms:
        match = re.fullmatch(rf"{pattern}{_LAUNCH_TAIL_RE}", line, re.IGNORECASE)
        if match and match.group("task_id"):
            return _launch_of(match)

    dispatch_match = re.fullmatch(
        rf"{_LAUNCH_LEAD_IN_RE}{_PLAN_ADDRESS_RE}/(?P<task_id>{_TASK_ID_RE}){_ATTEMPT_CLAUSE_RE}{_LAUNCH_TAIL_RE}",
        line,
        re.IGNORECASE,
    )
    if dispatch_match:
        return _launch_of(dispatch_match)

    bare_match = re.fullmatch(rf"{_PLAN_ARG_RE}/(?P<task_id>{_TASK_ID_RE})", prompt.strip(), re.IGNORECASE)
    if bare_match:
        return _launch_of(bare_match)

    return None


def _first_nonempty_line(prompt: str) -> str:
    """Return the first line of *prompt* carrying anything but whitespace.

    Args:
        prompt: The sub-agent's initial prompt string.

    Returns:
        The stripped first non-empty line, or ``""`` when the prompt is all whitespace.
    """
    for raw_line in prompt.splitlines():
        line = raw_line.strip()
        if line:
            return line
    return ""


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
    60-second SubagentStop hook deadline in ``hooks/hooks.json`` -- a default
    at or above that deadline lets Claude Code's own external SIGKILL win the
    race before this method's internal timeout handling (and process-tree
    cleanup) ever runs, which is exactly the orphaned-process failure mode
    described in ``.claude/rules/hook-subprocess-invocation.md``.

    Args:
        args: Subcommand and options to pass to the SAM CLI (e.g.
            ``["plan", "read", "--address", "P1/T1"]``).
        timeout: Subprocess timeout in seconds. Must stay below the
            SubagentStop hook's own timeout for the reason above.

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


def handle_subagent_stop(hook_input: dict[str, Any]) -> None:
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

    Every failure is printed to stderr and none is fatal: the SubagentStop critical path must not
    be blocked, so this returns normally however the settle went and :func:`main` exits 0. It never
    no-ops silently — a settle that could not be attempted says which fact was missing, and one
    that failed says the attempt stays open.

    Args:
        hook_input: Parsed hook input from stdin.
    """
    transcript_path_raw = hook_input.get("agent_transcript_path", "")
    transcript_path = Path(transcript_path_raw) if transcript_path_raw else None
    if transcript_path is None:
        print(
            "[hook] SubagentStop: no agent_transcript_path in hook input — cannot correlate the "
            "stopping agent to an attempt, so nothing was settled",
            file=sys.stderr,
        )
        return

    launch = _resolve_launch(transcript_path)
    if launch is not None:
        _call_sam_plan_settle(launch, _resolve_return_text(hook_input, transcript_path))


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


def main() -> None:
    """Main entry point for the hook script."""
    try:
        hook_input = parse_hook_input()
    except (ValueError, json.JSONDecodeError) as e:
        print(f"Failed to parse hook input: {e}", file=sys.stderr)
        sys.exit(2)

    event_name = hook_input.get("hook_event_name", "")

    disabled_hooks = parse_disabled_hooks()
    if should_skip_hook(event_name, disabled_hooks):
        hook_id = _EVENT_TO_HOOK_ID.get(event_name, event_name)
        print(f"[hook] Skipped: {hook_id} (disabled)", file=sys.stderr)
        sys.exit(0)

    if event_name == "SubagentStop":
        handle_subagent_stop(hook_input)
    sys.exit(0)


if __name__ == "__main__":
    main()
