---
name: 'backlog: add status field to BacklogItem model'
description: <div><sub>2026-03-12T02:09:48Z</sub>
metadata:
  topic: backlog-add-status-field-to-backlogitem-model
  source: Code review 2026-03-11
  added: '2026-03-11'
  priority: completed
  type: Refactor
  status: done
  issue: '#612'
  last_synced: '2026-03-14T01:26:48Z'
  groomed: '2026-03-12'
  plan: plan/tasks-1-add-status-field-to-backlogitem-model.md
---

## Groomed (2026-03-12)

### Groomed

<div><sub>2026-03-12T02:09:48Z</sub>

### Priority

6/10 — Eliminates a redundant disk read on every `backlog view` call. Low risk, well-scoped, directly improves model correctness and code hygiene. Blocked by nothing.

### Impact

- Bottleneck: every call to `view_result_from_local_item()` re-opens and re-parses the per-item file solely to extract the `status:` frontmatter field, even though the file was already parsed into a `BacklogItem` by `parse_item_file()` moments earlier.
- Blocks: any future caller that constructs a `BacklogItem` and needs status without going through `view_result_from_local_item()` is forced to either call the view helper or re-read the file.

### Benefits

- Removes one redundant file read per `backlog view` invocation.
- Makes `BacklogItem` a complete model of the on-disk item — callers do not need a second source to get status.
- Enables future tools (list filters, batch status checks) to read status from the already-parsed model rather than issuing additional I/O.
- Consistent with how `IssueStatus`, `ViewItemResult`, and `IssueLocalFields` all carry their own `status` field.

### Expected Behavior

When a per-item file is parsed, the resulting `BacklogItem` carries the `status` value from the frontmatter `status:` field (e.g. `"in-progress"`, `"needs-grooming"`, `""`). Callers that previously called `view_result_from_local_item()` only to obtain status can instead read `item.status` directly. The `view_result_from_local_item()` function continues to work correctly and populates `ViewItemResult.status` from `BacklogItem.status` rather than re-reading the file.

### Desired Structure

- `BacklogItem` at `.claude/skills/backlog/backlog_core/models.py:140` gains `status: str = ""`.
- `parse_item_file()` in `.claude/skills/backlog/backlog_core/parsing.py` populates `item.status` from the frontmatter `status:` field alongside the other frontmatter fields it already reads.
- `view_result_from_local_item()` reads `item.status` from the passed `BacklogItem` instead of re-reading the file from disk.
- No other callers require changes unless they were also bypassing the model to read status directly from disk.

### Acceptance Criteria

1. `BacklogItem` has a `status: str = ""` field — confirm with `grep 'status' .claude/skills/backlog/backlog_core/models.py`.
2. Running `uv run .claude/skills/backlog/scripts/backlog.py view <any-item-with-status>` returns the correct status value without a second file open after `parse_item_file()` completes.
3. Existing tests in the backlog test suite pass without modification — confirm with `uv run pytest .claude/skills/backlog/ -q`.
4. `view_result_from_local_item()` no longer calls `open()` / re-reads the file inside its body — confirm by reading the function after the change.
5. Items without a `status:` frontmatter key produce `BacklogItem.status == ""` (default) — no KeyError or AttributeError.

### Resources

| Type | Item |
|------|------|
| Prior work | `.claude/skills/backlog/backlog_core/models.py` — `BacklogItem` class at line 140; `IssueStatus`, `ViewItemResult`, `IssueLocalFields` show the `status: str = ""` pattern to follow |
| Prior work | `.claude/skills/backlog/backlog_core/parsing.py` — `parse_item_file()` and `view_result_from_local_item()` are the two functions to modify |
| Prior work | `.claude/skills/backlog/backlog_core/ARCHITECTURE.md` — documents the refactor history and function rename map |

### Dependencies

- Depends on: None
- Blocks: None directly; contributes to the broader BacklogItem completeness work noted in #611 (backlog CLI deduplication)

### Effort

Small — single field addition to a Pydantic model, one assignment in `parse_item_file()`, one read substitution in `view_result_from_local_item()`. All changes are in two files. No schema migration needed; `status` defaults to `""`.
</div>

### Issue Classification

<div><sub>2026-03-12T02:10:24Z</sub>

Type: procedural
Scenario-target: Add missing field to data model, populate during parsing, remove redundant file read.
Analysis method: none (straightforward field addition)
</div>


## Fact-Check

<div><sub>2026-03-12T02:10:18Z</sub>

Claims checked: 2
VERIFIED: 2 | REFUTED: 0 | INCONCLUSIVE: 0

1. "BacklogItem model lacks a status field" — VERIFIED via `grep` of models.py:140. BacklogItem has 15 fields; none is `status`.
2. "view_result_from_local_item() must re-read the file from disk to extract status" — VERIFIED via groomer agent research of parsing.py.
</div>

## RT-ICA

<div><sub>2026-03-12T02:10:21Z</sub>

Goal: Eliminate redundant file re-read in view_result_from_local_item() by adding status to BacklogItem.
Conditions:
1. BacklogItem model location | AVAILABLE | models.py:140
2. parse_item_file() location | AVAILABLE | parsing.py
3. view_result_from_local_item() location | AVAILABLE | parsing.py
4. Status extraction pattern | AVAILABLE | frontmatter metadata.status
Decision: APPROVED
Missing: None
</div>