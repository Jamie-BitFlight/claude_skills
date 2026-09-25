"""Falsifiers for source partitions, coverage receipts and complete data aggregates."""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path

import pytest
from pydantic import ValidationError

import file_metrics
from source_tools import Plan, Receipt, Receipts, build_plan, profile_delimited, read_chunk, read_plan, reconcile


def store_plan(tmp_path: Path, text: str, budget: int = 12) -> tuple[Path, Path, Plan]:
    """Create an explicit source and retained plan for a bounded test."""
    source = tmp_path / "source.txt"
    source.write_bytes(text.encode("utf-8"))
    plan = build_plan(source, budget)
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(plan.model_dump_json(), encoding="utf-8")
    return source, plan_path, plan


def receipts_for(plan: Plan) -> Receipts:
    """Supply explicit mocked inspection records, not a real model execution."""
    return Receipts(
        schema_version=1,
        source_sha256=plan.source_sha256,
        outcomes=[
            Receipt(chunk_id=item.id, chunk_sha256=item.sha256, state="inspected", evidence_ref=f"trace:{item.id}")
            for item in plan.chunks
        ],
    )


@pytest.mark.parametrize("text", ["", "abc", "x" * 100, "# A\nalpha\n# B\nbeta\n", "é中\r\n" * 20])
def test_partition_is_complete_without_overlap(tmp_path: Path, text: str) -> None:
    """Reassembling requested chunks recovers every original character exactly once."""
    source, path, plan = store_plan(tmp_path, text)
    chunks = [read_chunk(source, path, item.id)["text"] for item in plan.chunks]
    assert "".join(str(item) for item in chunks) == text
    assert sum(item.end - item.start for item in plan.chunks) == len(text)
    assert all(item.end - item.start <= 12 for item in plan.chunks)
    assert plan.source_sha256 == hashlib.sha256(text.encode()).hexdigest()


def test_missing_middle_receipt_cannot_be_complete(tmp_path: Path) -> None:
    """Missing coverage stays explicit even when first/last chunks succeeded."""
    _, _, plan = store_plan(tmp_path, "first\ncritical middle\nlast\n", 6)
    receipts = receipts_for(plan)
    missing = receipts.outcomes.pop(1).chunk_id
    result = reconcile(plan, receipts)
    assert result["status"] == "RECORDED_PARTIAL"
    assert result["missing"] == [missing]


def test_failure_preserves_reason_and_does_not_inherit_success(tmp_path: Path) -> None:
    """A failed worker is a recorded gap, not an empty successful contribution."""
    _, _, plan = store_plan(tmp_path, "abcdef", 3)
    receipts = receipts_for(plan)
    receipts.outcomes[1] = Receipt(
        chunk_id=plan.chunks[1].id, chunk_sha256=plan.chunks[1].sha256, state="failed", reason="reader timed out"
    )
    result = reconcile(plan, receipts)
    assert result["status"] == "RECORDED_PARTIAL"
    assert result["failed"][0]["reason"] == "reader timed out"
    assert result["semantic_support"] == "UNVERIFIED"


@pytest.mark.parametrize("fault", ["duplicate", "unknown", "digest", "source", "no_evidence", "no_reason"])
def test_receipt_contract_rejects_false_completion(tmp_path: Path, fault: str) -> None:
    """Each bad receipt violates identity, uniqueness or the outcome contract."""
    _, _, plan = store_plan(tmp_path, "abcdef", 3)
    receipts = receipts_for(plan)
    if fault == "duplicate":
        receipts.outcomes.append(receipts.outcomes[0])
    elif fault == "unknown":
        receipts.outcomes[0].chunk_id = "unknown"
    elif fault == "digest":
        receipts.outcomes[0].chunk_sha256 = "0" * 64
    elif fault == "source":
        receipts.source_sha256 = "0" * 64
    elif fault == "no_evidence":
        receipts.outcomes[0].evidence_ref = None
    else:
        receipts.outcomes[0].state = "failed"
    with pytest.raises(ValueError, match=r"Receipt|Receipts|Inspected|Failed"):
        reconcile(plan, receipts)


def test_changed_source_and_removed_plan_chunk_are_rejected(tmp_path: Path) -> None:
    """Recompute the partition rather than trusting a plan's self-reported coverage."""
    source, path, plan = store_plan(tmp_path, "abcdefghijkl", 3)
    source.write_text("changed", encoding="utf-8")
    with pytest.raises(ValueError, match="current source"):
        read_plan(source, path)
    source.write_text("abcdefghijkl", encoding="utf-8")
    plan.chunks.pop(1)
    path.write_text(plan.model_dump_json(), encoding="utf-8")
    with pytest.raises(ValueError, match="current source"):
        read_plan(source, path)


