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
from typing import Final

_REPO_ROOT = Path(__file__).parents[2]
_SCRIPTS_DIR = _REPO_ROOT / ".claude" / "skills" / "research-curator" / "scripts"
_VALIDATE_SCRIPT = _SCRIPTS_DIR / "validate_research.py"

# Per AGENTS.md's "Bounded subprocess execution" gotcha: wrap external commands that could hang
# (uv resolving PEP 723 deps, or a spawned child left running) so a timeout kills the whole
# process group instead of stalling the pytest worker indefinitely.
_RUN_BOUNDED: Final = (
    "uv",
    "run",
    "--script",
    str(_REPO_ROOT / "scripts" / "run_bounded.py"),
    "--timeout-seconds",
    "60",
    "--",
)


def _uv_path() -> str:
    """Locate the uv binary, raising RuntimeError if not found."""
    found = shutil.which("uv")
    if found is None:
        raise RuntimeError("uv binary not found on PATH — cannot run CLI tests")
    return found


def _run_json(path: Path) -> dict:
    """Run validate_research.py main --json on a single file and parse the result."""
    cmd = [*_RUN_BOUNDED, _uv_path(), "run", "--script", str(_VALIDATE_SCRIPT), "main", "--json", str(path)]
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


def _write_yaml_entry_verified_only(path: Path, *, research_date: str, cross_references: bool) -> None:
    """Write a YAML-frontmatter entry with a legacy ``metadata.verified`` date and no body date at all.

    Mirrors the corpus shape Codex found still regressed after the body-date
    fallback: no ``## Freshness Tracking`` section in the body, so the fallback
    also returns ``None`` unless ``verified`` itself is a recognized alias of
    ``last_verified``.
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
"""
    if cross_references:
        frontmatter += """
## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Other](../other/other.md) | other | related |
"""
    path.write_text(frontmatter, encoding="utf-8")


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


class TestYamlEntryVerifiedOnlyFallback:
    """A YAML entry with only ``metadata.verified`` and no body date still gets the exemption.

    Regression guard for the second false positive Codex found on PR #3506,
    reproduced against the real corpus at ``research/agent-frameworks/agno.md``
    (``metadata.verified: "2026-01-31"``, no body Freshness Tracking section):
    the body-date fallback alone doesn't help when there is no body date to
    fall back to -- ``verified`` itself must be recognized as an alias.
    """

    def test_pre_cutoff_verified_only_exempts_yaml_entry(self, tmp_path: Path) -> None:
        """A pre-cutoff ``metadata.verified`` date exempts the entry with no body date at all."""
        entry = tmp_path / "example.md"
        _write_yaml_entry_verified_only(entry, research_date="2026-01-15", cross_references=False)
        result = _run_json(entry)
        assert result["entries"][0]["format"] == "yaml_frontmatter"
        assert _issues_for(result, "cross_references_absent") == []

    def test_post_cutoff_verified_only_still_warns_yaml_entry(self, tmp_path: Path) -> None:
        """The ``verified`` alias must not suppress the warning for a post-cutoff entry."""
        entry = tmp_path / "example.md"
        _write_yaml_entry_verified_only(entry, research_date="2026-06-01", cross_references=False)
        result = _run_json(entry)
        issues = _issues_for(result, "cross_references_absent")
        assert len(issues) == 1
        assert issues[0]["severity"] == "warning"


def write_yaml_entry_second_schema_only(path: Path, *, research_date: str, cross_references: bool) -> None:
    """Write a YAML-frontmatter entry using the second historical schema's flat date keys.

    Mirrors the live corpus shape (e.g. ``research/coding-agents/claude-codepro.md``):
    root-level ``date_created``/``date_last_reviewed`` keys (not nested under
    ``metadata``, and not the first schema's ``research_date``/``last_verified``
    spellings) with no body ``## Freshness Tracking`` section, so resolution
    depends entirely on ``reference_date_yaml`` recognizing ``date_last_reviewed``
    as an alias.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    frontmatter = f"""\
---
title: "Example"
category: "developer-tools"
resource_url: "https://example.com/example"
date_created: "{research_date}"
date_last_reviewed: "{research_date}"
status: published
---

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

