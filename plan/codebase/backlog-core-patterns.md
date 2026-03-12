# Backlog Core Patterns and Conventions

**Analysis Date:** 2026-03-12
**Package:** backlog_core
**Focus:** Field population patterns, status handling, model conventions

## BacklogItem Model and Field Population

**Location:** `.claude/skills/backlog/backlog_core/models.py:140-166`

The `BacklogItem` model uses Pydantic `BaseModel` with all fields defaulting to empty/falsy values to support incremental construction during parsing:

```python
class BacklogItem(BaseModel):
    """Parsed backlog item from a per-item file.

    Replaces the untyped ``dict`` that was previously passed between functions.
    All fields default to empty/falsy values so items can be constructed
    incrementally during parsing.
    """

    title: str = ""
    description: str = ""
    source: str = "Not specified"
    added: str = ""
    priority: str = ""
    item_type: str = "Feature"
    issue: str = ""
    plan: str = ""
    research_first: str = ""
    files: str = ""
    suggested_location: str = ""

    section: str = ""
    file_path: str = ""
    skip: bool = False
    groomed: str = ""
    last_synced: str = ""
    raw_body: str = ""
```

**Key Pattern:** Fields are organized into three groups:
1. **Content fields** (top): title, description, source, added, priority, item_type, issue, plan, research_first, files, suggested_location
2. **Metadata fields** (middle): section, file_path, skip, groomed, last_synced
3. **Raw body** (bottom): raw_body

**Status handling observation:** `BacklogItem` does NOT have a `status` field currently. The `skip` boolean field is derived from status during parsing (line 243 of parsing.py: `skip=_fm_str(fm, meta, "status").lower() in {"done", "resolved"}`).

## Field Population Pattern in parse_item_file()

**Location:** `.claude/skills/backlog/backlog_core/parsing.py:220-247`

The `parse_item_file()` function demonstrates a consistent field-resolution pattern:

```python
def parse_item_file(text: str, path: Path) -> BacklogItem:
    """Parse a single per-item backlog file (frontmatter + body). Handles both flat and research-style metadata block.

    Returns:
        BacklogItem with parsed fields from frontmatter and body.
    """
    if not text.startswith("---"):
        return BacklogItem(raw_body=text)
    fm, meta, body = _parse_frontmatter(text)
    # Research-style: name, description, metadata.*
    # Flat (legacy): title, source, added, ...
    plan_raw = _fm_str(fm, meta, "plan")
    groomed = _fm_str(fm, meta, "groomed")
    if not groomed and "## Groomed" in body:
        groomed = "true"
    return BacklogItem(
        title=str(fm.get("name") or fm.get("title") or ""),
        description=str(fm.get("description") or ""),
        source=_fm_str(fm, meta, "source"),
        added=_fm_str(fm, meta, "added"),
        priority=_fm_str(fm, meta, "priority"),
        issue=_fm_str(fm, meta, "issue"),
        plan="" if plan_raw.upper() == "N/A" else plan_raw,
        skip=_fm_str(fm, meta, "status").lower() in {"done", "resolved"},
        groomed=groomed,
        last_synced=_fm_str(fm, meta, "last_synced"),
        raw_body=body,
    )
```

### Field Resolution Pattern

**`_fm_str()` helper** (line 191-197):
```python
def _fm_str(fm: dict[str, object], meta: dict[str, str], key: str, fm_key: str = "") -> str:
    """Resolve a string field from metadata dict with frontmatter fallback.

    Returns:
        Resolved string value, or empty string if not found.
    """
    return str(meta.get(key) or fm.get(fm_key or key) or "")
```

Pattern: `meta.get(key) or fm.get(fm_key or key) or ""` — checks nested metadata dict first, falls back to flat frontmatter, then empty string.

### Frontmatter Parsing

**`_parse_frontmatter()` helper** (line 200-217):
- Tries `loads_frontmatter()` first (from `frontmatter_utils` module)
- Falls back to manual split on `---` for malformed YAML
- Returns tuple: `(fm_dict, meta_dict, body_text)`
- Extracts `metadata` key from frontmatter if present (nested format)
- Stringifies nested dict values to support both flat and research-style formats

### Status → Skip Conversion

Currently, status is resolved during parsing but only the boolean `skip` field is stored:

```python
skip=_fm_str(fm, meta, "status").lower() in {"done", "resolved"}
```

