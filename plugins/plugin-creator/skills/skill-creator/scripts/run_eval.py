#!/usr/bin/env python3
"""Run trigger evaluation for a skill description.

Tests whether a skill's description causes Claude to trigger (read the skill)
for a set of queries. Outputs results as JSON.
"""

from __future__ import annotations

import argparse
import json
import os
import select
import subprocess
import sys
import time
import uuid
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from scripts.utils import parse_skill_md

# Sentinel values used by stream-event processing helpers
_TRIGGERED = "triggered"
_NOT_TRIGGERED = "not_triggered"
_CONTINUE = "continue"

# Buffer read size for subprocess stdout
_CHUNK_SIZE = 8192

# Pre-built environment without CLAUDECODE to allow nesting claude -p
# inside a Claude Code session. Built once to avoid copying os.environ per spawn.
_CLEAN_ENV = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}


def find_project_root() -> Path:
    """Find the project root by walking up from cwd looking for .claude/.

    Mimics how Claude Code discovers its project root, so the command file
    we create ends up where claude -p will look for it.

    Returns:
        Path to the project root directory, or cwd if not found.
    """
    current = Path.cwd()
    for parent in [current, *current.parents]:
        if (parent / ".claude").is_dir():
            return parent
    return current


def _write_command_file(commands_dir: Path, clean_name: str, skill_name: str, skill_description: str) -> Path:
    """Create a temporary skill command file in the Claude commands directory.

    Args:
        commands_dir: Directory in which to create the command file.
        clean_name: Unique filename stem (without .md extension).
        skill_name: Human-readable skill name for the command header.
        skill_description: Skill description to embed in the command frontmatter.

    Returns:
        Path to the created command file.
    """
    commands_dir.mkdir(parents=True, exist_ok=True)
    command_file = commands_dir / f"{clean_name}.md"
    indented_desc = "\n  ".join(skill_description.split("\n"))
    content = (
        f"---\ndescription: |\n  {indented_desc}\n---\n\n# {skill_name}\n\nThis skill handles: {skill_description}\n"
    )
    command_file.write_text(content)
    return command_file


def _build_claude_cmd(query: str, model: str | None) -> list[str]:
    """Build the claude -p command list for a query.

    Args:
        query: The user query to evaluate.
        model: Optional model identifier; when None the user-configured default is used.

    Returns:
        List of command tokens ready to pass to subprocess.
    """
    cmd = ["claude", "-p", query, "--output-format", "stream-json", "--verbose", "--include-partial-messages"]
    if model:
        cmd.extend(["--model", model])
    return cmd


def _process_stream_event(
    se: dict[str, Any], clean_name: str, pending_tool_name: str | None, accumulated_json: str
) -> tuple[str, str | None, str]:
    """Process a single stream_event payload and advance detection state.

    Args:
        se: The ``event`` sub-dict from the outer ``stream_event`` JSON object.
        clean_name: The unique command-file name used to detect triggering.
        pending_tool_name: Active tool name awaiting input accumulation, or None.
        accumulated_json: JSON accumulated so far for the pending tool call.

    Returns:
        A 3-tuple ``(decision, pending_tool_name, accumulated_json)`` where
        *decision* is one of the module-level sentinel strings
        ``_TRIGGERED``, ``_NOT_TRIGGERED``, or ``_CONTINUE``.
    """
    se_type = se.get("type", "")
    no_change = (_CONTINUE, pending_tool_name, accumulated_json)

    if se_type == "content_block_start":
        cb = se.get("content_block", {})
        if cb.get("type") != "tool_use":
            return no_change
        tool_name = cb.get("name", "")
        new_pending = tool_name if tool_name in {"Skill", "Read"} else None
        decision = _CONTINUE if new_pending else _NOT_TRIGGERED
        return decision, new_pending, ""

    if se_type == "content_block_delta" and pending_tool_name:
        delta = se.get("delta", {})
        if delta.get("type") == "input_json_delta":
            accumulated_json += delta.get("partial_json", "")
        decision = _TRIGGERED if clean_name in accumulated_json else _CONTINUE
        return decision, pending_tool_name, accumulated_json

    if se_type in {"content_block_stop", "message_stop"}:
        if pending_tool_name:
            decision = _TRIGGERED if clean_name in accumulated_json else _NOT_TRIGGERED
            return decision, None, ""
        if se_type == "message_stop":
            return _NOT_TRIGGERED, None, ""

    return no_change


