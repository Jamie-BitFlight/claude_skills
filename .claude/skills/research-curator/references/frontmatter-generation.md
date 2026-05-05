# Frontmatter Generation

Canonical YAML frontmatter schema for all research entries, extraction rules from every observed existing format, and the procedure for generating or backfilling frontmatter on any entry.

---

## Canonical Schema

Every research entry file must begin with this YAML frontmatter block:

```yaml
---
title: "{Resource Name}"
subtitle: "{One-phrase description of what it is}"
category: "{directory-name}"
resource_url: "{primary homepage or source URL}"
github_url: "{GitHub repository URL}"
date_created: "YYYY-MM-DD"
date_last_reviewed: "YYYY-MM-DD"
status: "published"
---
```

Field rules:

- `title`: Official name of the resource, no version suffix
- `subtitle`: One short phrase — what the resource *is*, not what it *does*. 5–10 words max.
- `category`: The parent directory name as-is (e.g., `agent-frameworks`, `mcp-ecosystem`)
- `resource_url`: The primary URL listed in the entry — homepage preferred, GitHub if no homepage
- `github_url`: GitHub repository URL. Omit field entirely when absent from the entry.
- `date_created`: Date the research entry was first written
- `date_last_reviewed`: Date of the most recent content verification
- `status`: Always `published` for completed entries

---

## Format Detection

Before extracting fields, detect which of the four formats the entry uses:

```mermaid
flowchart TD
    Read["Read first 30 lines of entry file"] --> Q1{"File starts with '---'?"}
    Q1 -->|"No"| FormatA["Format A — No frontmatter<br>Pure Markdown heading body"]
    Q1 -->|"Yes"| Q2{"Frontmatter contains 'title:' key?"}
    Q2 -->|"Yes"| Q3{"Frontmatter contains 'resource_url:' or 'date_created:' keys?"}
    Q3 -->|"Yes"| FormatD["Format D — Full canonical<br>esp-claw / Trellis style"]
    Q3 -->|"No"| FormatB["Format B — Minimal<br>Trellis-minimal style (title + resource_url + created)"]
    Q2 -->|"No"| Q4{"Frontmatter contains 'name:' key?"}
    Q4 -->|"Yes"| FormatC["Format C — Agno-style<br>name + metadata nested block"]
    Q4 -->|"No"| FormatB
```

---

## Field Extraction by Format

### Format A — No frontmatter (Markdown heading body)

| Target field | Extraction source |
|---|---|
| `title` | Content of first `# {Title}` heading — strip leading `# ` |
| `subtitle` | First sentence of `## Overview` section body (up to first period) |
| `category` | Parent directory name from file path |
| `resource_url` | `**Source URL**: <url>` body pattern — extract URL from angle brackets or bare value |
| `github_url` | `**GitHub Repository**: <url>` pattern — extract URL; omit if absent |
| `date_created` | `**Research Date**: YYYY-MM-DD` pattern in header block; fallback: git log first-commit date |
| `date_last_reviewed` | `Last Verified \| YYYY-MM-DD` row in Freshness Tracking table; fallback: same as `date_created` |
| `status` | Always `published` |

### Format B — Minimal frontmatter (Trellis style)

| Target field | Source key(s) |
|---|---|
| `title` | `title:` |
| `subtitle` | `title:` value after em-dash if present; otherwise first sentence of `## Overview` |
| `category` | `category:` key; fallback: parent directory name |
| `resource_url` | `resource_url:` |
| `github_url` | Infer from `resource_url:` if it is a `github.com` URL; otherwise look for `**Repository**: <url>` in body; omit if absent |
| `date_created` | `created:` |
| `date_last_reviewed` | `last_reviewed:` |
| `status` | `status:` key if present; default `published` |

### Format C — Agno nested metadata

| Target field | Source key path |
|---|---|
| `title` | `name:` top-level key |
| `subtitle` | `description:` — truncate at first period or 80 chars, whichever is shorter |
| `category` | `metadata.category:` key; fallback: parent directory name |
| `resource_url` | `metadata.source_url:` |
| `github_url` | `metadata.github:` — prefix with `https://github.com/` if value has no scheme |
| `date_created` | `metadata.verified:` (earliest available proxy) |
| `date_last_reviewed` | `metadata.verified:` |
| `status` | Always `published` |

