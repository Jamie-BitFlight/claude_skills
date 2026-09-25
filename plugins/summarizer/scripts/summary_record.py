#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pydantic>=2.12.5"]
# ///
"""Validate evidence handoffs against caller identity and final output bytes.

Schema/identity consistency is not proof of factual support or actual source access.
The model is the schema authority; `schema` emits its JSON Schema projection.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Identity = Annotated[str, StringConstraints(min_length=1)]
Digest = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
Format = Literal["structured", "bullets", "tldr", "json", "table", "outline"]


class RecordModel(BaseModel):
    """Reject unknown fields and coercions at a versioned boundary."""

    model_config = ConfigDict(extra="forbid", strict=True, hide_input_in_errors=True)


class Coverage(RecordModel):
    """Describe inspected scope independently from confidence in its contents."""

    state: Literal["complete", "partial", "unavailable"]
    scope: Text
    inspected: list[Text]
    omitted: list[Text]
    reason: Text | None = None

    @model_validator(mode="after")
    def coherent(self) -> Self:
        """Require explicit evidence of partial/unavailable scope.

        Returns:
            This coverage record after its state invariants pass.
        """
        if self.state == "complete" and (self.omitted or not self.inspected):
            raise ValueError("Complete coverage requires inspected scope and no omissions.")
        if self.state == "unavailable" and self.inspected:
            raise ValueError("Unavailable coverage cannot contain inspected locations.")
        if self.state != "complete" and (not self.reason or not self.omitted):
            raise ValueError("Incomplete coverage requires omissions and their reason.")
        if self.state == "partial" and not self.inspected:
            raise ValueError("Use unavailable when nothing was inspected.")
        return self


class Source(RecordModel):
    """Source identity is separate from acquisition transport and media type."""

    id: Text
    path: Identity
    transport: Literal["local", "url", "inline"]
    media_type: Text
    revision: Text | None
    coverage: Coverage
    origin: Text | None = None
    reliability_note: Text | None = None


class Support(RecordModel):
    """One source location supporting one claim, not an entire merged paragraph."""

    source_id: Text
    locator: Text
    excerpt: Text | None = None


class Finding(RecordModel):
    """Keep the smallest useful claim and its material qualifications together."""

    id: Text
    claim: Text
    basis: Literal["observed", "inferred"]
    support: list[Support] = Field(min_length=1)
    qualifiers: list[Text]


class Gap(RecordModel):
    """Absence, failed access and unperformed assessment are different states."""

    state: Literal["searched_absent", "inaccessible", "not_assessed"]
    source_ids: list[Text] = Field(min_length=1)
    scope: Text
    detail: Text


class Conflict(RecordModel):
    """Record disagreement without silently choosing a preferred claim."""

    finding_ids: list[Text] = Field(min_length=2)
    explanation: Text


class SummaryRecord(RecordModel):
    """Versioned evidence sidecar; presentation remains in the selected template."""

    schema_version: Literal[1]
    request_id: Identity
    sources: list[Source] = Field(min_length=1)
    findings: list[Finding]
    selected_findings: list[Text]
    gaps: list[Gap]
    conflicts: list[Conflict]
    confidence: Literal["high", "medium", "low"]
    confidence_notes: Text
    output_format: Format
    output_sha256: Digest

    @field_validator("schema_version", mode="before")
    @classmethod
    def integer_version(cls, value: object) -> object:
        """JSON true is not schema version 1, despite Python equality.

        Returns:
            The unchanged integer version for literal validation.
        """
        if type(value) is not int:
            raise ValueError("Schema version must be an integer.")
        return value

    @model_validator(mode="after")
    def references(self) -> Self:
        """Check identity, provenance edges and impossible coverage claims.

        Returns:
            This record after identity and support references pass.
        """
        sources = {source.id: source for source in self.sources}
        findings = {finding.id: finding for finding in self.findings}
        if len(sources) != len(self.sources) or len(findings) != len(self.findings):
            raise ValueError("Source and finding IDs must be unique.")
        if len(set(self.selected_findings)) != len(self.selected_findings):
            raise ValueError("Selected finding IDs must be unique.")
        if not set(self.selected_findings).issubset(findings):
            raise ValueError("Selected findings must resolve to recorded findings.")
        for finding in self.findings:
            for support in finding.support:
                source = sources.get(support.source_id)
                if source is None or source.coverage.state == "unavailable":
                    raise ValueError("Finding support requires an inspected, known source.")
        return self

    @model_validator(mode="after")
    def gap_references(self) -> Self:
        """Preserve the distinction between searched absence and inaccessible scope.

        Returns:
            This record after gap scope references pass.
        """
        sources = {source.id: source for source in self.sources}
        for gap in self.gaps:
            if len(set(gap.source_ids)) != len(gap.source_ids) or not set(gap.source_ids).issubset(sources):
                raise ValueError("Gap source IDs must be unique and resolve.")
            if gap.state == "searched_absent" and any(
                sources[source_id].coverage.state == "unavailable" for source_id in gap.source_ids
            ):
                raise ValueError("Unavailable content cannot establish searched absence.")
            if gap.state == "inaccessible" and any(
                sources[source_id].coverage.state == "complete" for source_id in gap.source_ids
            ):
                raise ValueError("Inaccessible gaps require incomplete source coverage.")
        return self

    @model_validator(mode="after")
    def conflict_references(self) -> Self:
        """Bind disagreements to distinct recorded findings.

        Returns:
            This record after conflict references pass.
        """
        findings = {finding.id for finding in self.findings}
        for conflict in self.conflicts:
            if len(set(conflict.finding_ids)) != len(conflict.finding_ids):
                raise ValueError("A conflict must reference distinct findings.")
            if not set(conflict.finding_ids).issubset(findings):
                raise ValueError("Conflict finding IDs must resolve.")
        return self


def unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """Reject duplicate JSON keys rather than silently accepting the last value.

    Returns:
        The object with duplicate keys rejected.
    """
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON object key.")
        result[key] = value
    return result


def validate_record(
    record_path: Path, *, request_id: str, source_paths: list[str], output: Path, output_format: str
) -> SummaryRecord:
    """Bind a record to caller expectations, not values selected by the record.

    Returns:
        The record bound to the supplied caller and output bytes.
    """
    data = json.loads(record_path.read_text(encoding="utf-8"), object_pairs_hook=unique_object)
    record = SummaryRecord.model_validate(data)
    if record.request_id != request_id:
        raise ValueError("Record request identity does not match the caller.")
    if Counter(source.path for source in record.sources) != Counter(source_paths):
        raise ValueError("Record source inventory does not match the caller.")
    if record.output_format != output_format:
        raise ValueError("Record format does not match the caller.")
    if hashlib.sha256(output.read_bytes()).hexdigest() != record.output_sha256:
        raise ValueError("Record does not describe the current output bytes.")
    return record


def main() -> int:
    """Emit compact machine-readable results; never infer semantic success.

    Returns:
        Zero for a valid operation, one for invalid records, or two for unavailable inputs.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("schema", help="Emit the generated evidence JSON Schema.")
    digest = commands.add_parser("digest", help="Compute the digest of delivered output bytes.")
    digest.add_argument("output", type=Path)
    check = commands.add_parser("validate", help="Check caller-bound evidence and output identity.")
    check.add_argument("record", type=Path)
    check.add_argument("--request-id", required=True)
    check.add_argument("--source", action="append", required=True)
    check.add_argument("--output", type=Path, required=True)
    check.add_argument("--format", required=True, choices=["structured", "bullets", "tldr", "json", "table", "outline"])
    args = parser.parse_args()
    if args.command == "schema":
        print(json.dumps(SummaryRecord.model_json_schema(), separators=(",", ":")))
        return 0
    try:
        if args.command == "digest":
            print(json.dumps({"output_sha256": hashlib.sha256(args.output.read_bytes()).hexdigest()}, separators=(",", ":")))
            return 0
        record = validate_record(
            args.record, request_id=args.request_id, source_paths=args.source, output=args.output, output_format=args.format
        )
    except (OSError, UnicodeError) as exc:
        print(json.dumps({"status": "UNVERIFIED", "error": str(exc)}, separators=(",", ":")))
        return 2
    except ValueError as exc:
        print(json.dumps({"status": "INVALID", "error": str(exc)}, separators=(",", ":")))
        return 1
    complete = all(source.coverage.state == "complete" for source in record.sources)
    result = {
        "status": "RECORD_VALID",
        "coverage": "complete" if complete else "partial",
        "semantic_support": "UNVERIFIED",
    }
    print(json.dumps(result, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
