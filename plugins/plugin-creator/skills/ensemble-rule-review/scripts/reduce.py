#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Corroboration-weighting reducer for the ensemble-rule-review pattern.

Reads one fixed-schema findings file per worker, deduplicates findings on a
STABLE key (the worker's assigned group id plus the normalized location — never
the free-form rule slug, which differs between workers), counts how many
distinct workers independently reported each finding (the corroboration weight),
drops PASS verdicts and the low-weight tail, and prints a ranked report.

Fixed finding schema each worker emits (one block per finding, blocks separated
by the block-start field reappearing):

    - group: <stable assigned group/dimension id, identical across workers>
      rule: <free-form descriptive slug — NOT used for corroboration keying>
      location: <path:line>
      verdict: VIOLATION | PASS   # optional; absent means VIOLATION
      severity: critical | high | medium | low
      evidence: "<exact snippet>"

Why key on group, not rule: workers author their own `rule` slugs, so two
workers flagging the same defect emit different slugs. Keying corroboration on
the worker-authored slug would never corroborate. The `group` id is assigned by
the orchestrator (the rule-group number from the rotating split) and is therefore
identical across workers — the only stable corroboration key.

Usage:
    uv run reduce.py REPORT_DIR [--glob 'review-*.md'] [--keep-threshold N]

Worker id is the report filename stem (e.g. review-A.md -> "A").
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

FIELD_RE = re.compile(r"^\s*(?:-\s+)?([A-Za-z_]+):\s*(.*)$")
# Capture the FULL path token (not just the basename) so two different files sharing a
# basename never collapse into the same key and fabricate a false corroboration.
LOCATION_LINE_RE = re.compile(r"(\S+):(\d+)")
SEVERITY_RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1}
BLOCK_START_FIELD = "group"
# A finding is "corroborated" once at least this many distinct workers report it.
CORROBORATION_MIN = 2


@dataclass
class Finding:
    """One parsed finding block from a worker report."""

    group: str
    location: str
    rule: str = ""
    verdict: str = "VIOLATION"
    severity: str = "low"
    evidence: str = ""


@dataclass
class Merged:
    """A deduplicated finding with accumulated corroboration."""

    group: str
    location: str
    agents: set[str] = field(default_factory=set)
    rules: set[str] = field(default_factory=set)
    severity: str = "low"

    @property
    def weight(self) -> int:
        """Corroboration weight: the count of distinct workers that reported this finding."""
        return len(self.agents)


def normalize_location(raw: str) -> str:
    """Normalize a location to `path:line`, preserving the path to avoid false merges.

    Strips an absolute-path prefix down to the repo-relative path and trims whitespace,
    but keeps the directory portion: two files with the same basename in different
    directories (e.g. `src/foo/config.py:10` vs `tests/foo/config.py:10`) must NOT
    collapse to one key, or unrelated findings would fabricate a false corroboration.

    Returns:
        The `path:line` string with any leading `/` stripped, or the stripped input
        when no line number is present.
    """
    match = LOCATION_LINE_RE.search(raw)
    if match:
        path = match.group(1).lstrip("/")
        return f"{path}:{match.group(2)}"
    return raw.strip()


def parse_report(text: str) -> list[Finding]:
    """Parse fixed-schema finding blocks from one worker report.

    Returns:
        The `Finding` objects parsed from the report text.
    """
    findings: list[Finding] = []
    fields: dict[str, str] = {}

    def flush() -> None:
        if BLOCK_START_FIELD in fields and "location" in fields:
            findings.append(
                Finding(
                    group=fields[BLOCK_START_FIELD],
                    location=fields["location"],
                    rule=fields.get("rule", ""),
                    verdict=fields.get("verdict", "VIOLATION").upper(),
                    severity=fields.get("severity", "low").lower(),
                    evidence=fields.get("evidence", ""),
                )
            )

    for line in text.splitlines():
        match = FIELD_RE.match(line)
        if not match:
            continue
        key, value = match.group(1).lower(), match.group(2).strip().strip('"')
        if key == BLOCK_START_FIELD and fields:
            flush()
            fields = {}
        fields[key] = value
    if fields:
        flush()
    return findings