def test_bad_budget_and_boolean_version_are_rejected(tmp_path: Path) -> None:
    """Control values must be explicit positive integers and integer versions."""
    source, _, plan = store_plan(tmp_path, "abc")
    with pytest.raises(ValueError, match="positive"):
        build_plan(source, 0)
    data = plan.model_dump()
    data["schema_version"] = True
    with pytest.raises(ValidationError, match="integer"):
        Plan.model_validate(data)


def test_csv_profile_covers_missing_values_after_first_ten_rows(tmp_path: Path) -> None:
    """Whole-dataset claims use all records, including a late missing value."""
    source = tmp_path / "data.csv"
    source.write_text("id,value\n" + "".join(f"{i},{i}\n" for i in range(1, 12)) + "12,\n", encoding="utf-8")
    result = profile_delimited(source)
    assert result["row_count"] == 12
    assert result["columns"][1]["empty_count"] == 1
    assert result["columns"][1]["numeric_count"] == 11
    assert result["columns"][1]["numeric_min"] == "1"
    assert result["columns"][1]["numeric_max"] == "11"


def test_multiline_csv_is_counted_as_records_not_lines(tmp_path: Path) -> None:
    """Quoted newlines do not inflate the record count."""
    source = tmp_path / "multiline.csv"
    source.write_bytes(b'\xef\xbb\xbfid,note\r\n1,"two\nlines"\r\n2,null\r\n')
    result = profile_delimited(source)
    assert result["row_count"] == 2
    assert result["physical_lines"] == 4
    assert result["columns"][1]["empty_count"] == 0


@pytest.mark.parametrize("text", ["", "a,a\n1,2\n", "a,b\n1\n", 'a,b\n1,"unterminated'])
def test_invalid_dataset_cannot_report_complete(tmp_path: Path, text: str) -> None:
    """Malformed headers, record widths and CSV syntax fail instead of sampling around them."""
    source = tmp_path / "bad.csv"
    source.write_text(text, encoding="utf-8")
    with pytest.raises((ValueError, csv.Error)):
        profile_delimited(source)


def test_tsv_and_exact_numeric_range(tmp_path: Path) -> None:
    """Decimal ranges do not silently round through floating point."""
    source = tmp_path / "data.tsv"
    source.write_text("value\tflag\n100000000000000000001\ttrue\n0.01\tfalse\n", encoding="utf-8")
    result = profile_delimited(source)
    assert result["columns"][0]["numeric_max"] == "100000000000000000001"
    assert result["columns"][0]["numeric_min"] == "0.01"
    assert result["columns"][1]["observed_types"] == {"boolean": 2}


def test_utf8_probe_does_not_split_a_valid_character(tmp_path: Path) -> None:
    """A valid multibyte character spanning byte 8192 remains text."""
    source = tmp_path / "unicode.txt"
    source.write_text("a" * 8191 + "é text", encoding="utf-8")
    assert file_metrics.is_text_file(source)
    assert file_metrics.get_file_metrics(source)["is_text"]


def test_zero_tail_never_expands_to_the_whole_source(tmp_path: Path) -> None:
    """Explicit zero tail means no tail, including a file longer than the head."""
    source = tmp_path / "source.txt"
    source.write_text("first\nsecond\nthird\n", encoding="utf-8")
    result = file_metrics.extract_excerpt(source, head_lines=1, tail_lines=0)
    assert result == {"head": "first", "tail": None, "total_lines": 3}


def test_invalid_later_encoding_is_not_silently_replaced(tmp_path: Path) -> None:
    """Valid prefix does not authorize replacement decoding of unreadable later bytes."""
    source = tmp_path / "later.txt"
    source.write_bytes(b"a" * 9000 + b"\xff")
    assert "error" in file_metrics.count_metrics(source)
    result = file_metrics.get_file_metrics(source)
    assert "error" in result
    assert result["word_count"] is None
    assert file_metrics.format_human_readable(result).startswith("Error:")


def test_read_failure_is_not_a_successful_binary_classification(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The public metrics boundary propagates access failures instead of hiding them as binary."""
    source = tmp_path / "source.txt"
    source.write_text("content", encoding="utf-8")

    def deny(_: Path) -> bool:
        raise PermissionError("access denied")

    monkeypatch.setattr(file_metrics, "probe_text", deny)
    assert file_metrics.get_file_metrics(source)["error"] == "access denied"


def test_unknown_chunk_does_not_return_arbitrary_content(tmp_path: Path) -> None:
    """Chunk addressing requires membership of the verified partition."""
    source, path, _ = store_plan(tmp_path, "abc")
    with pytest.raises(ValueError, match="Unknown"):
        read_chunk(source, path, "not-planned")