def _process_assistant_event(event: dict[str, Any], clean_name: str) -> bool:
    """Detect triggering from a full assistant message event (fallback path).

    Args:
        event: The parsed JSON event with ``type == "assistant"``.
        clean_name: The unique command-file name used to detect triggering.

    Returns:
        True when the assistant message contains a matching Skill or Read tool call.
    """
    message = event.get("message", {})
    for content_item in message.get("content", []):
        if content_item.get("type") != "tool_use":
            continue
        tool_name = content_item.get("name", "")
        tool_input = content_item.get("input", {})
        if (tool_name == "Skill" and clean_name in tool_input.get("skill", "")) or (
            tool_name == "Read" and clean_name in tool_input.get("file_path", "")
        ):
            return True
    return False


def _dispatch_event(
    event: dict[str, Any], clean_name: str, pending_tool_name: str | None, accumulated_json: str
) -> tuple[bool | None, str | None, str]:
    """Dispatch a parsed JSON event and return a triggering decision.

    Args:
        event: Parsed JSON event from the claude stream.
        clean_name: Unique command-file name used to detect triggering.
        pending_tool_name: Active tool name awaiting accumulation, or None.
        accumulated_json: JSON accumulated so far for the pending tool call.

    Returns:
        A 3-tuple ``(decision, pending_tool_name, accumulated_json)`` where
        *decision* is ``True`` (triggered), ``False`` (not triggered), or
        ``None`` (no decision yet — continue reading).
    """
    event_type = event.get("type")

    if event_type == "stream_event":
        se = event.get("event", {})
        verdict, pending_tool_name, accumulated_json = _process_stream_event(
            se, clean_name, pending_tool_name, accumulated_json
        )
        if verdict == _TRIGGERED:
            return True, pending_tool_name, accumulated_json
        if verdict == _NOT_TRIGGERED:
            return False, pending_tool_name, accumulated_json
        return None, pending_tool_name, accumulated_json

    if event_type == "assistant":
        return _process_assistant_event(event, clean_name), None, ""

    if event_type == "result":
        return False, None, ""

    return None, pending_tool_name, accumulated_json


def _read_process_output(process: subprocess.Popen[bytes], timeout: int, clean_name: str) -> bool:
    """Read and parse process stdout until triggering is detected or timeout.

    Args:
        process: Running subprocess with a readable stdout pipe.
        timeout: Maximum wall-clock seconds to wait for a decision.
        clean_name: The unique command-file name used to detect triggering.

    Returns:
        True when the skill was triggered, False otherwise.
    """
    buffer = ""
    pending_tool_name: str | None = None
    accumulated_json = ""
    start_time = time.time()

    if process.stdout is None:
        return False

    while time.time() - start_time < timeout:
        if process.poll() is not None:
            if process.stdout is not None:
                remaining = process.stdout.read()
                if remaining:
                    buffer += remaining.decode("utf-8", errors="replace")
            break

        ready, _, _ = select.select([process.stdout], [], [], 1.0)
        if not ready:
            continue

        assert process.stdout is not None
        chunk = os.read(process.stdout.fileno(), _CHUNK_SIZE)
        if not chunk:
            break
        buffer += chunk.decode("utf-8", errors="replace")

        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            line = line.strip()
            if not line:
                continue

            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            decision, pending_tool_name, accumulated_json = _dispatch_event(
                event, clean_name, pending_tool_name, accumulated_json
            )
            if decision is not None:
                return decision

    return False


def run_single_query(
    query: str, skill_name: str, skill_description: str, timeout: int, project_root: str, model: str | None = None
) -> bool:
    """Run a single query and return whether the skill was triggered.

    Creates a command file in .claude/commands/ so it appears in Claude's
    available_skills list, then runs ``claude -p`` with the raw query.
    Uses --include-partial-messages to detect triggering early from
    stream events (content_block_start) rather than waiting for the
    full assistant message, which only arrives after tool execution.

    Args:
        query: The user query to evaluate against the skill.
        skill_name: Human-readable name of the skill being tested.
        skill_description: Skill description to embed in the command file.
        timeout: Maximum seconds to wait for the claude process.
        project_root: Path string to the project root directory.
        model: Optional model identifier override.

    Returns:
        True when the skill was triggered by the query, False otherwise.
    """
    unique_id = uuid.uuid4().hex[:8]
    clean_name = f"{skill_name}-skill-{unique_id}"
    commands_dir = Path(project_root) / ".claude" / "commands"
    command_file = _write_command_file(commands_dir, clean_name, skill_name, skill_description)

    try:
        cmd = _build_claude_cmd(query, model)
        # Remove CLAUDECODE env var to allow nesting claude -p inside a
        # Claude Code session. The guard is for interactive terminal conflicts;
        # programmatic subprocess usage is safe.
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, cwd=project_root, env=_CLEAN_ENV
        )
        try:
            return _read_process_output(process, timeout, clean_name)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
    finally:
        command_file.unlink(missing_ok=True)