def reduce_findings(reports: dict[str, list[Finding]], keep_threshold: int) -> list[Merged]:
    """Dedup on (group, normalized-location), count corroboration, rank, cut tail.

    Returns:
        The surviving `Merged` findings (weight >= keep_threshold), ranked by
        corroboration weight then severity, highest first.
    """
    merged: dict[tuple[str, str], Merged] = {}
    for agent, findings in reports.items():
        for finding in findings:
            if finding.verdict == "PASS":
                continue
            location = normalize_location(finding.location)
            key = (finding.group, location)
            entry = merged.get(key)
            if entry is None:
                entry = Merged(group=finding.group, location=location)
                merged[key] = entry
            entry.agents.add(agent)
            if finding.rule:
                entry.rules.add(finding.rule)
            if SEVERITY_RANK.get(finding.severity, 1) > SEVERITY_RANK.get(entry.severity, 1):
                entry.severity = finding.severity

    survivors = [m for m in merged.values() if m.weight >= keep_threshold]
    survivors.sort(key=lambda m: (m.weight, SEVERITY_RANK.get(m.severity, 1)), reverse=True)
    return survivors


def load_reports(report_dir: Path, glob: str) -> dict[str, list[Finding]]:
    """Load one report per file; worker id is the filename stem.

    Returns:
        A mapping of worker id to that worker's parsed findings.
    """
    reports: dict[str, list[Finding]] = {}
    for path in sorted(report_dir.glob(glob)):
        agent = path.stem.rsplit("-", 1)[-1] if "-" in path.stem else path.stem
        reports[agent] = parse_report(path.read_text(encoding="utf-8"))
    return reports


def format_report(reports: dict[str, list[Finding]], survivors: list[Merged], keep_threshold: int) -> str:
    """Render the ranked reducer output.

    Returns:
        The formatted multi-line report string.
    """
    lines: list[str] = []
    counts = {agent: len(findings) for agent, findings in reports.items()}
    lines.append(f"per-worker finding counts: {counts}")
    total_raw = sum(counts.values())
    kept = [m for m in survivors if m.weight >= CORROBORATION_MIN]
    tail = [m for m in survivors if m.weight < CORROBORATION_MIN]
    lines.extend((
        f"raw findings: {total_raw}   distinct after dedup: {len(survivors)}",
        f"corroborated (weight>=2): {len(kept)}   lone (weight=1): {len(tail)}",
        f"keep_threshold: {keep_threshold}",
        "",
        "=== RANKED (corroboration weight, then severity) ===",
    ))
    for m in survivors:
        tag = "KEEP" if m.weight >= CORROBORATION_MIN else "tail"
        agents = "".join(sorted(m.agents))
        rules = "|".join(sorted(m.rules)) or "?"
        lines.append(
            f"[{tag} w={m.weight}] group={m.group} {m.location}  sev={m.severity}  agents={agents}  rule={rules}"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """Run the reducer CLI.

    Returns:
        Process exit code: 0 on success, 2 on input error.
    """
    parser = argparse.ArgumentParser(description="Corroboration-weighting reducer for ensemble-rule-review.")
    parser.add_argument("report_dir", type=Path, help="Directory containing one report file per worker.")
    parser.add_argument("--glob", default="*.md", help="Glob for worker report files (default: *.md).")
    parser.add_argument(
        "--keep-threshold",
        type=int,
        default=1,
        help="Minimum corroboration weight to retain (default 1 = keep all, rank only).",
    )
    args = parser.parse_args(argv)

    if not args.report_dir.is_dir():
        print(f"error: not a directory: {args.report_dir}", file=sys.stderr)
        return 2

    reports = load_reports(args.report_dir, args.glob)
    if not reports:
        print(f"error: no reports matched {args.glob} in {args.report_dir}", file=sys.stderr)
        return 2

    survivors = reduce_findings(reports, args.keep_threshold)
    print(format_report(reports, survivors, args.keep_threshold))
    return 0


if __name__ == "__main__":
    sys.exit(main())
