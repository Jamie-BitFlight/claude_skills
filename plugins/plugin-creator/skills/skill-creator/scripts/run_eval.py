#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["ruamel-yaml>=0.19.1"]
#
# [tool.ty.environment]
# root = ["..", "."]
# ///
"""Evaluate description triggering in disposable, per-sample projects.

A positive observation records a matching Skill/Read invocation, not successful
skill execution. A negative requires a successful terminal result and exit.
User-level configuration is still inherited; this is not a clean-room model eval.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import math
import os
import queue
import signal
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

if __package__:
    from .utils import parse_skill_md
else:
    from utils import parse_skill_md

# Reaping a terminated OS process is outside the model observation deadline.
_CLEANUP_SECONDS = 5


class EvaluationError(RuntimeError):
    """The run did not produce an admissible behavioral observation."""


def find_project_root() -> Path:
    """Return the caller's project identity; samples never write into it."""
    current = Path.cwd()
    return next((p for p in (current, *current.parents) if (p / ".claude").is_dir()), current)


def validate_eval_set(eval_set: list[dict[str, Any]]) -> None:
    """Reject missing or ambiguous query identities before dispatch or splitting."""
    if not isinstance(eval_set, list) or not eval_set:
        raise ValueError("eval set must be a nonempty list")
    seen: set[str] = set()
    for item in eval_set:
        if not isinstance(item, dict):
            raise ValueError("each eval must be an object")
        query = item.get("query")
        if not isinstance(query, str) or not query.strip() or type(item.get("should_trigger")) is not bool:
            raise ValueError("each eval requires a nonempty query and boolean should_trigger")
        # Query text is the existing result/partition key. Reject rather than merge
        # duplicate observations or allow conflicting labels across partitions.
        if query in seen:
            raise ValueError(f"duplicate query identity: {query!r}")
        seen.add(query)


def _write_command_file(commands_dir: Path, clean_name: str, skill_name: str, skill_description: str) -> Path:
    """Write the synthetic command only inside this sample's temporary project."""
    commands_dir.mkdir(parents=True, exist_ok=True)
    command_file = commands_dir / f"{clean_name}.md"
    indented_desc = "\n  ".join(skill_description.split("\n"))
    command_file.write_text(
        f"---\ndescription: |\n  {indented_desc}\n---\n\n# {skill_name}\n\nThis skill handles: {skill_description}\n",
        encoding="utf-8",
    )
    return command_file


def _build_claude_cmd(query: str, model: str | None) -> list[str]:
    """Build the existing Claude streaming invocation without shell interpolation."""
    cmd = ["claude", "-p", query, "--output-format", "stream-json", "--verbose", "--include-partial-messages"]
    if model:
        cmd.extend(["--model", model])
    return cmd


def _matches(tool: str, inputs: Any, clean_name: str) -> bool:
    """Match the invocation field, not arbitrary prose containing the identifier."""
    if not isinstance(inputs, dict):
        return False
    if tool == "Skill":
        return inputs.get("skill") == clean_name
    if tool == "Read":
        value = inputs.get("file_path")
        return isinstance(value, str) and Path(value).name == f"{clean_name}.md"
    return False


class _TriggerStream:
    """Track interleaved tool blocks until a match or an actual terminal result."""

    def __init__(self, clean_name: str) -> None:
        self.clean_name = clean_name
        self.pending: dict[int, dict[str, Any]] = {}
        self.triggered = False
        self.complete = False

    def feed(self, event: dict[str, Any]) -> None:
        """Consume one decoded host event; unrelated actions are not negatives."""
        if event.get("type") == "result":
            if event.get("is_error") is not False or event.get("subtype") != "success":
                raise EvaluationError(f"unsuccessful or unsupported terminal result: {event!r}")
            if self.pending:
                raise EvaluationError("terminal result arrived with unfinished tool arguments")
            self.complete = True
        elif event.get("type") == "assistant":
            message = event.get("message", {})
            for item in message.get("content", []):
                if item.get("type") == "tool_use":
                    self.triggered |= _matches(item.get("name", ""), item.get("input"), self.clean_name)
        elif event.get("type") == "stream_event":
            part = event.get("event", {})
            index = part.get("index", 0)
            kind = part.get("type")
            if kind == "content_block_start":
                block = part.get("content_block", {})
                if block.get("type") == "tool_use":
                    self.pending[index] = {"name": block.get("name", ""), "input": block.get("input", {}), "json": ""}
            elif kind == "content_block_delta" and index in self.pending:
                delta = part.get("delta", {})
                if delta.get("type") == "input_json_delta":
                    self.pending[index]["json"] += delta.get("partial_json", "")
            elif kind == "content_block_stop" and index in self.pending:
                block = self.pending.pop(index)
                inputs = json.loads(block["json"]) if block["json"] else block["input"]
                self.triggered |= _matches(block["name"], inputs, self.clean_name)


