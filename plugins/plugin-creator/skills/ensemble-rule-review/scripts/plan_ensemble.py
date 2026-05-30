#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Planner for the ensemble-rule-review pattern — the deterministic map-side bookend.

Given a ruleset split into stable groups, this computes the balanced rotating-overlap
worker assignment (cyclic block design: N agents, each a window of `w` consecutive
groups), assigns every worker an absolute output path, and verifies uniform redundancy
BEFORE any agent is spawned. It removes the manual bookkeeping that produces the
recurring bugs — wrong output paths, drifted group ids, ad-hoc (non-uniform) overlap,
and per-worker (instead of per-rule) group tagging.

Pair with reduce.py (the reduce-side bookend): plan -> spawn focused-reviewer x N -> reduce.
Both ends are deterministic code; only the per-worker rule-matching is left to the LLM.

Input: a JSON file mapping stable group id -> list of rule strings. Example:

    {
      "1": ["no bare except", "no swallowed exceptions"],
      "2": ["no Any outside boundaries", "no legacy typing imports"],
      "3": ["functions under 50 lines", "no deep nesting"]
    }

Usage:
    plan_ensemble.py RULES_JSON --report-dir /abs/reports [--window 2] [--target PATH] [--json]

Output (human table by default, or a machine plan with --json): one row per worker giving
its worker id, the groups it covers, the absolute OUTFILE to write, and the rules to apply;
plus the recommended keep-threshold (= window, for a precision gate) and a redundancy check.
"""

from __future__ import annotations

import argparse
import json
import string
import sys
from dataclasses import dataclass, field
from pathlib import Path

MIN_GROUPS = 3
WORKER_IDS = string.ascii_uppercase


@dataclass
class WorkerPlan:
    """One worker's assignment in the rotating-overlap ensemble."""

    worker_id: str
    groups: list[str]
    outfile: str
    rules_by_group: dict[str, list[str]] = field(default_factory=dict)


def parse_groups(raw: object) -> dict[str, list[str]]:
    """Validate untyped JSON at the boundary into a typed group->rules mapping.

    Returns:
        A `dict[str, list[str]]` of group id to rule strings.

    Raises:
        TypeError: when the structure is not an object of id -> list[str].
    """
    if not isinstance(raw, dict):
        msg = "rules JSON must be an object mapping group id -> list of rule strings"
        raise TypeError(msg)
    parsed: dict[str, list[str]] = {}
    for key, value in raw.items():
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            msg = f"group {key!r} must map to a list of rule strings"
            raise TypeError(msg)
        parsed[str(key)] = [str(item) for item in value]
    return parsed


def rotate_assignment(group_ids: list[str], window: int) -> list[list[str]]:
    """Compute the cyclic rotating-window group assignment, one window per worker.

    Worker i covers `window` consecutive groups starting at index i (wrapping). With
    N groups and N workers this gives uniform redundancy r = window: every group is
    covered by exactly `window` workers.

    Returns:
        A list of length len(group_ids); element i is worker i's list of group ids.
    """
    n = len(group_ids)
    return [[group_ids[(i + offset) % n] for offset in range(window)] for i in range(n)]


def redundancy(assignment: list[list[str]], group_ids: list[str]) -> dict[str, int]:
    """Count how many workers cover each group.

    Returns:
        A mapping of group id to the number of workers that hold it.
    """
    counts = dict.fromkeys(group_ids, 0)
    for groups in assignment:
        for g in groups:
            counts[g] += 1
    return counts


def build_plan(groups: dict[str, list[str]], window: int, report_dir: str) -> list[WorkerPlan]:
    """Build the per-worker plan from the grouped ruleset.

    Returns:
        One WorkerPlan per worker, each with its groups, absolute outfile, and rules.
    """
    group_ids = list(groups)
    assignment = rotate_assignment(group_ids, window)
    base = Path(report_dir)
    plans: list[WorkerPlan] = []
    for i, covered in enumerate(assignment):
        wid = WORKER_IDS[i] if i < len(WORKER_IDS) else f"W{i}"
        outfile = str(base / f"worker-{wid}.md")
        plans.append(
            WorkerPlan(worker_id=wid, groups=covered, outfile=outfile, rules_by_group={g: groups[g] for g in covered})
        )
    return plans