This pattern means:
- Any status value of "done" or "resolved" (case-insensitive) sets `skip=True`
- Other status values (`"open"`, etc.) result in `skip=False`
- The original status string is NOT stored on `BacklogItem`

## Status Field in Related Models

Three other models already have explicit `status` fields:

### IssueStatus
**Location:** `.claude/skills/backlog/backlog_core/models.py:197-201`

```python
class IssueStatus(BaseModel):
    """GitHub issue status and milestone from batch fetch."""

    status: str = ""
    milestone: str = ""
```

Used to store status fetched from GitHub API (open/closed).

### IssueLocalFields
**Location:** `.claude/skills/backlog/backlog_core/models.py:233-242`

```python
class IssueLocalFields(BaseModel):
    """Backlog-relevant fields extracted from a PyGithub Issue object."""

    title: str = ""
    body: str = ""
    priority: str = "P1"
    item_type: str = "Feature"
    status: str = "open"
    updated_at: str = ""
    milestone: str = ""
```

Stores `status` with default `"open"`. Used when syncing GitHub issues to local.

### ViewItemResult
**Location:** `.claude/skills/backlog/backlog_core/models.py:212-230`

```python
class ViewItemResult(BaseModel):
    """Result of viewing a single backlog item, optionally enriched with GitHub data."""

    title: str = ""
    priority: str = ""
    description: str = ""
    source: str = ""
    added: str = ""
    plan: str = ""
    issue: str = ""
    file_path: str = ""
    groomed: bool = False
    status: str = ""
    number: int | None = None
    state: str = ""
    body: str = ""
    labels: list[str] = Field(default_factory=list)
    milestone: str = ""
    sections: dict[str, dict[str, object]] = Field(default_factory=dict)
```

`status` field defaults to empty string. This is the "view" response model returned by operations.

## view_result_from_local_item() Implementation

**Location:** `.claude/skills/backlog/backlog_core/parsing.py:784-815`

The current implementation demonstrates the redundant file re-read issue:

```python
def view_result_from_local_item(item: BacklogItem) -> ViewItemResult:
    """Build view result from a local backlog item.

    Returns:
        ViewItemResult with title, priority, issue, plan, file_path, groomed, and
        optionally description/source/added/status from the per-item file.
    """
    result = ViewItemResult(
        title=item.title,
        priority=item.section,
        issue=item.issue,
        plan=item.plan,
        file_path=item.file_path,
        groomed=bool(item.groomed),
    )
    # Use fields already parsed on BacklogItem instead of re-reading the file
    result.description = item.description or ""
    result.source = item.source or ""
    result.added = item.added or ""
    if item.raw_body:
        result.body = item.raw_body
    # status is not on BacklogItem — extract from frontmatter metadata if file exists
    fp = item.file_path
    if fp and Path(fp).exists():
        raw = Path(fp).read_text(encoding="utf-8")
        post = loads_frontmatter(raw)
        fm_raw = post.metadata if hasattr(post, "metadata") else (post[0] if isinstance(post, tuple) else {})
        fm: dict[str, str] = dict(fm_raw) if isinstance(fm_raw, dict) else {}
        meta_raw = fm.get("metadata", {})
        meta: dict[str, str] = dict(meta_raw) if isinstance(meta_raw, dict) else {}
        result.status = str(meta.get("status", fm.get("status", "")))
    return result
```

### Current Behavior

**Lines 791-804:** Fields already available on `BacklogItem` are used directly (description, source, added, raw_body).