def _read_process_output(process: subprocess.Popen[bytes], timeout: float, clean_name: str) -> bool:
    """Observe a match, or require a successful completed run for a negative.

    A reader thread supports pipes on both POSIX and Windows. The caller owns
    process-tree termination and stream cleanup, including on timeout.
    """
    if process.stdout is None:
        raise EvaluationError("stdout unavailable")
    events: queue.Queue[bytes | Exception | None] = queue.Queue()
    stdout = process.stdout

    def read_lines() -> None:
        try:
            for line in iter(stdout.readline, b""):
                events.put(line)
        except (OSError, ValueError) as exc:
            events.put(exc)
        finally:
            events.put(None)

    reader = threading.Thread(target=read_lines, daemon=True)
    reader.start()
    deadline = time.monotonic() + timeout
    state = _TriggerStream(clean_name)
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise EvaluationError("TIMEOUT: no terminal observation before deadline")
        try:
            line = events.get(timeout=remaining)
        except queue.Empty as exc:
            raise EvaluationError("TIMEOUT: no terminal observation before deadline") from exc
        if isinstance(line, Exception):
            raise EvaluationError(f"stream read failed: {line}") from line
        if line is None:
            if not state.complete:
                raise EvaluationError("INCOMPLETE: stream ended without successful terminal result")
            try:
                code = process.wait(timeout=max(0, deadline - time.monotonic()))
            except subprocess.TimeoutExpired as exc:
                raise EvaluationError("TIMEOUT: process did not exit after terminal result") from exc
            if code != 0:
                raise EvaluationError(f"process exited {code}")
            return False
        if not line.strip():
            continue
        try:
            event = json.loads(line)
            if not isinstance(event, dict):
                raise ValueError("event is not an object")
            state.feed(event)
        except (ValueError, TypeError, AttributeError) as exc:
            raise EvaluationError(f"invalid stream event: {exc}") from exc
        if state.triggered:
            return True


def _terminate(process: subprocess.Popen[bytes]) -> None:
    """Stop this sample's process group before disposing of its workspace."""
    if os.name == "posix":
        with contextlib.suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGKILL)
    elif process.poll() is None:
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            check=True,
            capture_output=True,
            timeout=_CLEANUP_SECONDS,
        )
    process.wait(timeout=_CLEANUP_SECONDS)


