"""Tests for verify_migration_fidelity.py.

verify_migration_fidelity is invoked exclusively by AI agents via subprocess,
so its ``main`` command emits a single compact JSON object on stdout — these
tests parse that JSON and assert on structured fields. The full markdown
report it also writes to disk is unaffected by the Rich removal (it never
used Rich) and is not the focus here.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from backlog_core.operations import render_sections_as_body
from backlog_core.yaml_io import load_item_text, save_item

# ---------------------------------------------------------------------------
# Bootstrap: add the harness package to sys.path so the script under test
# can be imported directly in the test environment.
# ---------------------------------------------------------------------------
_HARNESS_DIR = Path(__file__).resolve().parents[1]
if str(_HARNESS_DIR) not in sys.path:
    sys.path.insert(0, str(_HARNESS_DIR))

from scripts.verify_migration_fidelity import CONTENT_LOSS, MATCH, FileResult, VerificationReport, _summary_payload, app
from typer.testing import CliRunner

runner = CliRunner()

_ITEM_MD = """\
---
name: Test migration item
description: A test item for fidelity verification.
metadata:
  source: test-session
  added: '2026-01-15'
  priority: P1
  type: Feature
  status: open
  issue: '#42'
---

## Context

Some context content that must survive migration.
"""


def _write_matching_pair(backlog_dir: Path, name: str = "item1") -> None:
    """Write a .md.bak / .yaml pair guaranteed to classify as MATCH.

    Loads the fixture .md text into a BacklogItem, saves it as .yaml, then
    writes the .md.bak body as the exact rendered output of that same item
    — so verify_file() finds zero diff.
    """
    md_path = Path(f"{name}.md")
    item = load_item_text(_ITEM_MD, md_path)

    yaml_path = backlog_dir / f"{name}.yaml"
    save_item(item, yaml_path)

    rendered_body = render_sections_as_body(item).rstrip()
    bak_path = backlog_dir / f"{name}.md.bak"
    bak_path.write_text(f"---\nname: {item.title}\n---\n\n{rendered_body}\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# _summary_payload — direct unit coverage
# ---------------------------------------------------------------------------


def test_summary_payload_reports_classification_counts(tmp_path: Path) -> None:
    report = VerificationReport(
        results=[
            FileResult(bak_path=Path("a.md.bak"), classification=MATCH),
            FileResult(bak_path=Path("b.md.bak"), classification=CONTENT_LOSS, diff_lines=["-lost line\n"]),
        ],
        total_bak=2,
        skipped_no_yaml=1,
        errors=0,
    )

    payload = _summary_payload(report, tmp_path, verbose=False)

    assert payload["total_bak"] == 2
    assert payload["processed"] == 2
    assert payload["skipped_no_yaml"] == 1
    assert payload["classification_counts"] == {"MATCH": 1, "MINOR_DIFF": 0, "CONTENT_LOSS": 1, "CONTENT_GAIN": 0}


def test_summary_payload_includes_content_loss_preview(tmp_path: Path) -> None:
    # FileResult.lost_lines strips only the leading '-' diff marker, so the
    # trailing newline from the diff line is preserved in the preview.
    result = FileResult(bak_path=Path("b.md.bak"), classification=CONTENT_LOSS, diff_lines=["-lost line\n"])
    report = VerificationReport(results=[result], total_bak=1)

    payload = _summary_payload(report, tmp_path, verbose=False)

    assert payload["content_loss_items"] == [{"file": "b.md.bak", "missing_preview": "lost line\n"}]


def test_summary_payload_omits_verbose_diffs_by_default(tmp_path: Path) -> None:
    result = FileResult(bak_path=Path("b.md.bak"), classification=CONTENT_LOSS, diff_lines=["-lost line\n"])
    report = VerificationReport(results=[result], total_bak=1)

    payload = _summary_payload(report, tmp_path, verbose=False)

    assert payload["verbose_diffs"] == []


def test_summary_payload_includes_verbose_diffs_when_requested(tmp_path: Path) -> None:
    result = FileResult(bak_path=Path("b.md.bak"), classification=CONTENT_LOSS, diff_lines=["-lost line\n"])
    report = VerificationReport(results=[result], total_bak=1)

    payload = _summary_payload(report, tmp_path, verbose=True)

    assert payload["verbose_diffs"] == [{"file": "b.md.bak", "classification": CONTENT_LOSS, "diff": "-lost line\n"}]


def test_summary_payload_includes_verification_errors(tmp_path: Path) -> None:
    result = FileResult(bak_path=Path("c.md.bak"), error="load_item failed: boom")
    report = VerificationReport(results=[result], total_bak=1, errors=1)

    payload = _summary_payload(report, tmp_path, verbose=False)

    assert payload["verification_errors"] == [{"file": "c.md.bak", "error": "load_item failed: boom"}]


# ---------------------------------------------------------------------------
# main command — CLI-level JSON contract
# ---------------------------------------------------------------------------


def test_main_missing_backlog_dir_errors(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"

    result = runner.invoke(app, ["--backlog-dir", str(missing)])

    assert result.exit_code == 1
    assert "does not exist" in result.output.lower() or "not found" in result.output.lower()


def test_main_reports_match_and_exits_0(tmp_path: Path) -> None:
    _write_matching_pair(tmp_path)

    result = runner.invoke(app, ["--backlog-dir", str(tmp_path)])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["total_bak"] == 1
    assert payload["classification_counts"]["MATCH"] == 1
    assert payload["classification_counts"]["CONTENT_LOSS"] == 0
    assert Path(payload["report_path"]).exists()

    Path(payload["report_path"]).unlink()


def test_main_no_yaml_counterpart_is_skipped(tmp_path: Path) -> None:
    (tmp_path / "orphan.md.bak").write_text("---\nname: orphan\n---\n\nbody\n", encoding="utf-8")

    result = runner.invoke(app, ["--backlog-dir", str(tmp_path)])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["skipped_no_yaml"] == 1
    assert payload["processed"] == 0

    Path(payload["report_path"]).unlink()
