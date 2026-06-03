r"""Live-arm dispatch — subprocess calls to claude -p headless mode.

This module is the ONLY part of the runner that costs tokens.
Do NOT call run_arm during unit tests.

Verified claude -p interface (from claude --help, 2026-06-03):
  claude -p "<prompt>"                       # print mode, text output
  claude -p "<prompt>" --output-format json  # structured JSON result
  claude -p "<prompt>" --model <alias>       # e.g. sonnet, haiku
  claude -p "<prompt>" --bare                # skip hooks/plugins/CLAUDE.md
  claude -p "<prompt>" --no-session-persistence

JSON result fields (verified by live test):
  result          — the model's text response
  duration_ms     — wall-clock time in milliseconds
  total_cost_usd  — reported token cost
  usage.input_tokens, usage.output_tokens

Design — symmetric arms
-----------------------
Both arms run the IDENTICAL call:

    claude -p "<preamble + PROMPT.md>" --output-format json \\
           --no-session-persistence

with cwd set to the arm directory.  The divergence (single-agent vs ensemble)
lives entirely in each arm's .claude/skills/review-against-solid-principles/
SKILL.md — not in this Python module.

The preamble unconditionally instructs the agent to read and follow the skill
file.  This guarantees the skill governs the review regardless of whether
CLAUDE.md auto-loading or skill auto-load applies in headless mode.

After the arm completes, this module:
  1. Reads ./findings/findings.md from the arm directory.
  2. Writes ./findings/run-meta.json with token counts and timing so the
     score command can compute deterministic costs post-hoc.

run-meta.json schema
--------------------
{
  "input_tokens": <int>,
  "output_tokens": <int>,
  "duration_ms": <float>,
  "total_cost_usd_reported": <float>
}

total_cost_usd_reported is stored for reconciliation only — the authoritative
cost figure is computed by runner/cost.py from the manifest price table.
"""

from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Locate the experiment root and shared PROMPT.md
# ---------------------------------------------------------------------------
_HERE = Path(__file__).parent
_EXPERIMENT_ROOT = _HERE.parent
_PROMPT_PATH = _EXPERIMENT_ROOT / "PROMPT.md"

# Preamble prepended unconditionally to the shared prompt so the agent reads
# the arm's SKILL.md before starting the review.  The path is relative to the
# arm's working directory (cwd when claude -p is invoked).
_SKILL_PREAMBLE = (
    "Read and follow .claude/skills/review-against-solid-principles/SKILL.md "
    "to understand how to conduct this review, then:\n\n"
)


@dataclass
class ArmRunResult:
    """Raw output from one arm run.

    Attributes:
        findings_paths: Output file paths written by the arm (normally one).
        duration_ms: Total wall-clock time for the arm in milliseconds.
        reported_cost_usd: Token cost as reported by claude -p (non-deterministic;
            stored for display in the run summary only).  The authoritative cost
            figure is computed deterministically by scorer from the manifest price
            table using token counts in run-meta.json.
        errors: Subprocess or parse errors (arm failed; result may be partial).
    """

    findings_paths: list[Path] = field(default_factory=list)
    duration_ms: float = 0.0
    reported_cost_usd: float = 0.0
    errors: list[str] = field(default_factory=list)


def _write_run_meta(findings_dir: Path, payload: dict, reported_ms: float, cost_usd: float) -> None:
    """Write findings/run-meta.json with token counts and timing for post-hoc cost computation.

    Args:
        findings_dir: Directory to write run-meta.json into (created if absent).
        payload: Parsed JSON payload from claude -p.
        reported_ms: Wall-clock duration in milliseconds.
        cost_usd: Reported cost from claude -p (stored for reconciliation only).
    """
    usage = payload.get("usage") or {}
    meta = {
        "input_tokens": int(usage.get("input_tokens", 0)),
        "output_tokens": int(usage.get("output_tokens", 0)),
        "duration_ms": reported_ms,
        "total_cost_usd_reported": cost_usd,
    }
    findings_dir.mkdir(parents=True, exist_ok=True)
    (findings_dir / "run-meta.json").write_text(json.dumps(meta), encoding="utf-8")


def run_arm(arm_dir: Path) -> ArmRunResult:
    """Dispatch one arm by running the shared prompt with cwd set to arm_dir.

    Both arms use the identical call.  The SKILL.md in each arm's .claude/
    directory controls what the agent does with the prompt (single-pass vs
    ensemble fan-out, model selection, output location).

    The runner reads PROMPT.md at call time so changes to the prompt are
    picked up without restarting the runner.

    Args:
        arm_dir: Root directory for this arm.  Must contain
            .claude/skills/review-against-solid-principles/SKILL.md.
            The arm writes findings to ./findings/findings.md relative to
            this directory.

    Returns:
        ArmRunResult with the findings path (when written) and cost/latency.

    Raises:
        FileNotFoundError: When PROMPT.md does not exist.
        subprocess.CalledProcessError: When claude -p exits non-zero.
        json.JSONDecodeError: When the JSON response cannot be parsed.
    """
    prompt_text = _PROMPT_PATH.read_text(encoding="utf-8")
    full_prompt = _SKILL_PREAMBLE + prompt_text

    cmd = ["claude", "-p", full_prompt, "--output-format", "json", "--no-session-persistence"]

    t0 = time.monotonic()
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True, cwd=str(arm_dir))
    elapsed_ms = (time.monotonic() - t0) * 1000

    payload = json.loads(proc.stdout)
    reported_ms: float = float(payload.get("duration_ms", elapsed_ms))
    cost_usd: float = float(payload.get("total_cost_usd", 0.0))

    findings_dir = arm_dir / "findings"
    _write_run_meta(findings_dir, payload, reported_ms, cost_usd)

    findings_path = findings_dir / "findings.md"
    result = ArmRunResult(duration_ms=reported_ms, reported_cost_usd=cost_usd)
    if findings_path.is_file():
        result.findings_paths.append(findings_path)
    else:
        result.errors.append(
            f"findings.md not found at {findings_path} after arm completed. "
            "Arm may have written output elsewhere or failed silently."
        )
    return result
