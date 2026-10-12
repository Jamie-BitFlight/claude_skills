"""Focused hostile fixtures for the frozen-evidence reducer."""

from __future__ import annotations

import hashlib
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "reduce_workflow_evidence.py"
spec = importlib.util.spec_from_file_location("workflow_reducer", SCRIPT)
assert spec
assert spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def fixture(tmp_path):
    source = tmp_path / "source.md"
    source.write_text("hello world", encoding="utf-8")
    assignments = {
        "w1": ["fork", "branch", "reference", "dispatch"],
        "w2": ["fork", "branch", "tool", "artifact"],
        "w3": ["reference", "dispatch", "tool", "artifact"],
    }
    manifest = {
        "version": 1,
        "sources": [{"path": "source.md", "sha256": hashlib.sha256(source.read_bytes()).hexdigest()}],
        "assignments": assignments,
    }
    finding = {"rule": "fork", "path": "source.md", "start": 0, "end": 5, "quote": "hello", "kind": "decision"}
    reports = [
        {"worker": "w1", "findings": [finding]},
        {"worker": "w2", "findings": [finding]},
        {"worker": "w3", "findings": []},
    ]
    return manifest, reports


def test_corrob_and_determinism(tmp_path):
    manifest, reports = fixture(tmp_path)
    first = module.reduce_frozen(manifest, reports, tmp_path)
    assert len(first["verified"]) == 1
    assert first["verified"][0]["workers"] == ["w1", "w2"]
    assert module.canonical(first) == module.canonical(
        module.reduce_frozen(manifest, list(reversed(reports)), tmp_path)
    )


def test_singleton_unverified(tmp_path):
    manifest, reports = fixture(tmp_path)
    reports[1]["findings"] = []
    result = module.reduce_frozen(manifest, reports, tmp_path)
    assert not result["verified"]
    assert len(result["unverified_items"]) == 1


@pytest.mark.parametrize(
    "mutation", ["digest", "quote", "duplicate_worker", "wrong_rule", "escaped_path", "bad_span", "invalid_assignment"]
)
def test_reject_hostile_evidence(tmp_path, mutation):
    manifest, reports = fixture(tmp_path)
    finding = reports[0]["findings"][0]
    if mutation == "digest":
        manifest["sources"][0]["sha256"] = "0" * 64
    elif mutation == "quote":
        finding["quote"] = "wrong"
    elif mutation == "duplicate_worker":
        reports[2]["worker"] = "w1"
    elif mutation == "wrong_rule":
        finding["rule"] = "artifact"
    elif mutation == "escaped_path":
        manifest["sources"][0]["path"] = "../source.md"
    elif mutation == "bad_span":
        finding["end"] = 999
    elif mutation == "invalid_assignment":
        manifest["assignments"]["w3"] = []
    with pytest.raises((module.ExtractionError, TypeError, KeyError, ValueError)):
        module.reduce_frozen(manifest, reports, tmp_path)


def test_in_root_symlink_component_rejected(tmp_path):
    manifest, reports = fixture(tmp_path)
    (tmp_path / "real").mkdir()
    (tmp_path / "real" / "source.md").write_text("hello world", encoding="utf-8")
    (tmp_path / "alias").symlink_to(tmp_path / "real", target_is_directory=True)
    manifest["sources"][0]["path"] = "alias/source.md"
    for report in reports:
        for finding in report["findings"]:
            finding["path"] = "alias/source.md"
    with pytest.raises(module.ExtractionError, match="symlinked"):
        module.reduce_frozen(manifest, reports, tmp_path)


def test_utf8_byte_span_and_source_bytes_preserved(tmp_path):
    manifest, reports = fixture(tmp_path)
    source = tmp_path / "source.md"
    source.write_text("héllo", encoding="utf-8")
    original_bytes = source.read_bytes()
    manifest["sources"][0]["sha256"] = hashlib.sha256(original_bytes).hexdigest()
    for report in reports[:2]:
        report["findings"][0].update(end=3, quote="hé")

    result = module.reduce_frozen(manifest, reports, tmp_path)

    assert result["verified"][0]["quote"] == "hé"
    assert source.read_bytes() == original_bytes


def test_cli_rejects_decoded_non_objects_without_overwriting_output(tmp_path):
    invalid = tmp_path / "invalid.json"
    invalid.write_text("[]", encoding="utf-8")
    output = tmp_path / "staged.json"
    sentinel = b"existing staged artifact"
    output.write_bytes(sentinel)

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--root",
            str(tmp_path),
            "--manifest",
            str(invalid),
            "--worker",
            str(invalid),
            "--worker",
            str(invalid),
            "--worker",
            str(invalid),
            "--output",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 2
    assert "manifest must decode to an object" in completed.stderr
    assert output.read_bytes() == sentinel
