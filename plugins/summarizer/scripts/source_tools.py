#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pydantic>=2.12.5"]
# ///
"""Plan source chunks, reconcile recorded coverage, and profile complete CSV/TSV data.

Commands emit compact JSON. Chunk offsets are Unicode character offsets into an exact UTF-8
snapshot, not token counts. Completion receipts are evidence references, not a semantic oracle.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import Field, field_validator

from summary_record import Digest, Identity, RecordModel, Text, unique_object

Positive = Annotated[int, Field(ge=1)]
Offset = Annotated[int, Field(ge=0)]


class Versioned(RecordModel):
    """Require an explicit integer version on persistent source-work records."""

    schema_version: Literal[1]

    @field_validator("schema_version", mode="before")
    @classmethod
    def integer_version(cls, value: object) -> object:
        """Reject booleans masquerading as version one.

        Returns:
            The unchanged integer version for subsequent literal validation.
        """
        if type(value) is not int:
            raise ValueError("Schema version must be an integer.")
        return value


class Chunk(RecordModel):
    """One non-overlapping interval in the decoded source snapshot."""

    id: Text
    start: Offset
    end: Positive
    sha256: Digest


class Plan(Versioned):
    """A complete mechanically generated partition with caller-selected size."""

    source_path: Identity
    source_sha256: Digest
    max_chars: Positive
    char_count: Offset
    chunks: list[Chunk]


class Receipt(RecordModel):
    """A worker outcome for an exact planned chunk."""

    chunk_id: Text
    chunk_sha256: Digest
    state: Literal["inspected", "failed"]
    evidence_ref: Text | None = None
    reason: Text | None = None


class Receipts(Versioned):
    """Recorded outcomes tied to one source revision."""

    source_sha256: Digest
    outcomes: list[Receipt]


def snapshot(source: Path) -> tuple[bytes, str]:
    """Read one strict UTF-8 snapshot without newline or replacement transformations.

    Returns:
        Original bytes and their strict UTF-8 decoding.
    """
    raw = source.read_bytes()
    return raw, raw.decode("utf-8")


def build_plan(source: Path, max_chars: int) -> Plan:
    """Return a complete partition, preferring heading or newline boundaries.

    Returns:
        A partition of the complete source snapshot.
    """
    if isinstance(max_chars, bool) or max_chars < 1:
        raise ValueError("max_chars must be positive.")
    raw, text = snapshot(source)
    chunks: list[Chunk] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        if end < len(text):
            window = text[start:end]
            headings = list(re.finditer(r"(?m)^#{1,6} ", window))
            boundary = headings[-1].start() if headings else 0
            if boundary == 0:
                boundary = window.rfind("\n") + 1
            if boundary > 0:
                end = start + boundary
        value = text[start:end]
        chunks.append(
            Chunk(id=f"c{start}-{end}", start=start, end=end, sha256=hashlib.sha256(value.encode()).hexdigest())
        )
        start = end
    return Plan(
        schema_version=1,
        source_path=str(source),
        source_sha256=hashlib.sha256(raw).hexdigest(),
        max_chars=max_chars,
        char_count=len(text),
        chunks=chunks,
    )


def read_plan(source: Path, path: Path) -> Plan:
    """Reject edited boundaries, lost chunks and stale or substituted source bytes.

    Returns:
        The plan matching the current complete source partition.
    """
    plan = Plan.model_validate(json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object))
    expected = build_plan(source, plan.max_chars)
    if plan != expected:
        raise ValueError("Plan does not match the complete current source partition.")
    return plan


def read_chunk(source: Path, plan_path: Path, chunk_id: str) -> dict[str, Any]:
    """Return only the explicitly requested chunk and its stable source coordinates.

    Returns:
        Chunk identity, offsets and unmodified decoded content.
    """
    plan = read_plan(source, plan_path)
    chunk = next((item for item in plan.chunks if item.id == chunk_id), None)
    if chunk is None:
        raise ValueError("Unknown chunk ID.")
    raw, text = snapshot(source)
    if hashlib.sha256(raw).hexdigest() != plan.source_sha256:
        raise ValueError("Source changed during chunk acquisition.")
    return {"source_sha256": plan.source_sha256, **chunk.model_dump(), "text": text[chunk.start : chunk.end]}


def reconcile(plan: Plan, receipts: Receipts) -> dict[str, Any]:
    """Report missing and failed receipts without claiming the content was understood.

    Returns:
        Recorded coverage state with every missing or failed chunk.
    """
    if receipts.source_sha256 != plan.source_sha256:
        raise ValueError("Receipts belong to a different source revision.")
    expected = {chunk.id: chunk for chunk in plan.chunks}
    recorded: dict[str, Receipt] = {}
    for receipt in receipts.outcomes:
        if receipt.chunk_id not in expected or receipt.chunk_id in recorded:
            raise ValueError("Receipt IDs must be unique planned chunks.")
        if receipt.chunk_sha256 != expected[receipt.chunk_id].sha256:
            raise ValueError("Receipt chunk content identity does not match.")
        if receipt.state == "inspected" and (not receipt.evidence_ref or receipt.reason):
            raise ValueError("Inspected receipts require an evidence reference and no failure reason.")
        if receipt.state == "failed" and not receipt.reason:
            raise ValueError("Failed receipts require a reason.")
        recorded[receipt.chunk_id] = receipt
    missing = [chunk_id for chunk_id in expected if chunk_id not in recorded]
    failed = [item.model_dump() for item in receipts.outcomes if item.state == "failed"]
    return {
        "status": "RECORDED_PARTIAL" if missing or failed else "RECORDED_COMPLETE",
        "source_sha256": plan.source_sha256,
        "expected_chunks": len(expected),
        "inspected_chunks": sum(item.state == "inspected" for item in receipts.outcomes),
        "missing": missing,
        "failed": failed,
        "semantic_support": "UNVERIFIED",
    }


def classify_value(value: str) -> tuple[str, Decimal | None]:
    """Classify observed scalar syntax, not an inferred schema or business meaning.

    Returns:
        Observed scalar kind and a finite decimal when numeric.
    """
    if value == "":
        return "empty", None
    if value.lower() in {"true", "false"}:
        return "boolean", None
    try:
        number = Decimal(value)
    except InvalidOperation:
        return "text", None
    if not number.is_finite():
        return "text", None
    kind = "integer" if re.fullmatch(r"[+-]?\d+", value) else "decimal"
    return kind, number


def profile_column(values: list[str]) -> dict[str, Any]:
    """Return exact empty counts, observed kinds and ranges over numeric cells only.

    Returns:
        Exact counts and numeric-subset ranges for the supplied values.
    """
    kinds: Counter[str] = Counter()
    numeric: list[Decimal] = []
    for value in values:
        kind, number = classify_value(value)
        kinds[kind] += 1
        if number is not None:
            numeric.append(number)
    return {
        "empty_count": kinds["empty"],
        "observed_types": dict(sorted(kinds.items())),
        "numeric_count": len(numeric),
        "numeric_min": str(min(numeric)) if numeric else None,
        "numeric_max": str(max(numeric)) if numeric else None,
    }


def profile_delimited(source: Path, delimiter: str | None = None) -> dict[str, Any]:
    """Profile every parsed CSV/TSV record; never equate physical lines with records.

    Returns:
        Full parsed-record statistics with source snapshot identity.
    """
    raw = source.read_bytes()
    text = raw.decode("utf-8-sig")
    separator = delimiter if delimiter is not None else "\t" if source.suffix.lower() == ".tsv" else ","
    if len(separator) != 1:
        raise ValueError("Delimiter must be one character.")
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=separator, strict=True)
    header = next(reader, None)
    if not header or any(not item for item in header) or len(set(header)) != len(header):
        raise ValueError("A nonempty unique header is required.")
    columns: list[list[str]] = [[] for _ in header]
    count = 0
    for row in reader:
        if len(row) != len(header):
            raise ValueError(f"Record {count + 1} has a different field count from the header.")
        for column, value in zip(columns, row, strict=True):
            column.append(value)
        count += 1
    return {
        "status": "PROFILED",
        "source_path": str(source),
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "row_count": count,
        "physical_lines": len(text.splitlines()),
        "coverage": "complete",
        "columns": [{"name": name, **profile_column(values)} for name, values in zip(header, columns, strict=True)],
        "empty_definition": "zero-length parsed cells; literal null/NA and whitespace are not assumed missing",
    }


def main() -> int:
    """Expose read-only mechanical operations with explicit inputs and JSON results.

    Returns:
        Zero for success, one for partial receipts, or two for invalid/unavailable inputs.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    plan_command = commands.add_parser("plan")
    plan_command.add_argument("source", type=Path)
    plan_command.add_argument("--max-chars", type=int, required=True)
    chunk_command = commands.add_parser("chunk")
    chunk_command.add_argument("source", type=Path)
    chunk_command.add_argument("--plan", type=Path, required=True)
    chunk_command.add_argument("--id", required=True)
    coverage_command = commands.add_parser("coverage")
    coverage_command.add_argument("source", type=Path)
    coverage_command.add_argument("--plan", type=Path, required=True)
    coverage_command.add_argument("--receipts", type=Path, required=True)
    profile_command = commands.add_parser("profile")
    profile_command.add_argument("source", type=Path)
    profile_command.add_argument("--delimiter")
    args = parser.parse_args()
    try:
        if args.command == "plan":
            result = build_plan(args.source, args.max_chars).model_dump()
        elif args.command == "chunk":
            result = read_chunk(args.source, args.plan, args.id)
        elif args.command == "coverage":
            plan = read_plan(args.source, args.plan)
            receipts = Receipts.model_validate(
                json.loads(args.receipts.read_text(encoding="utf-8"), object_pairs_hook=unique_object)
            )
            result = reconcile(plan, receipts)
        else:
            result = profile_delimited(args.source, args.delimiter)
    except (OSError, UnicodeError) as exc:
        print(json.dumps({"status": "UNVERIFIED", "error": str(exc)}, separators=(",", ":")))
        return 2
    except (ValueError, csv.Error) as exc:
        print(json.dumps({"status": "INVALID", "error": str(exc)}, separators=(",", ":")))
        return 2
    print(json.dumps(result, separators=(",", ":")))
    return 1 if result.get("status") == "RECORDED_PARTIAL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
