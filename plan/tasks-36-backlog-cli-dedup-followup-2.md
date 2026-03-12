---
tasks:
  - task: "Fix missing _status key in backlog_item_to_display_dict adapter (latent data loss in round-trip conversion)"
    status: pending
    parent_task: "plan/tasks-1-backlog-cli-dedup.md"
---

# Task: Fix Missing _status Key in Display Dict Adapter

## Parent Task
- Original: `plan/tasks-1-backlog-cli-dedup.md`
- Review Date: 2026-03-12

## Status
- [ ] Pending

## Priority
Low

## Description

The `backlog_item_to_display_dict` function (line 185) converts a `BacklogItem` to the dict format used by CLI display/mutation code. The inverse function `_dict_to_backlog_item_fields` (line 151) converts a dict back to `BacklogItem` field kwargs.

There is a field asymmetry: `_dict_to_backlog_item_fields` reads `d.get("_status", "")` (line 181) to populate the `status` field, but `backlog_item_to_display_dict` never sets `_status` in the output dict. This means any round-trip through `BacklogItem -> display dict -> BacklogItem` silently drops the `status` field.

Currently no code path performs this exact round-trip on the status field, so this is latent rather than active. However, it violates the silent failure prevention rule: the adapter pair should be symmetric.

**Fix**: Add `"_status": item.status` to `backlog_item_to_display_dict` output dict, alongside the existing `_skip`, `_groomed`, `_last_synced` fields.

## Acceptance Criteria
- [ ] `backlog_item_to_display_dict` includes `"_status": item.status` in returned dict
- [ ] Round-trip test: `BacklogItem(status="open")` -> `backlog_item_to_display_dict` -> `_dict_to_backlog_item_fields` -> `BacklogItem.model_validate` preserves `status="open"`
- [ ] All existing tests continue to pass

## Files to Modify
- `.claude/skills/backlog/scripts/backlog.py:202-223` -- Add `"_status": item.status` to the dict in `backlog_item_to_display_dict`

## Verification Steps
1. `uv run pytest .claude/skills/backlog/tests/ -x -q` -- all tests pass
2. Manual verification: `uv run python -c "..."` testing round-trip preserves status field

## References
- Original review: code-reviewer phase of `/complete-implementation`
- Silent failure prevention rule: `.claude/rules/silent-failure-prevention.md`
- Related code: `.claude/skills/backlog/scripts/backlog.py` lines 151-223
