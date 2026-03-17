# Backlog Item Matching Patterns

Document of HOW backlog item matching works TODAY across the codebase. Maps existing patterns, conventions, and constraints — not proposed designs.

Extracted from: `item-schema.md` (reference documentation), SKILL.md consumer files (work-backlog-item, complete-implementation), MCP tool registrations, and CLI source inspection.

---

## 1. Backlog Item Data Model

### Frontmatter Schema (Per-Item File)

Canonical schema from `.claude/skills/backlog/references/item-schema.md`. Each backlog item file is stored as `.claude/backlog/{priority}-{slug}.md`.

```yaml
---
name: string                                    # Full item title (matches GitHub issue title)
description: string                             # One-sentence problem/goal summary
metadata:
  topic: string                                 # Slug derived from title (kebab-case, max 60 chars)
  source: string                                # What triggered this item
  added: YYYY-MM-DD                             # Creation date
  priority: P0|P1|P2|Ideas                      # Priority tier (governs filename prefix)
  type: Feature|Bug|Refactor|Docs|Chore         # Item type/category
  status: needs-grooming|groomed|blocked|...    # State machine (see below)
  groomed: YYYY-MM-DD (optional)                # Set when all 7 grooming sections present
  issue: '#N' (optional)                        # GitHub issue number (string with # prefix)
  milestone: integer (optional)                 # GitHub milestone number
  plan: string (optional)                       # Relative path to SAM task file
---
```

**Field Ownership & Lifecycle:**

| Field | Written By | Updated By | Notes |
|-------|-----------|-----------|-------|
| `name`, `description`, `metadata.topic` | `create-backlog-item` + backlog script | — | Set at creation |
| `metadata.source`, `metadata.added` | `create-backlog-item` + backlog script | — | Set at creation |
| `metadata.priority`, `metadata.type` | `create-backlog-item` | — | Set at creation |
| `metadata.status` | All skills on state transitions | — | State machine field (see Section 2) |
| `metadata.groomed` | `groom-backlog-item` | — | Set only when all 7 grooming sections present |
| `metadata.issue` | `backlog_sync` MCP tool | — | Set on GitHub issue creation |
| `metadata.milestone` | `group-items-to-milestone` skill | — | Set on milestone assignment |
| `metadata.plan` | `work-backlog-item` skill | — | Set when SAM task file created |

### Body Sections (Canonical Order)

Sections appear in this order; populated incrementally after creation:

```
1. Description (prose)
2. Acceptance Criteria (bullet list)
3. Research First (optional questions)
4. Suggested Location (optional codebase path)
5. Fact-Check (V/R/I counts — by groom-backlog-item Step 4)
6. RT-ICA (information completeness assessment — by groom-backlog-item Step 5b)
7. Groomed (subsections: Reproducibility, Dependencies, Skills, Agents, Prior Work, etc.)
8. Acceptance Criteria Verification (per-criterion PASS/FAIL with file:line evidence)
```

**Groomed State Definition:** An item is **fully groomed** only when ALL 7 sections (Fact-Check through Prior Work) are present. `metadata.groomed` MUST NOT be set until all 7 exist.

---

## 2. Matching Points in the Codebase

### 2.1 Consumer: `work-backlog-item` Skill (Step 1)

**File:** `.claude/skills/work-backlog-item/SKILL.md`

**Matching Entry Point:** Step 1 — "Find the Backlog Item"

**Algorithm:**
```
1. Call mcp__backlog__backlog_list() tool with no filters initially
2. Search the `title` field of each item in returned JSON array
3. Match criterion: case-insensitive substring match
   - Title parameter = <item_ref/> (positional args joined)
   - Zero matches → interactive: offer to create; AUTO_MODE: invoke create-backlog-item --auto
   - Multiple matches → interactive: list and ask user; AUTO_MODE: log, pick first match
   - One match → proceed to Step 2 (Extract Item Fields)
4. Record the priority section (P0, P1, P2, Ideas) the item belongs to
```

**AUTO_MODE Special Case:**
- When invoked as `--auto` with NO title given (`<item_ref/>` empty), apply auto-select rule:
  - Scan P0 section for first open item
  - If none found, scan P1 section for first open item
  - Use title of first found item
  - Skip items with `status: done` or `status: resolved` (already filtered by `backlog_list`)