def validate_inputs(groups: dict[str, list[str]], window: int, report_dir: str) -> list[str]:
    """Check the planner inputs against the pattern's invariants.

    Returns:
        A list of human-readable error strings; empty when the inputs are valid.
    """
    errors: list[str] = []
    if len(groups) < MIN_GROUPS:
        errors.append(f"need at least {MIN_GROUPS} groups for overlap denoising, got {len(groups)}")
    window_ok = groups and 2 <= window < len(groups)  # noqa: PLR2004
    if not window_ok:
        errors.append(f"window must satisfy 2 <= window < n_groups ({len(groups)}); got {window}")
    if any(not rules for rules in groups.values()):
        empty = [g for g, rules in groups.items() if not rules]
        errors.append(f"groups have no rules: {empty}")
    if not Path(report_dir).is_absolute():
        errors.append(f"--report-dir must be an absolute path (workers resolve varying cwd): {report_dir}")
    return errors


def format_plan(plans: list[WorkerPlan], counts: dict[str, int], window: int) -> str:
    """Render the human-readable plan and the redundancy / threshold guidance.

    Returns:
        The formatted multi-line plan string.
    """
    lines = [
        f"ensemble plan: {len(plans)} workers, window w={window}, uniform redundancy r={window}",
        f"recommended --keep-threshold: {window} (precision gate) | 1 (recall, rank only)",
        "",
        "redundancy per group (each must equal w):",
    ]
    lines.extend(f"  group {g}: {c} worker(s)" for g, c in counts.items())
    uniform = set(counts.values()) == {window}
    lines.extend((
        f"  uniform: {'YES' if uniform else 'NO — assignment is unbalanced'}",
        "",
        "=== WORKER ASSIGNMENTS ===",
    ))
    for p in plans:
        lines.append(f"worker {p.worker_id}  groups={p.groups}  OUTFILE={p.outfile}")
        for g, rules in p.rules_by_group.items():
            lines.extend(f"    [group {g}] {rule}" for rule in rules)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """Run the planner CLI.

    Returns:
        Process exit code: 0 on success, 2 on input error.
    """
    parser = argparse.ArgumentParser(description="Planner for the ensemble-rule-review rotating-overlap fan-out.")
    parser.add_argument("rules_json", type=Path, help="JSON file mapping group id -> list of rule strings.")
    parser.add_argument("--report-dir", required=True, help="ABSOLUTE directory where workers write reports.")
    parser.add_argument("--window", type=int, default=2, help="Groups per worker (overlap degree, default 2).")
    parser.add_argument("--json", action="store_true", help="Emit the machine-readable plan as JSON.")
    args = parser.parse_args(argv)

    if not args.rules_json.is_file():
        print(f"error: not a file: {args.rules_json}", file=sys.stderr)
        return 2
    try:
        raw = json.loads(args.rules_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"error: invalid JSON in {args.rules_json}: {exc}", file=sys.stderr)
        return 2
    try:
        groups = parse_groups(raw)
    except TypeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    errors = validate_inputs(groups, args.window, args.report_dir)
    if errors:
        for e in errors:
            print(f"error: {e}", file=sys.stderr)
        return 2

    plans = build_plan(groups, args.window, args.report_dir)
    counts = redundancy([p.groups for p in plans], list(groups))
    if args.json:
        print(
            json.dumps(
                {
                    "window": args.window,
                    "keep_threshold_precision": args.window,
                    "redundancy": counts,
                    "workers": [
                        {"id": p.worker_id, "groups": p.groups, "outfile": p.outfile, "rules": p.rules_by_group}
                        for p in plans
                    ],
                },
                indent=2,
            )
        )
    else:
        print(format_plan(plans, counts, args.window))
    return 0


if __name__ == "__main__":
    sys.exit(main())