def run_single_query(
    query: str, skill_name: str, skill_description: str, timeout: int, project_root: str, model: str | None = None
) -> bool:
    """Return bool for observed behavior; raise EvaluationError for missing evidence.

    project_root is retained for caller compatibility, not as the execution cwd.
    Each sample has an empty disposable project containing one synthetic command.
    User-level settings/authentication remain inherited and must be qualified in
    generalization claims. No project files or credentials are copied.
    """
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout must be positive and finite")
    if not skill_name or any(not (char.isalnum() or char == "-") for char in skill_name):
        raise ValueError("skill name must contain only letters, numbers and hyphens")
    with tempfile.TemporaryDirectory(prefix="skill-trigger-") as directory:
        workspace = Path(directory)
        clean_name = f"{skill_name}-skill-{uuid.uuid4().hex[:8]}"
        _write_command_file(workspace / ".claude" / "commands", clean_name, skill_name, skill_description)
        env = {key: value for key, value in os.environ.items() if key != "CLAUDECODE"}
        with tempfile.TemporaryFile() as stderr:
            try:
                process = subprocess.Popen(
                    _build_claude_cmd(query, model),
                    stdout=subprocess.PIPE,
                    stderr=stderr,
                    cwd=workspace,
                    env=env,
                    start_new_session=os.name == "posix",
                )
                try:
                    return _read_process_output(process, timeout, clean_name)
                finally:
                    _terminate(process)
                    if process.stdout is not None:
                        process.stdout.close()
            except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
                stderr.seek(0)
                diagnostic = stderr.read().decode("utf-8", errors="replace")
                raise EvaluationError(f"{exc}\n{diagnostic}".rstrip()) from exc


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
    """Keep invalid runs out of behavioral denominators and passing case verdicts."""
    validate_eval_set(eval_set)
    if num_workers < 1 or runs_per_query < 1 or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("workers, repetitions and timeout must be positive")
    if not math.isfinite(trigger_threshold) or not 0 < trigger_threshold <= 1:
        raise ValueError("trigger threshold must be in (0, 1]")
    observations: dict[str, list[dict[str, Any]]] = {item["query"]: [] for item in eval_set}
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = {
            executor.submit(
                run_single_query, item["query"], skill_name, description, timeout, str(project_root), model
            ): (item["query"], run + 1)
            for item in eval_set
            for run in range(runs_per_query)
        }
        for future in as_completed(futures):
            query, run = futures[future]
            try:
                triggered = future.result()
                if type(triggered) is not bool:
                    raise EvaluationError("runner returned no boolean observation")
                record = {"run": run, "status": "TRIGGERED" if triggered else "NOT_TRIGGERED"}
            except (OSError, RuntimeError, ValueError) as exc:
                record = {"run": run, "status": "ERROR", "error": str(exc)}
            observations[query].append(record)
    results = []
    for item in eval_set:
        records = sorted(observations[item["query"]], key=lambda record: record["run"])
        valid = sum(record["status"] != "ERROR" for record in records)
        triggers = sum(record["status"] == "TRIGGERED" for record in records)
        rate = triggers / valid if valid else None
        passed = None
        if valid == runs_per_query and rate is not None:
            passed = rate >= trigger_threshold if item["should_trigger"] else rate < trigger_threshold
        results.append({
            **item,
            "trigger_rate": rate,
            "triggers": triggers,
            "runs": len(records),
            "valid_runs": valid,
            "errors": len(records) - valid,
            "pass": passed,
            "observations": records,
        })
    summary = {
        "total": len(results),
        "passed": sum(r["pass"] is True for r in results),
        "failed": sum(r["pass"] is False for r in results),
        "inconclusive": sum(r["pass"] is None for r in results),
    }
    return {
        "skill_name": skill_name,
        "description": description,
        "results": results,
        "summary": summary,
        "environment": {
            "model": model,
            "caller_project": str(project_root),
            "sample_project": "disposable-per-run",
            "user_host_context": "inherited-not-isolated",
        },
    }


def main() -> None:
    """Emit JSON; exit 2 for incomplete evidence and 1 for behavioral failures."""
    parser = argparse.ArgumentParser(description="Run trigger evaluation for a skill description")
    parser.add_argument("--eval-set", required=True)
    parser.add_argument("--skill-path", required=True)
    parser.add_argument("--description", default=None)
    parser.add_argument("--num-workers", type=int, default=10)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--runs-per-query", type=int, default=3)
    parser.add_argument("--trigger-threshold", type=float, default=0.5)
    parser.add_argument("--model", default=None)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    try:
        eval_set = json.loads(Path(args.eval_set).read_text(encoding="utf-8"))
        name, description, _ = parse_skill_md(Path(args.skill_path))
        output = run_eval(
            eval_set,
            name,
            args.description or description,
            args.num_workers,
            args.timeout,
            find_project_root(),
            args.runs_per_query,
            args.trigger_threshold,
            args.model,
        )
    except (OSError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        raise SystemExit(2) from exc
    print(json.dumps(output, separators=(",", ":")))
    if args.verbose:
        print(json.dumps(output["summary"]), file=sys.stderr)
    raise SystemExit(2 if output["summary"]["inconclusive"] else int(output["summary"]["failed"] > 0))


if __name__ == "__main__":
    main()