**Extracted Fields (from MCP returned JSON):**

From JSON response:
- `title` (required)
- `plan` (optional)
- `section` (priority: P0, P1, P2, Ideas)
- `issue` (optional GitHub issue number)
- `groomed` (boolean)
- `file_path` (local per-item file path)

From per-item file (read if available):
- `description` (required)
- `metadata.source` (optional)
- `metadata.added` (optional)
- `research_first` (optional)
- `suggested_location` (optional)

**Gate:** If `plan` field present → stop and report "This item already has a plan at {path}."

---

### 2.2 Consumer: `complete-implementation` Skill (Step 2 & 4 — Follow-up Routing)

**File:** `plugins/python3-development/skills/complete-implementation/SKILL.md`

**Matching Entry Points:**
1. **Step 2 — Search Backlog by Title Keywords** (when follow-up files are detected)
2. **Step 4 — Recursion Gate** (decision: recurse vs defer to backlog)

#### Step 2: Derive Search Title from Filename

Algorithm for extracting keywords from filename:

```
Input filename: plan/tasks-8-data-validation-followup-1.md
├─ Extract feature slug: "data-validation" (strip "tasks-8-" and "-followup-1.md")
├─ Strip feature slug from end: "data-validation"
├─ Replace hyphens with spaces: "data validation"
└─ Output search keywords: "data validation"

Call: mcp__backlog__backlog_list()
Parse JSON response: search `title` field of each item
Match criterion: case-insensitive substring match (derived keywords appear in title)
```

**Outcomes:**

| Result | Action |
|--------|--------|
| **Match found** | Attach follow-up as plan to existing backlog item: `mcp__backlog__backlog_update(selector="{matched_item_title}", plan="{followup_file_path}")` |
| **No match found** | Create new backlog item: `Skill(skill: "create-backlog-item", args: "--auto {derived_title}")`, then attach plan via `mcp__backlog__backlog_update(selector="{derived_title}", plan="{followup_file_path}")` |

**Error Handling:**
- If `create-backlog-item --auto` logs `[AUTO] STOP -- duplicate detected`: treat as match found, run update with duplicate's title
- If filename doesn't match pattern `tasks-{N}-{slug}-followup-{k}.md`: use full filename as derived title

#### Step 4: Recursion Gate (Conditions for Immediate Follow-up Execution)

TWO conditions must BOTH be true to recurse immediately. If EITHER fails → defer to backlog.

```
Condition 1: Same session scope (ADR-3)
├─ Extract slug from parent: strip "tasks-{N}-" and ".md" from parent filename
├─ Extract slug from follow-up: strip "tasks-{N}-" and "-followup-{k}.md" from follow-up filename
└─ Match criterion: exact string equality

Condition 2: High priority (ADR-2)
├─ Read follow-up file content
├─ Extract ## Priority section
├─ Valid values: "High" (recurse), "Medium" or "Low" (defer)
└─ Default if missing: "Medium" (defer) with warning log
```

**Routing Decision:**

```
if (condition_1 AND condition_2):
    Skill(skill="implement-feature", args="{followup_task_file_path}")
    Then re-run complete-implementation on follow-up
else:
    Log: "Follow-up deferred — to resume: /work-backlog-item <title>"
    Don't recurse; track in backlog
```

#### Step Final: Commit Message Issue Linking

Before committing, search backlog for the current feature slug:

```
mcp__backlog__backlog_list(title="{slug}")
└─ Extract `issue` field from matching item
└─ If present and commit resolves that issue: append "Fixes #NNN" to commit message body
```

---

## 3. MCP Tool: `backlog_list`

**File:** `.claude/skills/backlog/backlog_core/server.py` (registration)

### Function Signature

```python
async def backlog_list(
    with_status: bool = False,
    from_github: bool = False,
    label: str | None = None,
    section: str | None = None,
    status: str | None = None,
    title: str | None = None,
    include_closed: bool = False
) -> dict
```

### Parameters

