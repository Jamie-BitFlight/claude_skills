"""Real local subprocess paths, not model or installed-host conformance tests."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.integration
SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
FIXTURES = Path(__file__).resolve().parents[1] / "evals" / "fixtures"


def invoke(script: str, *arguments: str) -> subprocess.CompletedProcess[str]:
    """Run the real CLI in the current test environment with a bounded process."""
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script), *arguments], capture_output=True, text=True, check=False, timeout=20
    )


def test_chunk_workflow_preserves_bytes_and_exposes_a_missing_receipt(tmp_path: Path) -> None:
    """CLI plan/read/join behavior rejects an omitted middle contribution."""
    source = tmp_path / "source.md"
    source.write_bytes(b"# Intro\nSeven found.\n# Limitation\nThree timed out.\n# End\n")
    plan_result = invoke("source_tools.py", "plan", str(source), "--max-chars", "18")
    assert plan_result.returncode == 0, plan_result.stdout + plan_result.stderr
    plan = json.loads(plan_result.stdout)
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(plan_result.stdout, encoding="utf-8")
    pieces = []
    outcomes = []
    for chunk in plan["chunks"]:
        result = invoke("source_tools.py", "chunk", str(source), "--plan", str(plan_path), "--id", chunk["id"])
        assert result.returncode == 0, result.stdout + result.stderr
        pieces.append(json.loads(result.stdout)["text"])
        outcomes.append({
            "chunk_id": chunk["id"],
            "chunk_sha256": chunk["sha256"],
            "state": "inspected",
            "evidence_ref": f"test-only-read:{chunk['id']}",
        })
    assert "".join(pieces).encode() == source.read_bytes()
    receipts = tmp_path / "receipts.json"
    data = {"schema_version": 1, "source_sha256": plan["source_sha256"], "outcomes": outcomes}
    receipts.write_text(json.dumps(data), encoding="utf-8")
    args = ("coverage", str(source), "--plan", str(plan_path), "--receipts", str(receipts))
    complete = invoke("source_tools.py", *args)
    assert complete.returncode == 0
    assert json.loads(complete.stdout)["status"] == "RECORDED_COMPLETE"
    removed = outcomes.pop(1)
    receipts.write_text(json.dumps(data), encoding="utf-8")
    partial = invoke("source_tools.py", *args)
    assert partial.returncode == 1
    assert json.loads(partial.stdout)["missing"] == [removed["chunk_id"]]
    source.write_bytes(b"changed")
    stale = invoke("source_tools.py", *args)
    assert stale.returncode == 2
    assert json.loads(stale.stdout)["status"] == "INVALID"


def test_profile_cli_reports_the_late_empty_cell() -> None:
    """Fixture expectations originate in the complete raw dataset."""
    result = invoke("source_tools.py", "profile", str(FIXTURES / "late-empty.csv"))
    assert result.returncode == 0, result.stdout + result.stderr
    data = json.loads(result.stdout)
    assert data["row_count"] == 12
    assert data["columns"][1]["empty_count"] == 1
    assert data["columns"][1]["numeric_max"] == "11"


def test_record_cli_binds_final_output_and_rejects_later_mutation(tmp_path: Path) -> None:
    """An actual producer/consumer CLI path cannot certify changed output bytes."""
    output = tmp_path / "summary.md"
    output.write_text("Seven of ten found; three requests timed out.\n", encoding="utf-8")
    digest = invoke("summary_record.py", "digest", str(output))
    assert digest.returncode == 0
    expected_hash = hashlib.sha256(output.read_bytes()).hexdigest()
    assert json.loads(digest.stdout)["output_sha256"] == expected_hash
    record: dict[str, Any] = {
        "schema_version": 1,
        "request_id": "cli-contract",
        "sources": [
            {
                "id": "A",
                "path": "fixture-source",
                "transport": "inline",
                "media_type": "text/plain",
                "revision": None,
                "coverage": {"state": "complete", "scope": "supplied text", "inspected": ["supplied text"], "omitted": []},
            }
        ],
        "findings": [
            {
                "id": "F1",
                "claim": "Seven of ten found; three requests timed out.",
                "basis": "observed",
                "support": [{"source_id": "A", "locator": "line 1"}],
                "qualifiers": ["Three requests timed out."],
            }
        ],
        "selected_findings": ["F1"],
        "gaps": [],
        "conflicts": [],
        "confidence": "high",
        "confidence_notes": "Literal test fixture; not a model-produced claim.",
        "output_format": "tldr",
        "output_sha256": expected_hash,
    }
    record_path = tmp_path / "record.json"
    record_path.write_text(json.dumps(record), encoding="utf-8")
    args = (
        "validate",
        str(record_path),
        "--request-id",
        "cli-contract",
        "--source",
        "fixture-source",
        "--output",
        str(output),
        "--format",
        "tldr",
    )
    result = invoke("summary_record.py", *args)
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)["semantic_support"] == "UNVERIFIED"
    output.write_text("All ten found.\n", encoding="utf-8")
    changed = invoke("summary_record.py", *args)
    assert changed.returncode == 1
    assert json.loads(changed.stdout)["status"] == "INVALID"


def test_metrics_cli_propagates_a_late_decoding_failure(tmp_path: Path) -> None:
    """A successful prefix probe cannot turn unreadable remaining bytes into success."""
    source = tmp_path / "invalid.txt"
    source.write_bytes(b"a" * 9000 + b"\xff")
    result = invoke("file_metrics.py", str(source), "--json")
    assert result.returncode == 1
    assert json.loads(result.stdout)["word_count"] is None
    assert "error" in json.loads(result.stdout)
