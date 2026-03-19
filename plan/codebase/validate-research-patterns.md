# CLI and Validation Patterns: research-curator

**Analysis Date:** 2026-03-19
**Focus:** Validate mode CLI patterns, validation rules, and agent integration

---

## Typer CLI Flag Patterns

**Location:** `.claude/skills/research-curator/scripts/validate_research.py:368-374`

The validate mode uses PEP 723 inline script dependencies (lines 2-5) and Typer for CLI argument/option parsing:

```python
# PEP 723 inline dependencies
# /// script
# requires-python = ">=3.11"
# dependencies = ["typer>=0.21.0"]
# ///

_PATH_ARG = typer.Argument(Path("./research/"), help="File or directory to validate")
_JSON_OPT = typer.Option(False, "--json", help="Output machine-readable JSON")
_VERBOSE_OPT = typer.Option(False, "--verbose", help="Show per-file detail")

@app.command()
def main(path: Path = _PATH_ARG, output_json: bool = _JSON_OPT, verbose: bool = _VERBOSE_OPT) -> None:
    """Validate research entries against quality standards."""
```

**Conventions:**

- Options defined as module-level constants with `_` prefix (e.g., `_JSON_OPT`, `_VERBOSE_OPT`)
- `typer.Argument()` for positional args, default `Path("./research/")`
- `typer.Option()` for flags with `--flag-name` syntax
- Help text provided inline for all options
- Boolean flags default to `False`
- Type annotations on all parameters (`Path`, `bool`)

**Invocation from SKILL.md** (`validate_research.py` is invoked via line 313):

```bash
uv run .claude/skills/research-curator/scripts/validate_research.py --json ./research/{target}
```

Three command variations exist:
- Single file: `--json ./research/category/name.md`
- Directory: `--json ./research/` (full directory validation)
- No flags: plain text output with `--verbose` optional for per-file detail

---

## Issue TypedDict Schema

**Location:** `.claude/skills/research-curator/scripts/validate_research.py:20-27`

```python
class Issue(TypedDict):
    """A single validation issue found in a research entry."""

    check: str
    severity: str
    message: str
    line: int | None
```

**Fields:**

| Field | Type | Purpose | Examples |
|-------|------|---------|----------|
| `check` | `str` | Check function name that detected the issue | `"section_completeness"`, `"header_fields"`, `"empty_sections"`, `"access_dates"`, `"freshness_tracking"`, `"statistics_currency"`, `"url_format"`, `"formatting_suggestions"` |
| `severity` | `str` | Severity level determining action | `"error"` (must fix), `"warning"` (should fix), `"info"` (optional) |
| `message` | `str` | Human-readable description | `"Missing section: Overview"`, `"Reference without access date on line 5"` |
| `line` | `int \| None` | File line number where issue occurs, or `None` for document-level issues | `1`, `42`, or `None` for missing sections |

**How issues are emitted:** Each check function (lines 107-349) returns `list[Issue]` and all issues are aggregated:

```python
all_issues: list[Issue] = []
all_issues.extend(_check_section_completeness(sections))
all_issues.extend(_check_header_fields(header_lines))
all_issues.extend(_check_empty_sections(lines, sections))
# ... etc for all checks
```

---

## JSON Output Structure

**Location:** `.claude/skills/research-curator/scripts/validate_research.py:397-408`

Output structure when `--json` flag is set:

```python
result = {
    "summary": {
        "total": total,              # count of entries scanned
        "passed": passed,            # entries with status "pass" (zero errors)
        "errors": total_errors,      # sum of error-severity issues across all entries
        "warnings": total_warnings,  # sum of warning-severity issues across all entries
        "info": total_info,          # sum of info-severity issues across all entries
    },
    "entries": entries,  # list of per-file result dicts
}
```

Each entry in `entries` list:

```python
{
    "file": relative,         # path relative to research_root (e.g., "infrastructure/some-tool.md")
    "status": "pass" | "fail",  # "fail" if any error-severity issues; "pass" otherwise
    "issues": [               # list of Issue TypedDict dicts
        {
            "check": "section_completeness",
            "severity": "error",
            "message": "Missing section: Overview",
            "line": None
        },
        # ... more issues
    ]
}
```

**Status logic** (line 350-351):

```python
has_errors = any(i["severity"] == "error" for i in all_issues)
status = "fail" if has_errors else "pass"
```

Entry status is `"fail"` if ANY error-severity issue exists; otherwise `"pass"`. Warnings and info do not affect status.

---

## Plain Text vs JSON Output

**Plain text output** (lines 410-425):

When `output_json=False`:

```
Research Validation: {total} entries scanned
  ✓ {passed} passed
  ✗ {failed} failed ({total_errors} errors, {total_warnings} warnings)
  {total_warnings} warnings
```

With `--verbose`, adds:

```
✓ category/resource-name.md
  ERROR: Missing section: Overview
  WARNING: Reference without access date on line 10
```

