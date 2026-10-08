"""Focused hostile fixtures for the frozen-evidence reducer."""
import hashlib
import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "reduce_workflow_evidence.py"
spec = importlib.util.spec_from_file_location("workflow_reducer", SCRIPT)
assert spec and spec.loader
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
    manifest = {"version": 1, "sources": [{"path": "source.md", "sha256": hashlib.sha256(source.read_bytes()).hexdigest()}], "assignments": assignments}
    finding = {"rule": "fork", "path": "source.md", "start": 0, "end": 5, "quote": "hello", "kind": "decision"}
    reports = [{"worker": "w1", "findings": [finding]}, {"worker": "w2", "findings": [finding]}, {"worker": "w3", "findings": []}]
    return manifest, reports


def test_corrob_and_determinism(tmp_path):
    manifest, reports = fixture(tmp_path)
    first = module.reduce_frozen(manifest, reports, tmp_path)
    assert len(first["verified"]) == 1
    assert first["verified"][0]["workers"] == ["w1", "w2"]
    assert module.canonical(first) == module.canonical(module.reduce_frozen(manifest, list(reversed(reports)), tmp_path))


def test_singleton_unverified(tmp_path):
    manifest, reports = fixture(tmp_path)
    reports[1]["findings"] = []
    result = module.reduce_frozen(manifest, reports, tmp_path)
    assert not result["verified"]
    assert len(result["unverified_items"]) == 1


@pytest.mark.parametrize("mutation", ["digest", "quote", "duplicate_worker", "wrong_rule", "escaped_path", "bad_span", "invalid_assignment"])
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