- [Example](https://example.com) (accessed {research_date})
"""
    if cross_references:
        frontmatter += """
## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Other](../other/other.md) | other | related |
"""
    path.write_text(frontmatter, encoding="utf-8")


class TestYamlEntrySecondSchemaDateAliases:
    """A YAML entry using the second schema's ``date_last_reviewed``/``date_created`` keys.

    Regression guard for the deferred item recorded on PR #3508: once
    ``_YAML_HEADER_ALIASES``/``_YAML_FRESHNESS_ALIASES`` accept
    ``date_created``/``date_last_reviewed`` for field-completeness checks,
    ``reference_date_yaml``'s own precedence list must also recognize those
    spellings, or the ``cross_references_absent`` exemption never resolves a
    date for entries using the second schema with no body Freshness Tracking
    section.
    """

    def test_pre_cutoff_date_last_reviewed_exempts_yaml_entry(self, tmp_path: Path) -> None:
        """A pre-cutoff ``date_last_reviewed`` exempts the entry with no body date at all."""
        entry = tmp_path / "example.md"
        write_yaml_entry_second_schema_only(entry, research_date="2026-01-15", cross_references=False)
        result = _run_json(entry)
        assert result["entries"][0]["format"] == "yaml_frontmatter"
        assert _issues_for(result, "cross_references_absent") == []

    def test_post_cutoff_date_last_reviewed_still_warns_yaml_entry(self, tmp_path: Path) -> None:
        """The ``date_last_reviewed`` alias must not suppress the warning for a post-cutoff entry."""
        entry = tmp_path / "example.md"
        write_yaml_entry_second_schema_only(entry, research_date="2026-06-01", cross_references=False)
        result = _run_json(entry)
        issues = _issues_for(result, "cross_references_absent")
        assert len(issues) == 1
        assert issues[0]["severity"] == "warning"

    def test_pre_cutoff_date_created_alone_exempts_yaml_entry(self, tmp_path: Path) -> None:
        """``date_created`` alone (no ``date_last_reviewed``) also resolves and exempts a pre-cutoff entry."""
        entry = tmp_path / "example.md"
        frontmatter = """\
---
title: "Example"
category: "developer-tools"
resource_url: "https://example.com/example"
date_created: "2026-01-15"
status: published
---

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

- [Example](https://example.com) (accessed 2026-01-15)
"""
        entry.parent.mkdir(parents=True, exist_ok=True)
        entry.write_text(frontmatter, encoding="utf-8")
        result = _run_json(entry)
        assert result["entries"][0]["format"] == "yaml_frontmatter"
        assert _issues_for(result, "cross_references_absent") == []


def _write_yaml_entry_stale_frontmatter(path: Path, *, frontmatter_date: str, body_date: str) -> None:
    """Write a YAML entry whose frontmatter ``verified`` predates a fresher body Last Verified.

    Mirrors the corpus shape Codex found on PR #3506's third review round (e.g.
    ``research/context-management/claude-mem.md``: frontmatter ``2026-01-31``,
    body ``2026-05-08``): a rerun updated the body Freshness Tracking section
    but not the legacy frontmatter field, so resolving frontmatter first would
    use the stale, pre-cutoff date to wrongly exempt an entry that is actually
    past the cutoff.
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
  verified: "{frontmatter_date}"
---

# Example

"""
    path.write_text(frontmatter + _body(body_date, cross_references=False), encoding="utf-8")


class TestYamlEntryPrefersBodyOverStaleFrontmatter:
    """The body Freshness Tracking date wins over a stale frontmatter ``verified`` value.

    Regression guard for the false negative Codex found on PR #3506's third
    review round: checking frontmatter before the body let a rerun that only
    updated the body silently keep the old, pre-cutoff exemption.
    """

    def test_post_cutoff_body_date_overrides_pre_cutoff_frontmatter(self, tmp_path: Path) -> None:
        """A pre-cutoff frontmatter date must not exempt an entry the body shows is post-cutoff."""
        entry = tmp_path / "example.md"
        _write_yaml_entry_stale_frontmatter(entry, frontmatter_date="2026-01-31", body_date="2026-05-08")
        result = _run_json(entry)
        issues = _issues_for(result, "cross_references_absent")
        assert len(issues) == 1
        assert issues[0]["severity"] == "warning"


def _write_text_entry_alias_body_date(path: Path, *, header_date: str, body_date: str) -> None:
    """Write a text-header entry whose body Freshness Tracking uses the ``Research Date`` alias.

    Mirrors the corpus shape Codex found on PR #3506's fourth review round:
    ``FRESHNESS_ALIASES`` accepts ``Research Date`` inside ``## Freshness
    Tracking`` as satisfying the ``Last Verified`` field, but the regex that
    resolves the cutoff-exemption date only matched the literal ``Last
    Verified`` label, so a refreshed entry using the alias fell back to the
    older header date instead of the current body one.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    header = f"""\
# Example

**Research Date**: {header_date}
**Source URL**: https://example.com/example
**Version at Research**: 1.0.0
**License**: MIT

---

"""
    body = _body(body_date, cross_references=False).replace(
        f"- **Last Verified**: {body_date}", f"- **Research Date**: {body_date}"
    )
    path.write_text(header + body, encoding="utf-8")


class TestTextEntryRecognizesFreshnessAliasLabel:
    """The body Freshness Tracking date resolves even when it uses the ``Research Date`` alias label.

    Regression guard for the false-exemption Codex found on PR #3506's fourth
    review round: the date-resolution regex must accept the same
    ``FRESHNESS_ALIASES`` labels ``_check_freshness_tracking_text`` already
    accepts for field completeness, or a refreshed entry using the alias is
    silently exempted using its stale header date.
    """

    def test_post_cutoff_alias_body_date_overrides_pre_cutoff_header(self, tmp_path: Path) -> None:
        """A pre-cutoff header date must not exempt an entry whose aliased body date is post-cutoff."""
        entry = tmp_path / "example.md"
        _write_text_entry_alias_body_date(entry, header_date="2026-01-15", body_date="2026-06-01")
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
