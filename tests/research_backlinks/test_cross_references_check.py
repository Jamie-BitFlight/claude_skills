"""Tests for the cross_references_absent validator check and the header_fields severity fix.

Covers the gap identified by /skill-lapidary:establish-validatable-goals against
research-curator: validation-rules.md documented `cross_references_absent` as an
implemented warning check with a date-based exemption, but validate_research.py
had no such check; and validation-rules.md mislabeled `header_fields` as
error-severity while the code (and the Validation Gate flowchart) treats it as
warning-severity.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).parents[2] / ".claude" / "skills" / "research-curator" / "scripts"
_VALIDATE_SCRIPT = _SCRIPTS_DIR / "validate_research.py"


def _uv_path() -> str:
    """Locate the uv binary, raising RuntimeError if not found."""
    found = shutil.which("uv")
    if found is None:
        raise RuntimeError("uv binary not found on PATH — cannot run CLI tests")
    return found


def _run_json(path: Path) -> dict:
    """Run validate_research.py main --json on a single file and parse the result."""
    cmd = [_uv_path(), "run", "--script", str(_VALIDATE_SCRIPT), "main", "--json", str(path)]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return json.loads(result.stdout)


def _body(research_date: str, cross_references: bool) -> str:
    """Build the shared body sections used by both entry formats."""
    content = f"""\
## Overview

Example test entry.

## Problem Addressed

Test.

## Key Features

- Feature A

## Technical Architecture

Simple.

## Installation & Usage

```bash
pip install example
```

## Relevance to Claude Code Development

Test.

## References

- [Example](https://example.com) (accessed {research_date})

## Freshness Tracking

- **Last Verified**: {research_date}
- **Version at Verification**: 1.0.0
- **Next Review Recommended**: 2027-01-01
"""
    if cross_references:
        content += """
## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Other](../other/other.md) | other | related |
"""
    return content


def _write_entry(path: Path, *, research_date: str, cross_references: bool) -> None:
    """Write a minimal well-formed text-header entry, with a controllable date and Cross-References section."""
    path.parent.mkdir(parents=True, exist_ok=True)
    header = f"""\
# Example

**Research Date**: {research_date}
**Source URL**: https://example.com/example
**Version at Research**: 1.0.0
**License**: MIT

---

"""
    path.write_text(header + _body(research_date, cross_references), encoding="utf-8")


def _write_yaml_entry_with_body_date(path: Path, *, research_date: str, cross_references: bool) -> None:
    """Write a YAML-frontmatter entry whose freshness date lives only in the body.

    Mirrors the legacy corpus shape that regressed: the frontmatter carries the
    date under ``metadata.verified`` — a spelling the validator does not
    enumerate — while the body Freshness Tracking table carries it plainly.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    frontmatter = f"""\
---
name: Example
license: MIT
metadata:
  category: developer-tools
  source_url: https://example.com/example
  version: "1.0.0"
  verified: "{research_date}"
---

# Example

"""
    path.write_text(frontmatter + _body(research_date, cross_references), encoding="utf-8")


def _issues_for(entry_json: dict, check: str) -> list[dict]:
    return [i for i in entry_json["entries"][0]["issues"] if i["check"] == check]


class TestCrossReferencesAbsent:
    """cross_references_absent: warns when missing on/after the cutoff, exempts entries before it."""

    def test_recent_entry_without_section_warns(self, tmp_path: Path) -> None:
        """Entry dated after the cutoff with no Cross-References section gets the warning."""
        entry = tmp_path / "example.md"
        _write_entry(entry, research_date="2026-06-01", cross_references=False)
        result = _run_json(entry)
        issues = _issues_for(result, "cross_references_absent")
        assert len(issues) == 1
        assert issues[0]["severity"] == "warning"

    def test_recent_entry_with_section_is_clean(self, tmp_path: Path) -> None:
        """Entry dated after the cutoff with a Cross-References section gets no warning."""
        entry = tmp_path / "example.md"
        _write_entry(entry, research_date="2026-06-01", cross_references=True)
        result = _run_json(entry)
        assert _issues_for(result, "cross_references_absent") == []

    def test_old_entry_without_section_is_exempt(self, tmp_path: Path) -> None:
        """Entry dated before 2026-03-12 with no Cross-References section is exempt."""
        entry = tmp_path / "example.md"
        _write_entry(entry, research_date="2026-01-15", cross_references=False)
        result = _run_json(entry)
        assert _issues_for(result, "cross_references_absent") == []


class TestYamlEntryBodyDateFallback:
    """A YAML entry whose date lives only in the body still gets the cutoff exemption.

    Regression guard for the false positive Codex found on PR #3506: legacy
    entries store the freshness date under frontmatter spellings the validator
    does not enumerate (``metadata.verified``), so resolving from frontmatter
    alone reported pre-cutoff entries as missing Cross-References.
    """

    def test_pre_cutoff_body_date_exempts_yaml_entry(self, tmp_path: Path) -> None:
        """Body Last Verified before the cutoff exempts the entry despite unknown frontmatter keys."""
        entry = tmp_path / "example.md"
        _write_yaml_entry_with_body_date(entry, research_date="2026-01-15", cross_references=False)
        result = _run_json(entry)
        assert result["entries"][0]["format"] == "yaml_frontmatter"
        assert _issues_for(result, "cross_references_absent") == []

    def test_post_cutoff_body_date_still_warns_yaml_entry(self, tmp_path: Path) -> None:
        """The fallback must not suppress the warning for an entry dated after the cutoff."""
        entry = tmp_path / "example.md"
        _write_yaml_entry_with_body_date(entry, research_date="2026-06-01", cross_references=False)
        result = _run_json(entry)
        issues = _issues_for(result, "cross_references_absent")
        assert len(issues) == 1
        assert issues[0]["severity"] == "warning"


class TestHeaderFieldsSeverity:
    """header_fields must report warning severity, matching the Validation Gate flowchart."""

    def test_missing_header_field_is_warning_not_error(self, tmp_path: Path) -> None:
        """An entry missing a required header field reports header_fields as a warning."""
        entry = tmp_path / "example.md"
        _write_entry(entry, research_date="2026-06-01", cross_references=True)
        # Drop the License line to trigger header_fields.
        text = entry.read_text(encoding="utf-8").replace("**License**: MIT\n", "")
        entry.write_text(text, encoding="utf-8")

        result = _run_json(entry)
        issues = _issues_for(result, "header_fields")
        assert len(issues) == 1
        assert issues[0]["severity"] == "warning"
        assert result["entries"][0]["status"] == "pass", "header_fields alone must not fail the entry"