**Lines 805-814:** **File re-read occurs here:** The function re-reads the file from disk to extract the `status` field because:
1. `BacklogItem` has no `status` field
2. Only `skip` boolean is available (doesn't preserve original status value)
3. The file is re-opened and re-parsed with `loads_frontmatter()` to extract the status

### Inefficiency Pattern

The redundant file I/O:
- File is read once in `parse_item_file()` to extract all fields
- File is read AGAIN in `view_result_from_local_item()` to extract status
- Both use the same parsing pattern (`_parse_frontmatter()` → frontmatter_utils)

### Defensive Tuple Handling

Line 810 shows defensive unpacking:
```python
fm_raw = post.metadata if hasattr(post, "metadata") else (post[0] if isinstance(post, tuple) else {})
```

This suggests `loads_frontmatter()` can return either:
- Object with `.metadata` attribute, or
- Tuple (legacy format), or
- Dict-like fallback

## Testing Patterns

**Location:** `.claude/skills/backlog/tests/test_backlog_core_parsing.py`

### Test Data Structure

Uses multi-format fixtures to cover both parsing paths:

```python
# Nested-metadata format (produced by build_backlog_frontmatter)
_NESTED_META_FRONTMATTER = """\
---
name: My Test Item
description: A test description
metadata:
  source: test-source
  added: '2026-01-01'
  priority: P1
  type: Feature
  status: open
  topic: my-test-item
---
Body content here.
"""

# Legacy flat format
_FLAT_FRONTMATTER = """\
---
title: Legacy Title
source: legacy-source
added: '2025-12-01'
priority: P0
status: open
---
Legacy body.
"""
```

### Test Naming Convention

Functions use descriptive names following pattern `test_[function]_[scenario]_[expected_outcome]`:
- `test_parse_item_file_nested_meta_sets_title`
- `test_parse_item_file_flat_priority_accessible`
- `test_parse_item_file_flat_done_status_sets_skip_true`

### Status-to-Skip Conversion Testing

Tests verify status strings convert to boolean:
- `test_parse_item_file_flat_done_status_sets_skip_true` — verifies "done" → `skip=True`
- `test_parse_item_file_flat_open_status_sets_skip_false` — verifies other values → `skip=False`

## Conventions

### 1. Default Field Values Pattern

All Pydantic models use sensible defaults:
- String fields: `""`
- Bool fields: `False`
- Collection fields: `Field(default_factory=list)` or `Field(default_factory=dict)`
- One exception: `BacklogItem.source` defaults to `"Not specified"`

### 2. Field Resolution Priority

When resolving optional fields from two sources (nested metadata + flat frontmatter):
1. Check nested `metadata` dict first
2. Fall back to flat frontmatter key
3. Fall back to empty string or default

### 3. Boolean Status Encoding

Status strings are converted to booleans during parsing rather than storing the original string. This pattern:
- Simplifies callers (boolean checks instead of string comparisons)
- Loses the original status value (requires re-reading file to preserve it)

### 4. Raw Body Preservation

All parsing functions preserve `raw_body` (the unstructured body text) to allow:
- Round-trip preservation of sections not explicitly parsed
- Section detection post-parsing (e.g., checking `"## Groomed" in body`)

### 5. File Path Storage

`file_path` is stored as string (not Path object) on `BacklogItem` for:
- Serializability (JSON compatibility with MCP responses)
- Consistency with other string fields
- Converted to `Path` only when used for I/O

### 6. Incremental Construction

`BacklogItem` is designed for incremental field population:
- All fields have defaults
- Can construct partially and fill fields later
- See `parse_backlog_from_directory()` which sets `section`, `file_path`, `skip` fields AFTER initial parsing

### 7. Fallback Chain for Optional Fields

The `_fm_str()` pattern shows consistent fallback handling:
```python
str(meta.get(key) or fm.get(fm_key or key) or "")
```

Order: nested metadata → flat key → empty string. Used for: source, added, priority, issue, plan, groomed, last_synced.

### 8. Groomed Field Multi-Source Detection

The `groomed` field demonstrates multi-path detection:

```python
groomed = _fm_str(fm, meta, "groomed")  # Try frontmatter first
if not groomed and "## Groomed" in body:  # Fallback: check body
    groomed = "true"
```

Allows grooming status from either frontmatter or markdown section presence.

### 9. Plan Field Normalization

The `plan` field normalizes "N/A" to empty string:

```python
plan="" if plan_raw.upper() == "N/A" else plan_raw
```

This allows frontmatter to explicitly indicate "no plan" while still normalizing to empty for consistency.

## Summary of Key Patterns

| Pattern | Location | Purpose |
|---------|----------|---------|
| Field defaults to empty/false | models.py:140-166 | Enable incremental construction |
| `_fm_str()` helper for resolution | parsing.py:191-197 | Unified fallback chain |
| Status → skip boolean conversion | parsing.py:243 | Simplify caller logic |
| Raw body preservation | parsing.py:246 | Enable round-trip and section detection |
| File re-read in view_result | parsing.py:805-814 | Workaround: status not on BacklogItem |
| Multi-format test fixtures | test_backlog_core_parsing.py | Cover both legacy and modern formats |
| Incremental section assignment | parsing.py:284-291 | Derive section from filename, override with metadata |

---

*Patterns and conventions analysis: 2026-03-12*
