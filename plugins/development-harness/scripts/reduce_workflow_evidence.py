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
WORKERS = frozenset({"w1", "w2", "w3"})
REQUIRED_WORKER_COUNT = len(WORKERS)
REQUIRED_CORROBORATION_COUNT = 2
FORMAT_VERSION = 1
MANIFEST_KEYS = frozenset({"version", "sources", "assignments"})
REPORT_KEYS = frozenset({"worker", "findings"})
FINDING_KEYS = frozenset({"rule", "path", "start", "end", "quote", "kind"})
SOURCE_KEYS = frozenset({"path", "sha256"})
FINDING_FIELD_NAMES = ("rule", "path", "start", "end", "quote", "kind")


def canonical(value: object) -> bytes:
    """Serialize a JSON-compatible value deterministically as UTF-8 bytes.

    Returns:
        Canonical JSON followed by a newline.
    """
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + chr(10)).encode("utf-8")


def _load(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_mapping(path: Path, label: str) -> dict[str, object]:
    value = _load(path)
    if not isinstance(value, dict):
        raise ExtractionError(f"{label} must decode to an object")
    return value


def _admit_assignments(manifest: dict[str, object]) -> dict[str, list[str]]:
    assignments_value = manifest["assignments"]
    if not isinstance(assignments_value, dict) or set(assignments_value) != WORKERS:
        raise ExtractionError("invalid assignments")
    assignments: dict[str, list[str]] = {}
    for worker in WORKERS:
        rules = assignments_value[worker]
        if not isinstance(rules, list) or any(not isinstance(rule, str) for rule in rules):
            raise ExtractionError("invalid rule slices")
        if not set(rules) <= RULES or len(rules) != len(set(rules)):
            raise ExtractionError("invalid rule slices")
        assignments[worker] = rules
    if any(sum(rule in assignments[worker] for worker in WORKERS) != REQUIRED_CORROBORATION_COUNT for rule in RULES):
        raise ExtractionError("each rule must have exactly two independent assignments")
    return assignments


def _admit_sources(manifest: dict[str, object], root: Path) -> dict[str, bytes]:
    source_items = manifest["sources"]
    if not isinstance(source_items, list):
        raise ExtractionError("invalid source list")
    sources: dict[str, bytes] = {}
    for item in source_items:
        if not isinstance(item, dict) or set(item) != SOURCE_KEYS:
            raise ExtractionError("invalid source descriptor")
        name, digest = item["path"], item["sha256"]
        if not isinstance(name, str) or not isinstance(digest, str):
            raise ExtractionError("invalid source descriptor")
        path = Path(name)
        if path.is_absolute() or ".." in path.parts or not path.parts or name in sources or str(path) != name:
            raise ExtractionError("unsafe or duplicate source path")
        full = root / path
        if any(
            component.is_symlink()
            for component in (root / Path(*path.parts[:index]) for index in range(1, len(path.parts) + 1))
        ):
            raise ExtractionError("symlinked source path component")
        if not full.is_file() or not full.resolve().is_relative_to(root.resolve()):
            raise ExtractionError("missing or escaped source")
        data = full.read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            raise ExtractionError("source digest mismatch")
        sources[name] = data
    if not sources:
        raise ExtractionError("empty source scope")
    return sources


def _admit_manifest(manifest: dict[str, object], root: Path) -> tuple[dict[str, list[str]], dict[str, bytes]]:
    if set(manifest) != MANIFEST_KEYS or manifest["version"] != FORMAT_VERSION:
        raise ExtractionError("unsupported manifest")
    return _admit_assignments(manifest), _admit_sources(manifest, root)


def _admit_reports(reports: list[dict[str, object]]) -> list[tuple[str, list[object]]]:
    if len(reports) != REQUIRED_WORKER_COUNT:
        raise ExtractionError("exactly three distinct workers are required")
    admitted: list[tuple[str, list[object]]] = []
    for report in reports:
        if set(report) != REPORT_KEYS:
            raise ExtractionError("invalid worker report")
        worker, findings = report["worker"], report["findings"]
        if not isinstance(worker, str) or not isinstance(findings, list):
            raise ExtractionError("invalid worker report")
        admitted.append((worker, findings))
    if {worker for worker, _ in admitted} != WORKERS:
        raise ExtractionError("exactly three distinct workers are required")
    return admitted


def _admit_finding(
    finding: object, worker: str, assignments: dict[str, list[str]], sources: dict[str, bytes]
) -> tuple[str, str, int, int, str, str]:
    if not isinstance(finding, dict) or set(finding) != FINDING_KEYS:
        raise ExtractionError("invalid finding shape")
    rule, name = finding["rule"], finding["path"]
    if not isinstance(rule, str) or not isinstance(name, str) or rule not in assignments[worker] or name not in sources:
        raise ExtractionError("unassigned rule or source")
    start, end = finding["start"], finding["end"]
    data = sources[name]
    if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(data):
        raise ExtractionError("invalid byte span")
    quote, kind = finding["quote"], finding["kind"]
    if not isinstance(quote, str) or data[start:end] != quote.encode("utf-8"):
        raise ExtractionError("source quote mismatch")
    if not isinstance(kind, str) or not kind:
        raise ExtractionError("invalid kind")
    return rule, name, start, end, quote, kind


def _reduce_votes(
    reports: list[tuple[str, list[object]]], assignments: dict[str, list[str]], sources: dict[str, bytes]
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    votes: defaultdict[tuple[str, str, int, int, str, str], set[str]] = defaultdict(set)
    for worker, findings in reports:
        for finding in findings:
            votes[_admit_finding(finding, worker, assignments, sources)].add(worker)
    verified: list[dict[str, object]] = []
    unverified: list[dict[str, object]] = []
    for key, workers in sorted(votes.items()):
        row: dict[str, object] = dict(zip(FINDING_FIELD_NAMES, key, strict=True))
        row["workers"] = sorted(workers)
        (verified if len(workers) >= REQUIRED_CORROBORATION_COUNT else unverified).append(row)
    return verified, unverified


def reduce_frozen(manifest: dict[str, object], reports: list[dict[str, object]], root: Path) -> dict[str, object]:
    """Validate frozen evidence and corroborate exact source-backed finding tuples.

    Returns:
        Canonical reducer data containing corroborated and uncorroborated findings.
    """
    assignments, sources = _admit_manifest(manifest, root)
    verified, unverified = _reduce_votes(_admit_reports(reports), assignments, sources)
    return {"version": FORMAT_VERSION, "verified": verified, "unverified_items": unverified}


def main() -> int:
    """Run the reducer command-line interface.

    Returns:
        Zero after creating a new staging file containing the reducer result.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--worker", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if len(args.worker) != REQUIRED_WORKER_COUNT:
        parser.error("exactly three --worker files required")
    try:
        result = reduce_frozen(
            _load_mapping(args.manifest, "manifest"),
            [_load_mapping(path, "worker report") for path in args.worker],
            args.root,
        )
        result_bytes = canonical(result)
    except (ExtractionError, OSError, KeyError, TypeError, ValueError, AttributeError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    # Output is staging only. Never overwrite an existing artifact implicitly.
    try:
        with args.output.open("xb") as stream:
            stream.write(result_bytes)
    except OSError as exc:
        parser.error(f"cannot create staged output: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
