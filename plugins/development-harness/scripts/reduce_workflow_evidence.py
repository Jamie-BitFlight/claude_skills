# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Deterministic, fail-closed reducer for frozen workflow extraction reports.

This producer never invokes models and never publishes workflow layers. Live worker
dispatch, runtime admission, and final publication are separate gates of #3223.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path


class ExtractionError(ValueError):
    """Frozen extraction evidence failed admission."""


RULES = frozenset({"fork", "branch", "reference", "dispatch", "tool", "artifact"})


def canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def _load(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def reduce_frozen(manifest: dict, reports: list[dict], root: Path) -> dict:
    """Validate immutable worker evidence and corroborate exact source-span claims."""
    if len(reports) != 3 or {r.get("worker") for r in reports} != {"w1", "w2", "w3"}:
        raise ExtractionError("exactly three distinct workers are required")
    if set(manifest) != {"version", "sources", "assignments"} or manifest["version"] != 1:
        raise ExtractionError("unsupported manifest")
    assignments = manifest["assignments"]
    if set(assignments) != {"w1", "w2", "w3"}:
        raise ExtractionError("invalid assignments")
    if any(\n        not isinstance(v, list)\n        or any(not isinstance(rule, str) for rule in v)\n        or not set(v) <= RULES\n        or len(v) != len(set(v))\n        for v in assignments.values()\n    ):
        raise ExtractionError("invalid rule slices")
    if any(sum(rule in assignments[w] for w in assignments) != 2 for rule in RULES):
        raise ExtractionError("each rule must have exactly two independent assignments")
    sources = {}
    for item in manifest["sources"]:
        if not isinstance(item, dict) or set(item) != {"path", "sha256"}:
            raise ExtractionError("invalid source descriptor")
        name = item["path"]
        path = Path(name)
        if path.is_absolute() or ".." in path.parts or not path.parts or name in sources or str(path) != name:
            raise ExtractionError("unsafe or duplicate source path")
        full = root / path
        if any(component.is_symlink() for component in (root / Path(*path.parts[:i]) for i in range(1, len(path.parts) + 1))):
            raise ExtractionError("symlinked source path component")
        if not full.is_file() or not full.resolve().is_relative_to(root.resolve()):
            raise ExtractionError("missing or escaped source")
        data = full.read_bytes()
        if hashlib.sha256(data).hexdigest() != item["sha256"]:
            raise ExtractionError("source digest mismatch")
        sources[name] = data
    if not sources:
        raise ExtractionError("empty source scope")
    votes = defaultdict(set)
    for report in reports:
        worker = report["worker"]
        if not isinstance(report, dict) or set(report) != {"worker", "findings"} or not isinstance(report["findings"], list):
            raise ExtractionError("invalid worker report")
        for finding in report["findings"]:
            if not isinstance(finding, dict) or set(finding) != {"rule", "path", "start", "end", "quote", "kind"}:
                raise ExtractionError("invalid finding shape")
            rule, name = finding["rule"], finding["path"]
            if not isinstance(rule, str) or not isinstance(name, str) or rule not in assignments[worker] or name not in sources:
                raise ExtractionError("unassigned rule or source")
            start, end = finding["start"], finding["end"]
            data = sources[name]
            if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(data):
                raise ExtractionError("invalid byte span")
            quote = finding["quote"]
            if not isinstance(quote, str) or data[start:end] != quote.encode("utf-8"):
                raise ExtractionError("source quote mismatch")
            if not isinstance(finding["kind"], str) or not finding["kind"]:
                raise ExtractionError("invalid kind")
            key = (rule, name, start, end, quote, finding["kind"])
            votes[key].add(worker)
    verified, unverified = [], []
    for key, workers in sorted(votes.items()):
        row = dict(zip(("rule", "path", "start", "end", "quote", "kind"), key, strict=True))
        row["workers"] = sorted(workers)
        (verified if len(workers) >= 2 else unverified).append(row)
    return {"version": 1, "verified": verified, "unverified_items": unverified}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--worker", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if len(args.worker) != 3:
        parser.error("exactly three --worker files required")
    try:
        result = reduce_frozen(_load(args.manifest), [_load(p) for p in args.worker], args.root)
    except (ExtractionError, OSError, KeyError, TypeError, ValueError, AttributeError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    # Output is staging only. Never overwrite an existing artifact implicitly.
    try:
        with args.output.open("xb") as stream:
            stream.write(canonical(result))
    except OSError as exc:
        parser.error(f"cannot create staged output: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