| Parameter | Type | Purpose | Valid Values |
|-----------|------|---------|--------------|
| `with_status` | bool | Include GitHub issue status field in response | `true`, `false` |
| `from_github` | bool | Refresh local cache from GitHub Issues before listing | `true`, `false` |
| `label` | str | Filter by GitHub label | e.g., `"priority:p1"`, `"type:bug"` |
| `section` | str | Filter by priority section | `"P0"`, `"P1"`, `"P2"`, `"Ideas"` (case-insensitive) |
| `status` | str | Filter by status value | e.g., `"needs-grooming"`, `"status:in-progress"` |
| `title` | str | Filter by title substring (case-insensitive) | Any substring; matching is substring-based |
| `include_closed` | bool | Include items with terminal status | `true`, `false` |

### Return Shape

```json
{
  "items": [
    {
      "title": "string — full item title",
      "priority": "P0|P1|P2|Ideas",
      "section": "P0|P1|P2|Ideas",
      "issue": "#N (optional, string with # prefix)",
      "plan": "relative/path/to/task-file.md (optional)",
      "groomed": "boolean",
      "file_path": "absolute/path/to/.claude/backlog/item.md",
      "status": "status string"
    },
    ...
  ],
  "count": "integer — total items in result"
}
```

### Filtering Logic

**Filters are applied with AND logic** — all specified filters must match for an item to be included.

| Filter | Matching Criterion | Notes |
|--------|-------------------|-------|
| `section` | `metadata.priority` matches section value | Case-insensitive comparison |
| `label` | GitHub issue label contains exact label string | Requires `from_github=true` or live sync |
| `status` | `metadata.status` value matches status parameter | Exact string match (e.g., `"needs-grooming"` matches only that status) |
| `title` | Case-insensitive substring match in item `name` field | Empty string matches all |
| `include_closed` | When `false` (default): excludes terminal statuses (done, resolved, closed) | Filtering applied automatically |

**No `type` filtering parameter:** The MCP tool does NOT have a `type` parameter. Note: the `create_backlog_item` tool has a `type_` parameter (the item type: Feature, Bug, Refactor, Docs, Chore), but `backlog_list` does not expose filtering by item type.

---

## 4. CLI Tool: `backlog.py list` Command

**File:** `.claude/skills/backlog/scripts/backlog.py`

### Command Signature

```bash
uv run .claude/skills/backlog/scripts/backlog.py list [OPTIONS]
```

### Options (CLI-Level Parameters)

Maps to MCP tool parameters. Supports the same filters as the MCP tool.

---

## 5. Helper Functions & Parsing

### `find_item()` Function

**File:** `.claude/skills/backlog/backlog_core/parsing.py`

**Purpose:** Locate a single backlog item by selector (title substring, issue number, or URL).

**Selector Types Supported:**
- Title substring (case-insensitive): `"Error Recovery"`
- GitHub issue number with hash: `"#42"`
- Bare issue number: `"42"`
- GitHub issue URL: `"https://github.com/Jamie-BitFlight/claude_skills/issues/42"`

**Algorithm:**
1. Identify selector type (hash prefix, numeric, or URL pattern)
2. If URL: extract issue number
3. Call `backlog_list()` with appropriate filters
4. Return matching item or error if zero/multiple matches

---

## 6. Test Coverage

**Directory:** `.claude/skills/backlog/tests/`

Key test modules exercising matching logic:

- `test_backlog_core_operations.py` — tests for `backlog_list()` function
- `test_backlog_core_server.py` — MCP tool registration and response validation
- `test_backlog_core_parsing.py` — parsing, matching, field extraction
- `test_scenarios.py` — end-to-end workflows (consumer usage patterns)
- `test_backlog_gh_first.py` — GitHub Issue-first loading path

---

## 7. Data Flow: CLI → MCP → Operations → Matching

