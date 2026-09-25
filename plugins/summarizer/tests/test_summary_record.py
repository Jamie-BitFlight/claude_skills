"""Contract-based fault sensitivity for caller-bound evidence records."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from summary_record import SummaryRecord, unique_object, validate_record


def example() -> dict[str, Any]:
    """Literal expectations independent of serialization by the production model."""
    return {
        "schema_version": 1,
        "request_id": "request-1",
        "sources": [
            {
                "id": "A",
                "path": "source-A",
                "transport": "local",
                "media_type": "text/plain",
                "revision": "sha-A",
                "coverage": {"state": "complete", "scope": "lines 1-2", "inspected": ["lines 1-2"], "omitted": []},
            }
        ],
        "findings": [
            {
                "id": "F1",
                "claim": "100 requests per minute",
                "basis": "observed",
                "support": [{"source_id": "A", "locator": "line 1"}],
                "qualifiers": [],
            }
        ],
        "selected_findings": ["F1"],
        "gaps": [],
        "conflicts": [],
        "confidence": "high",
        "confidence_notes": "Direct claim from the inspected scope.",
        "output_format": "tldr",
        "output_sha256": hashlib.sha256(b"summary").hexdigest(),
    }


def test_valid_record_binds_to_caller_and_bytes(tmp_path: Path) -> None:
    """Source identity, request identity and output are independent inputs."""
    record_path = tmp_path / "evidence.json"
    output = tmp_path / "summary.md"
    record_path.write_text(json.dumps(example()), encoding="utf-8")
    output.write_bytes(b"summary")
    record = validate_record(
        record_path, request_id="request-1", source_paths=["source-A"], output=output, output_format="tldr"
    )
    assert record.findings[0].support[0].source_id == "A"
    output.write_bytes(b"changed summary")
    with pytest.raises(ValueError, match="current output bytes"):
        validate_record(
            record_path, request_id="request-1", source_paths=["source-A"], output=output, output_format="tldr"
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [("request_id", "another-request"), ("source_paths", ["another-source"]), ("output_format", "json")],
)
def test_rejects_caller_mismatch(tmp_path: Path, field: str, value: object) -> None:
    """A worker cannot redefine the request from its own response."""
    record_path = tmp_path / "evidence.json"
    output = tmp_path / "summary.md"
    record_path.write_text(json.dumps(example()), encoding="utf-8")
    output.write_bytes(b"summary")
    kwargs: dict[str, Any] = {
        "request_id": "request-1",
        "source_paths": ["source-A"],
        "output": output,
        "output_format": "tldr",
    }
    kwargs[field] = value
    with pytest.raises(ValueError, match="caller"):
        validate_record(record_path, **kwargs)


@pytest.mark.parametrize(
    "fault",
    [
        "duplicate_source",
        "duplicate_finding",
        "missing_source",
        "unavailable_support",
        "false_complete",
        "missing_failure_reason",
        "missing_selected_finding",
        "duplicate_selected",
        "missing_conflict",
        "self_conflict",
        "unavailable_absence",
        "unknown_gap_source",
    ],
)
def test_rejects_contract_violations(fault: str) -> None:
    """Each mutation violates a declared invariant, not current output wording."""
    data = example()
    if fault == "duplicate_source":
        data["sources"].append(copy.deepcopy(data["sources"][0]))
    elif fault == "duplicate_finding":
        data["findings"].append(copy.deepcopy(data["findings"][0]))
    elif fault == "missing_source":
        data["findings"][0]["support"][0]["source_id"] = "unknown"
    elif fault in {"unavailable_support", "unavailable_absence"}:
        data["sources"][0]["coverage"] = {
            "state": "unavailable",
            "scope": "whole source",
            "inspected": [],
            "omitted": ["whole source"],
            "reason": "HTTP 403",
        }
        if fault == "unavailable_absence":
            data["findings"] = []
            data["selected_findings"] = []
            data["gaps"] = [
                {"state": "searched_absent", "source_ids": ["A"], "scope": "whole source", "detail": "No feature"}
            ]
    elif fault == "false_complete":
        data["sources"][0]["coverage"]["omitted"] = ["line 2"]
    elif fault == "missing_failure_reason":
        data["sources"][0]["coverage"].update(state="partial", omitted=["line 2"])
    elif fault == "missing_selected_finding":
        data["selected_findings"] = ["unknown"]
    elif fault == "duplicate_selected":
        data["selected_findings"] *= 2
    elif fault in {"missing_conflict", "self_conflict"}:
        data["conflicts"] = [
            {"finding_ids": ["F1", "unknown" if fault == "missing_conflict" else "F1"], "explanation": "Conflict"}
        ]
    elif fault == "unknown_gap_source":
        data["gaps"] = [
            {"state": "not_assessed", "source_ids": ["unknown"], "scope": "whole source", "detail": "Not assessed"}
        ]
    with pytest.raises(ValidationError):
        SummaryRecord.model_validate(data)


def test_partial_sources_remain_explicit_and_do_not_erase_successful_findings() -> None:
    """Partial acquisition is not the same as absence or an invalid record."""
    data = example()
    data["sources"].append({
        "id": "B",
        "path": "source-B",
        "transport": "url",
        "media_type": "unknown",
        "revision": None,
        "coverage": {
            "state": "unavailable",
            "scope": "whole page",
            "inspected": [],
            "omitted": ["whole page"],
            "reason": "HTTP 403",
        },
    })
    data["gaps"] = [{"state": "inaccessible", "source_ids": ["B"], "scope": "whole page", "detail": "HTTP 403"}]
    result = SummaryRecord.model_validate(data)
    assert result.sources[1].coverage.reason == "HTTP 403"
    assert result.findings[0].claim == "100 requests per minute"


def test_qualifier_keeps_its_own_support() -> None:
    """The per-key qualifier is supported by B, not silently attributed to A."""
    data = example()
    source_b = copy.deepcopy(data["sources"][0])
    source_b.update(id="B", path="source-B")
    data["sources"].append(source_b)
    data["findings"].append({
        "id": "F2",
        "claim": "100 requests per minute per key",
        "basis": "observed",
        "support": [{"source_id": "B", "locator": "line 7"}],
        "qualifiers": ["per key"],
    })
    result = SummaryRecord.model_validate(data)
    assert [item.source_id for item in result.findings[1].support] == ["B"]
    assert result.findings[1].qualifiers == ["per key"]


def test_duplicate_json_keys_are_rejected() -> None:
    """Duplicate values cannot silently replace request identity."""
    with pytest.raises(ValueError, match="Duplicate"):
        json.loads('{"request_id":"a","request_id":"b"}', object_pairs_hook=unique_object)


def test_boolean_is_not_a_schema_version() -> None:
    """JSON booleans must not alias integer version identifiers."""
    data = example()
    data["schema_version"] = True
    with pytest.raises(ValidationError, match="integer"):
        SummaryRecord.model_validate(data)


@pytest.mark.parametrize(("field", "value"), [("verified", True), ("schema_version", 2)])
def test_rejects_unknown_field_or_version(field: str, value: object) -> None:
    """Unknown claims and versions cannot extend the contract silently."""
    data = example()
    data[field] = value
    with pytest.raises(ValidationError):
        SummaryRecord.model_validate(data)


def test_rejects_empty_source_location() -> None:
    """A blank locator cannot carry claim provenance."""
    data = example()
    data["findings"][0]["support"][0]["locator"] = " "
    with pytest.raises(ValidationError):
        SummaryRecord.model_validate(data)