### Format D — Full canonical (already has matching fields)

Reuse existing values. Normalize field names if needed (e.g., `created:` → `date_created:`). Do not regenerate fields that are already correct.

---

## Generation Procedure

Apply to a single entry file — use this whether creating frontmatter for a new entry or updating an existing one.

```mermaid
flowchart TD
    Start(["Entry file path known"]) --> Detect["Detect format — follow Format Detection diagram"]
    Detect --> Extract["Extract all target fields using format-specific rules"]
    Extract --> Validate{"Any required field empty<br>after extraction?"}
    Validate -->|"Yes — field could not be extracted"| Fill["Fill missing field:<br>title/subtitle: read ## Overview and derive<br>resource_url: search body for any URL near resource name<br>dates: use git log --follow --diff-filter=A --format='%as' -- {path} | tail -1<br>category: use parent directory name"]
    Validate -->|"No — all fields resolved"| HasFrontmatter{"Does file already<br>have YAML frontmatter?"}
    Fill --> HasFrontmatter
    HasFrontmatter -->|"No — Format A"| Prepend["Prepend frontmatter block to file<br>Write '---\\n{fields}\\n---\\n' before existing content"]
    HasFrontmatter -->|"Yes — Formats B/C/D"| Replace["Replace existing frontmatter block<br>Write canonical fields in place of old block<br>Preserve all body content unchanged"]
    Prepend --> Verify["Read first 10 lines of modified file<br>Confirm '---' delimiters present and field count matches"]
    Replace --> Verify
    Verify --> Done(["Frontmatter written"])
```

### Writing the frontmatter block

Write only fields that have non-empty values. Always include `title`, `category`, `resource_url`, `date_created`, `date_last_reviewed`, `status`. Include `subtitle` when extractable. Omit `github_url` when absent — do not write `github_url: ""`.

---

## Standalone Backfill Procedure (`--add-frontmatter`)

Use when the SKILL.md `--add-frontmatter` mode is invoked. Targets one entry or all entries in the vault.

```mermaid
flowchart TD
    Start(["--add-frontmatter argument parsed"]) --> Q{"Argument value?"}
    Q -->|"category/name — single entry"| VerifyFile{"Does ./research/category/name.md exist?"}
    Q -->|"all — every entry"| GlobAll["Glob ./research/**/*.md<br>Exclude README.md and ./research/insights/**"]
    VerifyFile -->|"No"| Error(["Report: entry not found. Stop."])
    VerifyFile -->|"Yes"| Single["Apply Generation Procedure to single file"]
    Single --> CommitSingle(["Commit: 'docs(research): add frontmatter to category/name'"])
    GlobAll --> Filter["Filter out entries that already have Format D canonical frontmatter<br>(all 8 target fields present and non-empty)"]
    Filter --> Count["Report: N entries need frontmatter, M already complete"]
    Count --> Wave["Process in waves of 10:<br>Apply Generation Procedure to each file<br>Collect paths of modified files"]
    Wave --> WaveDone{"All entries processed?"}
    WaveDone -->|"No — more entries"| Wave
    WaveDone -->|"Yes"| CommitAll["Commit all modified files:<br>'docs(research): backfill frontmatter on N entries'"]
    CommitAll --> Report(["Report: N updated, M skipped (already canonical), K failed (list paths)"])
```

### Skipping logic

Skip an entry during `--all` backfill if its frontmatter already contains all of these fields with non-empty values: `title`, `category`, `resource_url`, `date_created`, `date_last_reviewed`, `status`. Partial frontmatter (missing any field) is not skipped — it is upgraded to canonical.

---

## Integration Points

- **Default mode**: After `@research-curator` agent returns the new entry path, apply the Generation Procedure to that file before spawning the four concurrent post-creation tasks.
- **Rerun mode**: After `@research-curator` agent updates an existing entry, apply the Generation Procedure to refresh `date_last_reviewed` and ensure canonical format.
- **Standalone**: `--add-frontmatter category/name` or `--add-frontmatter all` follows the Standalone Backfill Procedure above.