def run_eval(
    eval_set: list[dict[str, Any]],
    skill_name: str,
    description: str,
    num_workers: int,
    timeout: int,
    project_root: Path,
    runs_per_query: int = 1,
    trigger_threshold: float = 0.5,
    model: str | None = None,
) -> dict[str, Any]:
    """Run the full eval set and return results.

    Args:
        eval_set: List of evaluation items, each with ``query`` and ``should_trigger`` keys.
        skill_name: Human-readable name of the skill being evaluated.
        description: Skill description to test for triggering behaviour.
        num_workers: Maximum number of parallel worker processes.
        timeout: Per-query timeout in seconds.
        project_root: Path to the project root used for command-file creation.
        runs_per_query: Number of independent runs per query for reliability sampling.
        trigger_threshold: Minimum trigger rate to count as "triggered" for positive cases.
        model: Optional model identifier override for the claude subprocess.

    Returns:
        Dictionary containing ``skill_name``, ``description``, ``results`` list,
        and ``summary`` with ``total``, ``passed``, and ``failed`` counts.
    """
    results: list[dict[str, Any]] = []

    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        future_to_info: dict[Any, tuple[dict[str, Any], int]] = {}
        for item in eval_set:
            for run_idx in range(runs_per_query):
                future = executor.submit(
                    run_single_query, item["query"], skill_name, description, timeout, str(project_root), model
                )
                future_to_info[future] = (item, run_idx)

        query_triggers: dict[str, list[bool]] = {}
        query_items: dict[str, dict[str, Any]] = {}
        for future in as_completed(future_to_info):
            item, _ = future_to_info[future]
            query = item["query"]
            query_items[query] = item
            if query not in query_triggers:
                query_triggers[query] = []
            try:
                query_triggers[query].append(future.result())
            except (RuntimeError, OSError, ValueError) as exc:
                print(f"Warning: query failed: {exc}", file=sys.stderr)
                query_triggers[query].append(False)

    for query, triggers in query_triggers.items():
        item = query_items[query]
        trigger_rate = sum(triggers) / len(triggers)
        should_trigger: bool = item["should_trigger"]
        did_pass = trigger_rate >= trigger_threshold if should_trigger else trigger_rate < trigger_threshold
        results.append({
            "query": query,
            "should_trigger": should_trigger,
            "trigger_rate": trigger_rate,
            "triggers": sum(triggers),
            "runs": len(triggers),
            "pass": did_pass,
        })

    passed = sum(1 for r in results if r["pass"])
    total = len(results)

    return {
        "skill_name": skill_name,
        "description": description,
        "results": results,
        "summary": {"total": total, "passed": passed, "failed": total - passed},
    }


def main() -> None:
    """Entry point: parse CLI arguments, load eval set, run evaluation, emit JSON."""
    parser = argparse.ArgumentParser(description="Run trigger evaluation for a skill description")
    parser.add_argument("--eval-set", required=True, help="Path to eval set JSON file")
    parser.add_argument("--skill-path", required=True, help="Path to skill directory")
    parser.add_argument("--description", default=None, help="Override description to test")
    parser.add_argument("--num-workers", type=int, default=10, help="Number of parallel workers")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout per query in seconds")
    parser.add_argument("--runs-per-query", type=int, default=3, help="Number of runs per query")
    parser.add_argument("--trigger-threshold", type=float, default=0.5, help="Trigger rate threshold")
    parser.add_argument("--model", default=None, help="Model to use for claude -p (default: user's configured model)")
    parser.add_argument("--verbose", action="store_true", help="Print progress to stderr")
    args = parser.parse_args()

    eval_set = json.loads(Path(args.eval_set).read_text(encoding="utf-8"))
    skill_path = Path(args.skill_path)

    if not (skill_path / "SKILL.md").exists():
        print(f"Error: No SKILL.md found at {skill_path}", file=sys.stderr)
        sys.exit(1)

    name, original_description, _content = parse_skill_md(skill_path)
    description = args.description or original_description
    project_root = find_project_root()

    if args.verbose:
        print(f"Evaluating: {description}", file=sys.stderr)

    output = run_eval(
        eval_set=eval_set,
        skill_name=name,
        description=description,
        num_workers=args.num_workers,
        timeout=args.timeout,
        project_root=project_root,
        runs_per_query=args.runs_per_query,
        trigger_threshold=args.trigger_threshold,
        model=args.model,
    )

    if args.verbose:
        summary = output["summary"]
        print(f"Results: {summary['passed']}/{summary['total']} passed", file=sys.stderr)
        for r in output["results"]:
            status = "PASS" if r["pass"] else "FAIL"
            rate_str = f"{r['triggers']}/{r['runs']}"
            print(f"  [{status}] rate={rate_str} expected={r['should_trigger']}: {r['query'][:70]}", file=sys.stderr)

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
