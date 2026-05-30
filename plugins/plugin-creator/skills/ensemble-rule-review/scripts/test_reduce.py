#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pytest"]
# ///
"""Tests for the ensemble-rule-review corroboration reducer.

Run: uv run --with pytest pytest test_reduce.py
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import reduce as r

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

WORKER_A = """# Worker A
- group: 2
  rule: any-without-justification
  location: create_plugin.py:121
  severity: high
  evidence: "dict[str, Any]"

- group: 2
  rule: any-without-justification
  location: create_plugin.py:127
  severity: high
  evidence: "manifest: dict[str, Any]"
"""

# Worker C flags the SAME line 121 with a DIFFERENT rule slug — corroboration must
# still fire because keying is on (group, location), not the free-form rule slug.
WORKER_C = """# Worker C
- group: 2
  rule: any-not-in-boundary-module
  location: create_plugin.py:121
  severity: high
  evidence: "def create_plugin_json(...) -> dict[str, Any]:"
"""


def test_parse_allows_list_item_dash() -> None:
    findings = r.parse_report(WORKER_A)
    assert len(findings) == 2
    assert findings[0].group == "2"
    assert findings[0].location == "create_plugin.py:121"


def test_corroboration_keys_on_group_not_rule() -> None:
    """Two workers, same (group, line), different rule slugs -> one weight-2 finding."""
    reports = {"A": r.parse_report(WORKER_A), "C": r.parse_report(WORKER_C)}
    survivors = r.reduce_findings(reports, keep_threshold=1)
    line121 = [m for m in survivors if m.location == "create_plugin.py:121"]
    assert len(line121) == 1
    assert line121[0].weight == 2
    assert line121[0].agents == {"A", "C"}
    # Both distinct slugs are retained for display, but did not block the merge.
    assert line121[0].rules == {"any-without-justification", "any-not-in-boundary-module"}


def test_lone_finding_stays_weight_one() -> None:
    reports = {"A": r.parse_report(WORKER_A), "C": r.parse_report(WORKER_C)}
    survivors = r.reduce_findings(reports, keep_threshold=1)
    line127 = [m for m in survivors if m.location == "create_plugin.py:127"]
    assert len(line127) == 1
    assert line127[0].weight == 1


def test_keep_threshold_drops_tail() -> None:
    reports = {"A": r.parse_report(WORKER_A), "C": r.parse_report(WORKER_C)}
    survivors = r.reduce_findings(reports, keep_threshold=2)
    assert all(m.weight >= 2 for m in survivors)
    assert all(m.location != "create_plugin.py:127" for m in survivors)


def test_pass_verdict_excluded() -> None:
    report = """- group: 1
  rule: typed
  location: x.py:10
  verdict: PASS
  severity: low
"""
    reports = {"A": r.parse_report(report)}
    assert r.reduce_findings(reports, keep_threshold=1) == []


def test_verdict_defaults_to_violation_when_absent() -> None:
    findings = r.parse_report(WORKER_A)
    assert all(f.verdict == "VIOLATION" for f in findings)


def test_normalize_location_strips_abs_prefix_but_keeps_path() -> None:
    # Absolute prefix stripped to repo-relative, but the directory is PRESERVED.
    assert r.normalize_location("  /repo/src/foo/config.py:10 ") == "repo/src/foo/config.py:10"
    assert r.normalize_location("src/foo/config.py:10") == "src/foo/config.py:10"


def test_same_basename_different_dirs_do_not_corroborate() -> None:
    """Two files sharing a basename must NOT collapse into one weight-2 finding."""
    a = """- group: 1
  rule: x
  location: src/foo/config.py:10
  severity: high
"""
    c = """- group: 1
  rule: x
  location: tests/foo/config.py:10
  severity: high
"""
    survivors = r.reduce_findings({"A": r.parse_report(a), "C": r.parse_report(c)}, keep_threshold=1)
    assert len(survivors) == 2
    assert all(m.weight == 1 for m in survivors)


def test_severity_escalates_to_highest() -> None:
    report = """- group: 1
  rule: a
  location: x.py:10
  severity: low
- group: 1
  rule: b
  location: x.py:10
  severity: critical
"""
    merged = r.reduce_findings({"A": r.parse_report(report)}, keep_threshold=1)
    assert len(merged) == 1
    assert merged[0].severity == "critical"


def test_ranking_weight_then_severity() -> None:
    reports = {"A": r.parse_report(WORKER_A), "C": r.parse_report(WORKER_C)}
    survivors = r.reduce_findings(reports, keep_threshold=1)
    # Corroborated (weight 2) ranks above lone (weight 1).
    assert survivors[0].weight == 2


def test_load_reports_derives_worker_id_from_stem(tmp_path: Path) -> None:
    (tmp_path / "review-A.md").write_text(WORKER_A, encoding="utf-8")
    (tmp_path / "review-C.md").write_text(WORKER_C, encoding="utf-8")
    reports = r.load_reports(tmp_path, "review-*.md")
    assert set(reports) == {"A", "C"}


def test_main_runs_end_to_end(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (tmp_path / "review-A.md").write_text(WORKER_A, encoding="utf-8")
    (tmp_path / "review-C.md").write_text(WORKER_C, encoding="utf-8")
    code = r.main([str(tmp_path), "--glob", "review-*.md"])
    assert code == 0
    out = capsys.readouterr().out
    assert "corroborated (weight>=2): 1" in out
    assert "KEEP w=2" in out


def test_main_errors_on_missing_dir(tmp_path: Path) -> None:
    assert r.main([str(tmp_path / "nope")]) == 2
