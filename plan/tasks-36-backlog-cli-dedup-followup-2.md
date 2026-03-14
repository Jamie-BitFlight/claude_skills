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

## Context Manifest

### Discovered During Implementation

_Session Date: 2026-03-14_

During implementation, we discovered several concrete facts about the `BacklogItem` model and the adapter pair that were not documented in the original task description. The fix was applied exactly as specified, but the implementation surfaced structural details that matter for future work on this adapter.

**Key Discoveries:**

1. **`BacklogItem.status` is a plain `str`, not an enum**: The field is declared as `str = ""` (empty string default). There is no `StatusEnum` or equivalent. This means the conditional guard `if item.status:` correctly treats an empty string as falsy — an item with no status set produces no `_status` key in the display dict, exactly matching the behavior of `_groomed` and `_last_synced`.

2. **Round-trip symmetry is preserved via `d.get("_status", "")`**: The inverse function `_dict_to_backlog_item_fields` at line 186 uses `d.get("_status", "")`. When `_status` is absent (empty-status item), the get returns `""`, which matches `BacklogItem`'s default. When `_status` is present (non-empty status), it round-trips correctly. The conditional write and the defaulted read form a symmetric pair.

3. **Zero prior test coverage for either adapter function**: Before this change, neither `backlog_item_to_display_dict` nor `_dict_to_backlog_item_fields` had any tests. The 12-case round-trip test added here is the first test for these functions. This gap was not flagged in the original task description.

4. **Line 1751 TODO referencing #612**: A pre-existing TODO comment in `backlog.py` references issue #612. It is unrelated to this change and was not addressed. It is noted here to prevent future confusion about whether it was intentionally left.

#### Updated Technical Details

- `backlog_item_to_display_dict` now outputs `_status` key only when `item.status` is truthy (non-empty string), at lines 228-229
- `_dict_to_backlog_item_fields` reads `_status` via `d.get("_status", "")` at line 186 — absent key returns empty string, matching the model default
- Test file: `.claude/skills/backlog/tests/test_backlog_display_dict_roundtrip.py` (12 cases, all passing)
- Total test suite: 594 tests pass, linting clean

#### Gotchas for Future Developers

- The conditional write pattern (`if item.X: d["_X"] = item.X`) is used for `_groomed`, `_last_synced`, and now `_status`. Any new optional string fields added to `BacklogItem` should follow this same pattern to maintain adapter symmetry.
- Both adapter functions are in `backlog.py` (the CLI layer), not in `backlog_core/`. The docstring on `backlog_item_to_display_dict` explicitly marks this adapter as temporary per architecture spec Section 5.6. Any significant extension of this adapter should be evaluated against the migration plan in that spec section.
