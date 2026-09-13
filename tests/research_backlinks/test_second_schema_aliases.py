"""Tests for the YAML frontmatter key aliases the ``header_fields`` and
``freshness_tracking`` checks accept.

Covers the frontmatter-schema conflict identified by
``/skill-lapidary:establish-validatable-goals`` against research-curator:
``references/entry-template.md`` (the reachable schema — ``research_date``,
``source_url``, ``freshness_tracking.last_verified``) and the now-deleted
``references/frontmatter-generation.md`` (an unreachable competing schema —
``date_created``, ``resource_url``, ``date_last_reviewed``) disagreed on key
spellings for the same four fields. The live corpus under ``research/``
contains entries written in both spellings, so ``validate_research.py``
accepts both instead of requiring a corpus-wide rewrite.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).parents[2] / ".claude" / "skills" / "research-curator" / "scripts"
_VALIDATE_SCRIPT = _SCRIPTS_DIR / "validate_research.py"

_BODY = """\
# Example

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

- [Example](https://example.com) (accessed 2026-06-01)
"""


def _uv_path() -> str:
    """Locate the uv binary, raising RuntimeError if not found."""
    found = shutil.which("uv")
    if found is None:
        raise RuntimeError("uv binary not found on PATH — cannot run CLI tests")
    return found


def _run_json(path: Path) -> dict:
    """Run ``validate_research.py main --json`` on a single file and parse the result."""
    cmd = [_uv_path(), "run", "--script", str(_VALIDATE_SCRIPT), "main", "--json", str(path)]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return json.loads(result.stdout)


def _write_yaml_entry(path: Path, frontmatter_lines: list[str]) -> None:
    """Write a YAML-frontmatter entry with a well-formed body and the given frontmatter lines."""
    path.parent.mkdir(parents=True, exist_ok=True)
    frontmatter = "\n".join(["---", *frontmatter_lines, "---", ""])
    path.write_text(frontmatter + _BODY, encoding="utf-8")


def _issues_for(entry_json: dict, check: str) -> list[dict]:
    return [i for i in entry_json["entries"][0]["issues"] if i["check"] == check]


class TestSecondSchemaHeaderFieldAliases:
    """``header_fields`` accepts the second schema's key spellings."""

    def test_resource_url_satisfies_source_url(self, tmp_path: Path) -> None:
        """``resource_url`` resolves the Source URL requirement."""
        entry = tmp_path / "example.md"
        _write_yaml_entry(
            entry,
            [
                'title: "Example"',
                'resource_url: "https://example.com/example"',
                'version_at_research: "1.0.0"',
                'license: "MIT"',
                'date_created: "2026-06-01"',
            ],
        )
        result = _run_json(entry)
        messages = [i["message"] for i in _issues_for(result, "header_fields")]
        assert not any("Source URL" in m for m in messages), messages

    def test_date_created_satisfies_research_date(self, tmp_path: Path) -> None:
        """``date_created`` resolves the Research Date requirement."""
        entry = tmp_path / "example.md"
        _write_yaml_entry(
            entry,
            [
                'title: "Example"',
                'source_url: "https://example.com/example"',
                'version_at_research: "1.0.0"',
                'license: "MIT"',
                'date_created: "2026-06-01"',
            ],
        )
        result = _run_json(entry)
        messages = [i["message"] for i in _issues_for(result, "header_fields")]
        assert not any("Research Date" in m for m in messages), messages

    def test_second_schema_entry_passes_header_fields_entirely(self, tmp_path: Path) -> None:
        """An entry using every second-schema spelling has zero ``header_fields`` issues."""
        entry = tmp_path / "example.md"
        _write_yaml_entry(
            entry,
            [
                'title: "Example"',
                'subtitle: "One-line disambiguation"',
                'resource_url: "https://example.com/example"',
                'date_created: "2026-06-01"',
                'date_last_reviewed: "2026-06-01"',
                'version_at_research: "1.0.0"',
                'license: "MIT"',
            ],
        )
        result = _run_json(entry)
        assert _issues_for(result, "header_fields") == []


class TestSecondSchemaFreshnessAliases:
    """``freshness_tracking`` accepts ``date_last_reviewed`` as Last Verified."""

    def test_date_last_reviewed_satisfies_last_verified(self, tmp_path: Path) -> None:
        """``date_last_reviewed`` resolves the Last Verified freshness requirement."""
        entry = tmp_path / "example.md"
        _write_yaml_entry(
            entry,
            [
                'title: "Example"',
                'resource_url: "https://example.com/example"',
                'date_created: "2026-06-01"',
                'date_last_reviewed: "2026-06-01"',
                'version_at_verification: "1.0.0"',
                'next_review: "2026-09-01"',
            ],
        )
        result = _run_json(entry)
        messages = [i["message"] for i in _issues_for(result, "freshness_tracking")]
        assert not any("Last Verified" in m for m in messages), messages

    def test_second_schema_entry_passes_freshness_tracking_entirely(self, tmp_path: Path) -> None:
        """An entry using every second-schema freshness spelling has zero ``freshness_tracking`` issues."""
        entry = tmp_path / "example.md"
        _write_yaml_entry(
            entry,
            [
                'title: "Example"',
                'resource_url: "https://example.com/example"',
                'date_created: "2026-06-01"',
                'date_last_reviewed: "2026-06-01"',
                'version_at_verification: "1.0.0"',
                'next_review: "2026-09-01"',
            ],
        )
        result = _run_json(entry)
        assert _issues_for(result, "freshness_tracking") == []
