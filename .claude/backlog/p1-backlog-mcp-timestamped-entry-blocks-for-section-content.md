---
name: 'Backlog MCP: Timestamped entry blocks for section content'
description: 'Each content entry in a section is wrapped in a timestamped, addressable block:'
metadata:
  topic: backlog-mcp-timestamped-entry-blocks-for-section-content
  source: User request
  added: '2026-03-11'
  priority: P1
  type: Feature
  status: in-progress
  issue: '#583'
  last_synced: '2026-03-12T12:47:33Z'
  groomed: '2026-03-11'
  plan: docs/superpowers/plans/2026-03-10-backlog-mcp-timestamped-entry-blocks.md
---

## Groomed (2026-03-11)

### Decision

### Entry Block Format (user, 2026-03-10)

Each content entry in a section is wrapped in a timestamped, addressable block:

```html
<div><sub>{ISO-8601-UTC-timestamp}</sub>

Markdown content here.
</div>
```

- `<sub>` is both the visible timestamp and the parseable entry ID — single element, no duplication
- `<div>` is the block wrapper — handles multi-paragraph content, code blocks, lists
- ISO 8601 strings sort lexicographically — natural chronological ordering
- Entry IDs are unique across the entire issue body

### API Design (user, 2026-03-10)

**Parameters added to backlog_update and backlog_groom:**
- `entry_id` (optional): target a specific block for overwrite. If unique across the issue, `section` is not required.

**Behavior matrix:**
- `section` + `content` (no entry_id) → append new timestamped block to section
- `section` + `content` + `entry_id` → overwrite that specific block within the section
- `entry_id` + `content` (no section) → overwrite block by ID anywhere in the issue (if unique)
- `entry_id` alone (no content) → reserved for future remove operation

**New tool:**
- `backlog_remove_entry(selector, entry_id)` — explicit entry deletion

**backlog_view enhancements:**
- Response includes `num_entries` per section
- Entry metadata: `id`, `preview` (first ~80 chars)
- Pagination operates on entry/block count, not line count

### Legacy Content Migration (user, 2026-03-10)

Existing section content without `<div><sub>` wrappers is not migrated proactively. On first new append to a section containing legacy content:
1. Wrap existing content in `<div><sub>{added_date}T00:00:00Z</sub>` (derived from item's `added` metadata field)
2. Append the new entry with current timestamp
3. Legacy entries become addressable via their assigned ID

### Affected Components (user, 2026-03-10)

- `backlog_update` — section+content write path
- `backlog_groom` — section+content write path
- `backlog_view` — response shape adds entry metadata
- `backlog_pull` — merge logic must respect entry block boundaries
- `operations.py` — new entry block parser/writer utilities
- `parsing.py` — regex patterns for `<div><sub>([^<]+)</sub>`

### Decision

### Struck Entry Format (user, 2026-03-10)

Entries are never deleted. They are struck through with a reason and collapsed:

```html
<div><sub>2026-03-10T22:18:04Z</sub>
<details><summary>struck: 2026-03-11T09:00:00Z — reason text here</summary>

Original content preserved.
</details>
</div>
```

Active vs struck determined by presence of `<details><summary>struck:` — no extra metadata field.

### groomed_content Deprecated (user, 2026-03-10)

`groomed_content` parameter removed from both `backlog_update` and `backlog_groom`. All writes go through entry blocks — no escape hatch that bypasses the system. Full section replacement uses `replace_section=True` which strikes all existing entries with a reason, then appends new content as a single timestamped block.

### parse_entries Interface (user, 2026-03-10)

```text
parse_entries(section_body, show="all", since=None, added_date="0000-00-00")
```

`show` accepts: `"all"`, `"last"`, `"first"`, `"struck"`, positive int (first N from span), negative int (last N from span).

`since` filters span start — only entries at or after that datetime considered before `show` applied.

Example: `parse_entries(body, show=-3, since="2026-03-10")` → 3 most recent active entries since March 10th.

### Duplicate Timestamp Handling (user, 2026-03-10)

Write time: always use bare ISO timestamp, no pre-check. Parse time: if duplicates found, assign `-0`, `-1` suffixes in document order. Caller targets specific one via suffixed form.

### Entry-Aware Merge in backlog_pull (user, 2026-03-10)

Merge rules: entry only on one side → keep. Both sides one struck → keep struck. Both active → keep longer. Both struck → keep later struck timestamp.

Diff output: git-diff style with full entry content (no truncation). `dry_run=True` returns diff without writing. `diff=True` applies merge and returns diff.

### Pagination Change (user, 2026-03-10)

`offset`/`limit` in `backlog_view` replaced with entry-based pagination. Breaking change — clean break, no backward compatibility.

## RT-ICA

**Goal**: Add timestamped, addressable entry blocks to backlog section content for audit trail and non-destructive history.

**Prerequisites**:
- Current operations.py section-write paths — AVAILABLE (agent discovery)
- Current parsing.py patterns — AVAILABLE (agent discovery)
- Design spec — AVAILABLE (docs/superpowers/specs/2026-03-10-backlog-mcp-timestamped-entry-blocks-design.md)
- Implementation plan — AVAILABLE (docs/superpowers/plans/2026-03-10-backlog-mcp-timestamped-entry-blocks.md)
- FastMCP 3.x tool patterns — AVAILABLE (existing server.py)
- Test fixtures — AVAILABLE (existing test files)

**Decision**: APPROVED — no missing inputs.