```
┌─────────────────────────────────────────────────────────────────┐
│ Consumer Entry Points                                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│ work-backlog-item Step 1:        complete-implementation Step 2:│
│  - Query by title substring      - Query by derived keyword     │
│  - Single match (proceed)        - Match/no-match (route)       │
│  - Zero/multiple matches (ask)   - Decision for follow-up       │
└─────────────┬──────────────────────────┬───────────────────────┘
              │                          │
              ▼                          ▼
┌─────────────────────────────────────────────────────────────────┐
│ MCP Layer: backlog_list Tool                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│ Parameters: section, status, label, title, with_status, ...    │
│ Returns: JSON array of items matching all specified filters     │
│          + count                                                │
│                                                                  │
└─────────────┬──────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Operations Layer: backlog_core/operations.py                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│ Function: backlog_list(section=None, status=None, ...)         │
│                                                                  │
│ Filtering Logic:                                                │
│ 1. Read all per-item files from .claude/backlog/                │
│ 2. Parse YAML frontmatter for metadata                          │
│ 3. Apply filters (AND logic):                                   │
│    - IF section specified: filter by metadata.priority          │
│    - IF status specified: filter by metadata.status             │
│    - IF title specified: case-insensitive substring match       │
│    - IF include_closed=false: exclude terminal statuses         │
│ 4. Build JSON response with item fields                         │
│ 5. Return items array + count                                   │
│                                                                  │
└─────────────┬──────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Data Source: Per-Item Files (.claude/backlog/*.md)              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│ File naming: {priority}-{slug}.md                               │
│ e.g., p0-sam-integration.md, p1-auth-system.md                 │
│                                                                  │
│ Content:                                                         │
│  - YAML frontmatter (metadata)                                  │
│  - Body sections (description, acceptance criteria, groomed...) │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 8. Metadata Fields: Availability vs Exposure

### Fields Available in Per-Item File Frontmatter

```yaml
metadata:
  topic                 # AUTO-DERIVED: slug from title
  source                # REQUIRED: what triggered this item
  added                 # REQUIRED: creation date (YYYY-MM-DD)
  priority              # REQUIRED: P0|P1|P2|Ideas
  type                  # REQUIRED: Feature|Bug|Refactor|Docs|Chore
  status                # REQUIRED: state machine field
  groomed               # OPTIONAL: YYYY-MM-DD when set
  issue                 # OPTIONAL: GitHub issue number (#N string)
  milestone             # OPTIONAL: GitHub milestone number (int)
  plan                  # OPTIONAL: path to SAM task file
```

### Fields Exposed by `backlog_list` MCP Tool

```json
{
  "title": "from frontmatter name field",
  "priority": "from metadata.priority",
  "section": "from metadata.priority (same as priority)",
  "issue": "from metadata.issue (optional)",
  "plan": "from metadata.plan (optional)",
  "groomed": "boolean derived from presence of groomed date",
  "file_path": "absolute path to per-item file",
  "status": "from metadata.status"
}
```

### Fields NOT Exposed by `backlog_list`

These require reading the per-item file directly:

- `metadata.topic` (slug)
- `metadata.source` (origin)
- `metadata.added` (creation date)
- `metadata.type` (Feature, Bug, Refactor, Docs, Chore)
- Body sections (description, acceptance criteria, research first, suggested location, fact-check, RT-ICA, groomed content)

**Rationale:** MCP tool returns summary metadata for quick filtering and decision-making. Detailed content is in the per-item file, read on-demand by consumers.

---

## 9. Matching Implementation Summary

### Matching Patterns Across Codebase

| Location | Matching Method | Criterion | Input | Output |
|----------|-----------------|-----------|-------|--------|
| `work-backlog-item` Step 1 | `backlog_list(title=...)` + substring match | Case-insensitive substring in title | title substring | Item or zero/multiple matches |
| `work-backlog-item` Step 2 | Direct field access from JSON response | Extract fields from MCP JSON | MCP response | Item fields (title, plan, issue, groomed, file_path, section) |
| `complete-implementation` Step 2 | `backlog_list()` + substring match | Case-insensitive substring in title | Derived keywords from filename | Item or no match |
| `complete-implementation` Final | `backlog_list(title=...)` | Substring match on slug | feature slug | Item to extract issue number |
| CLI: `backlog.py list` | `backlog_list()` with filter params | AND logic: all specified filters must match | CLI arguments | JSON response |

### No Type Filtering in MCP Tool

**Important:** The MCP `backlog_list` tool does NOT have a `type` parameter for filtering by item type (Feature/Bug/Refactor/Docs/Chore). The metadata field `metadata.type` exists but is not exposed as a filter parameter. Filtering by item type would require:
1. Reading the per-item file directly, OR
2. Adding a `type` parameter to the MCP tool (currently not present)

---

## 10. Special Cases & Constraints

### Issue-First Path (`work-backlog-item` Step 1b)

When invoked with `#N`, bare number, or GitHub URL:
- Skip title-based matching entirely
- Fetch from GitHub Issue directly using `mcp__backlog__backlog_view` tool (different tool)
- Assemble working item from GitHub issue + optional per-item file data
- No substring matching; exact issue number match

