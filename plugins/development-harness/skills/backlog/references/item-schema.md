# Backlog Item Schema

Canonical schema for per-item files at `~/.dh/projects/{slug}/backlog/{priority}-{slug}.md`.
All skills that read or write item files MUST conform to this schema.

SOURCE: Derived from comparative analysis of GSD repo patterns and claude_skills backlog skill implementations (accessed 2026-02-26).

---

## Frontmatter Fields

```yaml
---
name: string          # REQUIRED — full item title (matches GitHub issue title)
description: string   # REQUIRED — one-sentence summary of the problem or goal
metadata:
  topic: string       # REQUIRED — slug derived from title (kebab-case, max 60 chars)
  source: string      # REQUIRED — what triggered this item
  added: YYYY-MM-DD   # REQUIRED — date item was created
  priority: P0|P1|P2|Ideas   # REQUIRED — priority tier
  type: Feature|Bug|Refactor|Docs|Chore   # REQUIRED
  status: needs-grooming|groomed|blocked|in-milestone|in-progress|done|resolved|closed   # REQUIRED
  groomed: YYYY-MM-DD     # optional — set by groom-backlog-item when all required sections present (defined in finalize.md)
  issue: '#N'             # optional — GitHub issue number (string with # prefix)
  milestone: integer      # optional — GitHub milestone number
  plan: string            # optional — relative path to SAM task file
---
```

### Field Ownership

| Field | Written by | Notes |
|---|---|---|
| `name` | create-backlog-item | Set at creation |
| `description` | create-backlog-item | Set at creation |
| `metadata.topic` | backlog script | Auto-derived from title |
| `metadata.source` | create-backlog-item | Set at creation |
| `metadata.added` | backlog script | Set at creation |
| `metadata.priority` | create-backlog-item | Set at creation |
| `metadata.type` | create-backlog-item | Set at creation |
| `metadata.status` | all skills | Updated on state transitions (see state-machine.md) |
| `metadata.groomed` | groom-backlog-item | Set when all required sections present (defined in finalize.md) |
| `metadata.issue` | backlog script | Set on GitHub issue creation |
| `metadata.milestone` | group-items-to-milestone | Set on milestone assignment |
| `metadata.plan` | work-backlog-item | Set when SAM task file created |

---

## Body Sections — Canonical Order

Sections appear in this order. All sections after Description are populated incrementally by downstream skills — they do not exist in newly created items.

```
1.  Description                        (written by: create-backlog-item — body prose)
2.  Acceptance Criteria                (written by: create-backlog-item — bullet list)
3.  Research First                     (written by: create-backlog-item — optional)
4.  Suggested Location                 (written by: create-backlog-item — optional)
5.  Fact-Check                         (written by: groom-backlog-item Step 4)
6.  RT-ICA                             (written by: groom-backlog-item Step 5 — MUST be written before groomer agent)
7.  Groomed                            (written by: backlog-item-groomer agent — contains subsections)
    7a. Reproducibility
    7b. Priority
    7c. Impact
    7d. Scope
    7e. Output / Evidence
    7f. Dependencies
    7g. Research
    7h. Skills
    7i. Agents
    7j. Prior Work
    7k. Files
    7l. Decision
8.  Acceptance Criteria Verification   (written by: work-backlog-item close — per-criterion PASS/FAIL with file:line evidence)
```

### Section Details

**Description** — prose summary of the problem. Do not include "how to fix it" — describe the observed gap or need.

**Acceptance Criteria** — bullet list, each criterion must be a specific verifiable condition:

```markdown
**Acceptance Criteria**:
- Running `command X` produces `output Y`
- File `~/.dh/projects/{slug}/backlog/p1-{slug}.md` exists with correct frontmatter
- `backlog_view(selector="#N")` returns `state: "open"` in the dict
```

P0 items: at least one criterion required. Non-P0: optional but recommended.

**Script gap**: `backlog.py` does not yet have an `--acceptance-criteria` flag. Skills write this
section directly to the item file body. Script support is planned.

**Research First** — questions to answer before grooming can proceed. Surfaced to groomer agent.

```markdown
**Research first**: What patterns exist for X? How does Y handle Z?
```

**Suggested Location** — codebase location where implementation work lands:

```markdown
**Suggested location**: `plugins/plugin-creator/`
```