**JSON output** (lines 397-408):

When `output_json=True`, outputs compact JSON with no pretty-printing except `indent=2` for readability.

Exit code behavior (lines 427-429):

```python
if total_errors > 0:
    sys.exit(1)
sys.exit(0)
```

Exit code `1` only if ANY error-severity issues found; otherwise `0` (warnings and info don't affect exit code).

---

## Check Function Signature Pattern

**Location:** `.claude/skills/research-curator/scripts/validate_research.py:107-349`

All check functions follow this pattern:

```python
def _check_CHECKNAME(lines: list[str], sections: dict[str, tuple[int, int]]) -> list[Issue]:
    """Check description.

    Returns:
        List of ``Issue`` dicts, one per detected issue. Empty list when check passes.
    """
    issues: list[Issue] = []

    # detection logic
    if condition:
        issues.append({
            "check": "check_name_identifier",
            "severity": "error" | "warning" | "info",
            "message": "Human-readable message",
            "line": line_number_or_none,
        })

    return issues
```

**Naming:** `_check_{functionality}` with lowercase underscore-separated name (e.g., `_check_section_completeness`, `_check_empty_sections`).

**Parameters vary by check:**

| Check | Parameters | Purpose |
|-------|-----------|---------|
| `_check_section_completeness` | `sections: dict` | Verify required sections exist |
| `_check_header_fields` | `header_lines: list[str]` | Verify header block fields |
| `_check_empty_sections` | `lines: list[str]`, `sections: dict` | Detect empty section bodies |
| `_check_access_dates` | `lines: list[str]`, `sections: dict` | Verify URLs have access dates |
| `_check_freshness_tracking` | `lines: list[str]`, `sections: dict` | Verify freshness fields exist |
| `_check_statistics_currency` | `lines: list[str]`, `sections: dict`, `today: date` | Detect stale dates in Key Statistics |
| `_check_url_format` | `lines: list[str]` | Detect malformed URLs |
| `_check_formatting_suggestions` | `lines: list[str]` | Detect markdown formatting issues |

**Return type:** Always `list[Issue]` — empty list means check passed.

---

## URL Detection Pattern

**Location:** `.claude/skills/research-curator/scripts/validate_research.py:56-58`

Two regex patterns for URL matching:

```python
URL_PATTERN = re.compile(r"https?://[^\s>)\]]+")
ACCESS_DATE_PATTERN = re.compile(r"(?:accessed\s+\d{4}-\d{2}-\d{2}|\(\d{4}-\d{2}-\d{2}\))")
DATE_PATTERN = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
```

**Usage in checks:**

- `URL_PATTERN.findall(line)` in `_check_access_dates` (line 192) — extracts all `http://` and `https://` URLs from a line
- `ACCESS_DATE_PATTERN.search(line)` (line 193) — validates that a URL has a trailing access date in format `accessed YYYY-MM-DD` or `(YYYY-MM-DD)`
- `DATE_PATTERN.finditer(line)` in `_check_statistics_currency` (line 251) — finds all ISO date strings in Key Statistics section to check staleness

---

## Section Parsing Pattern

**Location:** `.claude/skills/research-curator/scripts/validate_research.py:61-104`

Helper functions parse markdown structure:

```python
def _parse_sections(lines: list[str]) -> dict[str, tuple[int, int]]:
    """Return mapping of section heading -> (start_line, end_line) (1-indexed)."""
    # ... finds all ## headings, records start/end line numbers
    return sections

def _get_header_block(lines: list[str]) -> tuple[list[str], int]:
    """Return lines before the first --- separator and the line count."""
    # ... returns header lines up to YAML separator
    return header_lines, i

def _section_content(lines: list[str], start: int, end: int) -> str:
    """Extract content between section heading and next heading/separator (0-indexed range)."""
    # ... joins non-heading lines, strips empty content
    return content
```

**Markdown structure assumed:**

```markdown
---
Header metadata
---

## Section Name

Content here

## Next Section

More content
```

Lines 1-indexed throughout the codebase for user-facing error messages.

---

## Required Sections and Aliases

**Location:** `.claude/skills/research-curator/scripts/validate_research.py:31-54`

Required sections (exact names):

```python
REQUIRED_SECTIONS = [
    "Overview",
    "Problem Addressed",
    "Key Statistics",
    "Key Features",
    "Technical Architecture",
    "Installation & Usage",
    "Relevance to Claude Code Development",
    "References",
    "Freshness Tracking",
]
```

Section aliases accepted as substitutes:

```python
SECTION_ALIASES: dict[str, list[str]] = {
    "Installation & Usage": ["Installation and Usage"]
}
```

Aliases allow flexibility; if primary name is missing, check looks for aliases (line 120-121).

Required header fields:

```python
REQUIRED_HEADER_FIELDS = ["Research Date", "Source URL", "Version at Research", "License"]
```

Freshness Tracking fields:

```python
FRESHNESS_REQUIRED_FIELDS = ["Last Verified", "Version at Verification", "Next Review Recommended"]

FRESHNESS_ALIASES: dict[str, list[str]] = {
    "Last Verified": ["Research Date"],
    "Next Review Recommended": ["Next Review"],
}
```

---

## Validation Rules Reference

**Location:** `.claude/skills/research-curator/references/validation-rules.md`

Validation rules are defined externally and referenced from SKILL.md (line 285). Severity mapping (lines 9-25):

**Error severity** (structural violations — auto-fixable via agent):
- `section_completeness` — missing required sections
- `header_fields` — missing required header block fields
- `empty_sections` — sections exist but have no content

**Warning severity** (quality issues — reported but not auto-fixed):
- `access_dates` — URLs in References lack access dates
- `freshness_tracking` — Freshness Tracking section missing fields
- `statistics_currency` — dates in Key Statistics older than 6 months
- `url_format` — malformed URLs missing `http://` or `https://`
- `cross_references_absent` — no Cross-References section (for entries created on/after 2026-03-12)

**Info severity** (optional observations):
- `formatting_suggestions` — markdown formatting issues (MD031 blank lines around code fences)

---

## Agent Integration: Fix Mode

**Location:** `.claude/agents/research-curator.md:431-437`

The agent supports `--fix` mode to repair validation issues:

```python
### `--fix` Mode (fix validation issues)

1. Receive the specific issues to fix (from validate_research.py output).
2. READ the entry file.
3. Fix ONLY the specified issues. Do NOT rewrite sections that are not flagged.
4. Return an itemized list of each fix applied.
```

**Orchestrator delegation pattern** (from SKILL.md lines 320-325):

```bash
prompt: "--fix ./research/{category}/{name}.md
Issues to fix (from validator JSON):
  - {exact issue text from JSON}
  - {exact issue text from JSON}"
```

Orchestrator passes the exact error message strings from the JSON output — not paraphrases. Agent receives structured issue list and applies targeted fixes.

**Error auto-fix workflow** (SKILL.md lines 303-307):

- Run validator script with `--json` flag
- Parse JSON output, extract error-severity issues
- Spawn `@research-curator` agents in waves of 5 (like batch mode)
- Each agent receives `--fix` flag plus the exact issue list from JSON
- Agents apply fixes, report what was fixed
- Warnings and info issues are reported to user but not auto-fixed

---

## Data Flow: Validation → Fix

```
validate_research.py --json
    ↓
    Outputs JSON with "entries" list containing Issue dicts
    ↓
SKILL.md orchestrator parses JSON output
    ↓
    Filters for severity == "error"
    ↓
    Extracts exact message text from each error Issue dict
    ↓
Spawns @research-curator agent with --fix flag
    ↓
    Agent reads entry file
    ↓
    Fixes only the specified issues (by matching message text)
    ↓
    Reports itemized fixes applied
    ↓
SKILL.md reports summary counts (exact counts from JSON, exact fix descriptions from agent)
```

---

## File Collection Pattern

**Location:** `.claude/skills/research-curator/scripts/validate_research.py:356-365`

```python
def collect_files(path: Path) -> list[Path]:
    """Collect markdown files to validate, excluding README.md.

    Returns:
        Sorted list of markdown file paths.
    """
    if path.is_file():
        return [path] if path.suffix == ".md" and path.name != "README.md" else []
    files = sorted(path.rglob("*.md"))
    return [f for f in files if f.name != "README.md"]
```

**Logic:**
- If path is a file: validate only if `.md` and not `README.md`
- If path is a directory: glob all `*.md` files recursively, exclude `README.md`
- Always return sorted list (ensures deterministic ordering)

---

## Freshness Tracking Constants

**Location:** `.claude/skills/research-curator/scripts/validate_research.py:233-264`

Staleness threshold for Key Statistics section:

```python
cutoff = today - timedelta(days=180)
# ... flags any date older than 6 months
```

If a date in Key Statistics is before the cutoff, warning is emitted with message:

```
"Stale date {date_str} in Key Statistics (older than 6 months)"
```

Today's date sourced from:

```python
today = datetime.now(tz=UTC).date()
```

---

## Summary Report Calculations

**Location:** `.claude/skills/research-curator/scripts/validate_research.py:391-395`

Summary statistics calculated from aggregated issues:

```python
total = len(entries)
passed = sum(1 for e in entries if e["status"] == "pass")
total_errors = sum(1 for e in entries for i in e["issues"] if i["severity"] == "error")
total_warnings = sum(1 for e in entries for i in e["issues"] if i["severity"] == "warning")
total_info = sum(1 for e in entries for i in e["issues"] if i["severity"] == "info")
```

- `passed` count: entries with `status == "pass"` (only entries with zero errors)
- `total_errors`, `total_warnings`, `total_info`: sums across all issues in all entries
- Failed count computed as `total - passed` for display

---

_Pattern analysis completed: 2026-03-19_