### AUTO_MODE Auto-Select Behavior

When `--auto` invoked with NO title:
- Call `backlog_list()` with NO title filter (gets all items)
- Scan P0 section for first item with open status
- If none found, scan P1 section
- Pick first found; log selection
- Skip items already marked done/resolved/closed

### Groomed Status

`backlog_list` returns `groomed: boolean` derived from presence of `metadata.groomed` date. An item is groomed only if ALL 7 body sections exist (Fact-Check, RT-ICA, Reproducibility, Dependencies, Skills, Agents, Prior Work).

### Status Machine Values

From `metadata.status` field (governed by state machine — see `references/state-machine.md`):

Valid transitions:
- `needs-grooming` → `groomed` (via groom-backlog-item)
- `groomed` → `in-milestone` (via group-items-to-milestone)
- `in-milestone` → `in-progress` (via work-backlog-item)
- `in-progress` → `done` (via work-backlog-item complete)
- `done` → `resolved` (via work-backlog-item resolve)
- `done`, `resolved` → `closed` (via complete-milestone)

Terminal statuses (filtered out by default): `done`, `resolved`, `closed`

---

## 11. Filename Patterns & Directory Structure

### Per-Item File Naming

```
.claude/backlog/{priority}-{slug}.md

Priority prefix:  p0- | p1- | p2- | idea-
Slug:             kebab-case, derived from item title, max 60 chars
Example:          p0-sam-integration.md
                  p1-error-recovery-system.md
                  p2-optimize-parsing.md
                  idea-experimental-caching.md
```

### Follow-up File Naming

```
plan/tasks-{N}-{slug}-followup-{k}.md

N:                parent plan number (integer)
slug:             matches parent task file's slug
k:                follow-up number (1, 2, 3, ...)
Example:          plan/tasks-8-data-validation-followup-1.md
```

---

## 12. Known Limitations & Gaps

1. **No item type filtering:** `backlog_list` MCP tool does not expose a `type` filter parameter. Filtering by Feature/Bug/Refactor/Docs/Chore requires reading per-item files.

2. **No full-text search:** Matching is limited to substring match on title and priority/status/label filtering. Body content (description, acceptance criteria, etc.) is not searchable via MCP.

3. **GitHub sync direction:** Primary source of truth is GitHub Issues; local per-item files are cache. When data drifts, per-item frontmatter is canonical (used by SAM workflow), but GitHub is the published view.

4. **Milestone dual location:** Milestone membership is recorded in two locations (per-item `metadata.milestone` + GitHub Issue milestone field). Must be kept in sync by `group-items-to-milestone` skill.

5. **Script gaps noted in documentation:**
   - `backlog.py` does not yet have `--acceptance-criteria` flag (written directly to file by skills)
   - `backlog.py` does not yet have `--suggested-location` flag

---

## 13. References

- Item Schema: `.claude/skills/backlog/references/item-schema.md`
- State Machine: `.claude/skills/backlog/references/state-machine.md`
- Known Patterns: `.claude/skills/backlog/references/known-patterns.md`
- Consumer: `.claude/skills/work-backlog-item/SKILL.md` (Steps 0-9)
- Consumer: `plugins/python3-development/skills/complete-implementation/SKILL.md` (Follow-up Routing, Recursion Gate)
- CLI Source: `.claude/skills/backlog/scripts/backlog.py`
- MCP Server: `.claude/skills/backlog/backlog_core/server.py`
- Operations: `.claude/skills/backlog/backlog_core/operations.py`
- Parsing: `.claude/skills/backlog/backlog_core/parsing.py`