**Script gap**: `backlog.py` does not yet have a `--suggested-location` flag. Skills write this
field directly to the item file body. Script support is planned.

**Fact-Check** — verdict from fact-check skill. Written by groom-backlog-item Step 4:

```markdown
## Fact-Check

Claims checked: N
VERIFIED: N | REFUTED: N | INCONCLUSIVE: N
Refuted claims: [list]
Inconclusive claims: [list]
Citations: [list of sources]
```

**RT-ICA** — information completeness assessment. Written by groom-backlog-item Step 5b (before groomer agent):

```markdown
## RT-ICA

Goal: {one sentence}
Conditions:
1. {condition} | Status: AVAILABLE|DERIVABLE|MISSING | Info needed: {what}
...
Decision: APPROVED|BLOCKED
Missing: {list or "None"}
```

**Groomed** — output from backlog-item-groomer agent. Written after RT-ICA. Contains subsections in order listed above.

**Acceptance Criteria Verification** — written by `work-backlog-item close` after checking each criterion against the codebase. Contains per-criterion PASS/FAIL lines with file:line evidence. The `complete-milestone` pre-flight gate detects verified items by grepping for this section header.

```markdown
## Acceptance Criteria Verification

[PASS] Running `command X` produces `output Y` — verified at src/main.py:42
[FAIL] File `~/.dh/projects/{slug}/backlog/p1-{slug}.md` exists with correct frontmatter — file not found
[PASS] `backlog_view(selector="#N")` returns `state: "open"` — confirmed via MCP tool output

Overall: FAIL (2/3 criteria met)
```

---

## Item Completeness States

| State | Required fields | Required sections |
|---|---|---|
| Newly created | All frontmatter fields | Description, optionally AC + Research First + Suggested Location |
| Fact-checked | + | + Fact-Check section |
| RT-ICA assessed | + | + RT-ICA section |
| Fully groomed | `metadata.groomed` set | All required sections present (defined in finalize.md validation table) |
| In-milestone | `metadata.milestone` set, `metadata.status: in-milestone` | (same as fully groomed) |
| In-progress | `metadata.plan` set, `metadata.status: in-progress` | + plan file exists at path |
| Done | `metadata.status: done` | + Acceptance Criteria Verification section (all criteria PASS) |
| Closed | `metadata.status: closed` | Terminal — set by complete-milestone only |

An item is **fully groomed** only when ALL 8 of these sections are present in the item file (in this order):

1. `Fact-Check` — must contain V/R/I counts
2. `RT-ICA` — must contain `Decision: APPROVED` or `Decision: BLOCKED`
3. `Reproducibility`
4. `Dependencies`
5. `Skills` — content or explicit "None"
6. `Agents` — content or explicit "None"
7. `Prior Work`

`metadata.groomed` MUST NOT be set until all 8 are present. Partial grooming (e.g., only Fact-Check and RT-ICA written) is NOT considered groomed — groom-backlog-item resumes from the first missing section rather than restarting.

---

## Dual Milestone Location

Milestone membership is recorded in two locations that serve different purposes. Both MUST be kept in sync.

### 1. Per-item file frontmatter (machine-readable canonical)

```yaml
metadata:
  milestone: 5    # GitHub milestone number — integer
```

Written by `group-items-to-milestone` when item is assigned. Read by:
- `work-backlog-item` to determine which milestone an item belongs to
- `complete-milestone` to find all items in the milestone (via per-item file scan)

### 2. GitHub Issue milestone field (published view)

The GitHub Issue's milestone field is the published view. Written by `group-items-to-milestone` when assigning the item. Read by:
- `complete-milestone` straggler detection (queries GitHub API for milestone issues)
- Humans browsing GitHub Issues

### Sync rule

Both locations MUST be updated together. `group-items-to-milestone` is the only skill that writes milestone assignment — it writes both locations in the same operation. If they drift, the per-item frontmatter is canonical.

---

## Backlog Directory Structure

The backlog script reads per-item files from `~/.dh/projects/{slug}/backlog/`. Each file is named `{priority}-{slug}.md` (e.g., `p1-error-recovery.md`). The `work-backlog-item progress` subcommand scans this directory to produce situational awareness output.

SOURCE: claude_skills_backlog_management_systematic_improvements_list.md, Cross-Cutting Improvements section 5 (2026-02-26).
